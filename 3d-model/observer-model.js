// Gratheon Entrance Observer — parametric model of the Phase 3 production kit.
// Single source of truth for the browser viewer (index.html) and the GLB
// exporter (export-glb.mjs). All dimensions are in millimetres; the scene is
// built in metres (glTF convention).
//
// Axes match robotic-beehive/model/hive-model.js and
// beehive-sensors/model/scale-model.js:
//   X = left/right, Y = up, Z = front(+)/back(-), entrance at +Z.
//
// The Observer is built in its own frame and then placed on a hive, on the
// beehive scale or on the Robotic Beehive. Its origin is the middle of the
// entrance floor on the front face of the hive; +Z points away from the hive.
//
// Layout rules:
// - One slim arch: two side arms, the head across the top, a small ridged roof
//   over the middle and the landing board hinged between the arms. The entrance
//   stays free.
// - The doorway is moved forward onto the board by a short porch, so every bee
//   that goes in or out crosses the porch mouth on the board, even if it
//   landed on the hive wall. The mouth is the counting line.
// - The camera looks down at the board, tilted toward the hive so it also sees
//   the porch roof and the bottom of the hive wall. Arms, cables and the head
//   are outside its field of view.
// - Every cable enters from below, under the right cheek, and runs inside it.
// - The Observer hangs on two ears (entrance plate, scale risers or the robot
//   entrance frame), so the camera lands in the same place on every hive.

import * as THREE from 'three';

const MM = 0.001;

export const DEFAULTS = {
  context: 'hive', // 'hive' = on a hive stand, 'scale' = on the beehive scale, 'robot' = on the Robotic Beehive
  power: 'poe', // 'poe' = opal canopy, PoE+ powered; 'solar' = solar canopy + battery cassette
  boxes: 2, // hive bodies
  hive: { w: 506, d: 450, h: 285, lid: 80, bottomBoard: 60, entrance: 300, slot: 15 }, // Estonian hive (outer)
  stand: 200, // wooden hive stand height
  arch: { inner: 440, cheek: 14, board: 190 }, // inner width between the arms, arm thickness, board depth
  canopy: { ridge: 284, z0: 60, len: 150, w: 480, t: 4, slope: 4 }, // ridge underside height, start z, length, width, sheet, degrees each side
  head: { y: 203, z: 135, w: 438, h: 50, d: 90 }, // underside height, centre z, size
  camera: { eye: 185, hfov: 90, aspect: 16 / 9, px: 3840, tilt: 16 }, // lens height above the entrance floor, degrees, sensor width px, degrees toward the hive
  porch: { depth: 40, w: 312, wall: 4, roof: 4 }, // entrance porch: mouth distance from the hive face, inner width, wall and roof thickness
  boardSlope: 6, // degrees
  scale: { feet: 25, height: 112, deck: { w: 560, d: 510 }, base: { w: 504, d: 454, h: 60 } }, // from beehive-sensors DEFAULTS
  robot: { plinth: 200, bottomBoard: 150, post: { x: 372, z: 302 }, e: 22, clad: 18 }, // from robotic-beehive DEFAULTS
};

