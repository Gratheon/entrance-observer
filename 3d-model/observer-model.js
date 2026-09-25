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
// - A flat wall frame shaped like a house gable (entrance plate, two slim
//   uprights, two rafters) stays on the hive. It carries the porch with the
//   automatic gate and the landing board.
// - The head hangs on the apex of the frame: a ridge beam, a steep gable roof
//   running from the hive wall forward, and one small metal pod under the
//   ridge with the camera and the computer. Nothing but the pod is machined.
// - The ridge runs front to back, so rain and snow slide off the sides and
//   drip beside the landing board, never onto it.
// - A short porch moves the doorway onto the board, so every bee in or out
//   crosses the porch mouth in view, even if it landed on the hive wall. The
//   mouth is the counting line and holds the gate.
// - The camera looks down at the board, tilted toward the hive to also see the
//   porch and the bottom of the wall. Frame, roof and cables are outside the view.
// - Every cable enters from below, under the right upright, and runs inside it.

import * as THREE from 'three';

const MM = 0.001;

export const DEFAULTS = {
  context: 'hive', // 'hive' = on a hive stand, 'scale' = on the beehive scale, 'robot' = on the Robotic Beehive
  power: 'poe', // 'poe' = opal roof, PoE+ powered; 'solar' = solar roof + battery cassette
  gate: 'open', // entrance gate: 'open', 'reduced', 'guard' (hornet guard) or 'closed'
  boxes: 2, // hive bodies
  hive: { w: 506, d: 450, h: 285, lid: 80, bottomBoard: 60, entrance: 300, slot: 15 }, // Estonian hive (outer)
  stand: 200, // wooden hive stand height
  frame: { w: 456, post: 22, depth: 15 }, // wall frame: width, upright / rafter width, depth of the box sections
  roof: { ridge: 318, z0: 2, len: 212, halfW: 238, t: 3, slope: 30 }, // ridge underside height, start z, length, horizontal half-width, sheet, degrees
  beam: { w: 30, h: 36, len: 196 }, // ridge beam under the roof
  head: { y: 205, z: 135, w: 170, h: 57, d: 140 }, // camera + compute pod: underside height, centre z, size
  camera: { eye: 186, hfov: 90, aspect: 16 / 9, px: 3840, tilt: 16 }, // lens height above the entrance floor, degrees, sensor width px, degrees toward the hive
  porch: { depth: 46, w: 312, wall: 4, roof: 4, gateZ: 40, notch: 70, floorEnd: 48 }, // mouth distance from the hive face, inner width, wall/roof, gate plane, centre opening, porch floor end
  board: { w: 432, d: 150 }, // landing board, hinged at the porch floor
  boardSlope: 6, // degrees
  scale: { feet: 25, height: 112, deck: { w: 560, d: 510 }, base: { w: 504, d: 454, h: 60 } }, // from beehive-sensors DEFAULTS
  robot: { plinth: 200, bottomBoard: 150, post: { x: 372, z: 302 }, e: 22, clad: 18 }, // from robotic-beehive DEFAULTS
};

// Gate top edge height above the porch floor for each position. The gate rises
// out of a slit in the porch floor; its centre has a notch as deep as the porch
// is high, so one travel gives four openings.
export const GATE = {
  open: 0, // flush with the floor: the whole 312 × 17 mm mouth is open
  reduced: 17, // flat part meets the porch roof: only the 70 × 17 mm centre notch is open
  guard: 28.5, // notch top at 11.5 mm: a 70 × 5.5 mm slot, bees pass, hornets and wasps do not
  closed: 34, // notch top meets the porch roof
};

