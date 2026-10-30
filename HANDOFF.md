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

## Under-sink shelf — updated 2026-10-28 (dylan-MS-7C84)

**Resume:** Shelf v11 + closet riser + jar riser all designed and live; next is buying (Castorama trip) and building.

**Goal:** Two-shelf under-sink shelf for Dylan's cabinet in Palaiseau (the main item), plus two risers
cut from the same board and batten: one for the clothes closet, one for jars in a kitchen top closet.
Live at https://dylan-neff.web.cern.ch/misc/shelf/ (Design tab `index.html`, Cost & buy list `buy.html`).
Source lives here; the site repo only holds published copies.

**Layout (confirmed by Dylan, drawn and agreed in chat):** standing at the door looking in, the right is a solid wall (dishwasher behind it) and the shelves go against it. Cabinet = 40 cm wide at the door x 50 cm deep, its back is the outer kitchen wall. To the LEFT is an extra space 70 cm wide, same 50 cm depth, level with the cabinet, on the SAME straight back wall (110 cm from dishwasher wall to far left). The oven stands in front of it and blocks it. A corner counter covers everything. The basin starts 6 cm from the dishwasher wall and reaches 6 cm over the extra space. The extra space is not deeper than the cabinet; earlier versions wrongly put it behind the back wall.

**Axes (output frame, model.json / renders / page):** +x toward the dishwasher wall (right), so left = -x; +y away from you (y=0 door line, y=500 back wall); z up; right-handed. `build_model.py` is AUTHORED in the old frame (origin back-right corner, x grows to the left, y grows to the front) and `rot()` turns it 180 degrees about z on output. So constants in the file read as "distance left of the dishwasher wall" and "distance in front of the back wall". `plan_view.py` uses the authoring frame.

**Done (2026-10-28):**
- Shelf v11 (Dylan's idea): shelves use the full 400 mm board width. 400 back edge, 63 mm straight on the
  left at the back, the v10 diagonal extended, 100 front edge, 430 deep, 1170 cm2. Back-left corner is 15 mm
  past the door opening, in the open extra space (`check()` allows x up to 415 only at y <= 100). Post B
  moved to authoring x 363; rinse bottle moved 20 mm left. Model, plan view and Blender renders re-run.
- Nested cut: both shelves from 618 mm of board in 4 cuts (crosscut; one shared diagonal from edge A at
  63 mm to edge B at 555 mm; two 100 mm front cuts). Written up in section 4 of the Design tab with
  `renders/closet_cut_plan.png`. Section 4 also has a new guide to cutting the battens/dowels accurately.
- Closet riser: 750 x 400 top (closet ~76 cm wide with obstacles), four 182 mm batten legs, 200 mm tall,
  2 screws per leg, brackets/glue optional. Jar riser: 600 x 400 top, four 162 mm legs from Dylan's two
  1 m x 20 mm dowels, 180 mm tall. All fit on ONE board + ONE batten (board used to within the 10 mm end
  trims; ~180 mm batten left). `closet_riser.py` has the cost scaling for more closet risers.
- Buy list: coping saw replaced by Stanley JET-CUT fine 450 mm crosscut saw (17.90 Castorama; Amazon
  500 mm 16.92). Screws: 2 x Diall 20-pack 4x40 A2 (11.78; Les Ulis had 1 pack in stock). Brackets:
  VFANDV 20 stainless 40x40x16 with 15 mm screws, 7.79, https://www.amazon.fr/dp/B0D6YTK3KT (found by Dylan).
  Totals: recommended 99.47, all-Castorama 110.92, Amazon wherever possible 122.26. Amazon free delivery
  to 91120 from 45 EUR; Dylan appears not to have Prime.

**In progress / where it stopped:**
- Nothing half-done. Everything published and deployed 2026-10-28.

**Next steps:**
1. Dylan buys the timber at Castorama and the brackets on Amazon, then builds; answer build questions.
2. Size of the jar closet's shelf not confirmed; the 600 x 400 top is the maximum, cut smaller if needed.
3. Other Amazon links in `buy.html` are still searches, not product pages (only brackets are pinned).
4. Still unconfirmed guesses: extra space 70 cm wide, oven body depth, basin 6 cm over the extra space,
   82 mm from top shelf to basin, counter geometry. Re-measure before cutting.
5. Glue: Pattex Power says "water resistant" with no D-class; Sader Pro D3 100 g (9.89) states D3.

**Gotchas / decisions:**
- Dylan read the board's 400 mm width as shelf DEPTH; it is the side-to-side width. Depth stays 430.
- The v11 unit is 400 wide = door opening: it goes in turned (narrowest width 350 mm, square to the diagonal).
- Left/right confusion cost many turns earlier. Use the layout paragraph, not the render, for orientation.
- Z-fighting made a black bar when two coplanar faces overlapped; avoid overlapping wall slabs.
- Browser: Castorama is a SPA, wait 2-3 s between `navigate` and `get_page_text`. Castorama and Amazon
  were already set to 91120 / Castorama Les Ulis in Dylan's Chrome. Amazon `find` on a search page can
  exceed the context limit; use `get_page_text` instead.
- Deploy header warns about `stats_page_watcher`; that only matters for the x17 hub.
- Prices are static in the `ITEMS` array in `buy.html`; `KITCHEN_EUR` in `closet_riser.py` mirrors the
  recommended total and must be updated by hand.

**Key files & commands:**
- `under_sink_shelf/build_model.py` — geometry + design checks; `python3 under_sink_shelf/build_model.py` writes `model.json`
- `under_sink_shelf/plan_view.py` — `renders/shelf_plan.png`
- `under_sink_shelf/render_blender.py` — `~/Software/blender-5.1.0-linux-x64/blender -b --factory-startup --python under_sink_shelf/render_blender.py`
- `under_sink_shelf/closet_riser.py [n]` — cut plan (`renders/closet_cut_plan.png`), cost table, sag check
- Publish: `./under_sink_shelf/publish_to_site.sh`, then in `~/PycharmProjects/dylan-cern-site` commit and
  `./scripts/deploy-eos.sh` (needs `kinit dneff@CERN.CH`)

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