// ---------------------------------------------------------------------------
// Part descriptions (shown on hover in the viewer, exported as glTF extras)
// ---------------------------------------------------------------------------
export const PARTS = {
  plate: ['Entrance plate', 'Aluminium plate, powder-coated matt grey because its top edge is in the camera view, screwed to the bottom board with four stainless wood screws beside the entrance (a paper drill template is in the box). Its window matches the 300 × 15 mm entrance, it carries the entrance porch, and its two bent ears are all the Observer hangs on. The plate stays on the hive; the Observer lifts off in seconds for an inspection, a move or winter.'],
  riser: ['Scale risers', 'Two printed ASA brackets that hook onto the front rail of the beehive scale and carry the same ears as the entrance plate. The Observer then hangs on the scale base, not on the hive, so its own weight, the bees on the board and snow on the roof are never weighed.'],
  robotFront: ['Robot entrance frame', 'The Robotic Beehive entrance tunnels end in the same ears, so the same Observer hangs on the cabinet front. Power and data come from the robot PoE switch inside a corner post, and the robot can use the entrance counts to choose when to inspect.'],
  porch: ['Entrance porch', 'A 40 mm deep, 15 mm high tunnel across the full entrance, moulded in the same matt grey as the board. It moves the doorway forward onto the landing board. A bee that lands on the hive wall has to walk down onto the porch roof and step off its front edge, so every bee going in or out crosses the porch mouth, in full view. The mouth is the counting line. It is shorter than the tunnels of most electronic bee counters and open to the air, with no glass to clean or fog up.'],
  reducer: ['Entrance reducer', 'Grey slide in the porch roof (not yellow: it is where bees walk, so it must not look like a bee). Pushed forward it narrows the porch mouth against robbing, hornets or cold; parked back it leaves the full width open. It sits in the camera view, so the software knows its position.'],
  countLine: ['Counting line', 'A faint printed line just in front of the porch mouth, for people, not for the software: the software counts a track as in when it ends inside the porch and out when it starts there.'],
  thumb: ['Thumbscrews', 'One captive thumbscrew per side, through the ear into the arm. Hang the Observer on the ears, turn two screws and it is done: no tools, and the camera lands in exactly the same place every time.'],
  cheek: ['Side arms', 'Folded 2 mm aluminium box sections, powder-coated graphite, leaning forward from the entrance plate to the head. They are only as wide as they need to be to carry the head, so the arch stays light and open and bees can also fly in from the sides. The field of view stops short of their inner faces, so they never show in the video.'],
  channel: ['Cable channel', 'The right arm is hollow. The PoE cable enters it from below and runs up inside it to the head, so no cable is in the sun, in the rain or in front of the lens.'],
  gland: ['Cable entries', 'Under the right arm, facing the ground: the PoE cable gland and the accessory socket. Water runs off them, not into them, and the cable leaves with a drip loop.'],
  m12: ['Accessory port', 'M12 8-pin socket with the pinout of the beehive scale front connector: 5 V out, ground, 1-Wire, UART, wake and shield. One short lead to the scale powers the scale pod from the Observer and shares time and readings, so the scale needs no solar board and both upload through one link.'],
  head: ['Head', 'Extruded aluminium housing, IP65, across the top of the arch. It is also the heatsink: the compute sled presses onto it through a thermal pad, and the fins on top shed heat into the open gap under the roof. No fan to clog with dust or propolis.'],
  camera: ['Camera module', '8 MP (3840 × 2160) Sony STARVIS 2 sensor on its own MIPI CSI board with a locked-focus, low-distortion M12 lens, 90° wide. It sits 185 mm above the board, about 135 mm out from the hive, and is tilted 16° back toward the hive. It sees nearly the whole board, the porch roof and the bottom 35 mm of the hive wall, so bees that land on the wall are tracked from the moment they land. On the board that gives about 10 px per mm, a bee is about 140 px long and a varroa mite about 15 px, which is enough for pose keypoints and mites. A global-shutter module can replace it without changing the housing.'],
  hood: ['Lens hood + window', 'Matt black cone with a flat AR-coated glass window at its tip, facing the ground. Rain cannot reach it, the sky never reflects in it and the roof keeps direct sun off it. A 0.3 W heater film clears dew on cold mornings.'],
  led: ['Light bars', 'Two diffused LED bars beside the lens, with crossed polarisers on the LEDs and the lens to remove glints from shiny bees and wet pollen. They only flash in sync with the exposure at dusk or in deep shade, so they add less than 0.3 W on average.'],
  mic: ['Microphone', 'MEMS microphone behind a mesh under the head. Entrance audio (drone flight, piping, hornets, fanning) is stored with the counts for audio + video models.'],
  sensor: ['Light + climate sensor', 'Ambient light, temperature and humidity. The supervisor uses them to decide when bees can fly, which is when the computer has to run.'],
  supervisor: ['Supervisor board', 'Always-on ESP32-S3 board, the same carrier design as the beehive scale: PoE+ input, 12–24 V DC input, solar charger, fuel gauge and a load switch for the compute sled. It idles at about 0.1 W and only powers the computer when bees can fly (light, temperature, no rain, schedule). It also keeps time and forwards the scale readings.'],
  compute: ['Compute cassette', 'Raspberry Pi 5 (8 GB), Hailo-8 26 TOPS accelerator and 256 GB NVMe on one sled. It slides out of the right arm after a quarter-turn, like the beehive scale pod. The sled is the upgrade path: housing, camera, power and connectors stay the same, and a Jetson Orin NX or the next accelerator slides into the same bay when pose models need more compute.'],
  face: ['Service face', 'Honey-yellow face of the compute cassette: status ring, setup button and a USB-C port under a flap for copying full-resolution research clips on site.'],
  battery: ['Battery cassette', 'Solar version: four LiFePO4 32700 cells (12.8 V, 77 Wh) on a sled in the left bay, charged from the roof panels. LiFePO4 tolerates the heat of a summer day in the head better than Li-ion. In the PoE version this bay is empty or holds an LTE modem.'],
  blank: ['Left bay cover', 'Cover of the left bay. Behind it goes the battery cassette (solar version) or an LTE modem for apiaries without Wi-Fi or Ethernet.'],
  canopy: ['Roof', '480 × 150 mm of 4 mm opal (light-diffusing), UV-stabilised polycarbonate, cold-bent into a shallow ridge and set on four standoffs over the head. It keeps sun and rain off the head and the lens. Rain runs to the two side eaves and drips beside the landing board, outside the view. Being opal, it casts only a faint, soft shadow on the board, which does not cut bees in half in the image.'],
  solarCanopy: ['Solar roof', 'The same roof with two 5 W ETFE panels laminated on its slopes (10 W). Bees fly when the sun shines, so the panels produce the most when the Observer has the most to do. The solar version samples (2 minutes in every 15) rather than recording all day.'],
  board: ['Landing board', '10 mm HDPE, hinged between the arms at a 6° slope so rain drains off. It is the background of every frame, so it is part of the product: matt, neutral light grey. White would overexpose in the sun and hide pale pollen loads.'],
  insert: ['Board insert', 'The top 3 mm layer slides out forward for washing off droppings, dead bees and propolis. Spare inserts are cheap to keep.'],
  marker: ['Calibration markers', 'Four ArUco markers and a millimetre scale on the insert. The software finds them in every frame, so it knows the exact mm per pixel for bee size and speed, straightens the view, and raises an alert if the Observer has been knocked.'],
  hinge: ['Board hinge', 'Stainless pins. The board folds up flat for shipping and swings down if something hits it.'],
  harness: ['Internal harness', 'PoE and accessory lines from the entries under the right arm, up the cable channel to the supervisor board in the head.'],
  cable: ['Cables', 'One PoE cable (power and data, up to 100 m) from under the right arm, run along the ground. With the scale, one short M12 lead joins the Observer and the scale.'],
  fov: ['Camera field of view', 'What the camera sees: the bottom of the hive wall, the porch and the landing board, about 400 mm across. The arms, head, roof and cables are all outside it.'],
  bee: ['Bees', 'Honey bees on the landing board. At 4K each worker is about 140 px long, big enough for pose keypoints, pollen loads and mites.'],
  hive: ['Hive', 'A standard hive: bottom board, bodies and lid. The only change is the entrance plate screwed to the bottom board.'],
  stand: ['Hive stand', 'Any stand works: the Observer hangs on the hive entrance and does not touch the stand.'],
  scale: ['Beehive scale', 'Gratheon beehive scale, simplified. The Observer hangs on its front rail with two risers, and one M12 lead powers the scale pod and carries its readings.'],
  scaleLink: ['Scale connector', 'M12 socket under the front rail of the beehive scale. The Observer lead plugs in here in place of the solar landing board.'],
  robot: ['Robotic Beehive', 'Ghost of the Robotic Beehive cabinet. Its entrance tunnels end in the entrance frame the Observer hangs on, and the cable runs inside the cabinet to the robot PoE switch.'],
};

// ---------------------------------------------------------------------------
// Derived geometry and figures
// ---------------------------------------------------------------------------
const rad = (deg) => (deg * Math.PI) / 180;

export function derive(p) {
  const H = p.hive, R = p.robot, S = p.scale;
  let origin, hiveBase, bottomBoard, entranceY;
  if (p.context === 'scale') {
    const deckTop = S.feet + S.height;
    hiveBase = deckTop;
    bottomBoard = H.bottomBoard;
    entranceY = hiveBase + 12;
    // In front of the deck (railZ + 6), at entrance level: only the porch touches the weighed hive.
    origin = [0, entranceY, S.deck.d / 2 + 14];
  } else if (p.context === 'robot') {
    hiveBase = R.plinth + R.bottomBoard;
    bottomBoard = R.bottomBoard;
    entranceY = hiveBase - H.slot; // the slot is at the top of the tall varroa bottom board
    origin = [0, entranceY, R.post.z + R.e / 2 + R.clad];
  } else {
    hiveBase = p.stand;
    bottomBoard = H.bottomBoard;
    entranceY = hiveBase + 12;
    origin = [0, entranceY, H.d / 2];
  }
  const cam = p.camera, P = p.porch;
  const tanB = Math.tan(rad(p.boardSlope));
  const boardY = (z) => -2 - (z - 5) * tanB; // board surface height at local z
  const vfov = 2 * Math.atan(Math.tan(rad(cam.hfov / 2)) / cam.aspect);
  const wallZ = H.d / 2 - origin[2]; // hive front face in the observer frame (≤ 0)
  const porchTop = H.slot + 2 + P.roof; // top of the porch roof
  // The lens hangs 18 mm under the head floor and swings with the camera tilt.
  const tilt = rad(cam.tilt), drop = p.head.y - cam.eye;
  const eye = new THREE.Vector3(0, p.head.y - drop * Math.cos(tilt), p.head.z - drop * Math.sin(tilt));
  // A camera ray (a across, b along the image height) tilted toward the hive.
  const ray = (a, b) => new THREE.Vector3(a, -1, b).applyAxisAngle(new THREE.Vector3(1, 0, 0), tilt);
  // First surface a ray meets: porch roof, hive wall or landing board.
  const hit = (dir) => {
    let best = (eye.y + 2 + (eye.z - 5) * tanB) / (-dir.y - dir.z * tanB); // board plane
    const tr = (eye.y - porchTop) / -dir.y;
    const pr = eye.clone().addScaledVector(dir, tr);
    if (tr > 0 && tr < best && pr.z >= wallZ && pr.z <= P.depth && Math.abs(pr.x) <= P.w / 2 + P.wall) best = tr;
    if (dir.z < 0) {
      const tw = (wallZ - eye.z) / dir.z;
      if (tw > 0 && tw < best && eye.y + dir.y * tw > porchTop) best = tw;
    }
    return eye.clone().addScaledVector(dir, best);
  };
  const ta = Math.tan(rad(cam.hfov / 2)), tb = Math.tan(vfov / 2);
  // Outline of the view, sampled along the frame edges so it bends over the wall, porch and board.
  const outline = [];
  const edge = (a0, b0, a1, b1) => { for (let i = 0; i < 24; i++) { const u = i / 24; outline.push(hit(ray(a0 + (a1 - a0) * u, b0 + (b1 - b0) * u))); } };
  edge(-ta, -tb, ta, -tb); edge(ta, -tb, ta, tb); edge(ta, tb, -ta, tb); edge(-ta, tb, -ta, -tb);
  const corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([sx, sz]) => hit(ray(sx * ta, sz * tb)));
  const centre = hit(ray(0, 0));
  const fovW = 2 * ta * centre.distanceTo(eye); // across the image, at the optical axis
  const fovD = corners[2].z - wallZ; // from the hive face to the front of the view
  const wallSeen = Math.max(0, corners[0].y - porchTop); // hive wall visible above the porch
  return {
    origin, hiveBase, bottomBoard, entranceY, boardY, tanB, eye, corners, outline, vfov, wallZ, porchTop,
    fovW, fovD, wallSeen, pxPerMm: cam.px / fovW, boardFront: 5 + p.arch.board * Math.cos(rad(p.boardSlope)),
    lidTop: hiveBase + bottomBoard + p.boxes * H.h + H.lid,
  };
}

