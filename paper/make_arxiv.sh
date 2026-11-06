#!/usr/bin/env bash
# Build the arXiv submission bundle paper/arxiv.tar.gz from paper/main.tex.
#
# arXiv compiles with pdfLaTeX and does not run BibTeX, so the bundle carries main.bbl (built here) instead of
# refs.bib, plus only the .tex inputs, tables and PDF figures the paper actually uses. The script then compiles the
# bundle in a clean directory without refs.bib to prove it stands alone. Needs tectonic on PATH. Usage:
#   bash paper/make_arxiv.sh
set -euo pipefail
cd "$(dirname "$0")"
BUILD=$(mktemp -d)
STAGE=$(mktemp -d)
CHECK=$(mktemp -d)
trap 'rm -rf "$BUILD" "$STAGE" "$CHECK"' EXIT

tectonic --keep-intermediates --outdir "$BUILD" main.tex >/dev/null

cp main.tex part1.tex part2.tex appendix.tex "$STAGE/"
cp "$BUILD/main.bbl" "$STAGE/"
mkdir -p "$STAGE/tables" "$STAGE/figures"
for t in $(grep -ho '\\input{tables/[^}]*}' part1.tex part2.tex appendix.tex | sed 's/\\input{tables\/\(.*\)}/\1/' | sort -u); do
  cp "tables/$t.tex" "$STAGE/tables/"
done
for f in $(grep -ho '\\includegraphics\(\[[^]]*\]\)\?{[^}]*}' part1.tex part2.tex appendix.tex | sed 's/.*{\(.*\)}/\1/' | sort -u); do
  cp "figures/$f.pdf" "$STAGE/figures/"
done

# Self-containment check: compile the bundle with no refs.bib, reading main.bbl directly as arXiv's pdfLaTeX does
# (\input{main.bbl} stops tectonic from running its own BibTeX), and fail on any undefined citation or reference.
# tectonic is XeTeX-based, so the check runs before \pdfoutput=1 is added; that line only tells arXiv to use pdfLaTeX.
cp -r "$STAGE/." "$CHECK/"
sed -i 's/\\bibliography{refs}/\\input{main.bbl}/' "$CHECK/main.tex"
(cd "$CHECK" && tectonic --keep-logs main.tex >/dev/null 2>&1)
if grep -qi 'citation.*undefined\|reference.*undefined' "$CHECK/main.log"; then
  grep -i 'citation.*undefined\|reference.*undefined' "$CHECK/main.log" >&2
  echo "arXiv bundle has undefined citations or references" >&2
  exit 1
fi
{ echo '\pdfoutput=1 % arXiv: process with pdfLaTeX'; cat main.tex; } > "$STAGE/main.tex"

tar -czf arxiv.tar.gz -C "$STAGE" .
echo "built $(pwd)/arxiv.tar.gz ($(tar -tzf arxiv.tar.gz | grep -vc '/$') files); upload it at https://arxiv.org/submit"
