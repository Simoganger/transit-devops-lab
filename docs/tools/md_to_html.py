"""Render the interview guide Markdown to print-ready HTML (cover page, styles).
Usage: md_to_html.py <input.md> <output.html>  (called by build-pdf.sh)"""
import os, re, sys, markdown
src, out = sys.argv[1], sys.argv[2]
md = open(src, encoding="utf-8").read()
# Drop title + intro (they go on the cover), i.e. everything up to the first '---'
md = md.split("\n---\n", 1)[1]
def fix_lists(md):
    out=[]; infence=False; prev=""
    for line in md.split("\n"):
        if line.startswith("```"): infence = not infence
        if not infence:
            m=re.match(r"^( {1,3})([-*]|\d+\.) ", line)
            if m: line="    "+line.lstrip(" ")
            islist=re.match(r"^\s*([-*]|\d+\.) ", line)
            previs=re.match(r"^\s*([-*]|\d+\.) ", prev) or prev.startswith("    ")
            if islist and prev.strip() and not previs and not line.startswith("    "):
                out.append("")
        out.append(line); prev=line
    return "\n".join(out)
md = fix_lists(md)
body = markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"])
# Inline the SVG diagrams (docs/diagrams/*.svg) so the HTML is self-contained
docs_dir = os.path.dirname(os.path.abspath(src))
def inline_svg(m):
    alt, path = m.group(1), m.group(2)
    svg = open(os.path.join(docs_dir, path), encoding="utf-8").read()
    svg = re.sub(r'\s(width|height)="\d+"', "", svg, count=2)  # scale to the column width
    return f'<figure class="diagram" role="img" aria-label="{alt}">{svg}</figure>'
body = re.sub(r'<p><img alt="([^"]*)" src="(diagrams/[^"]+\.svg)" ?/?></p>', inline_svg, body)
# Page break before each top-level part, except the first
body = re.sub(r"<h1>", '<h1 class="part">', body)
cover = """
<section class="cover">
  <div class="kicker">INTERVIEW PREPARATION · NOVEMBER 2026</div>
  <h1 class="ctitle">Senior DevOps<br>ARTM</h1>
  <p class="lede">Autorité régionale de transport métropolitain: detailed technical answers,
  reference architectures and a ready-to-deploy GCP lab.</p>
  <div class="cards">
    <div class="card"><b>Part 1</b><span>42 technical questions and model answers</span></div>
    <div class="card"><b>Part 2</b><span>8 case studies with architecture</span></div>
    <div class="card"><b>Part 3</b><span>GKE Autopilot, ArgoCD and Cloud Armor lab</span></div>
  </div>
  <p class="tip">For each answer: <b>short definition → how I did it → trade-offs → a number or an anecdote</b>.
  Senior panels mostly assess how well you justify trade-offs.</p>
</section>
"""
css = """
@page { size: Letter; margin: 0.7in 0.7in 0.75in 0.7in; }
body { font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; font-size: 9.6pt; line-height: 1.42; color: #1d2330; }
h1, h2, h3 { color: #0b3d63; line-height: 1.2; break-after: avoid; }
h1.part { break-before: page; font-size: 20pt; border-bottom: 3px solid #0b6fa4; padding-bottom: 6px; margin-top: 0; }
h2 { font-size: 14pt; margin-top: 18px; border-bottom: 1px solid #d5dde6; padding-bottom: 3px; }
h3 { font-size: 11pt; margin-top: 12px; }
p { margin: 5px 0; }
ul, ol { margin: 4px 0 6px; padding-left: 20px; }
li { margin: 2px 0; }
code { font-family: Menlo, monospace; font-size: 8.4pt; background: #eef2f6; padding: 0 3px; border-radius: 3px; }
pre { background: #f4f7fa; border: 1px solid #d5dde6; border-radius: 4px; padding: 8px 10px; break-inside: avoid; overflow: hidden; }
pre code { background: none; padding: 0; font-size: 6.9pt; line-height: 1.08; white-space: pre; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 8.6pt; break-inside: auto; }
th, td { border: 1px solid #ccd6e0; padding: 4px 6px; vertical-align: top; text-align: left; }
th { background: #0b3d63; color: #fff; }
tr { break-inside: avoid; }
tr:nth-child(even) td { background: #f6f9fb; }
hr { display: none; }
figure.diagram { margin: 8px 0 10px; break-inside: avoid; }
figure.diagram svg { display: block; width: 100%; height: auto; border: 1px solid #d5dde6; border-radius: 4px; }
em { color: #3a4556; }
.cover { height: 9.3in; display: flex; flex-direction: column; justify-content: center; }
.kicker { letter-spacing: 2px; font-size: 9pt; color: #0b6fa4; font-weight: 600; }
.ctitle { font-size: 40pt; margin: 10px 0 14px; color: #0b3d63; border: none; }
.lede { font-size: 12.5pt; color: #3a4556; max-width: 5.6in; }
.cards { display: flex; gap: 12px; margin: 28px 0; }
.card { flex: 1; border: 1px solid #d5dde6; border-top: 4px solid #0b6fa4; border-radius: 4px; padding: 12px; }
.card b { display: block; color: #0b3d63; font-size: 12pt; margin-bottom: 4px; }
.card span { font-size: 9.5pt; color: #3a4556; }
.tip { background: #eef5fa; border-left: 4px solid #0b6fa4; padding: 10px 12px; font-size: 10pt; }
"""
html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>DevOps Interview Guide ARTM</title><style>{css}</style></head>
<body>{cover}{body}</body></html>"""
open(out, "w", encoding="utf-8").write(html)
