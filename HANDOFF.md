# Handoff

## Desktop speaker popping — updated 2026-10-19 (dylan-MS-7C84)

**Resume:** Z323 speakers pop on the onboard aux; Dylan is trying sub RCA to 3.5 mm. Ask how it went, then pick a DAC if needed.

**Goal:** Stop the loud popping (worse with volume) from the Logitech Z323 on the desktop and understand the faint periodic pop that remains with the PC cable unplugged.

**Done:**
- Audited the outputs and wrote everything up in `desktop_audio/NOTES.md`. No settings changed.

**In progress / where it stopped:**
- Dylan connected the sub's RCA input to a 3.5 mm plug in the PC as a trial. Outcome unknown.

**Next steps:**
1. Ask whether the loud popping and the faint double pop are gone.
2. If not: USB DAC or optical-to-RCA converter (see the notes); the faint pop is probably the speakers' own supply.

**Gotchas / decisions:**
- Unplugging at the PC end silenced the loud pop, so it is PC-side analog noise, not the speakers.

**Key files & commands:**
- `desktop_audio/NOTES.md` — findings and options
- `aplay -l`, `wpctl status` — list outputs

## Under-sink shelf — updated 2026-11-07 (dylan-MS-7C84)

**Resume:** Buy list, aisles and Castorama cut sheet live; Dylan went to Les Ulis to buy. Ask what they bought/cut, then build.

**Goal:** Two-shelf under-sink shelf for Dylan's cabinet in Palaiseau (the main item), plus two risers
cut from the same board and batten: one for the clothes closet, one for jars in a kitchen top closet.
Live at https://dylan-neff.web.cern.ch/misc/shelf/ (tabs: Design `index.html`, Cost & buy list `buy.html`,
Découpe `cuts.html`, Folding table `table.html`). Source lives here; the site repo only holds published copies.

**Layout (confirmed by Dylan, drawn and agreed in chat):** standing at the door looking in, the right is a solid wall (dishwasher behind it) and the shelves go against it. Cabinet = 40 cm wide at the door x 50 cm deep, its back is the outer kitchen wall. To the LEFT is an extra space 70 cm wide, same 50 cm depth, level with the cabinet, on the SAME straight back wall (110 cm from dishwasher wall to far left). The oven stands in front of it and blocks it. A corner counter covers everything. The basin starts 6 cm from the dishwasher wall and reaches 6 cm over the extra space.

**Axes (output frame, model.json / renders / page):** +x toward the dishwasher wall (right), y=0 door line, y=500 back wall, z up. `build_model.py` is AUTHORED in the old frame (origin back-right, x grows left, y grows to the front) and `rot()` turns it 180 degrees about z on output. `plan_view.py` uses the authoring frame.

**Done (2026-11-07):**
- New **Découpe** tab `under_sink_shelf/cuts.html`, French with English under each line, for the Castorama cutting desk.
  Pine board 2000 x 400: crosscut 618, crosscut 750, the rest (~624) stays whole for the jar riser (Dylan: recut it later).
  On the 618 piece: diagonal from 63 mm on edge A to 555 mm on edge B (same end), ~39 deg to B; then each shelf cut
  square 430 mm from its 400 mm end (front edge comes out 101-102). Section 5 = straight oak cuts for the table, for later.
- Buy list rebuilt for **Castorama Les Ulis**, stock/price/aisle read from castorama.fr on 7 Nov: big Allée column, Amazon
  column removed (old comparison kept at the bottom), phone layout. Basket EUR 125.00 (`KITCHEN_EUR` in `closet_riser.py` updated).
  Picks: board 75, batten 72, 200-pack A2 4x40 (114; Dylan wanted 200 for the table too), Diall stainless chair brackets
  15x40x40 4-pack x3 (113; galvanised 25-pack not stocked), short stainless screws "look in aisle 114" (none in stock
  online, EUR 8.38 is an estimate), Pattex glue (aisle unknown), Magnusson 500 mm 11 TPI saw (119) with alternatives,
  clamps 117, brush 17, linseed oil 22. Sandpaper removed (Dylan has 150 grit); Dylan has a drill and wood bits.
- Folding-table look-list under the buy list (oak 136, hinges 113, dowel 134, anchors 114, oil 27, hacksaw 119, jigsaw 121)
  plus what to check in store. Design tab's stale notes fixed (screws, saw, store name, v11 title).

**Next steps:**
1. Ask Dylan what was bought and whether Castorama did the diagonal; update the list if they swapped anything.
2. Build questions. The short bracket screws: shelf side must be <= 16 mm (18 mm shelf).
3. Still unconfirmed guesses: extra space 70 cm, oven depth, basin overhang, 82 mm top shelf to basin. Re-measure before cutting.

**Gotchas / decisions:**
- Castorama stock: product pages are a SPA; navigate, wait ~4 s, then read `main.innerText` ("Stock en magasin : N pièces",
  "Situé dans l'allée N"). The search page's in-store filter is unreliable (URL param ignored, marketplace items shown).
  `search?term=<EAN>` redirects to the product page. JET-CUT fine saw, galvanised bracket pack, Diall 3x16 / A2 3x20 screws
  were NOT in stock at Les Ulis on 7 Nov.
