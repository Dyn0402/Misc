#!/usr/bin/env bash
# Copy the built shelf pages into the site repo so they deploy with the site.
# Usage: publish_to_site.sh [path/to/dylan-cern-site]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SITE="${1:-$HERE/../../dylan-cern-site}"
DST="$SITE/misc/shelf"
mkdir -p "$DST/renders"
cp "$HERE/index.html" "$HERE/buy.html" "$HERE/model.json" "$DST/"
cp "$HERE"/renders/*.png "$DST/renders/"
# The site copy keeps its breadcrumb link back to the misc page.
sed -i 's#<p class="crumb">Misc / under-sink shelf</p>#<p class="crumb"><a href="../">misc</a> / shelf</p>#' "$DST/index.html" "$DST/buy.html"
echo "published to $DST"
