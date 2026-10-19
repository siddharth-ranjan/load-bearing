#!/usr/bin/env bash
# index.html is authored as a page fragment (the artifact host adds the document shell), so wrap it for static hosting.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p _site
{
  echo '<!doctype html><html lang="en"><head><meta charset="utf-8">'
  echo '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
  echo '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>'
  echo '</head><body>'
  cat index.html
  echo '</body></html>'
} > _site/index.html