- Dylan read the board's 400 mm width as shelf DEPTH; it is the side-to-side width. Depth stays 430.
- The v11 unit is 400 wide = door opening: it goes in turned (narrowest width 350 mm).
- Prices are static in the `ITEMS` array in `buy.html`; `KITCHEN_EUR` mirrors the basket by hand.

**Key files & commands:**
- `under_sink_shelf/build_model.py`, `plan_view.py`, `render_blender.py`, `closet_riser.py [n]` — geometry, renders, cut plan
- `under_sink_shelf/cuts.html` — shop cut sheet (hand-drawn SVG, board coords u along / v across)
- Publish: `bash under_sink_shelf/publish_to_site.sh`, then in `~/PycharmProjects/dylan-cern-site` commit, push and
  `./scripts/deploy-eos.sh` (needs Kerberos)

## P2 cosmic bench rates — updated 2026-10-30 (dylan-MS-7C84)

**Resume:** Simulation done (3-fold 0.51 Hz, top pair 14.3 Hz); rerun `P2/cosmic_rate.py` once Saclay confirms geometry.

**Goal:** Tell the Saclay P2 group what trigger rates to expect on their 3-scintillator cosmic bench.

**Done:**
- `P2/cosmic_rate.py` Monte Carlo (Guan angular spectrum, 160 m altitude), `P2/README.md`, `P2/results/`.

**Next steps:**
1. Get from Saclay: exact top-to-bottom distance, bar thickness, bottom-bar orientation, material above the bench.
2. Rerun with `--dist/--gap/--emin`; optionally add a rotated-bottom-bar case.

**Gotchas / decisions:**
- Assumed 150 cm, 3 cm gap, parallel bars, E > 0.2 GeV, 100 % efficiency. Model is ~10-15 % low on absolute normalisation.
- 3-fold equals top1 & bottom exactly for identical aligned bars (convexity).

## Kitchen folding table — updated 2026-11-06 (dylan-Yoga)

**Resume:** Oak-corbel fold-down table designed; Dylan looked at the oak on 11-07. Next: drill test, hinge side, then buy.

**Goal:** Wall-hung oak bar table (120 cm top) on the fridge-side wall in Palaiseau, folds down against the wall, fridge door
opens past it. Live as the "Folding table" tab: https://dylan-neff.web.cern.ch/misc/shelf/table.html (source `folding_table/`).

**Done:**
- Page with Three.js animation (4 support styles: steel, slim black, **oak corbels (chosen)**, cables), plan view, door-swing
  clearance check, dimensions, brick fixing, finish, section 8 shopping list with Castorama links/prices (read 2026-11-06) and what
  overlaps the shelf list. Deployed to EOS; site repo pushed.
- Design: 2 supports, 10 cm margin around the fridge door, top 120 x 50 trapezoid, 18 mm oak boards (Castorama 60x200 + 50x200, in stock
  Les Ulis), rail = 3 glued 18 mm layers, piano hinge, corbels fold flat to the wall then the table folds down. Wall behind the fridge and doorway drawn.
- Core list about 214 EUR (solid-brick anchors).

**In progress / where it stopped:**
- Nothing half-done. Photo of the wall is in `folding_table/photos/wall.jpg` (not published).

**Next steps:**
1. Dylan: 6 mm drill test (solid vs hollow brick) to choose anchors; measure doorway start/width behind the fridge, bin positions, wall length, counter wood/finish.
2. Confirm fridge door hinge side (Dylan said right; photo handle grooves look right, which would suggest a left hinge and change the table shape).
3. Buy (list in section 8; aisles at Les Ulis are on the buy-list tab's look-list); then update the page with measured values.
4. Ask what Dylan saw in store: oak colour/flatness, hinge screw-hole sizes, whether the cutting desk rips oak and the price per cut.
5. Shelf purchase covers the table's 4x40 rail screws (200-pack), glue, clamps, brush and saw.

**Gotchas / decisions:**
- Always deploy site updates to EOS without asking (memory: feedback-deploy-site-updates): `./scripts/deploy-eos.sh` in `dylan-cern-site` after `under_sink_shelf/publish_to_site.sh`.
- Bin positions and the back-wall doorway (15 cm thick, 90 x 205, starts 11 cm from the fridge side) are estimates; the recycle bin is ~4 cm from the freezer door swing at the assumed spot.
- Clearance numbers come from `node folding_table/check_clearance.mjs` (all four styles must PASS). Geometry lives in `folding_table/geom_block.js`; rebuild the page with `python3 folding_table/build_page.py`.
- Shelf 4x40 screws are too long for the 18 mm top; hinge needs the 3.5x16 pack. Oak corbel hinge strength is the weak point (use 3 hinges each if unsure).

**Key files & commands:**
- `folding_table/README.md`, `table.src.html`, `geom_block.js`, `check_clearance.mjs`, `build_page.py`
- `bash under_sink_shelf/publish_to_site.sh` then deploy from the site repo
