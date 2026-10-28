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

## Under-sink shelf — updated 2026-10-17 (dylan-MS-7C84)

**2026-10-28, closet risers:** Dylan asked whether the same wood could also make risers for the
clothes closet (existing shelves 80 x 40 cm, about 40 cm apart; new riser = same footprint,
20 cm tall, a board on 4 feet). `under_sink_shelf/closet_riser.py` has the cut plan and cost.
Decided: ONE riser, top 750 x 400 (closet ~76 cm wide with obstacles), legs 182 mm, 2 screws
per leg; brackets and glue optional on the riser. It fits in the kitchen board and batten for
0 EUR extra (2-3 risers would be +25.59). `buy.html` updated for it, and the coping saw swapped
for a Stanley JET-CUT fine 450 mm crosscut saw (17.90, Castorama, read 2026-10-28; Amazon not
checked). Then (same day) screws switched to 2 x Diall 20-packs (11.78; Les Ulis had 1 in stock),
Amazon prices added for the saw (16.92) and 200 A2 screws (14.90). Totals: recommended 101.43,
all-Castorama 110.92, Amazon wherever possible 124.22 (Amazon free delivery to 91120 from 45 EUR).
Leftovers: board ~360 x 400, batten ~175 mm: enough for a small U-shaped riser 36 x 20 x 20 cm.
Brackets then switched to the product Dylan found: VFANDV 20 stainless 40x40x16 with screws,
7.79 EUR, https://www.amazon.fr/dp/B0D6YTK3KT (photo: screws 15 mm, 4 holes; title says 80 screws,
photo 60). Totals now: recommended 99.47, all-Castorama 110.92, Amazon wherever possible 122.26.
The other Amazon links in buy.html are still search links, not products.
Jar riser (kitchen top closet, empty jars): 600 x 400 top on four 162 mm legs cut from Dylan's
two 1 m x 20 mm dowels, 18 cm tall, one 4x40 screw + glue per leg. It only fits on the board
because the two kitchen shelves are now cut NESTED (second turned 180 deg, narrow end at 191 mm,
621 mm total instead of 860); board is then used to within the 10 mm end trims. Design tab cut
list updated (also dropped the stale v4 notch row). Jar-closet shelf size not confirmed by Dylan.
Published to the site on 2026-10-28.

**Resume:** Shelf v10 and the Cost & buy list tab are live; wait for Dylan's feedback on the shape, then check Palaiseau stock.

**Goal:** Two-shelf under-sink shelf for Dylan's cabinet in Palaiseau. Was published on the site at https://dylan-neff.web.cern.ch/misc/shelf/ (Design tab: `index.html`, Cost & buy list tab: `buy.html`). Source moved here from `dylan-cern-site/misc/shelf/` on 2026-10-17. The built pages are still deployed from the site repo: run `publish_to_site.sh` here, then commit and deploy there.

**Layout (confirmed by Dylan, drawn and agreed in chat):** standing at the door looking in, the right is a solid wall (dishwasher behind it) and the shelves go against it. Cabinet = 40 cm wide at the door x 50 cm deep, its back is the outer kitchen wall. To the LEFT is an extra space 70 cm wide, same 50 cm depth, level with the cabinet, on the SAME straight back wall (110 cm from dishwasher wall to far left). The oven stands in front of it and blocks it. A corner counter covers everything. The basin starts 6 cm from the dishwasher wall and reaches 6 cm over the extra space. The extra space is not deeper than the cabinet; earlier versions wrongly put it behind the back wall.

**Axes (output frame, model.json / renders / page):** +x toward the dishwasher wall (right), so left = -x; +y away from you (y=0 door line, y=500 back wall); z up; right-handed. `build_model.py` is AUTHORED in the old frame (origin back-right corner, x grows to the left, y grows to the front) and `rot()` turns it 180 degrees about z on output. So constants in the file read as "distance left of the dishwasher wall" and "distance in front of the back wall". `plan_view.py` uses the authoring frame.

