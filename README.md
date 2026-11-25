# Transit DevOps Lab: GKE Autopilot + ArgoCD + Cloud Armor on GCP

Use case: **real-time vehicle positions API** (inspired by GTFS-Realtime), deployed with GitOps on GKE Autopilot in Montreal (`northamerica-northeast1`), protected by Cloud Armor, with event-driven ingestion through Pub/Sub, a Redis cache and PostgreSQL reference data.

## Architecture

```mermaid
flowchart TB
    users["Internet<br/>(riders, third-party apps)"]
    armor["Cloud Armor<br/>OWASP WAF · rate limit 429<br/>geo-filter (preview) · adaptive L7 DDoS"]
    lb["Static global IP<br/>Global L7 Load Balancer<br/>(GKE Gateway API)"]

    users --> lb
    armor -.-> lb

    subgraph vpc["VPC transit-lab-vpc"]
        subgraph gke["GKE Autopilot (private nodes)"]
            argocd["ns argocd: ArgoCD"]
            api["ns transit: vehicle-api<br/>(HPA 2-10, PDB, NetworkPolicy)<br/>KSA vehicle-api"]
        end
        subgraph psa["Private Service Access (private IPs)"]
            redis["Memorystore<br/>Redis (TTL)"]
            sql["Cloud SQL<br/>PostgreSQL 16 (private)"]
            pubsub["Pub/Sub<br/>vehicle-positions"]
        end
        nat["Cloud NAT"]
    end

    lb -- "NEG (direct to pods)" --> api
    api --> redis
    api --> sql
    api --> pubsub
    api --> nat
    api -- "Workload Identity" --> iam["IAM"]
    pubsub --> dlq["DLQ"] --> alert["Alert<br/>Cloud Monitoring"]

    secrets["Secret Manager<br/>(DB password, Canada replication)"]
    registry["Artifact Registry<br/>(immutable tags)"]

    subgraph github["GitHub"]
        repo["Git repository<br/>k8s/overlays/dev"]
        tf["terraform.yml<br/>fmt · validate · Checkov ·<br/>plan (PR comment) · apply (approval)"]
        app["app.yml<br/>.NET build · SonarQube · Trivy ·<br/>push · GitOps commit"]
    end

    github -- "OIDC (Workload Identity Federation, no keys)" --> gcp["GCP"]
    app -- "push image" --> registry
    app -- "GitOps commit" --> repo
    argocd -- "watches Git / sync" --> repo
```

> Note: Pub/Sub is a Google API, not a Private Service Access service. Pods reach it through **Private Google Access** on the GKE subnet. PSA only carries Redis and Cloud SQL.

## Interaction flows

Each diagram follows one type of user through the platform and names the component that handles each step.

### Flow 1: A rider or third-party app reads vehicle positions

```mermaid
sequenceDiagram
    autonumber
    actor C as Rider / third-party app
    participant LB as Global L7 LB<br/>(GKE Gateway, static IP)
    participant CA as Cloud Armor<br/>(transit-lab-edge-policy)
    participant NP as NetworkPolicy<br/>(Dataplane V2)
    participant API as vehicle-api pod<br/>(Autopilot, private node)
    participant R as Memorystore Redis<br/>(private IP via PSA)

    C->>LB: GET /api/v1/vehicles
    LB->>CA: Evaluate security policy
    alt OWASP WAF match (SQLi, XSS, LFI, RCE, scanner)
        CA-->>C: 403 Forbidden
    else Over rate limit per IP per minute
        CA-->>C: 429 Too Many Requests
    else Allowed (geo rule is preview only, logged)
        CA->>LB: allow
    end
    Note over LB: HTTPRoute matches the /api/ prefix<br/>NEG sends traffic straight to healthy pod IPs
    LB->>NP: TCP 8080 from 35.191.0.0/16 or 130.211.0.0/22
    NP->>API: allowed (everything else denied by default)
    API->>R: GET vehicles:snapshot
    alt Cache hit
        R-->>API: cached JSON
    else Cache miss
        R-->>API: nil
        API->>API: Build snapshot (simulated data)
        API->>R: SET vehicles:snapshot (TTL 10 s)
    end
    API-->>C: 200 application/json
```

