#!/usr/bin/env bash
# Builds docs/Interview-guide-DevOps-ARTM.pdf from docs/INTERVIEW-GUIDE-ARTM.md.
#   diagrams.py (SVGs) -> Markdown -> HTML (md_to_html.py) -> PDF (headless Chrome) -> footer + page numbers (add_footer.py)
# Requirements: python3 and Google Chrome (or set CHROME=/path/to/chrome).
set -euo pipefail

TOOLS_DIR="$(cd "$(dirname "$0")" && pwd)"
DOCS_DIR="$(dirname "$TOOLS_DIR")"
SRC="$DOCS_DIR/INTERVIEW-GUIDE-ARTM.md"
OUT="$DOCS_DIR/Interview-guide-DevOps-ARTM.pdf"
VENV="$TOOLS_DIR/.venv"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [[ -z "${CHROME:-}" ]]; then
  for c in "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" google-chrome chromium chromium-browser; do
    if [[ -x "$c" ]] || command -v "$c" >/dev/null 2>&1; then CHROME="$c"; break; fi
  done
fi
[[ -n "${CHROME:-}" ]] || { echo "Google Chrome not found; set CHROME=/path/to/chrome" >&2; exit 1; }

if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q --disable-pip-version-check -r "$TOOLS_DIR/requirements.txt"
fi

"$VENV/bin/python" "$TOOLS_DIR/diagrams.py"
"$VENV/bin/python" "$TOOLS_DIR/md_to_html.py" "$SRC" "$WORK/guide.html"
"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$WORK/raw.pdf" "file://$WORK/guide.html" 2>/dev/null
"$VENV/bin/python" "$TOOLS_DIR/add_footer.py" "$WORK/raw.pdf" "$OUT"
echo "Wrote $OUT"
