// Usage: node check_clearance.mjs [path/to/geom_block.js | table.html]
// Sweeps the fridge door from 0 to 120 degrees and reports the smallest gap to the table
// (out = in use, 0 deg; folded down against the wall = 90 deg), the brackets, the bins and the back wall.
import fs from "node:fs";
const src = fs.readFileSync(process.argv[2] ?? new URL("./geom_block.js", import.meta.url), "utf8");
const body = src.split("// GEOM-BEGIN")[1].split("// GEOM-END")[0];
const api = new Function(body + "; return {G, tablePlan, doorPlan, tableOutline, edgeS0, polyGap, stay, armPoint};")();
const { G, tablePlan, doorPlan, tableOutline, edgeS0, polyGap, stay, armPoint } = api;
console.log(`fridge-side edge starts ${edgeS0().toFixed(1)} cm from the fridge front at the pivot axis`);
const o = tableOutline();
console.log("outline (s,u) cm:", o.filter((_, i) => i < 2 || i % 9 === 0 || i === o.length - 1).map(p => p.map(v => v.toFixed(1)).join(",")).join("  "));
const sweep = (poly) => { let m = Infinity, at = 0; for (let th = 0; th <= 120; th += 0.5) { const g = polyGap(doorPlan(th), poly); if (g < m) { m = g; at = th; } } return [m, at]; };
let worst = Infinity;
for (const phi of [0, 15, 45, 75, 90]) {
  const [m, at] = sweep(tablePlan(phi));
  console.log(`table folded down ${String(phi).padStart(2)} deg: min door gap ${m.toFixed(2)} cm (door at ${at} deg)`);
  worst = Math.min(worst, m);
}
const plate = [[G.braceX[0] - 3, 0], [G.braceX[1] + 3, 0], [G.braceX[1] + 3, 1], [G.braceX[0] - 3, 1]];
const [mp] = sweep(plate); console.log(`bracket plates: min door gap ${mp.toFixed(2)} cm`);
for (const [name, c] of [["recycle bin", G.recycle], ["trash bin", G.trash]]) {
  const [mc] = sweep([[c.x0, 4], [c.x0 + c.w, 4], [c.x0 + c.w, 4 + c.t], [c.x0, 4 + c.t]]); console.log(`${name}: min door gap ${mc.toFixed(2)} cm`);
}
// stowed table hangs from y = hingeY - topT down by `depth`; the tallest bin is 60 cm
const bottom = G.hingeY - G.topT - G.depth; console.log(`folded table bottom edge ${bottom.toFixed(1)} cm up; tallest bin ${G.recycle.h} cm -> ${(bottom - G.recycle.h).toFixed(1)} cm above it`);
// brace: link length must stay constant and the stay must reach from straight (out) to folded
const s0 = stay(armPoint(0)), s90 = stay(armPoint(90));
console.log(`brace links ${s0.l.toFixed(1)} cm each; at 0 deg knee offset ${(Math.hypot(s0.K.d - (s0.Q.d + s0.P.d) / 2, s0.K.y - (s0.Q.y + s0.P.y) / 2)).toFixed(2)} cm (straight = 0); folded knee at ${s90.K.d.toFixed(1)}, ${s90.K.y.toFixed(1)} (d, y)`);
const bx = G.back; console.log(`back wall X=${-G.fridge.depth - bx.t}..${-G.fridge.depth}, opening d=${bx.openD0}..${bx.openD0 + bx.openW}; fridge side face at d=${G.fridge.w} -> ${bx.openD0 - G.fridge.w} cm to the doorway`);
const ok = worst > 0 && mp > 0;
console.log(ok ? "PASS: door clears the table, out or folded down" : "FAIL");
process.exit(ok ? 0 : 1);