Components: [network.tf](infra/network.tf) (static IP, VPC-native ranges), [gateway.yaml](k8s/base/gateway.yaml) (Gateway, HTTPRoute, GCPBackendPolicy, HealthCheckPolicy), [armor.tf](infra/armor.tf), [networkpolicy.yaml](k8s/base/networkpolicy.yaml), [deployment.yaml](k8s/base/deployment.yaml) (HPA 2-10, PDB), [data.tf](infra/data.tf) (Redis). The pod reads `REDIS_HOST` from the `transit-config` ConfigMap, which Terraform fills from the `infra` outputs ([platform/main.tf](platform/main.tf)).

### Flow 2: A vehicle or AVL feed publishes a position

```mermaid
sequenceDiagram
    autonumber
    actor V as Vehicle / AVL feed
    participant EDGE as LB + Cloud Armor<br/>+ NetworkPolicy
    participant API as vehicle-api pod<br/>(KSA transit/vehicle-api)
    participant IAM as Workload Identity<br/>(IAM)
    participant T as Pub/Sub topic<br/>vehicle-positions
    participant S as Subscription<br/>vehicle-positions-processor
    participant W as Consumer<br/>(not implemented yet)
    participant DLQ as vehicle-positions-dlq<br/>+ dlq-inspect subscription
    participant M as Cloud Monitoring

    V->>EDGE: POST /api/v1/vehicles/positions (JSON)
    EDGE->>API: Same edge checks as flow 1 (JSON body parsed by WAF)
    API->>IAM: KSA token exchange (no JSON key)
    IAM-->>API: Federated token with roles/pubsub.publisher
    API->>T: Publish (orderingKey = vehicleId, schema = vehicle-position.v1)
    T-->>API: messageId
    API-->>V: 202 Accepted {messageId}
    T->>S: Fan out (24 h topic retention)
    S->>W: Deliver in order per vehicle (ack deadline 20 s)
    alt Processed
        W-->>S: ack
    else Failure, retried with 5-60 s backoff
        S->>W: Redeliver (up to 5 attempts)
        S->>DLQ: Forward after 5 failed attempts
        DLQ->>M: num_undelivered_messages > 0 for 5 min
        M-->>M: Alert fires with runbook (inspect, fix, replay)
    end
```

Components: [Program.cs](app/Program.cs), [iam.tf](infra/iam.tf), [data.tf](infra/data.tf) (topic, subscriptions, DLQ), [monitoring.tf](infra/monitoring.tf).

> No workload consumes `vehicle-positions-processor` yet. In a running lab, unacknowledged messages are retried, land in the DLQ and fire the alert.

### Flow 3: An application developer ships code (CI, then GitOps CD)

```mermaid
sequenceDiagram
    autonumber
    actor D as Developer
    participant GH as GitHub<br/>(repo + app.yml)
    participant WIF as Workload Identity<br/>Federation (OIDC)
    participant AR as Artifact Registry<br/>(immutable tags)
    participant ARGO as ArgoCD<br/>(ns argocd)
    participant K as GKE Autopilot<br/>(ns transit)

    D->>GH: Pull request touching app/**
    GH->>GH: dotnet build, dotnet format check
    GH->>GH: SonarQube quality gate (if SONAR_TOKEN is set)
    GH->>GH: docker build vehicle-api:SHA
    GH->>GH: Trivy scan, fails on fixable HIGH or CRITICAL
    Note over GH: On a PR, the workflow stops here (no push)
    D->>GH: Merge to main
    GH->>GH: Same build, scan and quality steps
    GH->>WIF: GitHub OIDC token (this repository only)
    WIF-->>GH: Impersonate gh-ci-sa (artifactregistry.writer)
    GH->>AR: docker push vehicle-api:SHA
    GH->>GH: kustomize edit set image in k8s/overlays/dev
    GH->>GH: Commit and push "deploy(dev): vehicle-api SHA"
    loop Every 60 s
        ARGO->>GH: Poll k8s/overlays/dev
    end
    ARGO->>K: Sync (server-side apply, prune, selfHeal)
    K->>AR: Nodes pull image (node SA has artifactregistry.reader)
    K->>K: Rolling update (maxSurge 1, maxUnavailable 0, readiness /healthz)
    Note over D,K: Rollback: git revert the deploy commit and ArgoCD redeploys the previous tag.<br/>Manual drift (for example kubectl scale) is reverted by selfHeal.
```

