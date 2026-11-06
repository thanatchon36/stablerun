#!/usr/bin/env bash
# Fetch TeX Gyre Pagella (GUST Font License) into .tools/fonts so that the figures use the same Palatino as the
# paper (mathpazo). Without these files the figures fall back to STIX. Checksums are pinned.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .tools/fonts
declare -A SHA=(
  [regular]=44e64260716d8f2bbe412baa1ee99b7c995190ac4573177c24def0b9200438c7
  [bold]=dd4f9b69f0b24f1fb9be8634abf1fce2009e5c68a30842a3e9f5d6e535900abd
  [italic]=069bb27f48eb98a741715227fc6e4b7baf3639c29fc13925f70d1ed8884ac29a
  [bolditalic]=556fd64655a92bd9f5485ae2c03f7b9cdaf745a27a91d7edb3c3abde997206d2
)
for style in regular bold italic bolditalic; do
  f=".tools/fonts/texgyrepagella-$style.otf"
  if [ ! -f "$f" ]; then
    curl -fsSL -o "$f" "https://mirrors.ctan.org/fonts/tex-gyre/opentype/texgyrepagella-$style.otf"
  fi
  echo "${SHA[$style]}  $f" | sha256sum -c - >/dev/null
done
echo "fonts ready in .tools/fonts"
