#!/usr/bin/env bash
# slopcheck.sh - AI-slop linter for solitaire-cipher-lab prose.
#
# Runs two local, no-network slop linters:
#   - slopscore-lint (https://github.com/jman4162/slopscore)     -> 0-100 SlopScore
#   - slopless       (https://github.com/seochecks-ai/slopless)  -> rule findings
#
# Scans Markdown, the package's docstrings, and the explainer page (web/index.html),
# since most readers meet this project through the page rather than the README.
# slopless reads Markdown only; slopscore covers the .py and .html files.
#
# Advisory by default. With --strict, exits non-zero on high-severity slopscore
# findings, for CI.
#
# Known domain false positives in this repo, do not "fix" these:
#   LEXICAL_GENERIC_IMPORTANCE  "key"  -> the cipher key (the deck order)
#   REDUNDANT_ADJACENT_PAIR            -> repeated closing tags in web/index.html
#   PARALLEL_RULE_OF_THREE             -> when the three items are actual card
#                                         suits, steps or test kinds, not padding
#
# Usage:
#   scripts/slopcheck.sh                      # default file set
#   scripts/slopcheck.sh README.md            # explicit files
#   scripts/slopcheck.sh --strict
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 2

# Pinned so a linter upgrade changes results only in a commit that says so.
# Keep SLOPSCORE_VERSION in step with the rev in .pre-commit-config.yaml.
SLOPSCORE_VERSION="0.14.3"
SLOPLESS_VERSION="0.2.41"

STRICT=0
if [ "${1:-}" = "--strict" ]; then
  STRICT=1
  shift
fi

if [ $# -gt 0 ]; then
  files=("$@")
else
  files=()
  for f in README.md CONTRIBUTING.md SECURITY.md CHANGELOG.md web/index.html; do
    [ -f "$ROOT/$f" ] && files+=("$f")
  done
  while IFS= read -r f; do files+=("$f"); done \
    < <(find "$ROOT/docs" -name "*.md" 2>/dev/null | sort)
  while IFS= read -r f; do files+=("$f"); done \
    < <(find "$ROOT/src" -name "*.py" 2>/dev/null | sort)
fi

if [ ${#files[@]} -eq 0 ]; then
  echo "[slopcheck] nothing to scan" >&2
  exit 2
fi

echo "===== slopscore-lint (jman4162), profile: technical ====="
slopscore_rc=0
if command -v uvx >/dev/null 2>&1; then
  if [ "$STRICT" -eq 1 ]; then
    uvx --from "slopscore-lint==$SLOPSCORE_VERSION" slopscore-lint scan "${files[@]}" \
      --profile technical --fail-on high || slopscore_rc=$?
  else
    uvx --from "slopscore-lint==$SLOPSCORE_VERSION" slopscore-lint scan "${files[@]}" --profile technical || true
  fi
else
  echo "[slopcheck] uvx not found; install uv (https://docs.astral.sh/uv/)." >&2
fi

echo
echo "===== slopless (seochecks-ai) ====="
if command -v npx >/dev/null 2>&1; then
  md=()
  for f in "${files[@]}"; do case "$f" in *.md) md+=("$f");; esac; done
  if [ ${#md[@]} -gt 0 ]; then
    npx -y "slopless@$SLOPLESS_VERSION" "${md[@]}" 2>/dev/null | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
except Exception:
    print("[slopcheck] slopless produced no parseable output."); sys.exit(0)
# Readability scores are meaningless for API docs full of code identifiers, and
# the formatting rules fight deliberate house style.
ignore = {"slopless/word-repetition", "slopless/paragraph-length",
          "slopless/smart-quotes", "slopless/sentence-case",
          "slopless/coleman-liau", "slopless/flesch-kincaid",
          "slopless/gunning-fog"}
shown = hidden = 0
for result in data or []:
    path = result.get("filePath", "?")
    for m in result.get("messages", []):
        if m.get("ruleId") in ignore:
            hidden += 1
            continue
        shown += 1
        print("  %s:%s %s: %s" % (path, m.get("line", "?"), m.get("ruleId"), m.get("message")))
print("[slopcheck] slopless: %d substantive finding(s); %d style rule(s) hidden." % (shown, hidden))
' || true
  fi
else
  echo "[slopcheck] npx not found; skipping slopless." >&2
fi

echo
if [ "$STRICT" -eq 1 ]; then
  exit "$slopscore_rc"
fi
echo "[slopcheck] Advisory only. Review findings; ignore the documented false positives."