Components: [app.yml](.github/workflows/app.yml), [Dockerfile](app/Dockerfile), [bootstrap/main.tf](bootstrap/main.tf) (WIF, `gh-ci-sa`), [registry.tf](infra/registry.tf), [platform/main.tf](platform/main.tf) (ArgoCD Application), [k8s/overlays/dev](k8s/overlays/dev/kustomization.yaml).

### Flow 4: A platform engineer changes infrastructure (Terraform)

```mermaid
sequenceDiagram
    autonumber
    actor P as Platform engineer
    participant GH as GitHub<br/>(terraform.yml)
    participant WIF as Workload Identity<br/>Federation (OIDC)
    participant GCS as GCS state bucket<br/>(versioned, native lock)
    actor A as Approver<br/>(dev environment)
    participant GCP as GCP APIs
    participant K as GKE cluster

    P->>GH: Pull request touching infra/** or platform/**
    GH->>WIF: OIDC token
    WIF-->>GH: Impersonate gh-terraform-sa
    GH->>GH: fmt, init, validate, Checkov (soft fail)
    GH->>GCS: Read infra state, then plan
    GH-->>P: Plan posted as a PR comment
    P->>GH: Merge to main
    Note over GH: concurrency terraform-dev runs one pipeline at a time
    GH->>GCS: infra plan, saved as a workflow artifact
    GH->>A: Waiting for approval
    A-->>GH: Approve
    GH->>GCP: terraform apply tfplan (the exact approved plan)
    GH->>GCS: Write infra state
    GH->>GCS: platform plan reads infra outputs (terraform_remote_state)
    GH->>A: Waiting for approval
    A-->>GH: Approve
    GH->>K: Apply namespace, transit-config ConfigMap, ArgoCD, Application
    GH->>GCS: Write platform state
    Note over K: Pods pick up new endpoints (Redis, Pub/Sub, DB) from the ConfigMap
```