**Done:**
- 2026-10-17: source moved from `dylan-cern-site/misc/shelf/` to `under_sink_shelf/` (Misc commits `5b78a51`, `8fa1936`). Rebuilt `model.json` and the plan PNG match the site copies byte for byte. The built pages are published into the site with `under_sink_shelf/publish_to_site.sh` (site commits `d3242c1`, `9b349cf`). The live site is unchanged. Blender renders not re-run after the move.
- v7-v10: layout above; rinse bottle at the back, 1 cm left of the door opening (just out of view from the door); detergent boxes on the floor at the back, bin bags on the middle shelf; basin shifted left; walls in the animation made transparent (opacity 0.18); 2D plan view `renders/shelf_plan.png` first on the page.
- Shelf shape (v10): five sides, 370 back edge, 430 deep, 100 front edge; left edge straight for 100 mm at the back then one diagonal (about 39 degrees) to the 100 mm front edge. Area 1146 cm2. Only 10 of the 40 cm width is left at the front, so it is easy to reach into the extra space. Posts unchanged (back-right, front-right, back-left); the front-left is a cantilever.
- Castorama pages re-checked in Chrome on 2026-10-16: board 16.90, batten 8.69, screws 19.90, linseed 8.79 (all unchanged).
- `buy.html`: itemized list with Castorama prices and an Amazon.fr comparison, totals with "own it" tick boxes. Recommended basket 99.64 EUR, all-Castorama 109.13 EUR. Amazon wins only on brackets (22 stainless 40x40 with 88 screws, 9.75 EUR); no like-for-like timber on Amazon.
- Fixed a wrong claim: the 9 brackets need about 18 SHORT screws (3.5 x 16 mm, shelf is 18 mm thick), not the 4 x 40 pack.

**In progress / where it stopped:**
- Nothing half-done. Last deploy is commit `083ad93` on `master`, pushed.
- Dylan has not yet reacted to the v10 shape. I read "more space toward the back, less toward the front" as more SHELF at the back and a bigger cut-out at the front. If he meant the opposite, swap the two end widths in `OUTLINE_LOW`.

**Next steps:**
1. Ask Dylan if the v10 shape is right; adjust `OUTLINE_LOW` in `build_model.py` if not.
2. Stock at Palaiseau was NOT checked (Castorama asks for a postal code; I did not type one without permission). Ask Dylan for the code (91120?) or to go ahead.
3. Done 2026-10-28: Amazon bracket screws are 15 mm (VFANDV pack); 16 mm wide brackets are fine on 27 mm posts.
4. Still unconfirmed guesses: extra space 70 cm wide, oven drawn as a thin 20 mm front panel (does its body reach back into the space?), basin 6 cm over the extra space, top shelf only 82 mm below the basin, counter geometry.
5. Glue: Pattex Power says "water resistant" without a D-class; Sader Pro D3 100 g (9.89 EUR) states D3.

**Gotchas / decisions:**
- Left/right confusion cost many turns. Do not reason about orientation from the render; use the layout paragraph above. The 3D iso renders hide the oven and the far-left wall so the extra space is visible.
- Z-fighting made a black bar when two coplanar faces overlapped; avoid overlapping wall slabs.
- Browser tips: Castorama is a single-page app, `get_page_text` right after `navigate` returns the previous page; put a `computer wait` of 2-3 s between them in `browser_batch`. Amazon.fr served English text and prices for Paris 75001.
- The deploy script's header warns about `stats_page_watcher` on the DAQ machine; it only matters for the x17 hub, and shelf deploys have run without issue.
- Prices are static in the `ITEMS` array in `buy.html` (read 2026-10-16); update them there.

**Key files & commands:**
- `under_sink_shelf/build_model.py` — geometry source and design checks; `python3 under_sink_shelf/build_model.py` writes `model.json` (checks must pass)
- `under_sink_shelf/render_blender.py` — `~/Software/blender-5.1.0-linux-x64/blender -b --factory-startup --python under_sink_shelf/render_blender.py` writes `renders/shelf_{iso,iso_open,front}.png`
- `under_sink_shelf/plan_view.py` — `python3 under_sink_shelf/plan_view.py` writes `renders/shelf_plan.png` (matplotlib)
- `under_sink_shelf/index.html` — Design tab (Three.js animation reads `model.json`); `under_sink_shelf/buy.html` — Cost & buy list tab
- Publish: `./under_sink_shelf/publish_to_site.sh` copies `index.html`, `buy.html`, `model.json` and `renders/` into `dylan-cern-site/misc/shelf/`. Then deploy from the site repo with `./scripts/deploy-eos.sh` (needs a Kerberos ticket: `kinit dneff@CERN.CH`).
