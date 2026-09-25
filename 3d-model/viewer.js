// Interactive Entrance Observer viewer. mountEntranceObserver(root) wires up
// one viewer.html block; the root's data-eo elements are looked up inside it,
// so the viewer can be embedded in any page (see build-viewer.mjs).
//
// URL hash options (used by render-preview.mjs for product images):
//   #shot                   hide the panel and overlays
//   explode=0.6             exploded-view position 0..1
//   context=hive|scale|robot  what the Observer hangs on
//   power=poe|solar         opal canopy + PoE, or solar canopy + battery
//   hive=solid|ghost|off    hive display
//   fov=1                   show the camera field of view
//   inset=0                 hide the camera-view inset
//   theme=light|dark        force the colour theme
//   cam=hero|close|side|front  camera framing
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { buildObserver, energy, ENERGY, PARTS } from './observer-model.js';

// Parts list order in the panel, grouped by assembly.
const PART_ORDER = [
  ['Optics', ['camera', 'hood', 'led', 'board', 'insert', 'marker', 'hinge', 'fov']],
  ['Head', ['head', 'compute', 'face', 'supervisor', 'battery', 'blank', 'mic', 'sensor']],
  ['Arch', ['canopy', 'solarCanopy', 'cheek', 'channel', 'harness', 'gland', 'm12', 'thumb']],
  ['Mount', ['plate', 'riser', 'robotFront', 'cable']],
  ['Around it', ['bee', 'hive', 'stand', 'scale', 'scaleLink', 'robot']],
];

const SPECS = (s) => {
  const { derived: d, params: p } = s;
  const e = { ...ENERGY, ...energy() };
  const r = (v) => Math.round(v);
  return [
    ['Size', `${p.canopy.w} × ${r(p.canopy.ridge + p.canopy.t + 33)} × 225 mm (w × h × d)`],
    ['Camera', `8 MP 3840 × 2160, locked M12 lens, ${p.camera.hfov}°, ${p.camera.eye} mm above the board`],
    ['Board in view', `${r(d.fovW)} × ${r(d.fovD)} mm · ${d.pxPerMm.toFixed(1)} px/mm`],
    ['Bee / varroa', `≈ ${r(13 * d.pxPerMm)} px / ≈ ${r(1.5 * d.pxPerMm)} px long`],
    ['Compute', 'swappable sled: Pi 5 + Hailo-8 (Jetson Orin NX option)'],
    ['Supervisor', 'ESP32-S3, always on, ≈ 0.1 W'],
    ['Power in', p.power === 'solar' ? `${e.panelW} W roof panels + ${e.batteryWh} Wh LiFePO4` : 'PoE+ (802.3at) or 12–24 V DC'],
    ['Draw', `≈ 9 W observing · ${e.standby.toFixed(1)} Wh/day asleep`],
    ['Per flight day', `≈ ${r(e.continuous)} Wh continuous · ≈ ${r(e.sampled)} Wh sampled (2 of 15 min)`],
    ['Autonomy', p.power === 'solar' ? `≈ ${r(e.harvest)} Wh/day harvest in season · ${r(e.standbyDays)} days asleep on battery` : 'unlimited on PoE'],
    ['Links', 'Ethernet (PoE) · Wi-Fi · BLE setup · M12 accessory'],
    ['Mounting', { hive: 'entrance plate, 4 screws; hangs on 2 thumbscrews', scale: 'risers on the scale front rail (not weighed)', robot: 'robot entrance frame, same ears' }[p.context]],
    ['Target BOM', '≈ €350–450 at 100 units'],
  ];
};