// ---------------------------------------------------------------------------
// Part descriptions (shown on hover in the viewer, exported as glTF extras)
// ---------------------------------------------------------------------------
export const PARTS = {
  frame: ['Wall frame', 'One laser-cut, folded sheet of powder-coated steel or aluminium in the shape of a house gable: the entrance plate, two slim uprights and two rafters. It is screwed to the bottom board with four stainless screws and only leans on the hive body through two rubber pads, so the bodies still lift off. It stays on the hive and carries the porch, the gate and the landing board; the head hangs on its apex.'],
  plate: ['Entrance plate', 'Bottom of the wall frame, with a window matching the 300 × 15 mm entrance. Powder-coated matt grey, because its top edge is in the camera view.'],
  riser: ['Scale risers', 'On the beehive scale the wall frame stands on two printed ASA risers hooked onto the scale front rail, 2 mm clear of the hive. Frame, roof, snow and bees on the board are then carried by the scale base and never weighed.'],
  robotFront: ['Robot entrance frame', 'On the Robotic Beehive the wall frame is bolted to the cabinet front, where the entrance tunnel ends. Power and data come from the robot PoE switch inside a corner post.'],
  channel: ['Cable upright', 'The right upright is a closed box section. The PoE cable and the gate cable run up inside it to the apex and along the ridge beam to the pod: no cable is in the sun, in the rain or in front of the lens.'],
  gland: ['Cable entries', 'Under the foot of the right upright, facing the ground: the PoE cable gland and the accessory socket. Water runs off them, not into them, and the cable leaves with a drip loop.'],
  m12: ['Accessory port', 'M12 8-pin socket with the pinout of the beehive scale front connector: 5 V out, ground, 1-Wire, UART, wake and shield. One short lead to the scale powers the scale pod from the Observer and shares time and readings, so the scale needs no solar board and both upload through one link.'],
  thumb: ['Apex hook', 'The ridge beam ends in a hook that drops into a pocket at the apex of the wall frame, locked by one captive honey-yellow thumbscrew. The head lifts off in seconds and always lands in the same place, with the camera aimed the same way.'],
  beam: ['Ridge beam', 'Standard 30 × 36 mm aluminium extrusion from the apex forward, under the ridge. It carries the roof, the front rafters and the pod, and the cables run inside it.'],
  rafter: ['Front rafters', 'Two slim folded strips under the front edge of the roof, from the end of the ridge beam to the eaves. They carry snow on the front corners. They sit above the lens, outside the view.'],
  pod: ['Camera + compute pod', 'The only machined metal part: a 170 × 140 mm piece of finned aluminium extrusion, IP65, with printed end caps. It holds the camera, the compute sled and the supervisor, and it is the heatsink: the fins sit in the ventilated space under the roof. No fan to clog with dust or propolis.'],
  camera: ['Camera module', '8 MP (3840 × 2160) Sony STARVIS 2 sensor on its own MIPI CSI board with a locked-focus, low-distortion M12 lens, 90° wide. It sits 186 mm above the board, 135 mm out from the hive, tilted 16° back toward the hive: it sees nearly the whole board, the porch with the gate and the bottom of the hive wall, so bees that land on the wall are tracked from the moment they land. On the board that gives about 9.5 px per mm: a bee is about 125 px long and a varroa mite about 14 px. A global-shutter module can replace it without changing the pod.'],
  hood: ['Lens hood + window', 'Matt black cone with a flat AR-coated glass window at its tip, facing the ground. Rain cannot reach it, the sky never reflects in it and the roof keeps direct sun off it. A 0.3 W heater film clears dew on cold mornings.'],
  led: ['Light bars', 'Two short diffused LED bars beside the lens, with crossed polarisers on the LEDs and the lens to remove glints from shiny bees and wet pollen. They only flash in sync with the exposure at dusk or in deep shade, so they add less than 0.3 W on average.'],
  mic: ['Microphone', 'MEMS microphone behind a mesh under the pod. Entrance audio (drone flight, piping, hornets, fanning) is stored with the counts for audio + video models, and a hornet buzz is a second trigger for the gate.'],
  sensor: ['Light + climate sensor', 'Ambient light, temperature and humidity. The supervisor uses them to decide when bees can fly, which is when the computer has to run, and to narrow the gate on cold nights.'],
  supervisor: ['Supervisor board', 'Always-on ESP32-S3 board, the same carrier design as the beehive scale: PoE+ input, 12–24 V DC input, solar charger, fuel gauge, the gate motor driver and a load switch for the compute sled. It idles at about 0.1 W, only powers the computer when bees can fly, and moves the gate on its own when needed (cold night, lost power, expired hornet guard).'],
  compute: ['Compute cassette', 'Raspberry Pi 5 (8 GB), Hailo-8 26 TOPS accelerator and 256 GB NVMe on one sled. It slides out of the front of the pod after a quarter-turn. The sled is the upgrade path: pod, camera, power and connectors stay the same, and a Jetson Orin NX or the next accelerator slides into the same bay when pose models need more compute.'],
  face: ['Service face', 'Honey-yellow front of the compute cassette: status ring, setup button and a USB-C port under a flap for copying full-resolution research clips on site.'],
  battery: ['Battery cassette', 'Solar version: four LiFePO4 32700 cells (12.8 V, 77 Wh) on a sled that slides out of the left side of the pod, charged from the roof panels. LiFePO4 tolerates summer heat better than Li-ion. In the PoE version this bay is empty or holds an LTE modem.'],
  blank: ['Side bay cover', 'Cover of the pod side bay. Behind it goes the battery cassette (solar version) or an LTE modem for apiaries without Wi-Fi or Ethernet.'],
  canopy: ['Roof', 'A 3 mm opal (light-diffusing), UV-stabilised polycarbonate sheet bent once along the ridge into a 30° gable, 448 × 212 mm, from the hive wall forward. At 30° rain and snow slide off, to the sides: the eaves overhang the landing board edges, so drips fall beside the board, outside the view. Opal keeps its shadow on the board soft. It rests on the rafters of the wall frame at the back, the ridge beam and the front rafters.'],
  solarCanopy: ['Solar roof', 'The same gable with a 7 W ETFE panel laminated on each slope (14 W). Whichever way the hive faces, one slope gets the morning or afternoon sun. Bees fly when the sun shines, so the panels produce the most when the Observer has the most to do.'],
  porch: ['Entrance porch', 'A 46 mm deep, 17 mm high tunnel across the full entrance, in the same matt grey as the board. It moves the doorway forward onto the landing board: a bee that lands on the hive wall has to walk down onto the porch roof and step off in front of the mouth, so every bee in or out crosses the porch mouth in view. The mouth is the counting line. Open to the air, with no glass to clean or fog up.'],
  gate: ['Automatic entrance gate', 'A 2 mm plate that rises out of a slit in the porch floor at the mouth, with a 70 mm notch in its centre. One travel gives four positions: open (flush with the floor), reduced (only the 70 × 17 mm centre open, against wind, cold and robbing), hornet guard (a 70 × 5.5 mm slot: bees pass, hornets and wasps cannot) and closed (moving the hive, spraying nearby). It rises slowly with a soft silicone edge and a current limit, and only when the camera sees no bee in the mouth, so it cannot crush bees. Hidden under the floor when open.'],
  gateDrive: ['Gate drive', 'Sealed box under the porch floor: a micro geared stepper with a self-locking lead screw (the gate holds any position without power, and bees or hornets cannot push it), a hall sensor for the home position and a supercapacitor. If power is lost, the supercapacitor opens the gate: it fails open, never closed. The drive plugs into the right upright; a move takes about 5 s at 1 W.'],
  lintel: ['Gate lintel', 'The raised front edge of the porch roof. The gate slides up into it, and it marks the counting line from above.'],
  countLine: ['Counting line', 'A faint printed line just in front of the porch mouth, for people, not for the software: the software counts a track as in when it ends inside the porch and out when it starts there.'],
  board: ['Landing board', '10 mm HDPE, hinged to the front of the porch floor at a 6° slope so rain drains off, with an aluminium stiffener underneath. It is the background of every frame: matt, neutral light grey. White would overexpose in the sun and hide pale pollen loads.'],
  insert: ['Board insert', 'The top 3 mm layer slides out forward for washing off droppings, dead bees and propolis. Spare inserts are cheap to keep.'],
  marker: ['Calibration markers', 'Four ArUco markers and a millimetre scale on the insert. The software finds them in every frame, so it knows the exact mm per pixel for bee size and speed, straightens the view, and raises an alert if the Observer has been knocked.'],
  hinge: ['Board hinge', 'Stainless pins at the front of the porch floor. The board folds up flat for shipping and swings down if something hits it.'],
  harness: ['Internal harness', 'PoE, accessory and gate lines from the foot of the right upright, up inside it, over the rafter and along the ridge beam to the supervisor board in the pod.'],
  cable: ['Cables', 'One PoE cable (power and data, up to 100 m) from under the right upright, run along the ground. With the scale, one short M12 lead joins the Observer and the scale.'],
  fov: ['Camera field of view', 'What the camera sees: the bottom of the hive wall, the porch with the gate and the landing board, about 400 mm across. The frame, roof, pod and cables are all outside it.'],
  bee: ['Bees', 'Honey bees on the landing board, on the porch roof and on the hive wall. At 4K each worker is about 125 px long, big enough for pose keypoints, pollen loads and mites.'],
  hive: ['Hive', 'A standard hive: bottom board, bodies and lid. The only change is the wall frame screwed to the bottom board.'],
  stand: ['Hive stand', 'Any stand works: the Observer hangs on the hive entrance and does not touch the stand.'],
  scale: ['Beehive scale', 'Gratheon beehive scale, simplified. The Observer stands on its front rail with two risers, and one M12 lead powers the scale pod and carries its readings.'],
  scaleLink: ['Scale connector', 'M12 socket under the front rail of the beehive scale. The Observer lead plugs in here in place of the solar landing board.'],
  robot: ['Robotic Beehive', 'Ghost of the Robotic Beehive cabinet. Its entrance tunnel ends in the Observer porch, and the cable runs inside the cabinet to the robot PoE switch.'],
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
    // In front of the deck (railZ + 6), at entrance level: nothing touches the weighed hive.
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
  const boardY = (z) => -2 - (z - P.floorEnd) * tanB; // board surface height at local z
  const vfov = 2 * Math.atan(Math.tan(rad(cam.hfov / 2)) / cam.aspect);
  const wallZ = H.d / 2 - origin[2]; // hive front face in the observer frame (≤ 0)
  const pTop = H.slot + 2; // porch roof underside
  const porchTop = pTop + P.roof; // top of the porch roof
  const lintelTop = pTop + 21; // top of the gate lintel at the mouth
  // The lens hangs 19 mm under the pod floor and swings with the camera tilt.
  const tilt = rad(cam.tilt), drop = p.head.y - cam.eye;
  const eye = new THREE.Vector3(0, p.head.y - drop * Math.cos(tilt), p.head.z - drop * Math.sin(tilt));
  // A camera ray (a across, b along the image height) tilted toward the hive.
  const ray = (a, b) => new THREE.Vector3(a, -1, b).applyAxisAngle(new THREE.Vector3(1, 0, 0), tilt);
  // First surface a ray meets: gate lintel, porch roof, hive wall or landing board.
  const hit = (dir) => {
    let best = (eye.y + 2 - P.floorEnd * tanB + eye.z * tanB) / (-dir.y - dir.z * tanB); // board plane
    const flat = (y, z0, z1, halfX) => {
      const t = (eye.y - y) / -dir.y;
      const q = eye.clone().addScaledVector(dir, t);
      if (t > 0 && t < best && q.z >= z0 && q.z <= z1 && Math.abs(q.x) <= halfX) best = t;
    };
    flat(lintelTop, P.gateZ - 6, P.depth, P.w / 2 + P.wall);
    flat(porchTop, wallZ, P.gateZ - 6, P.w / 2 + P.wall);
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
    fovW, fovD, wallSeen, pxPerMm: cam.px / fovW, boardFront: P.floorEnd + p.board.d * Math.cos(rad(p.boardSlope)),
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
  sample: { on: 120, period: 600 }, // sampled mode: record 2 min every 10 min
  batteryWh: 77, depth: 0.9,
  panelW: 14, sunHours: 4.5, systemEff: 0.7, // May–August average for Estonia, near-horizontal panel
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
    gate: std(0x8e928d, { roughness: 0.9 }),
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
  if (!(p.gate in GATE)) p.gate = 'open';
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

  const F = p.frame, RF = p.roof, BM = p.beam, HD = p.head, H = p.hive, PO = p.porch;
  const FW = F.w / 2; // frame half-width
  const [ox, oy, oz] = d.origin;
  // Observer frame → world (the Observer is never rotated, only moved).
  const W = (x, y, z) => [ox + x, oy + y, oz + z];
  const tanR = Math.tan(rad(RF.slope));
  const roofUnder = (x) => RF.ridge - Math.abs(x) * tanR; // roof underside height at x
  const rafterY = (x) => roofUnder(x) - 12; // rafter centre line, just under the roof
  const postTop = rafterY(FW - F.post / 2); // where the uprights meet the rafters
  const apexY = rafterY(0);

  const obs = group(root, 'observer', ox, oy, oz);
  nodes.observer = obs;

  // ----- wall frame: plate, uprights, rafters (one folded sheet) --------------
  const framePart = { hive: 'frame', scale: 'frame', robot: 'robotFront' }[p.context];
  const frame = group(obs, 'wallFrame', 0, 0, 0, framePart);
  const WIN = H.entrance / 2 + 4, S = H.slot + 2; // window half-width and height
  const plateZ = p.context === 'robot' ? -2 : 0;
  const plateMat = M.plate;
  // entrance plate with a window matching the entrance slot
  slab(frame, -FW, -12, plateZ, 2 * FW, 12, 3, plateMat, 'plate');
  slab(frame, -FW, S, plateZ, 2 * FW, 44 - S, 3, plateMat, 'plate');
  for (const s of [-1, 1]) slab(frame, s > 0 ? WIN : -FW, 0, plateZ, FW - WIN, S, 3, plateMat, 'plate');
  if (p.context === 'hive') for (const sx of [-1, 1]) for (const y of [-6, 36]) cyl(frame, 4, 1.5, M.steel, sx * (WIN + 22), y, 3.6, 'z', 'plate', 12);
  // uprights (box sections; the right one carries the cables)
  const railTop = p.scale.feet + 50 - oy; // scale rail top, observer frame
  const postBottom = p.context === 'scale' ? railTop - 34 : -12;
  for (const s of [-1, 1]) {
    slab(frame, s > 0 ? FW - F.post : -FW, postBottom, plateZ, F.post, postTop - postBottom, F.depth, M.graphite, s > 0 ? 'channel' : framePart);
    // rafter from the top of the upright up to the apex, under the roof
    const x0 = s * (FW - F.post / 2), y0 = postTop, x1 = s * 8, y1 = rafterY(8);
    const len = Math.hypot(x1 - x0, y1 - y0);
    const r = box(frame, len + 12, F.post, F.depth, M.graphite, (x0 + x1) / 2, (y0 + y1) / 2, plateZ + F.depth / 2, framePart);
    r.rotation.z = Math.atan2(y1 - y0, x1 - x0);
    // rubber pad against the hive body
    cyl(frame, 7, 4, M.rubber, s * (FW - F.post / 2), postTop - 30, plateZ - 2, 'z', framePart, 16);
  }
  box(frame, 40, 22, F.depth + 6, M.graphite, 0, apexY - 12, plateZ + (F.depth + 6) / 2, framePart); // apex pocket
  // foot of the right upright: cable entries facing down
  const footX = FW - F.post / 2;
  slab(frame, FW - F.post - 2, -40, plateZ, F.post + 2, 30, 36, M.graphite, 'channel');
  cyl(frame, 7, 10, M.black, footX, -45, plateZ + 10, 'y', 'gland', 6);
  cyl(frame, 4, 4, M.rubber, footX, -51, plateZ + 10, 'y', 'gland', 16);
  cyl(frame, 8, 12, M.steel, footX, -46, plateZ + 27, 'y', 'm12', 20);
  cyl(frame, 9.5, 3, M.black, footX, -41.5, plateZ + 27, 'y', 'm12', 20);
  if (p.context === 'scale') {
    // printed risers: hooks over the scale front rail at the bottom of the uprights
    for (const s of [-1, 1]) slab(frame, s > 0 ? FW - F.post : -FW, railTop - 4, -18, F.post, 10, 18, M.asa, 'riser');
  }

  // ----- entrance porch + automatic gate --------------------------------------
  const PW2 = PO.w / 2, pTop = H.slot + 2;
  const porch = group(obs, 'porch', 0, 0, 0, 'porch');
  const pz0 = Math.min(d.wallZ, 0) + (p.context === 'scale' ? 2 : 3);
  const lz0 = PO.gateZ - 6; // lintel starts here
  slab(porch, -PW2 - PO.wall, pTop, pz0, PO.w + 2 * PO.wall, PO.roof, lz0 - pz0, M.porch, 'porch');
  slab(porch, -PW2 - PO.wall, pTop, lz0, PO.w + 2 * PO.wall, 21, PO.depth - lz0, M.porch, 'lintel');
  for (const s of [-1, 1]) slab(porch, s > 0 ? PW2 : -PW2 - PO.wall, 0, pz0, PO.wall, pTop, PO.depth - pz0, M.porch, 'porch');
  // floor with the gate slit, widened into an apron up to the uprights so the camera never sees the ground
  slab(porch, -(FW - F.post), -3, pz0, 2 * (FW - F.post), 3, PO.floorEnd - pz0, M.porch, 'porch');
  // gate drive box under the floor (not in view)
  slab(porch, -PW2 - 10, -45, PO.gateZ - 7, PO.w + 20, 42, 14, M.graphite, 'gateDrive');
  slab(porch, PW2 + 10, -45, PO.gateZ - 12, 36, 42, 24, M.graphite, 'gateDrive'); // motor end
  cyl(porch, 3, 40, M.steel, PW2 + 4, -24, PO.gateZ, 'y', 'gateDrive', 10);
  // the gate: flat plate with a centre notch, rising out of the floor
  const gate = group(porch, 'gate', 0, GATE[p.gate] ?? 0, PO.gateZ, 'gate');
  nodes.gate = gate;
  nodes.gateHome = 0;
  const N2 = PO.notch / 2, GH = 36;
  for (const s of [-1, 1]) {
    slab(gate, s > 0 ? N2 : -PW2, -GH, -1, PW2 - N2, GH, 2, M.gate, 'gate');
    slab(gate, s > 0 ? N2 : -PW2, -1.5, -1.3, PW2 - N2, 1.5, 2.6, M.gasket, 'gate'); // soft edge
  }
  slab(gate, -N2, -GH, -1, 2 * N2, GH - pTop, 2, M.gate, 'gate');
  slab(gate, -N2, -pTop - 1.5, -1.3, 2 * N2, 1.5, 2.6, M.gasket, 'gate');

  // ----- head: ridge beam, roof, front rafters, pod ---------------------------
  const headAsm = explodable(group(obs, 'head', 0, 0, 0, 'beam'), 0, 330, 0);
  nodes.head = headAsm;
  const beamTop = roofUnder(BM.w / 2) - 1;
  slab(headAsm, -BM.w / 2, beamTop - BM.h, plateZ + F.depth, BM.w, BM.h, BM.len, M.anod, 'beam');
  box(headAsm, 20, 14, 8, M.anod, 0, apexY - 6, plateZ + F.depth - 4, 'thumb'); // hook into the apex pocket
  cyl(headAsm, 7, 8, M.pod, 0, apexY - 4, plateZ + F.depth + 8, 'z', 'thumb', 20);
  // front rafters under the front edge of the roof
  const frontZ = RF.z0 + RF.len - 8;
  for (const s of [-1, 1]) {
    const len = RF.halfW / Math.cos(rad(RF.slope)) - 16;
    const r = box(headAsm, len, 10, 8, M.graphite, s * (len / 2) * Math.cos(rad(RF.slope)), RF.ridge - 7 - (len / 2) * Math.sin(rad(RF.slope)), frontZ, 'rafter');
    r.rotation.z = -s * rad(RF.slope);
  }
  // the roof: one sheet bent along the ridge
  const cPart = solar ? 'solarCanopy' : 'canopy';
  const roof = group(headAsm, 'roof', 0, RF.ridge, RF.z0, cPart);
  nodes.canopy = roof;
  const sheet = solar ? M.acm : M.opal;
  const slant = RF.halfW / Math.cos(rad(RF.slope));
  for (const s of [-1, 1]) {
    const half = group(roof, s > 0 ? 'roofRight' : 'roofLeft', 0, 0, 0, cPart);
    half.rotation.z = -s * rad(RF.slope);
    box(half, slant, RF.t, RF.len, sheet, (s * slant) / 2, RF.t / 2, RF.len / 2, cPart);
    box(half, 3, 10, RF.len, solar ? M.acm : M.opalEdge, s * (slant - 1.5), RF.t - 5, RF.len / 2, cPart); // drip edge at the eave
    if (solar) {
      box(half, slant - 24, 1.2, RF.len - 20, M.solar, s * (slant / 2 + 4), RF.t + 0.6, RF.len / 2, 'solarCanopy');
      for (let i = 1; i < 4; i++) box(half, 0.8, 1.5, RF.len - 20, M.solarGrid, s * (16 + (i * (slant - 24)) / 4), RF.t + 0.7, RF.len / 2, 'solarCanopy');
      box(half, slant - 24, 1.5, 0.8, M.solarGrid, s * (slant / 2 + 4), RF.t + 0.7, RF.len / 2, 'solarCanopy');
    }
  }
  box(roof, 12, 4, RF.len + 2, M.pod, 0, RF.t + 1, RF.len / 2, cPart); // honey-yellow ridge cap

  // pod: the only machined metal, hangs under the ridge beam
  const pod = explodable(group(headAsm, 'pod', 0, HD.y, HD.z, 'pod'), 0, -150, 0);
  nodes.pod = pod;
  const pw = HD.w, ph = HD.h, pd = HD.d;
  slab(pod, -pw / 2, 0, -pd / 2, pw, 4, pd, M.anod, 'pod');
  slab(pod, -pw / 2, ph - 5, -pd / 2, pw, 5, pd, M.anod, 'pod');
  for (const s of [-1, 1]) slab(pod, s > 0 ? pw / 2 - 4 : -pw / 2, 0, -pd / 2, 4, ph, pd, M.anod, 'pod');
  for (const s of [-1, 1]) cyl(pod, 4, pd, M.anod, s * (pw / 2 - 3), ph - 4, 0, 'z', 'pod', 12);
  slab(pod, -pw / 2 + 2, 0, -pd / 2, pw - 4, ph, 4, M.asa, 'pod'); // printed back cap
  for (let x = -70; x <= 70; x += 14) box(pod, 2.5, 5, pd - 10, M.anod, x, ph + 2.5, 0, 'pod'); // fins
  for (const s of [-1, 1]) box(pod, 16, BM.h, 20, M.anod, 0, ph + 4, s * 40, 'beam'); // hangers to the beam
  // underside: light bars, microphone, light/climate sensor
  for (const s of [-1, 1]) {
    box(pod, 120, 4, 10, M.white, 0, -2, s * 50, 'led');
    box(pod, 116, 1, 7, M.led, 0, -4.2, s * 50, 'led');
  }
  cyl(pod, 4, 1.5, M.matt, 60, -0.8, 12, 'y', 'mic', 20);
  cyl(pod, 6, 5, M.white, -60, -2.5, 12, 'y', 'sensor', 20);
  for (let i = 0; i < 3; i++) cyl(pod, 7 - i, 1, M.white, -60, -5.5 - i * 1.4, 12, 'y', 'sensor', 20);
  const sup = group(pod, 'supervisor', -20, ph - 11, -34, 'supervisor');
  box(sup, 80, 1.6, 50, M.pcb, 0, 0, 0, 'supervisor');
  box(sup, 15.4, 2.4, 20.5, M.can, -22, 2, 8, 'supervisor'); // ESP32-S3 module
  box(sup, 22, 5, 16, M.chip, 18, 3.3, -10, 'supervisor'); // PoE PD transformer

  // camera module + hood, tilted back toward the hive
  const camG = explodable(group(pod, 'cameraModule', 0, 0, 0, 'camera'), 0, -95, 0);
  camG.rotation.x = rad(p.camera.tilt);
  box(camG, 38, 1.6, 38, M.pcb, 0, 10, 0, 'camera');
  box(camG, 14, 3, 14, M.chip, 0, 8, 0, 'camera');
  cyl(camG, 8, 12, M.black, 0, 2, 0, 'y', 'camera', 24); // M12 lens barrel
  cyl(camG, 20, 16, M.matt, 0, -8, 0, 'y', 'hood', 32, 14); // hood cone, wide at the pod
  cyl(camG, 13, 1, M.glass, 0, -16.3, 0, 'y', 'hood', 32);
  cyl(camG, 15, 2, M.black, 0, -15.5, 0, 'y', 'hood', 32); // window bezel ring
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

  // compute cassette: slides out of the front of the pod
  const comp = explodable(group(pod, 'computeCassette', 0, 0, 0, 'compute'), 0, 0, 170);
  nodes.compute = comp;
  slab(comp, -48, 6, 0, 96, 3, pd / 2 - 2, M.asa, 'compute');
  const pi = group(comp, 'pi', 0, 14, pd / 4, 'compute');
  box(pi, 85, 1.6, 56, M.pcb, 0, 0, 0, 'compute');
  box(pi, 15, 1.4, 15, M.can, -8, 1.5, 0, 'compute');
  box(pi, 85, 1.6, 56, M.pcb, 0, 14, 0, 'compute'); // Hailo HAT
  box(pi, 14, 1.2, 14, M.chip, 4, 15.4, 4, 'compute');
  box(pi, 42, 1, 22, M.chip, 0, -2.5, 0, 'compute'); // NVMe underneath
  box(pi, 50, 4, 40, M.gasket, 0, 18, 0, 'compute'); // thermal pad to the pod roof
  const face = group(comp, 'serviceFace', 0, ph / 2, pd / 2 + 1.5, 'face');
  box(face, pw - 10, ph - 6, 3, M.pod, 0, 0, 0, 'face');
  place(face, cached('ring', () => new THREE.TorusGeometry(7 * MM, 1.6 * MM, 10, 28)), M.status, 40, 8, 1.8, 'face');
  cyl(face, 5, 3, M.podDark, 40, 8, 2, 'z', 'face', 24); // button inside the ring
  box(face, 14, 7, 2, M.rubber, 40, -12, 2, 'face'); // USB-C flap
  cyl(face, 6, 3, M.steel, -50, 0, 2, 'z', 'face', 20); // quarter-turn latch
  box(face, 9, 2, 1.5, M.black, -50, 0, 3.6, 'face');
  const hex = place(face, cached('hex', () => new THREE.CylinderGeometry(8 * MM, 8 * MM, 1.5 * MM, 6)), M.graphite, 0, 0, 1.8, 'face');
  hex.rotation.x = Math.PI / 2;

  // side bay: battery cassette (solar) or a cover
  if (solar) {
    const bat = explodable(group(pod, 'batteryCassette', 0, 0, 0, 'battery'), -170, 0, 0);
    nodes.battery = bat;
    for (let i = 0; i < 4; i++) cyl(bat, 16, 70, M.cellWrap, i % 2 ? 36 : -36, 24, i < 2 ? -52 : -20, 'x', 'battery', 24); // 4 × 32700 in the rear half
    slab(bat, -pw / 2 - 1.5, 3, -pd / 2 + 4, 3, ph - 6, pd - 8, M.podDark, 'battery');
  } else {
    slab(pod, -pw / 2 - 1.5, 3, -pd / 2 + 4, 3, ph - 6, pd - 8, M.graphite, 'blank');
  }
  if (!solar) {
    // Opal diffuses the sun: the roof and the pod under it cast no hard shadow on the board.
    roof.traverse((o) => { if (o.isMesh) o.castShadow = false; });
    pod.traverse((o) => { if (o.isMesh) o.castShadow = false; });
  }

  // ----- internal harness (inside the right upright; seen in the exploded view)
  cable(obs, [[footX, -38, plateZ + 10], [footX, 60, plateZ + 8], [footX, postTop - 20, plateZ + 8], [60, apexY - 40, plateZ + 8], [8, beamTop - 20, plateZ + 20], [8, beamTop - 20, HD.z - 40], [8, HD.y + HD.h, HD.z - 30]], 2.4, M.cable, 'harness');
  cable(obs, [[PW2 + 28, -30, PO.gateZ], [footX - 4, -30, PO.gateZ - 10], [footX, -30, plateZ + 20]], 1.6, M.cable, 'harness'); // gate drive lead

  // ----- landing board ------------------------------------------------------------
  const boardHinge = group(obs, 'landingBoard', 0, -2, PO.floorEnd, 'board');
  boardHinge.rotation.x = rad(p.boardSlope);
  explodable(boardHinge, 0, -20, 170);
  nodes.board = boardHinge;
  const BW = p.board.w, BD = p.board.d;
  slab(boardHinge, -BW / 2, -11, 0, BW, 8, BD, M.board, 'board');
  slab(boardHinge, -BW / 2 + 12, -3, 1, BW - 24, 3, BD - 5, M.insert, 'insert');
  box(boardHinge, 40, 3.2, 8, M.board, 0, -1.4, BD - 3, 'insert'); // finger notch lip
  box(boardHinge, BW - 40, 6, 20, M.alu, 0, -14, BD / 2, 'board'); // stiffener underneath
  for (const sx of [-1, 1]) cyl(boardHinge, 4, 14, M.steel, sx * (PW2 - 4), -6, 0, 'x', 'hinge', 12);
  // ArUco-style markers in the four corners (hand-set pattern, not a real ID)
  const pattern = [[1, 0, 1, 1], [0, 1, 0, 1], [1, 1, 0, 0], [0, 1, 1, 0]];
  for (const [mx, mz] of [[-1, 0], [1, 0], [-1, 1], [1, 1]]) {
    const cx = mx * 172, cz = mz ? BD - 50 : 18;
    box(boardHinge, 30, 0.4, 30, M.markBlack, cx, 0.2, cz, 'marker');
    pattern.forEach((row, r) => row.forEach((v, c) => {
      if (v) box(boardHinge, 5, 0.5, 5, M.markWhite, cx - 7.5 + c * 5, 0.3, cz - 7.5 + r * 5, 'marker');
    }));
  }
  // millimetre scale near the front edge (cm ticks, long every 5 cm)
  for (let x = -150; x <= 150; x += 10) box(boardHinge, 0.8, 0.3, x % 50 === 0 ? 8 : 4, M.markBlack, x, 0.15, BD - 28, 'marker');
  box(boardHinge, 301, 0.3, 0.8, M.markBlack, 0, 0.15, BD - 24, 'marker');
  // counting line: a faint printed line just in front of the porch mouth
  for (let x = -150; x < 150; x += 12) box(boardHinge, 7, 0.3, 1.2, M.markGrey, x + 3.5, 0.15, 3, 'countLine');

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
    [-120, 8, 0.3], [-60, 12, 2.9, true], [10, 30, -0.4], [55, 6, 3.3], [95, 70, 2.2, true], [-150, 95, 1.1],
    [140, 24, -2.6], [-30, 60, 0.9], [150, 110, -0.8], [-95, 48, 3.0, true], [30, 95, 2.6], [-10, 118, 3.1],
  ];
  for (const [x, z, r, pl] of walkers) addBee(bees, x, 2.2, z, r, pl);
  // wall landers: on the hive wall above the porch, then walking over the porch roof
  const beesWall = group(obs, 'beesWall');
  nodes.bees.push(beesWall);
  for (const [x, y] of [[-70, 40], [45, 52], [120, 34]]) {
    const b = addBee(beesWall, x, y, d.wallZ + 3, 0);
    b.rotation.x = Math.PI / 2; // head down, on the vertical wall
  }
  for (const [x, z, r] of [[-40, PO.gateZ - 20, 0.2], [80, PO.gateZ - 30, -0.3]]) addBee(beesWall, x, pTop + PO.roof + 2, z, r);
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
    // PoE cable: drip loop under the right upright, down the stand, away along the ground
    const g = W(footX, -51, plateZ + 10);
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
    const acc = W(footX, -48, plateZ + 27);
    cable(fieldCables, [acc, [acc[0], acc[1] - 20, acc[2] - 2], [acc[0] - 20, bY - 10, acc[2] - 30], [120, bY - 16, bd / 2 + 30], [60, bY - 12, bd / 2 + 18], [60, bY - 6, bd / 2 + 18]], 2.3, M.cable);
    const g = W(footX, -51, plateZ + 10);
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
    for (const s of [-1, 1]) box(rb, cw / 2 - FW - 6, holeY1 - holeY0, R.clad, M.robotClad, s * (cw / 2 + FW + 6) / 2, (holeY0 + holeY1) / 2, fz, 'robot');
    // entrance tunnel from the bottom board to the cabinet front
    box(rb, cw + 120, 20, 2 * PZ + 180, M.robot, 0, postH + 30, 0, 'robot'); // roof
    const g = W(footX, -51, plateZ + 10);
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

  return { root, nodes, params: p, derived: d, applyExplode, MM, GATE };
}
