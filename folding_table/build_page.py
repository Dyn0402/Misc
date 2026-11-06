#!/usr/bin/env python3
"""Build table.html: inline geom_block.js (the geometry shared with check_clearance.mjs) into table.src.html."""
from pathlib import Path
here = Path(__file__).parent
geom = (here / "geom_block.js").read_text()
src = (here / "table.src.html").read_text()
assert "/*GEOM*/" in src
(here / "table.html").write_text(src.replace("/*GEOM*/", geom))
print("wrote", here / "table.html")