export function mountEntranceObserver(root) {
  const $ = (name) => root.querySelector(`[data-eo="${name}"]`);
  const hash = new URLSearchParams(location.hash.replace(/^#/, ''));
  const shot = hash.has('shot');
  if (shot) root.classList.add('eo-shot');
  if (['light', 'dark'].includes(hash.get('theme'))) document.documentElement.dataset.theme = hash.get('theme');

  const canvas = $('canvas');
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: shot });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.6;

  const camera = new THREE.PerspectiveCamera(30, 1, 0.02, 60);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.maxPolarAngle = Math.PI * 0.495;
  controls.minDistance = 0.2;
  controls.maxDistance = 6;

  // The Observer's own camera, for the picture-in-picture view.
  const lensCam = new THREE.PerspectiveCamera(50, 16 / 9, 0.004, 5);
  lensCam.up.set(0, 0, -1); // hive at the top of the frame, as in the real video

  const sun = new THREE.DirectionalLight(0xfff6e5, 3.0);
  sun.position.set(-1.5, 3.2, 2.2);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -1.1, right: 1.1, top: 2.0, bottom: -0.6, near: 0.5, far: 8 });
  sun.shadow.bias = -0.0004;
  const fill = new THREE.DirectionalLight(0xdfe8ff, 0.6);
  fill.position.set(2, 1.2, -2.5);
  scene.add(sun, fill, new THREE.HemisphereLight(0xcfe6ff, 0x5d8f3a, 0.8));

  const groundMat = new THREE.MeshStandardMaterial({ color: 0x5da83a, roughness: 1 });
  const ground = new THREE.Mesh(new THREE.CircleGeometry(30, 96), groundMat);
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  // Outdoor backdrop: a sky dome that fades to haze at the horizon, and grass
  // that fogs into the same haze, so ground and sky meet without a seam.
  const skyMat = new THREE.ShaderMaterial({
    uniforms: { top: { value: new THREE.Color(0x1f7fe0) }, horizon: { value: new THREE.Color(0xcfe8f8) } },
    vertexShader: 'varying vec3 vDir; void main() { vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: 'uniform vec3 top; uniform vec3 horizon; varying vec3 vDir; void main() { float h = clamp(vDir.y, 0.0, 1.0); gl_FragColor = vec4(mix(horizon, top, smoothstep(0.0, 0.22, h)), 1.0);\n#include <colorspace_fragment>\n}',
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
  });
  const sky = new THREE.Mesh(new THREE.SphereGeometry(45, 32, 16), skyMat);
  sky.renderOrder = -1;
  scene.add(sky);
  scene.background = new THREE.Color(0xcfe8f8);
  scene.fog = new THREE.Fog(0xcfe8f8, 10, 34);
  const applyThemeColors = () => {
    const cs = getComputedStyle(root);
    const v = (name, fallback) => cs.getPropertyValue(name).trim() || fallback;
    const horizon = v('--eo-scene', '#cfe8f8');
    skyMat.uniforms.top.value.set(v('--eo-sky', '#1f7fe0'));
    skyMat.uniforms.horizon.value.set(horizon);
    scene.fog.color.set(horizon);
    scene.background.set(horizon);
    groundMat.color.set(v('--eo-ground', '#5da83a'));
  };
  applyThemeColors();
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyThemeColors);
  new MutationObserver(applyThemeColors).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

  // ---- model ---------------------------------------------------------------
  const opts = {
    context: ['hive', 'scale', 'robot'].includes(hash.get('context')) ? hash.get('context') : 'hive',
    power: hash.get('power') === 'solar' ? 'solar' : 'poe',
  };
  let hiveMode = ['solid', 'ghost', 'off'].includes(hash.get('hive')) ? hash.get('hive') : 'solid';
  let showFov = hash.get('fov') === '1';
  let showInset = hash.get('inset') !== '0';
  let explode = Math.max(0, Math.min(1, Number(hash.get('explode')) || 0));
  let explodeTarget = explode;
  let selected = null;
  let model;

  // Camera framings are relative to the Observer, wherever it is mounted.
  const frameCamera = () => {
    const [ox, oy, oz] = model.derived.origin.map((v) => v * 0.001);
    const at = (tx, ty, tz, cx, cy, cz) => { controls.target.set(ox + tx, oy + ty, oz + tz); camera.position.set(ox + cx, oy + cy, oz + cz); };
    const view = hash.get('cam');
    if (view === 'hero') at(0.02, 0.12, 0.06, 1.0, 0.52, 1.28);
    else if (view === 'close') at(0.02, 0.12 + explode * 0.12, 0.1, 0.95 + explode * 0.3, 0.42 + explode * 0.25, 1.05 + explode * 0.3);
    else if (view === 'side') at(0, 0.12, 0.1, -0.45, 0.62, 0.95);
    else if (view === 'front') at(0, 0.14, 0.1, 0.2, 0.34, 1.35);
    else if (opts.context === 'robot') at(0, 0.3, -0.1, 2.0, 0.9, 2.3);
    else at(0, 0.18, 0.0, 1.6, 0.75, 1.9);
  };

  function build() {
    if (model) {
      scene.remove(model.root);
      model.root.traverse((o) => o.geometry?.dispose());
    }
    model = buildObserver(opts);
    scene.add(model.root);
    model.applyExplode(explode);
    setHive(hiveMode);
    model.nodes.fov.visible = showFov;
    renderParts();
    renderSpecs();
    if (selected) highlight(selected);
  }

  function setHive(mode) {
    hiveMode = mode;
    for (const b of $('hive').querySelectorAll('button')) b.setAttribute('aria-pressed', String(b.dataset.value === mode));
    model.nodes.hive.visible = mode !== 'off';
    for (const m of model.nodes.hiveMaterials) {
      Object.assign(m, { transparent: mode === 'ghost', opacity: mode === 'ghost' ? 0.16 : 1, depthWrite: mode !== 'ghost' });
      m.needsUpdate = true;
    }
    model.nodes.hive.traverse((o) => { if (o.isMesh && o.userData.part === 'hive') o.castShadow = mode === 'solid'; });
  }

  const pressSeg = (name, value) => {
    for (const b of $(name).querySelectorAll('button')) b.setAttribute('aria-pressed', String(b.dataset.value === String(value)));
  };

  // ---- selection highlight ------------------------------------------------
  const glow = new Map();
  function highlight(part) {
    for (const [mesh, mat] of glow) mesh.material = mat;
    glow.clear();
    if (!part) return;
    model.root.traverse((o) => {
      if (!o.isMesh || o.userData.part !== part) return;
      glow.set(o, o.material);
      const m = o.material.clone();
      if (m.emissive) { m.emissive.set(0xf2b705); m.emissiveIntensity = 0.55; }
      o.material = m;
    });
  }
  function select(part) {
    selected = selected === part ? null : part;
    highlight(selected);
    for (const li of $('parts').children) li.classList.toggle('on', li.dataset.part === selected);
    if (selected) showInfo(selected);
  }
  function showInfo(part) {
    $('info-title').textContent = PARTS[part][0];
    $('info-text').textContent = PARTS[part][1];
  }

  // ---- panel ---------------------------------------------------------------
  function renderParts() {
    const list = $('parts');
    list.innerHTML = '';
    const present = new Set();
    model.root.traverse((o) => { if (o.userData.part) present.add(o.userData.part); });
    let n = 0;
    for (const [groupName, keys] of PART_ORDER) {
      for (const key of keys.filter((k) => present.has(k))) {
        const li = document.createElement('li');
        li.tabIndex = 0;
        li.dataset.part = key;
        li.innerHTML = '<span class="n"></span><span class="t"></span><span class="r"></span><span class="d"></span>';
        li.querySelector('.n').textContent = String(++n).padStart(2, '0');
        li.querySelector('.t').textContent = PARTS[key][0];
        li.querySelector('.r').textContent = groupName;
        li.querySelector('.d').textContent = PARTS[key][1];
        li.classList.toggle('on', key === selected);
        li.addEventListener('click', () => select(key));
        li.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); select(key); } });
        list.appendChild(li);
      }
    }
  }
  function renderSpecs() {
    $('specs').innerHTML = SPECS(model).map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('');
  }

  for (const b of $('context').querySelectorAll('button')) {
    b.addEventListener('click', () => {
      opts.context = b.dataset.value;
      pressSeg('context', opts.context);
      build();
      frameCamera();
    });
  }
  for (const b of $('power').querySelectorAll('button')) {
    b.addEventListener('click', () => {
      opts.power = b.dataset.value;
      pressSeg('power', opts.power);
      build();
    });
  }
  for (const b of $('hive').querySelectorAll('button')) b.addEventListener('click', () => setHive(b.dataset.value));
  const fovBox = $('fov');
  fovBox.checked = showFov;
  fovBox.addEventListener('change', () => { showFov = fovBox.checked; model.nodes.fov.visible = showFov; });
  const insetBox = $('inset');
  insetBox.checked = showInset;
  const insetLabel = $('inset-label');
  const syncInset = () => { insetLabel.hidden = !showInset || shot; };
  insetBox.addEventListener('change', () => { showInset = insetBox.checked; syncInset(); });
  syncInset();
  const explodeBtn = $('explode');
  const scrub = $('scrub');
  explodeBtn.addEventListener('click', () => { explodeTarget = explodeTarget > 0.5 ? 0 : 1; });
  scrub.addEventListener('input', () => { explode = explodeTarget = scrub.value / 1000; });

  // ---- hover / click on the model -----------------------------------------
  const ray = new THREE.Raycaster();
  const ptr = new THREE.Vector2();
  const pick = (e) => {
    const r = canvas.getBoundingClientRect();
    ptr.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ptr, camera);
    for (const h of ray.intersectObject(model.root, true)) {
      let o = h.object;
      if (o.isLine || (hiveMode === 'ghost' && o.userData.part === 'hive')) continue;
      let hidden = false;
      for (let q = o; q; q = q.parent) if (!q.visible) hidden = true;
      if (hidden) continue;
      while (o && !o.userData.part) o = o.parent;
      if (o && PARTS[o.userData.part]) return o.userData.part;
    }
    return null;
  };
  let lastPart = null;
  canvas.addEventListener('pointermove', (e) => {
    const part = pick(e);
    if (part && part !== lastPart && !selected) { lastPart = part; showInfo(part); }
  });
  let down = null;
  canvas.addEventListener('pointerdown', (e) => { down = [e.clientX, e.clientY]; });
  canvas.addEventListener('pointerup', (e) => {
    if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 4) return;
    const part = pick(e);
    if (part) select(part);
    else if (selected) select(selected);
  });

  // ---- loop ----------------------------------------------------------------
  let size = { w: 1, h: 1 };
  const resize = () => {
    const r = canvas.parentElement.getBoundingClientRect();
    size = { w: Math.max(1, r.width), h: Math.max(1, r.height) };
    renderer.setSize(size.w, size.h, false);
    camera.aspect = size.w / size.h;
    camera.updateProjectionMatrix();
  };
  new ResizeObserver(resize).observe(canvas.parentElement);
  resize();

  // Inset: what the Observer camera sees, in the top-right corner of the stage.
  const eyePos = new THREE.Vector3();
  const insetRect = () => {
    const w = Math.round(Math.min(size.w * 0.34, 340));
    const h = Math.round((w * 9) / 16);
    return { x: size.w - w - 12, y: 12, w, h }; // y from the top
  };
  const renderInset = () => {
    const { x, y, w, h } = insetRect();
    model.nodes.eye.getWorldPosition(eyePos);
    lensCam.position.copy(eyePos);
    lensCam.fov = THREE.MathUtils.radToDeg(model.derived.vfov);
    lensCam.aspect = 16 / 9;
    lensCam.updateProjectionMatrix();
    lensCam.lookAt(eyePos.x, eyePos.y - 1, eyePos.z);
    const fovWas = model.nodes.fov.visible;
    model.nodes.fov.visible = false;
    const yGL = size.h - y - h;
    renderer.setScissorTest(true);
    renderer.setScissor(x - 2, yGL - 2, w + 4, h + 4);
    renderer.setViewport(x - 2, yGL - 2, w + 4, h + 4);
    renderer.setClearColor(0xf2b705, 1);
    renderer.clear();
    renderer.setScissor(x, yGL, w, h);
    renderer.setViewport(x, yGL, w, h);
    renderer.render(scene, lensCam);
    renderer.setScissorTest(false);
    renderer.setViewport(0, 0, size.w, size.h);
    renderer.setClearColor(0x000000, 0);
    model.nodes.fov.visible = fovWas;
    insetLabel.style.top = `${y + h + 6}px`;
    insetLabel.style.width = `${w}px`;
  };

  pressSeg('context', opts.context);
  pressSeg('power', opts.power);
  build();
  frameCamera();
  const clock = new THREE.Clock();
  let chipState = '';
  const frame = () => {
    const dt = Math.min(clock.getDelta(), 0.1);
    if (explode !== explodeTarget) {
      const step = dt * 0.9;
      explode = Math.abs(explodeTarget - explode) <= step ? explodeTarget : explode + Math.sign(explodeTarget - explode) * step;
      model.applyExplode(explode);
      scrub.value = String(Math.round(explode * 1000));
    }
    const state = explode > 0.98 ? 'Exploded' : explode < 0.02 ? 'Assembled' : 'Exploding';
    const key = `${state}|${opts.context}`;
    if (key !== chipState) {
      chipState = key;
      $('chip').textContent = `${state} · ${{ hive: 'on a hive', scale: 'on the beehive scale', robot: 'on the Robotic Beehive' }[opts.context]}`;
    }
    explodeBtn.textContent = explodeTarget > 0.5 ? 'Assemble' : 'Explode';
    controls.update();
    // The dome travels with the camera, so zooming out never pushes its far
    // side past the camera's far plane (which clipped it to black).
    sky.position.copy(camera.position);
    renderer.render(scene, camera);
    if (showInset && explode < 0.02) renderInset();
    insetLabel.style.visibility = showInset && explode < 0.02 ? 'visible' : 'hidden';
  };
  // Only render while the viewer is on screen (it is embedded in long pages).
  new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting) { clock.getDelta(); renderer.setAnimationLoop(frame); }
    else renderer.setAnimationLoop(null);
  }).observe(root);
  frame();
  scrub.value = String(Math.round(explode * 1000));
  root.dataset.ready = '1';
}

export function mountAll() {
  for (const root of document.querySelectorAll('[data-entrance-observer]')) {
    if (root.dataset.mounted) continue;
    root.dataset.mounted = '1';
    try {
      mountEntranceObserver(root);
    } catch (err) {
      const note = document.createElement('p');
      note.textContent = `3D preview failed to start: ${err instanceof Error ? err.message : err}`;
      root.replaceChildren(note);
    }
  }
}