// Energy budget. Estimates to be replaced by measurements of the Phase 2 units
// (docs/DESIGN.md explains every figure).
export const ENERGY = {
  supervisorW: 0.12, // ESP32-S3 supervisor, regulators, sensors, idle PoE/charger
  activeW: 9, // Pi 5 + Hailo-8 + 4K camera + Ethernet while observing
  bootJ: 125, // ≈25 s boot at 5 W before the first frame
  flightHours: 12, // summer day with flight weather
  sample: { on: 120, period: 900 }, // sampled mode: record 2 min every 15 min
  batteryWh: 77, depth: 0.9,
  panelW: 10, sunHours: 4.5, systemEff: 0.7, // May–August average for Estonia, near-horizontal panel
};
export function energy(e = ENERGY) {
  const base = e.supervisorW * 24;
  const continuous = base + e.activeW * e.flightHours;
  const cycles = (e.flightHours * 3600) / e.sample.period;
  const sampled = base + (cycles * (e.activeW * e.sample.on + e.bootJ)) / 3600;
  const harvest = e.panelW * e.sunHours * e.systemEff;
  const usable = e.batteryWh * e.depth;
  return {
    continuous, sampled, standby: base, harvest,
    standbyDays: usable / base, // rain / cold: the computer stays off
    sampledDays: usable / sampled, // flight weather without sun
  };
}

// ---------------------------------------------------------------------------
// Materials
// ---------------------------------------------------------------------------
function makeMaterials() {
  const std = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.7, metalness: 0, ...o });
  return {
    alu: std(0xc9ced3, { metalness: 0.7, roughness: 0.38 }),
    anod: std(0xa9afb4, { metalness: 0.65, roughness: 0.42 }), // anodised extrusion
    graphite: std(0x34383c, { roughness: 0.55 }), // powder coat
    asa: std(0x2d3033, { roughness: 0.6 }),
    steel: std(0x9aa1a8, { metalness: 0.85, roughness: 0.3 }),
    black: std(0x141516, { roughness: 0.6 }),
    matt: std(0x0b0b0c, { roughness: 0.95 }),
    rubber: std(0x151515, { roughness: 0.95 }),
    pod: std(0xf2b705, { roughness: 0.5 }), // Gratheon honey yellow ASA
    podDark: std(0xc98f00, { roughness: 0.5 }),
    status: std(0xffc21a, { roughness: 0.3, emissive: 0xffb000, emissiveIntensity: 0.9 }),
    pcb: std(0x16301f, { roughness: 0.6 }),
    can: std(0xbfc5ca, { metalness: 0.8, roughness: 0.3 }),
    chip: std(0x121212, { roughness: 0.5 }),
    gasket: std(0x4a4f52, { roughness: 0.9 }),
    white: std(0xf1f0ea, { roughness: 0.8 }),
    led: std(0xfbfaf4, { roughness: 0.4, emissive: 0xfff6dc, emissiveIntensity: 0.25 }),
    board: std(0x9fa39f, { roughness: 0.95 }), // HDPE base
    insert: std(0xb9bcb7, { roughness: 0.97 }), // neutral light grey (≈ N7), matt
    markBlack: std(0x101010, { roughness: 0.9 }),
    markWhite: std(0xf4f4f0, { roughness: 0.9 }),
    markGrey: std(0x6f736f, { roughness: 0.9 }),
    porch: std(0xaeb1ac, { roughness: 0.95 }), // same matt grey family as the board
    porchDark: std(0x8e928d, { roughness: 0.95 }),
    plate: std(0x9ea29d, { roughness: 0.9 }), // matt powder coat: the plate is in the camera view
    opal: new THREE.MeshStandardMaterial({ color: 0xf6f5f0, roughness: 0.35, transparent: true, opacity: 0.8, side: THREE.DoubleSide }),
    opalEdge: std(0xe9e7e0, { roughness: 0.4 }),
    acm: std(0xeeeeea, { roughness: 0.5 }), // aluminium composite, white
    solar: std(0x162a52, { metalness: 0.35, roughness: 0.3 }),
    solarGrid: std(0x8fa3c2, { metalness: 0.6, roughness: 0.4 }),
    glass: new THREE.MeshPhysicalMaterial({ color: 0x9fb8c4, roughness: 0.05, metalness: 0.1, transparent: true, opacity: 0.6 }),
    cellWrap: std(0x2f8f5b, { roughness: 0.45 }),
    cable: std(0x202326, { roughness: 0.7 }),
    wood: [std(0xd7b07a, { roughness: 0.85 }), std(0xcfa46b, { roughness: 0.85 }), std(0xdcba88, { roughness: 0.85 })],
    lid: std(0xb98d5a, { roughness: 0.85 }),
    timber: std(0x7c5536, { roughness: 0.8 }),
    timberDark: std(0x6a462c, { roughness: 0.82 }),
    film: std(0x4a3325, { roughness: 0.8 }),
    beeBody: std(0x5a3a12, { roughness: 0.6 }),
    beeStripe: std(0xd49a1c, { roughness: 0.6 }),
    beeWing: new THREE.MeshStandardMaterial({ color: 0xe8f0f4, roughness: 0.2, transparent: true, opacity: 0.45 }),
    pollen: std(0xf0a020, { roughness: 0.8 }),
    fov: new THREE.MeshBasicMaterial({ color: 0xf2b705, transparent: true, opacity: 0.2, depthWrite: false, side: THREE.DoubleSide }),
    fovLine: new THREE.LineBasicMaterial({ color: 0xe0a800 }),
    robot: std(0x9aa1a8, { metalness: 0.6, roughness: 0.4, transparent: true, opacity: 0.55, depthWrite: false }),
    robotClad: std(0x8a6a48, { roughness: 0.8, transparent: true, opacity: 0.4, depthWrite: false }),
  };
}

