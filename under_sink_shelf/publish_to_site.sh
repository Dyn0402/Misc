#!/usr/bin/env bash
# Copy the built shelf pages into the site repo so they deploy with the site.
# Usage: publish_to_site.sh [path/to/dylan-cern-site]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SITE="${1:-$HERE/../../dylan-cern-site}"
DST="$SITE/misc/shelf"
mkdir -p "$DST/renders"
python3 "$HERE/../folding_table/build_page.py" >/dev/null
cp "$HERE/index.html" "$HERE/buy.html" "$HERE/cuts.html" "$HERE/model.json" "$HERE/../folding_table/table.html" "$DST/"
cp "$HERE"/renders/*.png "$DST/renders/"
# The site copy keeps its breadcrumb link back to the misc page.
sed -i 's#<p class="crumb">Misc / under-sink shelf</p>#<p class="crumb"><a href="../">misc</a> / shelf</p>#' "$DST/index.html" "$DST/buy.html" "$DST/cuts.html" "$DST/table.html"
sed -i 's#<p class="crumb">Misc / kitchen folding table</p>#<p class="crumb"><a href="../">misc</a> / shelf / folding table</p>#' "$DST/table.html"
echo "published to $DST"
