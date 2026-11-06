// GEOM-BEGIN
// Pure geometry in cm, shared by the page and by check_clearance.mjs.
// Frame: X along the wall, 0 at the fridge front, + away from the fridge.
//        d = distance out from the wall.  Y up.  Hinge side of the fridge doors = far from the wall.
const G = {
  fridge: { w: 59, depth: 63, h: 200, freezerH: 80, doorT: 6 },
  doorR: 59.3,            // swept radius of the door slab about its hinge: sqrt(59^2 + 6^2)
  margin: 3,              // design clearance added to the swept radius
  hingeY: 120,            // table top height
  railT: 3.2,             // wall rail thickness: the table hinge axis sits this far from the wall
  topT: 3.0,              // table top thickness
  depth: 55,              // table depth from the hinge axis
  angleDeg: 55,           // fridge-side edge angle from the wall (tangent to the door arc + margin)
  hingeLen: 140,          // length of the hinged edge along the wall
  farSkewDeg: 20,         // far edge leans in by this much from square
  cornerR: 5,             // radius of the two outer corners
  railX: [32, 180],       // wall rail span
  braceX: [75, 118, 161], // folding brackets
  stool: 70,
  recycle: { x0: 60, w: 45, t: 35, h: 60 },
  trash:   { x0: 110, w: 30, t: 28, h: 50 },
};
// Hinge pivot of the fridge doors, in (X, d) plan coordinates.
const pivot = () => ({ x: 0, d: G.fridge.w });
// Fridge-side edge: s = s0 + u / tan(alpha), u measured from the table hinge axis.
function edgeS0() {
  const a = G.angleDeg * Math.PI / 180, R = G.doorR + G.margin;
  const cy = G.fridge.w - G.railT;                     // pivot distance from the table hinge axis
  return -cy / Math.tan(a) + R / Math.sin(a);
}
// Table plan outline in (s = X, u = depth from hinge axis), counter-clockwise, rounded outer corners.
function tableOutline() {
  const a = G.angleDeg * Math.PI / 180, sk = G.farSkewDeg * Math.PI / 180;
  const s0 = edgeS0(), D = G.depth, s1 = s0 + G.hingeLen;
  const nearOuter = [s0 + D / Math.tan(a), D], farOuter = [s1 - D * Math.tan(sk), D];
  const corner = (p, from, to, r) => {   // quarter-ish arc replacing the corner p between segments from->p->to
    const v1 = [from[0]-p[0], from[1]-p[1]], v2 = [to[0]-p[0], to[1]-p[1]];
    const l1 = Math.hypot(...v1), l2 = Math.hypot(...v2);
    const u1 = [v1[0]/l1, v1[1]/l1], u2 = [v2[0]/l2, v2[1]/l2];
    const ang = Math.acos(u1[0]*u2[0] + u1[1]*u2[1]), t = r / Math.tan(ang/2);
    const A = [p[0]+u1[0]*t, p[1]+u1[1]*t], B = [p[0]+u2[0]*t, p[1]+u2[1]*t];
    const bis = [u1[0]+u2[0], u1[1]+u2[1]], bl = Math.hypot(...bis);
    const c = [p[0] + bis[0]/bl * r/Math.sin(ang/2), p[1] + bis[1]/bl * r/Math.sin(ang/2)];
    const a0 = Math.atan2(A[1]-c[1], A[0]-c[0]); let a1 = Math.atan2(B[1]-c[1], B[0]-c[0]);
    let da = a1 - a0; while (da > Math.PI) da -= 2*Math.PI; while (da < -Math.PI) da += 2*Math.PI;
    const pts = []; for (let i = 0; i <= 8; i++) { const t2 = a0 + da*i/8; pts.push([c[0]+r*Math.cos(t2), c[1]+r*Math.sin(t2)]); }
    return pts;
  };
  const h0 = [s0, 0], h1 = [s1, 0];
  return [h0, h1, ...corner(farOuter, h1, nearOuter, G.cornerR), ...corner(nearOuter, farOuter, h0, G.cornerR)];
}
// --- 2D convex helpers (plan view) ---
function hull(pts) {
  const p = pts.slice().sort((a, b) => a[0]-b[0] || a[1]-b[1]), cr = (o,a,b) => (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0]);
  const lo = [], up = [];
  for (const q of p) { while (lo.length>1 && cr(lo[lo.length-2], lo[lo.length-1], q) <= 0) lo.pop(); lo.push(q); }
  for (const q of p.reverse()) { while (up.length>1 && cr(up[up.length-2], up[up.length-1], q) <= 0) up.pop(); up.push(q); }
  return lo.slice(0,-1).concat(up.slice(0,-1));
}
function segDist(p, a, b) {
  const dx=b[0]-a[0], dy=b[1]-a[1], t=Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy||1)));
  return Math.hypot(p[0]-a[0]-t*dx, p[1]-a[1]-t*dy);
}
function inside(p, poly) { // convex, CCW
  for (let i=0;i<poly.length;i++){ const a=poly[i], b=poly[(i+1)%poly.length];
    if ((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]) < 0) return false; } return true;
}
function segsCross(a,b,c,d){ const o=(p,q,r)=>Math.sign((q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0]));
  return o(a,b,c)!==o(a,b,d) && o(c,d,a)!==o(c,d,b); }
function polyGap(A, B) { // 0 if they overlap, else the smallest distance
  for (const p of A) if (inside(p, B)) return 0;
  for (const p of B) if (inside(p, A)) return 0;
  let m = Infinity;
  for (let i=0;i<A.length;i++) for (let j=0;j<B.length;j++) {
    const a0=A[i],a1=A[(i+1)%A.length],b0=B[j],b1=B[(j+1)%B.length];
    if (segsCross(a0,a1,b0,b1)) return 0;
    m = Math.min(m, segDist(a0,b0,b1), segDist(a1,b0,b1), segDist(b0,a0,a1), segDist(b1,a0,a1));
  }
  return m;
}
// Door slab (plan view) after opening by theta (deg).  Local: x in [-doorT,0], z from hinge toward wall.
function doorPlan(thetaDeg) {
  const t = thetaDeg*Math.PI/180, P = pivot(), c = Math.cos(t), s = Math.sin(t);
  const f = G.fridge, loc = [[-f.doorT,0],[0,0],[0,f.w],[-f.doorT,f.w]];  // (x', z') with z' toward the wall
  return loc.map(([x,z]) => [P.x + x*c + z*s, P.d - (-x*s + z*c)]); // -> (X, d)
}
// Table plan footprint (convex hull of both faces) when folded by phi (deg) about the hinge axis.
function tablePlan(phiDeg) {
  const p = phiDeg*Math.PI/180, out = tableOutline(), pts = [];
  for (const [s,u] of out) for (const v of [0, -G.topT]) {      // v: local height below the hinge axis (top face at 0)
    pts.push([s, G.railT + u*Math.cos(p) - v*Math.sin(p)]);
  }
  return hull(pts);
}
// GEOM-END