// ---------------------------------------------------------------------------
// Builder helpers (geometry cache keeps the GLB small)
// ---------------------------------------------------------------------------
function helpers() {
  const geoCache = new Map();
  const cached = (key, make) => {
    if (!geoCache.has(key)) geoCache.set(key, make());
    return geoCache.get(key);
  };
  const place = (parent, geo, mat, x, y, z, part) => {
    const m = new THREE.Mesh(geo, mat);
    m.position.set(x * MM, y * MM, z * MM);
    m.castShadow = true;
    m.receiveShadow = true;
    if (part) m.userData.part = part;
    parent.add(m);
    return m;
  };
  const box = (parent, sx, sy, sz, mat, x = 0, y = 0, z = 0, part) =>
    place(parent, cached(`b${sx}|${sy}|${sz}`, () => new THREE.BoxGeometry(sx * MM, sy * MM, sz * MM)), mat, x, y, z, part);
  // Box given by its min corner and size.
  const slab = (parent, x0, y0, z0, sx, sy, sz, mat, part) => box(parent, sx, sy, sz, mat, x0 + sx / 2, y0 + sy / 2, z0 + sz / 2, part);
  // Cylinder along an axis ('x' | 'y' | 'z'); r2 makes a cone (r at +axis end, r2 at -axis end)
  const cyl = (parent, r, len, mat, x = 0, y = 0, z = 0, axis = 'y', part, seg = 20, r2 = r) => {
    const m = place(parent, cached(`c${r}|${r2}|${len}|${seg}`, () => new THREE.CylinderGeometry(r * MM, r2 * MM, len * MM, seg)), mat, x, y, z, part);
    if (axis === 'x') m.rotation.z = Math.PI / 2;
    if (axis === 'z') m.rotation.x = Math.PI / 2;
    return m;
  };
  const group = (parent, name, x = 0, y = 0, z = 0, part) => {
    const g = new THREE.Group();
    g.name = name;
    g.position.set(x * MM, y * MM, z * MM);
    if (part) g.userData.part = part;
    parent.add(g);
    return g;
  };
  // Flexible cable through points given in mm.
  const cable = (parent, pts, r, mat, part = 'cable') => {
    const curve = new THREE.CatmullRomCurve3(pts.map(([x, y, z]) => new THREE.Vector3(x * MM, y * MM, z * MM)), false, 'centripetal');
    const m = new THREE.Mesh(new THREE.TubeGeometry(curve, Math.max(24, pts.length * 12), r * MM, 8, false), mat);
    m.castShadow = true;
    m.userData.part = part;
    parent.add(m);
    return m;
  };
  return { box, slab, cyl, group, place, cached, cable };
}

