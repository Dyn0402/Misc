// Usage: node check_clearance.mjs [path/to/geom_block.js | table.html]
// Sweeps the fridge door from 0 to 120 degrees and reports the smallest gap to the table.
import fs from "node:fs";
const src = fs.readFileSync(process.argv[2] ?? new URL("./geom_block.js", import.meta.url), "utf8");
const body = src.split("// GEOM-BEGIN")[1].split("// GEOM-END")[0];
const api = new Function(body + "; return {G, tablePlan, doorPlan, tableOutline, edgeS0, polyGap};")();
const { G, tablePlan, doorPlan, tableOutline, edgeS0, polyGap } = api;
console.log(`fridge-side edge starts ${edgeS0().toFixed(1)} cm from the fridge front at the hinge axis`);
const o = tableOutline(); console.log("outline (s,u):", o.filter((_, i) => i % 8 === 0 || i < 2).map(p => p.map(v => v.toFixed(1)).join(",")).join("  "));
let worst = Infinity;
for (const phi of [0, 5, 15, 45, 90]) {
  let m = Infinity, at = 0;
  for (let th = 0; th <= 120; th += 0.5) { const g = polyGap(doorPlan(th), tablePlan(phi)); if (g < m) { m = g; at = th; } }
  console.log(`table fold ${String(phi).padStart(2)} deg: min door gap ${m.toFixed(2)} cm (at door ${at} deg)`);
  worst = Math.min(worst, m);
}
// rail (d in [0, railT], X in railX) against the door
const rail = [[G.railX[0], 0], [G.railX[1], 0], [G.railX[1], G.railT], [G.railX[0], G.railT]];
let mr = Infinity; for (let th = 0; th <= 120; th += 0.5) mr = Math.min(mr, polyGap(doorPlan(th), rail));
console.log(`wall rail: min door gap ${mr.toFixed(2)} cm`);
// cans against the door (floor level; the upper door starts at 80 cm so only the freezer door matters)
for (const [name, c] of [["recycle", G.recycle], ["trash", G.trash]]) {
  const box = [[c.x0, 0], [c.x0 + c.w, 0], [c.x0 + c.w, c.t], [c.x0, c.t]]; let mc = Infinity;
  for (let th = 0; th <= 120; th += 0.5) mc = Math.min(mc, polyGap(doorPlan(th), box));
  console.log(`${name} can: min door gap ${mc.toFixed(2)} cm`);
}
console.log(worst > 0 && mr > 0 ? "PASS: door clears the table, folded or down" : "FAIL");
process.exit(worst > 0 && mr > 0 ? 0 : 1);