`bootstrap/` is outside this flow. A project Owner applies it once from a workstation, then migrates its state into the bucket (see [Managing the state file in GCP](#managing-the-state-file-in-gcp)).

### Flow 5: An operator or on-call engineer

```mermaid
sequenceDiagram
    autonumber
    actor O as Operator
    participant IAM as Google IAM
    participant CP as GKE control plane<br/>(DNS endpoint)
    participant ARGO as ArgoCD server<br/>(ClusterIP)
    participant LOG as Cloud Logging
    participant M as Cloud Monitoring

    O->>IAM: gcloud auth login
    O->>CP: get-credentials --dns-endpoint, then kubectl
    CP->>IAM: Check the caller's IAM permissions
    Note over CP: IP endpoint has no authorized CIDRs.<br/>DNS endpoint works from anywhere with IAM.
    O->>CP: kubectl port-forward svc/argocd-server
    CP->>ARGO: Tunnel to localhost:8080 (admin user)
    O->>LOG: Cloud Armor DENY logs, LB logs (50% sampled)
    O->>LOG: VPC flow logs, NAT errors, Cloud SQL slow queries (over 500 ms)
    M-->>O: DLQ alert (notification channel still to be configured)
    Note over CP: Autopilot upgrades: Sundays 02:00-06:00 Montreal time (REGULAR channel)
```

## Repository layout

| Folder | Role | GCS state (prefix) |
|---|---|---|
| `bootstrap/` | APIs, state bucket, GitHub WIF, CI service accounts | `bootstrap` (after migration) |
| `infra/` | VPC, NAT, GKE Autopilot, Cloud Armor, Artifact Registry, Pub/Sub, Redis, Cloud SQL, Secret Manager, Workload Identity IAM, alert | `infra` |
| `platform/` | Namespace, ConfigMap (infra outputs → k8s), ArgoCD, ArgoCD Application | `platform` |
| `k8s/` | Kustomize manifests (Deployment, HPA, PDB, Gateway, HTTPRoute, GCPBackendPolicy, NetworkPolicy) | n/a (GitOps) |
| `app/` | Demo .NET 10 API + non-root Dockerfile | n/a |
| `.github/workflows/` | Terraform and application pipelines | n/a |
| `docs/` | Interview guide (Markdown + PDF) and `tools/build-pdf.sh` to regenerate the PDF | n/a |

The PDF in `docs/` is generated from `docs/INTERVIEW-GUIDE-ARTM.md`. After editing the Markdown, regenerate it with `docs/tools/build-pdf.sh` (requires `python3` and Google Chrome; set `CHROME=/path/to/chrome` if it is not found automatically).

Why three stacks? **Blast radius** (a mistake in the platform does not touch the network), **lifecycle** (bootstrap rarely changes), and a **technical constraint**: the `kubernetes`/`helm` providers need an existing cluster at plan time.

---

## Managing the state file in GCP

1. **Chicken-and-egg problem**: the bucket that will store the state does not exist yet. So `bootstrap` first runs with a **local** state, creates the bucket, and then its own state is **migrated** into the bucket (`terraform init -migrate-state`).
2. **Bucket** `<PROJECT_ID>-tfstate`:
   - uniform bucket-level access and `public_access_prevention = enforced`;
   - **versioning** enabled, which lets you restore a corrupted state;
   - lifecycle rules that keep 10 noncurrent versions, for at most 90 days;
   - Montreal region (the state contains secrets, such as the DB password).
3. **Locking**: native with the `gcs` backend (`.tflock` file), no external table. In CI, `concurrency: terraform-dev` also prevents two simultaneous runs.
4. **Separation**: one prefix per stack (`bootstrap`, `infra`, `platform`). The `platform` stack reads the `infra` outputs through `terraform_remote_state`.
5. **Access**: the `gh-terraform` account has `storage.objectAdmin` **on the bucket only**.
6. **Restoring a version**:
   ```bash
   gcloud storage ls -a gs://$PROJECT_ID-tfstate/infra/default.tfstate
   gcloud storage cp "gs://$PROJECT_ID-tfstate/infra/default.tfstate#<GENERATION>" \
                     gs://$PROJECT_ID-tfstate/infra/default.tfstate
   ```
7. **Orphaned lock** (interrupted run): `terraform force-unlock <LOCK_ID>`, only after confirming that no run is in progress.

---

## Step-by-step deployment

### 0. Prerequisites

- A **dedicated** GCP project with billing enabled, and the Owner role on that project (for the bootstrap only).
- Tools: `gcloud`, `terraform >= 1.9`, `kubectl`, `gke-gcloud-auth-plugin`, `gh` (GitHub CLI), `git`.
- A GitHub repository containing this code. **Public** for simplicity; otherwise see "Private repository" below.

```bash
export PROJECT_ID="my-transit-lab-project"
export REGION="northamerica-northeast1"
export GITHUB_REPO="my-account/transit-devops-lab"

gcloud auth login
gcloud auth application-default login
gcloud config set project "$PROJECT_ID"
```

Replace `REPLACE_PROJECT_ID` in `k8s/overlays/dev/kustomization.yaml`, then format the code:

```bash
sed -i "s/REPLACE_PROJECT_ID/$PROJECT_ID/" k8s/overlays/dev/kustomization.yaml
terraform fmt -recursive
```

### 1. Bootstrap (once, from your workstation)

```bash
cd bootstrap
terraform init
terraform apply -var="project_id=$PROJECT_ID" -var="github_repo=$GITHUB_REPO"

# Migrate the local state to the bucket
cp backend.tf.example backend.tf
terraform init -migrate-state -backend-config="bucket=${PROJECT_ID}-tfstate"
rm -f terraform.tfstate terraform.tfstate.backup   # after confirming the migration
cd ..
```

### 2. Configure GitHub

```bash
# Prints the commands to run (repository variables)
terraform -chdir=bootstrap output -raw github_variables_commands
# ... then run them (gh must be authenticated against the repository)

# "dev" environment with manual approval for applies
gh api -X PUT "repos/$GITHUB_REPO/environments/dev" \
  -F "reviewers[][type]=User" -F "reviewers[][id]=$(gh api user -q .id)"
```

Optional, for SonarQube/SonarCloud: the `SONAR_TOKEN` secret and the `SONAR_PROJECT_KEY`, `SONAR_ORG` and optionally `SONAR_HOST_URL` variables.

### 3. Infrastructure and platform

**Option A: through GitHub Actions (recommended)**

```bash
git add . && git commit -m "feat: transit lab" && git push origin main
```
The `terraform` workflow runs `infra` (plan, then approval in the Actions tab, then apply), then `platform`. Allow about 15 to 20 minutes (GKE and Cloud SQL take the longest).

**Option B: from your workstation**

```bash
cd infra
terraform init -backend-config="bucket=${PROJECT_ID}-tfstate"
terraform plan  -var-file=env/dev.tfvars -var="project_id=$PROJECT_ID" -out=tfplan
terraform apply tfplan
cd ../platform
terraform init -backend-config="bucket=${PROJECT_ID}-tfstate"
terraform apply -var-file=env/dev.tfvars -var="project_id=$PROJECT_ID" \
  -var="state_bucket=${PROJECT_ID}-tfstate" \
  -var="gitops_repo_url=https://github.com/${GITHUB_REPO}.git"
cd ..
```

### 4. Application

Any change in `app/` on `main` triggers `app.yml`, which chains: build, SonarQube, image, Trivy (blocking), push `vehicle-api:<sha>`, then a commit updating `k8s/overlays/dev`. ArgoCD detects that commit and deploys (in about 60 s).

First deployment: `gh workflow run app.yml`.

> If `main` is protected, the bot's `git push` fails. In that case, use a GitHub App or an automated promotion PR (best practice in production).

### 5. Checks

```bash
gcloud container clusters get-credentials transit-lab-gke --region $REGION --dns-endpoint
kubectl -n transit get pods,hpa,gateway,httproute
kubectl -n transit describe gateway transit-gateway   # wait for "Programmed=True" (~5 min)

# ArgoCD
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
kubectl -n argocd port-forward svc/argocd-server 8080:80   # http://localhost:8080 (admin)

IP=$(terraform -chdir=infra output -raw gateway_ip)
curl -s http://$IP/api/v1/vehicles | jq .          # 1st call "origin", then served from the 10 s cache

# Pub/Sub
curl -s -X POST http://$IP/api/v1/vehicles/positions -H 'Content-Type: application/json' \
  -d '{"vehicleId":"BUS-101","routeId":"55","lat":45.51,"lon":-73.56,"timestamp":"2026-11-21T08:00:00Z"}'
gcloud pubsub subscriptions pull vehicle-positions-processor --auto-ack --limit=5
```

### 6. Demonstrating Cloud Armor

```bash
# WAF: SQL injection → 403
curl -s -o /dev/null -w "%{http_code}\n" "http://$IP/api/v1/vehicles?id=1'%20OR%20'1'='1"

# Rate limiting: above 300 req/min → 429
for i in $(seq 1 400); do curl -s -o /dev/null -w "%{http_code}\n" http://$IP/api/v1/vehicles; done | sort | uniq -c

# Cloud Armor logs
gcloud logging read 'resource.type="http_load_balancer" AND jsonPayload.enforcedSecurityPolicy.outcome="DENY"' --limit=10 --format=json
```

### 7. Demonstrating GitOps (self-healing)

```bash
kubectl -n transit scale deploy vehicle-api --replicas=0   # manual drift
kubectl -n transit get deploy vehicle-api -w               # ArgoCD (selfHeal) restores the state from Git
```

Rollback: `git revert` the `deploy(dev): ...` commit, and ArgoCD goes back to the previous image.

### 8. Costs and teardown

Rough order of magnitude for a lab running continuously: GKE Autopilot (cluster fee and pods), Load Balancer, Cloud SQL `db-f1-micro`, 1 GB Redis and NAT. Expect a few dollars per day. Set `enable_cloudsql=false` and `enable_redis=false` to lower the bill, and **destroy after use**.

**Option A: through GitHub Actions (recommended)**

```bash
gh workflow run terraform.yml -f action=destroy -f confirm=destroy
```
The run destroys `platform` and then `infra`, and each destroy plan waits for approval in the `dev` environment. Before the platform destroy, it scales ArgoCD's application controller to zero so self-heal cannot recreate the Gateway. It then deletes the Gateway and waits for the load balancer to release the static IP. After the platform destroy, it waits for the GKE NEGs to disappear, then runs the infra destroy.

**Option B: from your workstation**

```bash
terraform -chdir=platform destroy -var-file=env/dev.tfvars -var="project_id=$PROJECT_ID" \
  -var="state_bucket=${PROJECT_ID}-tfstate" -var="gitops_repo_url=https://github.com/${GITHUB_REPO}.git"
kubectl -n transit delete gateway transit-gateway --ignore-not-found   # releases the LB before the VPC
terraform -chdir=infra destroy -var-file=env/dev.tfvars -var="project_id=$PROJECT_ID"
# Bootstrap: keep it (reusable) or destroy it. Note: a deleted WIF pool
# keeps its ID reserved for 30 days.
```

Also set up a **budget with alerts** (Billing > Budgets) before you start.

---

## Private repository

ArgoCD needs credentials. Create a read-only deploy key, then:
```bash
kubectl -n argocd create secret generic repo-gitops \
  --from-literal=type=git --from-literal=url=git@github.com:$GITHUB_REPO.git \
  --from-file=sshPrivateKey=./deploy_key
kubectl -n argocd label secret repo-gitops argocd.argoproj.io/secret-type=repository
```
And switch `gitops_repo_url` to SSH. In production, the secret comes from Secret Manager through External Secrets Operator.

## Known limitations and improvement ideas (good interview topics)

| Lab limitation | In production |
|---|---|
| HTTP only | Certificate Manager + Cloud DNS, HTTPS listener, 80→443 redirect, HSTS |
| ArgoCD via port-forward, admin account | OIDC SSO, per-team RBAC, AppProjects, exposure through IAP |
| The Terraform plan (CI artifact) contains the DB password | Password generated outside Terraform (Secret Manager rotation) or IAM DB auth; artifact encryption |
| Single environment | `env/dev`, `env/qa`, `env/prod`, separate projects, promotion by PR |
| GitHub Actions referenced by tag | Pin by SHA (supply-chain protection) + Dependabot |
| No image signing | cosign + Binary Authorization (only CI-signed images run) |
| Redis BASIC, Cloud SQL ZONAL | Redis STANDARD_HA, Cloud SQL REGIONAL + read replica |
| No API management gateway | Apigee in front of the API: developer keys, per-product quotas, open data portal |
| No canary | Argo Rollouts with automated metric analysis |
| No External Secrets | External Secrets Operator + Secret Manager (instead of the ConfigMap for secrets) |
| Helm chart versions not pinned | Pinning + Renovate |