// ---------------------------------------------------------------------------
// Scene
// ---------------------------------------------------------------------------
export function buildObserver(options = {}) {
  const p = { ...DEFAULTS, ...options };
  if (!['hive', 'scale', 'robot'].includes(p.context)) p.context = 'hive';
  if (!['poe', 'solar'].includes(p.power)) p.power = 'poe';
  const d = derive(p);
  const M = makeMaterials();
  const { box, slab, cyl, group, place, cached, cable } = helpers();
  const solar = p.power === 'solar';

  const root = new THREE.Group();
  root.name = 'EntranceObserver';
  const nodes = { root, explode: [] };
  const explodable = (g, dx, dy, dz) => {
    g.userData.home = g.position.clone();
    g.userData.explode = new THREE.Vector3(dx * MM, dy * MM, dz * MM);
    nodes.explode.push(g);
    return g;
  };
  // Cables and bees are hidden in the exploded view (they would float).
  const fieldCables = group(root, 'fieldCables');
  nodes.fieldCables = fieldCables;

  const A = p.arch, C = p.canopy, HD = p.head, H = p.hive;
  const IN = A.inner / 2, OUT = IN + A.cheek; // cheek inner / outer x
  const [ox, oy, oz] = d.origin;
  // Observer frame → world (the Observer is never rotated, only moved).
  const W = (x, y, z) => [ox + x, oy + y, oz + z];

  const obs = group(root, 'observer', ox, oy, oz);
  nodes.observer = obs;

  // ----- mount: entrance plate / scale risers / robot frame ------------------
  const mountPart = { hive: 'plate', scale: 'riser', robot: 'robotFront' }[p.context];
  const mount = group(obs, 'mount', 0, 0, 0, mountPart);
  // ears: bent forward at both ends, outside the cheeks
  const earBottom = p.context === 'hive' ? -12 : -40;
  for (const s of [-1, 1]) {
    slab(mount, s > 0 ? OUT + 1 : -OUT - 4, earBottom, 0, 3, 52 - earBottom, 34, M.plate, mountPart);
  }
  if (p.context === 'hive') {
    // plate with a window matching the entrance slot, four screws beside it
    const E2 = H.entrance / 2 + 4, S = H.slot + 2;
    slab(mount, -OUT - 4, -12, 0, 2 * OUT + 8, 12, 3, M.plate, 'plate');
    slab(mount, -OUT - 4, S, 0, 2 * OUT + 8, 44 - S, 3, M.plate, 'plate');
    for (const s of [-1, 1]) slab(mount, s > 0 ? E2 : -OUT - 4, 0, 0, OUT + 4 - E2, S, 3, M.plate, 'plate');
    for (const sx of [-1, 1]) for (const y of [-6, 36]) cyl(mount, 4, 1.5, M.steel, sx * (E2 + 30), y, 3.6, 'z', 'plate', 12);
  } else if (p.context === 'scale') {
    // printed risers from the scale rail up to the ears
    const railTop = p.scale.feet + 50 - oy; // top of the rail's vertical plate, observer frame
    for (const s of [-1, 1]) {
      slab(mount, s > 0 ? IN : -OUT, railTop - 34, -12, A.cheek, earBottom - railTop + 40, 40, M.asa, 'riser');
      slab(mount, s > 0 ? IN : -OUT, railTop - 4, -18, A.cheek, 10, 10, M.asa, 'riser'); // hook over the rail
    }
  } else {
    slab(mount, -OUT - 4, -14, -2, 2 * OUT + 8, 12, 5, M.plate, 'robotFront');
    slab(mount, -OUT - 4, H.slot + 2, -2, 2 * OUT + 8, 36, 5, M.plate, 'robotFront');
  }

  // ----- entrance porch: moves the doorway forward onto the board ---------------
  // Bees that land on the hive wall must walk over the porch roof and step down
  // onto the board, so every bee in or out crosses the porch mouth in view.
  const PO = p.porch, PW2 = PO.w / 2, pTop = H.slot + 2; // roof underside
  const porch = group(obs, 'porch', 0, 0, 0, 'porch');
  const pz0 = Math.min(d.wallZ, 0) + (p.context === 'hive' ? 3 : 0), plen = PO.depth - pz0;
  slab(porch, -PW2 - PO.wall, pTop, pz0, PO.w + 2 * PO.wall, PO.roof, plen, M.porch, 'porch');
  for (const s of [-1, 1]) slab(porch, s > 0 ? PW2 : -PW2 - PO.wall, -2, pz0, PO.wall, pTop + 2, plen, M.porch, 'porch');
  box(porch, PO.w + 2 * PO.wall, 1.5, 1.5, M.board, 0, pTop - 0.2, PO.depth - 0.75, 'porch'); // drip nose on the mouth
  if (pz0 < 0) slab(porch, -PW2, -3, pz0, PO.w, 3, 8 - pz0, M.porch, 'porch'); // floor over the gap to the board
  // slide-in entrance reducer, parked open inside the porch roof slot
  slab(porch, -60, pTop + PO.roof, PO.depth - 30, 120, 2, 22, M.porchDark, 'reducer');
  box(porch, 16, 3, 5, M.graphite, 0, pTop + PO.roof + 2.5, PO.depth - 12, 'reducer');

  // ----- side cheeks (extruded profile, box section) -------------------------
  const cheekShape = () => {
    const s = new THREE.Shape();
    const top = HD.y + HD.h + 1, z0 = HD.z - HD.d / 2 - 6, z1 = HD.z + HD.d / 2 + 6;
    const pts = [[4, -30], [58, -30], [58, 10], [z1, HD.y - 30], [z1, top], [z0, top], [4, 70]];
    s.moveTo(pts[0][0] * MM, pts[0][1] * MM);
    for (const [u, v] of pts.slice(1)) s.lineTo(u * MM, v * MM);
    s.closePath();
    return s;
  };
  const cheekGeo = cached('cheek', () => new THREE.ExtrudeGeometry(cheekShape(), {
    depth: (A.cheek - 2) * MM, bevelEnabled: true, bevelThickness: 1 * MM, bevelSize: 1.5 * MM, bevelSegments: 2,
  }));
  nodes.cheeks = [];
  for (const s of [-1, 1]) {
    const cheek = explodable(group(obs, s > 0 ? 'cheekRight' : 'cheekLeft', 0, 0, 0, 'cheek'), s * 120, 0, 0);
    nodes.cheeks.push(cheek);
    const m = place(cheek, cheekGeo, M.graphite, s > 0 ? OUT - 1 : -IN - 1, 0, 0, s > 0 ? 'channel' : 'cheek');
    m.rotation.y = -Math.PI / 2;
    // thumbscrew through the ear into the cheek
    cyl(cheek, 9, 8, M.pod, s * (OUT + 9), 30, 18, 'x', 'thumb', 24);
    cyl(cheek, 3, 10, M.steel, s * (OUT + 3), 30, 18, 'x', 'thumb', 10);
    if (s > 0) {
      // cable entries under the right cheek, facing down
      cyl(cheek, 7, 10, M.black, OUT - 7, -35, 18, 'y', 'gland', 6);
      cyl(cheek, 4, 4, M.rubber, OUT - 7, -41, 18, 'y', 'gland', 16);
      cyl(cheek, 8, 12, M.steel, OUT - 7, -36, 46, 'y', 'm12', 20);
      cyl(cheek, 9.5, 3, M.black, OUT - 7, -31.5, 46, 'y', 'm12', 20);
    }
  }
  // service opening frames on the cheek outer faces (the cassettes close them)
  const bayZ0 = HD.z - HD.d / 2 + 6, bayD = HD.d - 12, bayY0 = HD.y + 4, bayH = HD.h - 8;

  // ----- internal harness (inside the right cheek; seen in the exploded view)
  cable(obs, [[OUT - 7, -30, 18], [OUT - 7, 0, 22], [OUT - 7, 80, 40], [OUT - 7, 150, 62], [OUT - 8, HD.y + 14, HD.z - 20], [IN - 20, HD.y + 20, HD.z - 20]], 2.4, M.cable, 'harness');
  cable(obs, [[OUT - 7, -30, 46], [OUT - 9, 20, 44], [OUT - 9, 150, 70], [IN - 20, HD.y + 26, HD.z - 12]], 1.8, M.cable, 'harness');

  // ----- head --------------------------------------------------------------------
  const head = explodable(group(obs, 'head', 0, HD.y, HD.z, 'head'), 0, 170, 0);
  nodes.head = head;
  const hw = HD.w, hh = HD.h, hd = HD.d;
  // extruded shell: floor, roof, front, back (open at the ends for the cassettes)
  slab(head, -hw / 2, 0, -hd / 2, hw, 4, hd, M.anod, 'head');
  slab(head, -hw / 2, hh - 5, -hd / 2, hw, 5, hd, M.anod, 'head');
  for (const s of [-1, 1]) slab(head, -hw / 2, 0, s > 0 ? hd / 2 - 4 : -hd / 2, hw, hh, 4, M.anod, 'head');
  // rounded front/back edges read as an extrusion
  for (const s of [-1, 1]) cyl(head, 4, hw, M.anod, 0, 4, s * (hd / 2 - 3), 'x', 'head', 12);
  // cooling fins on top, running front-to-back under the canopy
  for (let x = -200; x <= 200; x += 20) box(head, 2.5, 7, hd - 10, M.anod, x, hh + 3.5, 0, 'head');
  // Gratheon stripe on the front face
  box(head, 140, 6, 1, M.pod, 0, hh / 2, hd / 2 + 0.5, 'head');
  // underside: light bars, microphone, light/climate sensor
  for (const s of [-1, 1]) {
    box(head, 300, 4, 12, M.white, 0, -2, s * 38, 'led');
    box(head, 296, 1, 9, M.led, 0, -4.2, s * 38, 'led');
  }
  cyl(head, 5, 1.5, M.matt, 160, -0.8, 0, 'y', 'mic', 20);
  cyl(head, 7, 5, M.white, -160, -2.5, 0, 'y', 'sensor', 20);
  for (let i = 0; i < 3; i++) cyl(head, 8 - i, 1, M.white, -160, -5.5 - i * 1.4, 0, 'y', 'sensor', 20);
  // supervisor board (fixed in the head)
  const sup = group(head, 'supervisor', -20, hh - 14, 0, 'supervisor');
  box(sup, 90, 1.6, 70, M.pcb, 0, 0, 0, 'supervisor');
  box(sup, 15.4, 2.4, 20.5, M.can, -22, 2, 10, 'supervisor'); // ESP32-S3 module
  box(sup, 22, 5, 16, M.chip, 18, 3.3, -14, 'supervisor'); // PoE PD transformer
  box(sup, 6, 1, 6, M.chip, 20, 1.3, 16, 'supervisor');

  // camera module + hood (drops out of the floor of the head in the exploded view)
  const camG = explodable(group(head, 'cameraModule', 0, 0, 0, 'camera'), 0, -95, 0);
  camG.rotation.x = rad(p.camera.tilt); // tilted back toward the hive
  box(camG, 38, 1.6, 38, M.pcb, 0, 10, 0, 'camera');
  box(camG, 14, 3, 14, M.chip, 0, 8, 0, 'camera');
  cyl(camG, 8, 12, M.black, 0, 2, 0, 'y', 'camera', 24); // M12 lens barrel
  cyl(camG, 20, 16, M.matt, 0, -8, 0, 'y', 'hood', 32, 14); // hood cone, wide at the head
  cyl(camG, 13, 1, M.glass, 0, -16.3, 0, 'y', 'hood', 32);
  cyl(camG, 15, 2, M.black, 0, -15.5, 0, 'y', 'hood', 32); // window bezel ring
  box(camG, 60, 1, 8, M.black, 0, 12, 18, 'camera'); // CSI flex

  // compute cassette: slides out of the right cheek
  const comp = explodable(group(head, 'computeCassette', 0, 0, 0, 'compute'), 230, 0, 0);
  nodes.compute = comp;
  slab(comp, 40, 5, -bayD / 2 + 4, OUT - 42, 3, bayD - 8, M.asa, 'compute');
  const pi = group(comp, 'pi', 130, 12, -4, 'compute');
  box(pi, 85, 1.6, 56, M.pcb, 0, 0, 0, 'compute');
  box(pi, 15, 1.4, 15, M.can, -8, 1.5, 0, 'compute');
  box(pi, 85, 1.6, 56, M.pcb, 0, 14, 0, 'compute'); // Hailo HAT
  box(pi, 14, 1.2, 14, M.chip, 4, 15.4, 4, 'compute');
  box(pi, 22, 1, 42, M.chip, 0, -2.5, 0, 'compute'); // NVMe underneath
  box(pi, 50, 4, 40, M.gasket, 0, 18, 0, 'compute'); // thermal pad to the roof
  // service face, 3 mm proud of the right cheek
  const face = group(comp, 'serviceFace', OUT + 1.5, HD.h / 2, 0, 'face');
  box(face, 3, bayH + 6, bayD + 8, M.pod, 0, 0, 0, 'face');
  place(face, cached('ring', () => new THREE.TorusGeometry(7 * MM, 1.6 * MM, 10, 28)), M.status, 1.8, 10, -26, 'face').rotation.y = Math.PI / 2;
  cyl(face, 5, 3, M.podDark, 2, 10, -26, 'x', 'face', 24); // button inside the ring
  box(face, 2, 7, 14, M.rubber, 2, -10, -26, 'face'); // USB-C flap
  cyl(face, 6, 3, M.steel, 2, 0, 30, 'x', 'face', 20); // quarter-turn latch
  box(face, 1.5, 2, 9, M.black, 3.6, 0, 30, 'face');

  // left bay: battery cassette (solar) or a blank cover
  if (solar) {
    const bat = explodable(group(head, 'batteryCassette', 0, 0, 0, 'battery'), -230, 0, 0);
    nodes.battery = bat;
    slab(bat, -OUT + 2, 5, -bayD / 2 + 4, OUT - 42, 3, bayD - 8, M.asa, 'battery');
    for (let i = 0; i < 4; i++) cyl(bat, 16, 70, M.cellWrap, -80 - i * 34, 25, -2, 'z', 'battery', 24);
    const bf = group(bat, 'batteryFace', -OUT - 1.5, HD.h / 2, 0, 'battery');
    box(bf, 3, bayH + 6, bayD + 8, M.podDark, 0, 0, 0, 'battery');
    cyl(bf, 6, 3, M.steel, -2, 0, 30, 'x', 'battery', 20);
  } else {
    const bl = group(head, 'blankCover', -OUT - 1.5, HD.h / 2, 0, 'blank');
    box(bl, 3, bayH + 6, bayD + 8, M.graphite, 0, 0, 0, 'blank');
    const hex = place(bl, cached('hex', () => new THREE.CylinderGeometry(9 * MM, 9 * MM, 1.5 * MM, 6)), M.pod, -1.8, 0, 0, 'blank');
    hex.rotation.z = Math.PI / 2;
  }

  // eye point for the camera-view inset (just below the window)
  const eye = new THREE.Object3D();
  eye.name = 'cameraEye';
  eye.position.set(0, (p.camera.eye - HD.y) * MM, 0);
  camG.add(eye);
  nodes.eye = eye;
  const aim = new THREE.Object3D(); // a point on the optical axis, for the inset camera
  aim.name = 'cameraAim';
  aim.position.set(0, (p.camera.eye - HD.y - 100) * MM, 0);
  camG.add(aim);
  nodes.aim = aim;

  // ----- canopy ----------------------------------------------------------------
  const canopy = explodable(group(obs, 'canopy', 0, C.ridge, C.z0, solar ? 'solarCanopy' : 'canopy'), 0, 220, 0);
  nodes.canopy = canopy;
  const cPart = solar ? 'solarCanopy' : 'canopy';
  const sheet = solar ? M.acm : M.opal;
  const halfW = C.w / 2;
  // Two slopes meeting at a ridge along Z: rain runs to the side eaves, beside the board.
  for (const s of [-1, 1]) {
    const half = group(canopy, s > 0 ? 'roofRight' : 'roofLeft', 0, 0, 0, cPart);
    half.rotation.z = -s * rad(C.slope);
    box(half, halfW, C.t, C.len, sheet, (s * halfW) / 2, C.t / 2, C.len / 2, cPart);
    box(half, 3, 12, C.len, solar ? M.acm : M.opalEdge, s * (halfW - 1.5), C.t - 6, C.len / 2, cPart); // eave drip edge
    if (solar) {
      box(half, halfW - 26, 1.2, C.len - 20, M.solar, s * (halfW / 2 + 2), C.t + 0.6, C.len / 2, 'solarCanopy');
      for (let i = 1; i < 4; i++) box(half, 0.8, 1.5, C.len - 20, M.solarGrid, s * (14 + (i * (halfW - 26)) / 4), C.t + 0.7, C.len / 2, 'solarCanopy');
      box(half, halfW - 26, 1.5, 0.8, M.solarGrid, s * (halfW / 2 + 2), C.t + 0.7, C.len / 2, 'solarCanopy');
    }
  }
  box(canopy, 10, 3, C.len + 2, M.pod, 0, C.t + 1, C.len / 2, cPart); // honey-yellow ridge cap
  // four standoffs from the head roof up to the underside of the roof
  const headTop = HD.y + HD.h;
  for (const sx of [-1, 1]) for (const dz of [-28, 28]) {
    const x = sx * 150, under = -Math.abs(x) * Math.tan(rad(C.slope));
    const len = C.ridge + under - headTop;
    cyl(canopy, 5, len, M.steel, x, under - len / 2, HD.z + dz - C.z0, 'y', cPart, 12);
  }
  if (!solar) {
    // Opal diffuses the sun: the canopy and the head under it cast no hard shadow on the board.
    canopy.traverse((o) => { if (o.isMesh) o.castShadow = false; });
    head.traverse((o) => { if (o.isMesh) o.castShadow = false; });
  }
  if (solar) {
    box(canopy, C.w - 30, 1.2, C.len - 24, M.solar, 0, C.t + 0.6, C.len / 2 + 2, 'solarCanopy');
    for (let i = 1; i < 6; i++) box(canopy, 0.8, 1.5, C.len - 24, M.solarGrid, -(C.w - 30) / 2 + (i * (C.w - 30)) / 6, C.t + 0.7, C.len / 2 + 2, 'solarCanopy');
    for (let i = 1; i < 4; i++) box(canopy, C.w - 30, 1.5, 0.8, M.solarGrid, 0, C.t + 0.7, 14 + (i * (C.len - 24)) / 4, 'solarCanopy');
  }

  // ----- landing board ------------------------------------------------------------
  const boardHinge = group(obs, 'landingBoard', 0, -2, 5, 'board');
  boardHinge.rotation.x = rad(p.boardSlope);
  explodable(boardHinge, 0, -20, 190);
  nodes.board = boardHinge;
  const BW = 2 * IN - 6, BD = A.board;
  slab(boardHinge, -BW / 2, -11, 0, BW, 8, BD, M.board, 'board');
  slab(boardHinge, -BW / 2 + 12, -3, 2, BW - 24, 3, BD - 6, M.insert, 'insert');
  box(boardHinge, 40, 3.2, 8, M.board, 0, -1.4, BD - 3, 'insert'); // finger notch lip
  for (const sx of [-1, 1]) cyl(boardHinge, 4, 14, M.steel, sx * (IN - 4), -6, 0, 'x', 'hinge', 12);
  // ArUco-style markers in the four corners (hand-set pattern, not a real ID)
  const pattern = [[1, 0, 1, 1], [0, 1, 0, 1], [1, 1, 0, 0], [0, 1, 1, 0]];
  for (const [mx, mz] of [[-1, 0], [1, 0], [-1, 1], [1, 1]]) {
    const cx = mx * 172, cz = mz ? BD - 40 : p.porch.depth + 18;
    box(boardHinge, 30, 0.4, 30, M.markBlack, cx, 0.2, cz, 'marker');
    pattern.forEach((row, r) => row.forEach((v, c) => {
      if (v) box(boardHinge, 5, 0.5, 5, M.markWhite, cx - 7.5 + c * 5, 0.3, cz - 7.5 + r * 5, 'marker');
    }));
  }
  // millimetre scale along the front edge (cm ticks, long every 5 cm)
  for (let x = -150; x <= 150; x += 10) box(boardHinge, 0.8, 0.3, x % 50 === 0 ? 8 : 4, M.markBlack, x, 0.15, BD - 30, 'marker');
  box(boardHinge, 301, 0.3, 0.8, M.markBlack, 0, 0.15, BD - 26, 'marker');
  // counting line: a faint printed line just in front of the porch mouth
  for (let x = -150; x < 150; x += 12) box(boardHinge, 7, 0.3, 1.2, M.markGrey, x + 3.5, 0.15, p.porch.depth + 1, 'countLine');

  // ----- bees -----------------------------------------------------------------------
  const bees = group(boardHinge, 'bees');
  const beesAir = group(obs, 'beesAir');
  nodes.bees = [bees, beesAir];
  const beeGeo = cached('bee', () => new THREE.SphereGeometry(1, 12, 8));
  const addBee = (parent, x, y, z, rotY, pollen = false) => {
    const b = group(parent, `bee_${parent.children.length}`, x, y, z, 'bee');
    b.rotation.y = rotY;
    const body = place(b, beeGeo, M.beeBody, 0, 0, 0, 'bee'); body.scale.set(2.2 * MM, 2 * MM, 6.5 * MM);
    const stripe = place(b, beeGeo, M.beeStripe, 0, 0.2, -2.5, 'bee'); stripe.scale.set(2.3 * MM, 2.05 * MM, 2.6 * MM);
    place(b, beeGeo, M.beeBody, 0, 0, 5.8, 'bee').scale.set(1.6 * MM, 1.5 * MM, 1.6 * MM); // head
    for (const s of [-1, 1]) {
      const wing = place(b, beeGeo, M.beeWing, s * 2.6, 2, -0.5, 'bee');
      wing.scale.set(2.2 * MM, 0.3 * MM, 5 * MM);
      wing.rotation.y = s * 0.35;
      if (pollen) place(b, beeGeo, M.pollen, s * 2.4, -0.6, -1, 'bee').scale.set(1.2 * MM, 1.2 * MM, 1.5 * MM);
    }
    return b;
  };
  const walkers = [
    [-120, 52, 0.3], [-60, 44, 2.9, true], [10, 78, -0.4], [55, 48, 3.3], [95, 120, 2.2, true], [-150, 140, 1.1],
    [140, 70, -2.6], [-30, 110, 0.9], [150, 150, -0.8], [-95, 95, 3.0, true], [30, 140, 2.6], [-10, 50, 3.1],
  ];
  for (const [x, z, r, pl] of walkers) addBee(bees, x, 2.2, z, r, pl);
  // wall landers: on the hive wall above the porch, then walking over the porch roof
  const beesWall = group(obs, 'beesWall');
  nodes.bees.push(beesWall);
  for (const [x, y] of [[-70, 40], [45, 52], [120, 34]]) {
    const b = addBee(beesWall, x, y, d.wallZ + 3, 0);
    b.rotation.x = Math.PI / 2; // head down, on the vertical wall
  }
  for (const [x, z, r] of [[-40, PO.depth - 18, 0.2], [80, PO.depth - 30, -0.3]]) addBee(beesWall, x, pTop + PO.roof + 2, z, r);
  for (const [x, y, z, r] of [[-60, 120, 330, 2.9], [110, 200, 420, -2.6], [-170, 70, 280, 0.6], [30, 260, 520, 3.4]]) {
    const b = addBee(beesAir, x, y, z, r);
    b.rotation.x = -0.25;
  }

  // ----- field of view (toggled in the viewer) ------------------------------------
  const fov = group(obs, 'fieldOfView', 0, 0, 0, 'fov');
  nodes.fov = fov;
  {
    const e = d.eye, cs = d.corners, ol = d.outline;
    const pts = [];
    for (const c of cs) pts.push(e.x, e.y, e.z, c.x, c.y, c.z);
    for (let i = 0; i < ol.length; i++) { const a = ol[i], b = ol[(i + 1) % ol.length]; pts.push(a.x, a.y + 0.5, a.z, b.x, b.y + 0.5, b.z); }
    const lg = new THREE.BufferGeometry();
    lg.setAttribute('position', new THREE.Float32BufferAttribute(pts.map((v) => v * MM), 3));
    const lines = new THREE.LineSegments(lg, M.fovLine);
    lines.userData.part = 'fov';
    fov.add(lines);
    const tri = [];
    for (let i = 0; i < ol.length; i++) { const a = ol[i], b = ol[(i + 1) % ol.length]; tri.push(e.x, e.y, e.z, a.x, a.y, a.z, b.x, b.y, b.z); }
    const tg = new THREE.BufferGeometry();
    tg.setAttribute('position', new THREE.Float32BufferAttribute(tri.map((v) => v * MM), 3));
    tg.computeVertexNormals();
    const mesh = new THREE.Mesh(tg, M.fov);
    mesh.userData.part = 'fov';
    fov.add(mesh);
  }
  fov.visible = false;

  // ----- context: hive, stand, scale, robot -------------------------------------------
  const hive = group(root, 'hive', 0, d.hiveBase, 0, 'hive');
  nodes.hive = hive;
  const hiveMats = [];
  const woodMat = (i) => { const m = M.wood[i % M.wood.length].clone(); hiveMats.push(m); return m; };
  const T = 25, E2 = H.entrance / 2, bb = d.bottomBoard;
  const slotY = d.entranceY - d.hiveBase; // slot floor, relative to the hive base
  const walls = (g, y0, h, mat) => {
    box(g, H.w, h, T, mat, 0, y0 + h / 2, H.d / 2 - T / 2, 'hive');
    box(g, H.w, h, T, mat, 0, y0 + h / 2, -H.d / 2 + T / 2, 'hive');
    for (const s of [-1, 1]) box(g, T, h, H.d - 2 * T, mat, s * (H.w / 2 - T / 2), y0 + h / 2, 0, 'hive');
  };
  if (p.context === 'robot') {
    // the robot bottom board sits on the plinth: the slot is at its top
    const bbMat = woodMat(2);
    box(hive, H.w, 12, H.d, bbMat, 0, -bb + 6, 0, 'hive');
    box(hive, H.w, bb, T, bbMat, 0, -bb / 2, -H.d / 2 + T / 2, 'hive');
    for (const s of [-1, 1]) {
      box(hive, T, bb, H.d - 2 * T, bbMat, s * (H.w / 2 - T / 2), -bb / 2, 0, 'hive');
      box(hive, H.w / 2 - E2, bb, T, bbMat, s * (H.w / 2 + E2) / 2, -bb / 2, H.d / 2 - T / 2, 'hive');
    }
    box(hive, H.entrance, bb - H.slot, T, bbMat, 0, -bb + (bb - H.slot) / 2, H.d / 2 - T / 2, 'hive');
    for (let i = 0; i < p.boxes; i++) walls(hive, i * H.h, H.h, woodMat(i));
  } else {
    const bbMat = woodMat(2), floor = 12;
    box(hive, H.w, floor, H.d, bbMat, 0, floor / 2, 0, 'hive');
    box(hive, H.w, bb, T, bbMat, 0, bb / 2, -H.d / 2 + T / 2, 'hive');
    for (const s of [-1, 1]) {
      box(hive, T, bb, H.d - 2 * T, bbMat, s * (H.w / 2 - T / 2), bb / 2, 0, 'hive');
      box(hive, H.w / 2 - E2, bb, T, bbMat, s * (H.w / 2 + E2) / 2, bb / 2, H.d / 2 - T / 2, 'hive');
    }
    box(hive, H.entrance, bb - slotY - H.slot, T, bbMat, 0, slotY + H.slot + (bb - slotY - H.slot) / 2, H.d / 2 - T / 2, 'hive');
    for (let i = 0; i < p.boxes; i++) walls(hive, bb + i * H.h, H.h, woodMat(i));
  }
  const lidY = (p.context === 'robot' ? 0 : bb) + p.boxes * H.h;
  const lidMat = M.lid.clone();
  hiveMats.push(lidMat);
  box(hive, H.w + 20, H.lid, H.d + 20, lidMat, 0, lidY + H.lid / 2, 0, 'hive');
  nodes.hiveMaterials = hiveMats;

  if (p.context === 'hive') {
    const st = group(root, 'stand', 0, 0, 0, 'stand');
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) box(st, 45, p.stand - 45, 45, M.timberDark, sx * 210, (p.stand - 45) / 2, sz * 170, 'stand');
    for (const sz of [-1, 1]) box(st, 520, 45, 45, M.timber, 0, p.stand - 22.5, sz * 170, 'stand');
    for (const sx of [-1, 1]) box(st, 45, 45, 300, M.timber, sx * 210, p.stand - 22.5, 0, 'stand');
    // PoE cable: drip loop under the cheek, down the stand, away along the ground
    const g = W(OUT - 7, -41, 18);
    cable(fieldCables, [g, [g[0], g[1] - 30, g[2] + 6], [g[0] + 4, g[1] - 60, g[2] - 6], [g[0] + 6, 120, g[2] - 4], [g[0] + 10, 8, g[2] - 10], [g[0] + 120, 3, 200], [900, 3, 60]], 2.8, M.cable);
  } else if (p.context === 'scale') {
    const S = p.scale, sc = group(root, 'scale', 0, 0, 0, 'scale');
    const bY = S.feet, bw = S.base.w, bd = S.base.d, deckY = S.feet + S.height - 18;
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
      cyl(sc, 5, S.feet, M.steel, sx * 200, S.feet / 2 + 4, sz * 150, 'y', 'scale', 12);
      cyl(sc, 20, 8, M.rubber, sx * 200, 4, sz * 150, 'y', 'scale', 28);
    }
    box(sc, bw, S.base.h, bd, M.timber, 0, bY + S.base.h / 2, 0, 'scale');
    box(sc, S.deck.w, 17, S.deck.d, M.timber, 0, deckY + 8.5, 0, 'scale');
    box(sc, S.deck.w, 1, S.deck.d, M.film, 0, deckY + 17.5, 0, 'scale');
    for (const s of [-1, 1]) {
      box(sc, S.deck.w, 40, 20, M.timber, 0, deckY - 20, s * (S.deck.d / 2 - 10), 'scale');
      box(sc, 20, 40, S.deck.d - 40, M.timber, s * (S.deck.w / 2 - 10), deckY - 20, 0, 'scale');
    }
    box(sc, 3, 38, 150, M.pod, bw / 2 + 1.5, bY + 20, 0, 'scale'); // pod face
    // front rail (the Observer risers hook on it) and the M12 connector under it
    const railZ = S.deck.d / 2 + 8;
    slab(sc, -220, bY + 16, bd / 2, 440, 4, railZ - bd / 2, M.alu, 'scale');
    slab(sc, -220, bY + 16, railZ - 4, 440, 30, 4, M.alu, 'scale');
    cyl(sc, 8, 14, M.steel, 60, bY + 9, bd / 2 + 18, 'y', 'scaleLink', 20);
    cyl(sc, 9, 12, M.black, 60, bY - 1, bd / 2 + 18, 'y', 'scaleLink', 20);
    const acc = W(OUT - 7, -38, 46);
    cable(fieldCables, [acc, [acc[0], acc[1] - 20, acc[2] - 2], [acc[0] - 20, bY - 10, acc[2] - 30], [120, bY - 16, bd / 2 + 30], [60, bY - 12, bd / 2 + 18], [60, bY - 6, bd / 2 + 18]], 2.3, M.cable);
    const g = W(OUT - 7, -41, 18);
    cable(fieldCables, [g, [g[0] + 4, g[1] - 30, g[2] + 4], [g[0] + 30, 30, g[2] + 10], [g[0] + 90, 3, g[2]], [700, 3, 150], [1100, 3, 60]], 2.8, M.cable);
  } else {
    // Robotic Beehive (ghost): posts, plinth, front cladding with the entrance frame
    const R = p.robot, E = R.e, PX = R.post.x, PZ = R.post.z;
    const rb = group(root, 'robotCabinet', 0, 0, 0, 'robot');
    nodes.robot = rb;
    const postH = d.lidTop + 520;
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
      box(rb, E, postH - 40, E, M.robot, sx * PX, 40 + (postH - 40) / 2, sz * PZ, 'robot');
      cyl(rb, 22, 10, M.robot, sx * PX, 5, sz * PZ, 'y', 'robot', 24);
    }
    for (const y of [51, R.plinth - 11, postH]) {
      box(rb, 2 * PX + E, E, E, M.robot, 0, y, PZ, 'robot');
      box(rb, 2 * PX + E, E, E, M.robot, 0, y, -PZ, 'robot');
      for (const s of [-1, 1]) box(rb, E, E, 2 * PZ - E, M.robot, s * PX, y, 0, 'robot');
    }
    // front cladding with an opening for the entrance tunnel mouth
    const fz = PZ + E / 2 + R.clad / 2, cw = 2 * PX + E, top = postH;
    const holeY0 = d.entranceY - 16, holeY1 = d.entranceY + H.slot + 40;
    box(rb, cw, holeY0 - 40, R.clad, M.robotClad, 0, 40 + (holeY0 - 40) / 2, fz, 'robot');
    box(rb, cw, top - holeY1, R.clad, M.robotClad, 0, holeY1 + (top - holeY1) / 2, fz, 'robot');
    for (const s of [-1, 1]) box(rb, cw / 2 - OUT - 6, holeY1 - holeY0, R.clad, M.robotClad, s * (cw / 2 + OUT + 6) / 2, (holeY0 + holeY1) / 2, fz, 'robot');
    // entrance tunnel from the bottom board to the cabinet front
    const tz0 = H.d / 2, tz1 = oz;
    box(rb, 2 * IN - 20, 4, tz1 - tz0, M.robotClad, 0, d.entranceY - 2, (tz0 + tz1) / 2, 'robot');
    box(rb, 2 * IN - 20, 4, tz1 - tz0, M.robotClad, 0, d.entranceY + H.slot + 2, (tz0 + tz1) / 2, 'robot');
    box(rb, cw + 120, 20, 2 * PZ + 180, M.robot, 0, postH + 30, 0, 'robot'); // roof
    const g = W(OUT - 7, -41, 18);
    cable(fieldCables, [g, [g[0], g[1] - 20, g[2] - 2], [g[0] + 30, g[1] - 36, fz + 6], [PX - 30, g[1] - 30, fz - 20], [PX - 10, g[1] - 60, PZ - 20]], 2.8, M.cable);
  }

  const applyExplode = (u) => {
    const e = u * u * (3 - 2 * u);
    for (const g of nodes.explode) g.position.copy(g.userData.home).addScaledVector(g.userData.explode, e);
    const quiet = u < 0.02;
    fieldCables.visible = quiet;
    for (const b of nodes.bees) b.visible = quiet;
  };
  applyExplode(0);

  return { root, nodes, params: p, derived: d, applyExplode, MM };
}
