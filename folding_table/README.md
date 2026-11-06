# Kitchen folding table

Wall-hung oak bar table (120 cm top) beside the fridge in Palaiseau, hinged to a rail on the brick
wall, folding flat against it. The fridge-side edge is cut at 55 degrees so the fridge door opens
past it. Published as the "Folding table" tab of the shelf pages (`dylan-cern-site/misc/shelf/table.html`).

- `geom_block.js`: the geometry (single source of truth, cm). Edit the numbers in `G` here.
- `table.src.html`: page template (Three.js scene, plan view, text). Holds a `/*GEOM*/` placeholder.
- `build_page.py`: inlines `geom_block.js` into the template, writes `table.html`.
- `check_clearance.mjs`: sweeps the fridge door 0 to 120 degrees against the table at five fold angles,
  the wall rail and the bins; exits non-zero if anything touches. Run: `node folding_table/check_clearance.mjs`.
- `photos/wall.jpg`: the photo of the wall (not published).
- Deploy: `under_sink_shelf/publish_to_site.sh` rebuilds the page and copies it into the site repo.

Inputs (Dylan, 2026-11-06): fridge 59 wide, 63 deep, 200 tall, freezer door 80, door 6 thick, hinge on
the side away from the wall; recycle bin 60 x 45 x 35, trash bin 50 x 30 x 28; stool 70 cm.
Estimates, to be measured: bin positions, wall length, hinge side (see the page's open questions).
