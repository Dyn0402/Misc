# Under-sink shelf

Two-shelf design for the cabinet under the kitchen sink in Palaiseau. Moved here
from the `dylan-cern-site` repo on 2026-10-17. The handoff with the decisions and
open questions is in [HANDOFF.md](HANDOFF.md).

- `index.html`: Design tab. Build review, renders, and a Three.js assembly animation
  that reads `model.json`. Loads Three.js from jsdelivr.
- `buy.html`: Cost & buy list tab. Itemized list with Castorama prices and an
  Amazon.fr comparison. Totals recompute from the "own it" tick boxes. Prices are
  static in the `ITEMS` array (read 2026-10-16).
- `model.json`: generated geometry. Regenerate after editing the design:

      python3 under_sink_shelf/build_model.py

  The script runs design checks (margins, post clearances, keep-out zones) and
  stops with a message if one fails.
- `plan_view.py`: 2D plan view, writes `renders/shelf_plan.png` (matplotlib).
- `render_blender.py`: headless Cycles renders to `renders/`:

      ~/Software/blender-5.1.0-linux-x64/blender -b --factory-startup --python under_sink_shelf/render_blender.py

Open the HTML pages in a browser to view them. The Design tab loads `model.json`
and the renders relative to its own folder.

Measurements (Dylan): opening 400 mm wide, 500 mm deep, floor to basin bottom
600 mm. Trap and hose positions are estimates from a photo. Re-measure before
cutting. The photos Dylan supplied are for reference only and are not published.
