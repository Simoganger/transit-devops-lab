"""Generate the architecture diagrams (SVG) used by INTERVIEW-GUIDE-ARTM.md.
Usage: python3 docs/tools/diagrams.py   -> writes docs/diagrams/case*.svg
Pure standard library; edit the coordinates below and re-run, then build-pdf.sh."""
import os
from html import escape

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "diagrams")

# Palette (matches the PDF styles in md_to_html.py)
KIND = {
    "edge":   ("#e8f1f8", "#0b6fa4"),   # network / entry points
    "comp":   ("#eaf5ee", "#2f855a"),   # compute
    "data":   ("#fdf3e3", "#b7791f"),   # data stores / messaging
    "sec":    ("#fbeaea", "#c53030"),   # security / failure
    "ext":    ("#f1f3f6", "#5a6577"),   # external actors
    "plain":  ("#ffffff", "#0b6fa4"),
}
INK, MUTED, ARROW = "#1d2330", "#4a5568", "#4a5568"


class D:
    def __init__(self, w, h):
        self.w, self.h, self.parts = w, h, []

    def add(self, s):
        self.parts.append(s)

    def box(self, x, y, w, h, title, subs=(), kind="plain", align="middle", dashed=False, tsize=13.5):
        fill, stroke = KIND[kind]
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{fill}" stroke="{stroke}" stroke-width="1.4"{dash}/>')
        lines = 1 + len(subs)
        lh_t, lh_s = tsize + 4, 15
        total = lh_t + lh_s * len(subs)
        ty = y + (h - total) / 2 + tsize
        tx = x + w / 2 if align == "middle" else x + 12
        self.text(tx, ty, title, size=tsize, weight=600, color="#0b3d63", anchor=align)
        for i, s in enumerate(subs):
            self.text(tx, ty + lh_t - 2 + i * lh_s, s, size=11.5, color=MUTED, anchor=align)

    def text(self, x, y, s, size=11.5, weight=400, color=INK, anchor="start", italic=False):
        st = ' font-style="italic"' if italic else ""
        a = {"start": "start", "middle": "middle", "end": "end"}[anchor]
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{a}"{st}>{escape(s)}</text>')

    def arrow(self, pts, label=None, lx=None, ly=None, dashed=False, color=ARROW, anchor="start", both=False):
        d = "M" + " L".join(f"{px},{py}" for px, py in pts)
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        start = ' marker-start="url(#ah)"' if both else ""
        self.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.5"{dash}{start} marker-end="url(#ah)"/>')
        if label:
            self.text(lx, ly, label, size=11, color="#5a6577", anchor=anchor, italic=True)

    def line(self, pts, dashed=False, color=ARROW):
        d = "M" + " L".join(f"{px},{py}" for px, py in pts)
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        self.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.5"{dash}/>')

    def frame(self, x, y, w, h, label, color="#0b6fa4"):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="none" stroke="{color}" stroke-width="1.2" stroke-dasharray="6 4"/>')
        self.text(x + 12, y + 18, label, size=11, weight=700, color=color)

    def svg(self):
        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" font-family="-apple-system, 'Helvetica Neue', Helvetica, Arial, sans-serif">
<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{ARROW}"/></marker></defs>
<rect width="{self.w}" height="{self.h}" fill="#ffffff"/>
{chr(10).join(self.parts)}
</svg>
"""

    def save(self, name):
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(self.svg())


def down(d, x, y1, y2, **kw):
    d.arrow([(x, y1), (x, y2)], **kw)


# ---------------------------------------------------------------- Case 1
def case1():
    d = D(960, 560)
    d.text(190, 26, "READ PATH (query side)", size=12, weight=700, color="#0b6fa4", anchor="middle")
    d.text(750, 26, "WRITE PATH (streaming ingestion)", size=12, weight=700, color="#b7791f", anchor="middle")
    d.line([(560, 12), (560, 548)], dashed=True, color="#c3ccd8")
    L, W = 40, 300
    c = L + W / 2
    d.box(L, 44, W, 44, "Apps: Chrono, third parties, signs", kind="ext")
    down(d, c, 88, 118)
    d.box(L, 118, W, 36, "Cloud DNS", kind="edge")
    down(d, c, 154, 182)
    d.box(L, 182, W, 58, "Global HTTPS LB + Cloud CDN", ["Cloud Armor: rate limiting"], kind="edge")
    d.text(352, 202, "CDN caches /vehicles and", size=11, color=MUTED, italic=True)
    d.text(352, 217, "/trip-updates for 5-15 s", size=11, color=MUTED, italic=True)
    down(d, c, 240, 268)
    d.box(L, 268, W, 50, "Apigee", ["per-client quotas (SpikeArrest)"], kind="edge")
    down(d, c, 318, 346)
    d.box(L, 346, W, 76, "GKE · read-api (stateless)", ["HPA on CPU + RPS, high min at peak", "PDB, multi-zone"], kind="comp")
    down(d, c, 422, 460, label="reads", lx=c + 8, ly=446)
    d.box(L, 460, W, 58, "Memorystore Redis HA", ["precomputed current state"], kind="data")

    R = 600
    rc = R + W / 2
    d.box(R, 44, W, 44, "Operator feeds (GTFS-RT, AVL)", kind="ext")
    down(d, rc, 88, 126)
    d.box(R, 126, W, 54, "Ingestion (normalizes)", ["Cloud Run / GKE"], kind="comp")
    down(d, rc, 180, 216)
    d.box(R, 216, W, 54, "Pub/Sub", ["ordering_key = vehicle_id"], kind="data")
    down(d, rc, 270, 306)
    d.box(R, 306, W, 70, "Dataflow (streaming)", ["windows, enrichment,", "delay detection"], kind="comp")
    d.arrow([(R, 352), (470, 352), (470, 489), (L + W + 2, 489)], label="writes current state", lx=478, ly=420)
    down(d, 680, 376, 460)
    down(d, 820, 376, 460)
    d.box(R, 460, 140, 58, "BigQuery", ["analytics"], kind="data")
    d.box(R + 160, 460, 140, 58, "Bigtable", ["history"], kind="data")
    d.save("case1-realtime-api.svg")


# ---------------------------------------------------------------- Case 2
def case2():
    d = D(960, 790)
    d.box(40, 18, 130, 42, "Developer", kind="ext")
    d.arrow([(170, 39), (240, 39)], label="PR", lx=205, ly=32, anchor="middle")
    d.box(240, 18, 220, 42, "GitHub (app repo)", kind="edge")
    down(d, 350, 60, 90)
    d.frame(40, 90, 880, 322, "GITHUB ACTIONS · OIDC → GCP (keyless, no SA keys)")
    d.text(60, 130, "On pull request", size=11, weight=700, color=MUTED)
    steps1 = ["Build + unit tests + coverage",
              "SonarQube quality gate (new code)",
              "SCA: Dependabot / dotnet list package --vulnerable",
              "docker build (multi-stage, non-root) → Trivy → SBOM (Syft)"]
    steps2 = ["Push to Artifact Registry · tag = commit SHA (immutable)",
              "cosign sign (keyless) + SLSA attestation",
              "Commit to GitOps repo: overlays/dev, image = …@sha256:digest"]

    def step(n, y, s):
        d.add(f'<rect x="60" y="{y}" width="580" height="28" rx="5" fill="#f6f9fb" stroke="#ccd6e0"/>')
        d.add(f'<circle cx="76" cy="{y + 14}" r="10" fill="#0b6fa4"/>')
        d.text(76, y + 18, str(n), size=11, weight=700, color="#fff", anchor="middle")
        d.text(96, y + 18.5, s, size=12)

    for i, s in enumerate(steps1):
        step(i + 1, 138 + i * 34, s)
    d.text(60, 296, "On merge to main", size=11, weight=700, color=MUTED)
    for i, s in enumerate(steps2):
        step(i + 5, 304 + i * 34, s)
    # gates
    for y, s in ((172, "Gate: failure = PR blocked"), (240, "Gate: CRITICAL CVE = blocked")):
        d.arrow([(640, y + 14), (668, y + 14)])
        d.box(668, y, 232, 28, s, kind="sec", tsize=11.5)

    down(d, 250, 412, 450)
    d.box(40, 450, 420, 58, "GitOps repo (k8s/)", ["promotion PRs dev → qa → prod · approvals, CODEOWNERS"], kind="data")
    d.box(500, 450, 420, 74, "Infra repo · Terraform module (separate pipeline)",
          ["database, Pub/Sub topic, IAM · plan on PR → approved apply", "outputs → ConfigMap / External Secrets"], kind="data")
    down(d, 130, 508, 552, label="pull", lx=138, ly=535)
    d.box(40, 552, 180, 58, "ArgoCD", ["one per environment"], kind="comp")

    rows = [(552, "GKE dev", "Smoke + integration tests", ["PostSync hook"]),
            (622, "GKE qa", "DAST (OWASP ZAP) + load tests", []),
            (692, "GKE prod", "Argo Rollouts canary 10% → 50% → 100%",
             ["AnalysisTemplate: 5xx < 1%, p95 < 300 ms, otherwise automatic rollback"])]
    for y, env, title, subs in rows:
        h = 58
        d.arrow([(220, 581), (250, 581), (250, y + h / 2), (300, y + h / 2)])
        d.box(300, y, 130, h, env, kind="comp")
        d.arrow([(430, y + h / 2), (470, y + h / 2)])
        d.box(470, y, 450, h, title, subs, kind="plain")
    d.frame(288, 538, 154, 226, "")
    d.text(365, 780, "Binary Authorization: unsigned images rejected", size=11, weight=700, color="#c53030", anchor="middle")
    d.save("case2-dotnet-pipeline.svg")


# ---------------------------------------------------------------- Case 3
def case3():
    d = D(960, 610)
    d.box(170, 16, 220, 40, "Bots / attackers", kind="sec")
    d.box(470, 16, 220, 40, "Legitimate riders", kind="comp")
    d.arrow([(280, 56), (280, 92)], color="#c53030")
    d.arrow([(580, 56), (580, 92)], color="#2f855a")
    X, W = 150, 560
    layers = [(92, 50), (172, 132), (334, 62), (426, 62), (518, 62)]
    for i, (y, h) in enumerate(layers):
        d.text(40, y + h / 2 + 4, f"LAYER {i + 1}", size=11, weight=700, color="#0b6fa4")
    d.text(740, 82, "WHAT IT STOPS", size=11, weight=700, color=MUTED)
    stops = ["Volumetric L3/L4 floods", "Bots, L7 attacks, brute force,", "Abusive clients, account takeover",
             "Saturation of the origin", "Card data exposure"]
    d.box(X, 92, W, 50, "Google Front End (anycast)", ["L3/L4 DDoS absorbed at Google's edge"], kind="edge")
    down(d, 430, 142, 172)
    d.box(X, 172, W, 132, "Cloud Armor", [
        "adaptive protection (L7 machine learning)",
        "reCAPTCHA Enterprise bot score on /checkout and /login",
        "rate_based_ban: > 100 req/min on /login → 10 min ban",
        "OWASP WAF rules · geo-filtering · IP reputation (Threat Intelligence)"], kind="sec")
    down(d, 285, 304, 334)
    down(d, 575, 304, 334)
    d.box(X, 334, 270, 62, "Apigee", ["per-client quotas, SpikeArrest"], kind="edge")
    d.box(X + 290, 334, 270, 62, "CIAM", ["adaptive MFA, anti credential-", "stuffing, account lockout"], kind="edge")
    down(d, 285, 396, 426)
    d.box(X, 426, W, 62, "GKE (private nodes, origin not exposed)",
          ["capped HPA · virtual waiting room on saturation · idempotent orders"], kind="comp")
    down(d, 430, 488, 518)
    d.box(X, 518, W, 62, "Payment processor (PCI DSS)",
          ["tokenization: no card data passes through our systems → reduced PCI scope"], kind="data")
    ys = [121, 230, 369, 461, 553]
    for y, s in zip(ys, stops):
        d.text(740, y, s, size=11.5, color=INK)
    d.text(740, 245, "credential stuffing", size=11.5, color=INK)
    d.save("case3-ddos-defence.svg")


# ---------------------------------------------------------------- Case 4
def case4():
    d = D(960, 590)
    d.add('<polygon points="480,14 650,50 480,86 310,50" fill="#f1f3f6" stroke="#5a6577" stroke-width="1.4"/>')
    d.text(480, 47, "Can the vendor package", size=12.5, weight=600, color="#0b3d63", anchor="middle")
    d.text(480, 63, "run in containers?", size=12.5, weight=600, color="#0b3d63", anchor="middle")
    d.arrow([(310, 50), (250, 50), (250, 112)], label="yes", lx=275, ly=43, anchor="middle")
    d.arrow([(650, 50), (710, 50), (710, 112)], label="no", lx=685, ly=43, anchor="middle")
    # Option A
    d.text(250, 130, "OPTION A · CONTAINERIZABLE", size=11.5, weight=700, color="#2f855a", anchor="middle")
    d.box(40, 142, 420, 92, "GitOps repo “vendor-x”",
          ["vendor (or in-house) Helm chart", "values-dev / qa / prod.yaml", "ExternalSecrets, NetworkPolicies"], kind="data")
    down(d, 250, 234, 270)
    d.box(40, 270, 420, 42, "ArgoCD", kind="comp")
    down(d, 250, 312, 348)
    d.box(40, 348, 420, 58, "GKE", ["dedicated namespace, quotas, Pod Security Standards"], kind="comp")
    # Option B
    d.text(710, 130, "OPTION B · NOT CONTAINERIZABLE", size=11.5, weight=700, color="#b7791f", anchor="middle")
    d.box(500, 142, 420, 58, "Packer: hardened, versioned VM image", ["CIS benchmark, Ops Agent, preinstalled software"], kind="data")
    down(d, 710, 200, 226)
    d.box(500, 226, 420, 58, "Terraform: Managed Instance Group", ["template, health check, autohealing, rolling update"], kind="comp")
    down(d, 710, 284, 310)
    d.box(500, 310, 420, 54, "Ansible / startup script", ["environment-specific configuration"], kind="comp")
    down(d, 710, 364, 390)
    d.box(500, 390, 420, 54, "Immutable deployment", ["new image = new template = MIG rollout"], kind="comp")
    d.arrow([(920, 417), (940, 417), (940, 171), (922, 171)], dashed=True)
    d.add('<text x="952" y="294" font-size="11" fill="#5a6577" font-style="italic" text-anchor="middle" transform="rotate(-90 952 294)">next vendor release</text>')
    # shared
    d.line([(250, 406), (250, 486)], dashed=True, color="#c3ccd8")
    d.line([(710, 444), (710, 486)], dashed=True, color="#c3ccd8")
    d.box(40, 486, 880, 82, "Platform standards enforced in both cases", [
        "Workload Identity or least-privilege VM service account · secrets in Secret Manager",
        "logs and metrics in Cloud Logging / Monitoring · backups · vulnerability scanning · private network"], kind="edge")
    d.save("case4-vendor-package.svg")


# ---------------------------------------------------------------- Case 5
def case5():
    d = D(960, 640)
    d.box(40, 16, 880, 74, "GCP Organization · Org Policies", [
        "allowed regions: Canada · no public IPs on VMs · no service account keys",
        "uniform bucket-level access · restricted IAM domains"], kind="edge")
    down(d, 190, 90, 128)
    down(d, 650, 90, 128)
    d.box(40, 128, 300, 54, "Non-prod folder", ["developers: editor"], kind="comp")
    d.box(380, 128, 540, 54, "Prod folder", ["humans: READ ONLY"], kind="sec")
    down(d, 515, 182, 222)
    down(d, 785, 182, 222)
    d.box(380, 222, 270, 118, "Normal change", [
        "PR → plan → review → apply", "via the Terraform SA, the only", "identity allowed to write to prod"], kind="comp")
    d.box(670, 222, 250, 118, "Emergency change", [
        "PAM (Privileged Access Manager)", "2 h just-in-time elevation", "justification + approval + audit log"], kind="sec")
    d.arrow([(795, 340), (795, 362), (515, 362), (515, 342)], dashed=True,
            label="then carried over into code", lx=655, ly=378, anchor="middle")

    d.frame(40, 398, 880, 222, "DRIFT DETECTION")
    lanes = [
        (430, [("Nightly GitHub Actions cron", 200), ("terraform plan -detailed-exitcode", 250), ("exit code 2 → GitHub issue + Slack/Teams alert", 330)]),
        (490, [("Cloud Asset Inventory feed", 200), ("Pub/Sub", 120), ("alert on changes not made by the Terraform SA", 460)]),
        (550, [("Audit Logs (Admin Activity)", 200), ("BigQuery: retention and investigations", 300)]),
    ]
    for y, chain in lanes:
        x = 60
        for i, (s, w) in enumerate(chain):
            kind = "sec" if i == len(chain) - 1 and y < 540 else "data" if i else "plain"
            d.box(x, y, w, 40, s, kind=kind, tsize=12)
            if i < len(chain) - 1:
                d.arrow([(x + w, y + 20), (x + w + 24, y + 20)])
            x += w + 24
    d.save("case5-governance.svg")


# ---------------------------------------------------------------- Case 6
def case6():
    d = D(960, 470)
    cols = [(40, "PHASE 0", "Foundations"), (360, "PHASE 1", "Connectivity and data"), (680, "PHASE 2", "Progressive cutover")]
    for x, k, t in cols:
        d.add(f'<rect x="{x}" y="16" width="250" height="54" rx="7" fill="#0b3d63"/>')
        d.text(x + 14, 37, k, size=11, weight=700, color="#9cc7e4")
        d.text(x + 14, 58, t, size=14, weight=600, color="#ffffff")
        d.add(f'<rect x="{x}" y="78" width="250" height="250" rx="7" fill="#f6f9fb" stroke="#ccd6e0"/>')
    d.arrow([(296, 43), (354, 43)])
    d.arrow([(616, 43), (674, 43)])

    def bullets(x, y, items):
        for i, (t, s) in enumerate(items):
            yy = y + i * 46
            d.add(f'<circle cx="{x + 18}" cy="{yy - 4}" r="3" fill="#0b6fa4"/>')
            d.text(x + 30, yy, t, size=12, weight=600, color=INK)
            if s:
                d.text(x + 30, yy + 16, s, size=11, color=MUTED)

    bullets(40, 104, [("GCP landing zone, all in IaC", None), ("Organization and folders", None),
                      ("Shared VPC and IAM", None), ("Centralized logs", None), ("Org Policies", None)])
    bullets(360, 104, [("AWS ⇄ GCP: HA VPN / Interconnect", "cross-cloud private link"),
                       ("DB replication by CDC", "Database Migration Service / Datastream"),
                       ("Objects: Storage Transfer Service", None),
                       ("Images: registry replication", None)])
    # Phase 2: traffic split bars
    d.text(694, 102, "Weighted DNS (60 s TTL)", size=12, weight=600)
    for i, g in enumerate((10, 50, 100)):
        y = 116 + i * 34
        bw = 220
        gw = bw * g / 100
        if g < 100:
            d.add(f'<rect x="{695}" y="{y}" width="{bw - gw}" height="22" fill="#f4b860"/>')
        d.add(f'<rect x="{695 + bw - gw}" y="{y}" width="{gw}" height="22" fill="#4a9fd6"/>')
        d.add(f'<rect x="695" y="{y}" width="{bw}" height="22" fill="none" stroke="#5a6577"/>')
        d.text(695 + bw / 2, y + 15.5, f"AWS {100 - g}%  ·  GCP {g}%", size=11, weight=600, color="#1d2330", anchor="middle")
    d.text(694, 240, "Side-by-side monitoring", size=12, weight=600)
    d.text(694, 256, "latency, errors, business metrics", size=11, color=MUTED)
    d.text(694, 286, "Rollback = DNS change", size=12, weight=600)
    d.text(694, 302, "back to the previous weights", size=11, color=MUTED)

    down(d, 805, 328, 362)
    d.add('<rect x="40" y="362" width="880" height="88" rx="7" fill="#f1f3f6" stroke="#5a6577"/>')
    d.text(54, 384, "PHASE 3 · DECOMMISSIONING", size=11, weight=700, color=MUTED)
    x = 54
    for i, s in enumerate(["Freeze", "Observation period", "Archiving", "Deletion", "Runbook updates"]):
        w = 60 + len(s) * 6.6
        d.box(x, 398, w, 36, s, kind="plain", tsize=12)
        if i < 4:
            d.arrow([(x + w, 416), (x + w + 22, 416)])
        x += w + 22
    d.save("case6-cloud-migration.svg")


# ---------------------------------------------------------------- Case 7
def case7():
    d = D(960, 720)
    d.box(40, 16, 180, 44, "Partners (API)", kind="ext")
    d.box(260, 16, 180, 44, "Chrono app (iOS/Android)", kind="ext", tsize=12.5)
    d.box(470, 16, 180, 44, "Website (SPA)", kind="ext")
    down(d, 350, 60, 110)
    down(d, 560, 60, 110)
    d.text(455, 82, "OIDC code", size=11, color="#5a6577", anchor="middle", italic=True)
    d.text(455, 96, "+ PKCE", size=11, color="#5a6577", anchor="middle", italic=True)
    down(d, 130, 60, 300)
    d.text(138, 170, "OAuth2 client", size=11, color="#5a6577", italic=True)
    d.text(138, 184, "credentials", size=11, color="#5a6577", italic=True)
    d.box(260, 110, 390, 146, "CIAM (Identity Platform / Auth0)", [
        "email + password, passkeys, Google / Apple",
        "adaptive MFA (risk-based)",
        "reCAPTCHA, anti-enumeration",
        "consent records (Law 25)",
        "blocking functions: validation, enrichment"], kind="sec")
    down(d, 455, 256, 300, label="JWT (15 min)", lx=463, ly=283)
    d.box(40, 300, 610, 56, "Apigee / API gateway",
          ["JWT validation (JWKS, iss, aud, exp, scopes) · per-client quotas"], kind="edge")
    down(d, 180, 356, 400)
    down(d, 500, 356, 400)
    d.box(40, 400, 280, 74, "Microservices", ["fine-grained authorization", "based on token claims"], kind="comp")
    d.box(360, 400, 280, 74, "Customer profile service", ["business source of truth: fares,", "preferences · keyed by sub, not email"], kind="comp")
    d.arrow([(650, 183), (780, 183), (780, 437), (642, 437)], label="account events", lx=788, ly=310)
    down(d, 500, 474, 512)
    d.box(360, 512, 280, 54, "Pub/Sub", ["account.created, account.deleted"], kind="data")
    d.arrow([(640, 539), (690, 539)])
    d.box(690, 512, 230, 54, "Consumers", ["CRM, sales, pseudonymized analytics"], kind="ext", tsize=13)

    d.line([(40, 598), (920, 598)], dashed=True, color="#c3ccd8")
    d.text(40, 590, "RIDERS (customer identity) ▲", size=11, weight=700, color=MUTED)
    d.text(40, 616, "▼ EMPLOYEES (workforce identity, a separate directory)", size=11, weight=700, color=MUTED)
    d.box(40, 626, 880, 76, "Workforce IdP (Entra ID / Google Workspace)", [
        "OIDC / SAML SSO to ArgoCD, Grafana, SaaS consoles · SCIM for the account lifecycle · groups → RBAC",
        "Never in the same directory as riders"], kind="edge")
    d.save("case7-ciam.svg")


# ---------------------------------------------------------------- Case 8
def case8():
    d = D(960, 330)
    y, h = 30, 66
    d.box(20, y, 170, h, "Validators", ["bus, metro", "local buffer: store & forward"], kind="ext")
    d.arrow([(190, y + h / 2), (270, y + h / 2)])
    d.text(222, y + h / 2 - 10, "4G/LTE", size=11, color="#5a6577", anchor="middle", italic=True)
    d.text(222, y + h / 2 + 18, "mTLS", size=11, color="#5a6577", anchor="middle", italic=True)
    d.box(270, y, 160, h, "Ingestion gateway", ["GKE, certificates"], kind="comp")
    d.arrow([(430, y + h / 2), (470, y + h / 2)])
    d.box(470, y, 140, h, "Pub/Sub / Kafka", [], kind="data")
    d.arrow([(610, y + h / 2), (650, y + h / 2)])
    d.box(650, y, 140, h, "Clearing service", [], kind="comp")
    d.arrow([(790, y + h / 2), (830, y + h / 2)])
    d.box(830, y, 110, h, "Sales DB", [], kind="data")
    down(d, 720, y + h, 140)
    d.box(620, 140, 200, 46, "Financial reconciliation", [], kind="data", tsize=12.5)

    d.text(20, 226, "USUAL SUSPECTS AT 3 A.M.", size=11, weight=700, color="#c53030")
    sus = [("Recent change", ["ArgoCD sync, Terraform,", "firewall / Cloud Armor rule"], None),
           ("Expired mTLS certificate", ["server cert or client CA"], (252, 67)),
           ("Quota / limit reached", ["NAT: OUT_OF_RESOURCES,", "connections, throughput"], (350, y + h)),
           ("Stuck consumer", ["backlog grows, DLQ fills up"], (540, y + h)),
           ("Saturated DB", ["connection pool exhausted"], (885, y + h))]
    for i, (t, subs, tgt) in enumerate(sus):
        bx = 20 + i * 186
        d.box(bx, 240, 172, 62, t, subs, kind="sec", tsize=12)
        if tgt:
            cx = bx + 86
            d.line([(cx, 240), (cx, 214), (tgt[0], 214), (tgt[0], tgt[1] + 4)], dashed=True, color="#c53030")
    d.save("case8-validators.svg")


if __name__ == "__main__":
    for f in (case1, case2, case3, case4, case5, case6, case7, case8):
        f()
    print("Wrote diagrams to", OUT)
