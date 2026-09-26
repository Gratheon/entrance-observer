// Marketing showcase: the Entrance Observer on a hive, exploding into its parts
// as the page scrolls. No controls, no panel. Mounts on every
// [data-eo-showcase] element; the <img> inside stays as the fallback (no JS,
// no WebGL) and as the placeholder until the first frame is drawn.
//
// Scroll mapping: while the element's centre moves from 75 % to 30 % of the
// viewport height, the Observer explodes; scrolling back reassembles it.
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { buildObserver } from './observer-model.js';

const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

export function mountShowcase(root) {
  const canvas = document.createElement('canvas');
  canvas.className = 'eo-showcase-canvas';
  canvas.setAttribute('aria-hidden', 'true');
  root.appendChild(canvas);

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
  renderer.setClearColor(0x000000, 0);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.7;
  const sun = new THREE.DirectionalLight(0xfff6e5, 2.6);
  sun.position.set(-1.2, 2.8, 2.2);
  sun.castShadow = true;
  sun.shadow.mapSize.set(1024, 1024);
  Object.assign(sun.shadow.camera, { left: -0.8, right: 0.8, top: 1.4, bottom: -0.4, near: 0.5, far: 6 });
  sun.shadow.bias = -0.0005;
  scene.add(sun, new THREE.HemisphereLight(0xeaf2ff, 0xb9c9a0, 0.9));
  // soft contact shadow on an invisible floor, so the hive stands on the page
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(4, 4), new THREE.ShadowMaterial({ opacity: 0.18 }));
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  scene.add(floor);

  const model = buildObserver({ context: 'hive', colour: 'blue', pattern: 'dots' });
  scene.add(model.root);
  const hiveMats = model.nodes.hiveMaterials;
  const stand = model.root.getObjectByName('stand');
  const standMats = [];
  stand?.traverse((o) => { if (o.isMesh && !standMats.includes(o.material)) { o.material = o.material.clone(); standMats.push(o.material); } });
  for (const m of [...hiveMats, ...standMats]) m.transparent = true;
  model.nodes.fov.visible = false;

  const camera = new THREE.PerspectiveCamera(28, 1, 0.05, 20);
  const [ox, oy, oz] = model.derived.origin.map((v) => v * 0.001);
  const target = new THREE.Vector3();

  let u = 0; // explode amount drawn
  let goal = 0; // explode amount the scroll position asks for
  let p = 0; // scroll progress 0..1
  let size = { w: 1, h: 1 };
  let raf = 0;
  let visible = false;

  const place = () => {
    // assembled: close on the Observer; exploded: pull back and up to fit the parts
    const e = smooth(0, 1, u);
    target.set(ox, oy + 0.17 + e * 0.17, oz + 0.06 + e * 0.05);
    const yaw = -0.62 + p * 0.5; // a slow quarter turn while scrolling
    const dist = 1.55 + e * 0.4;
    const pitch = 0.3 + e * 0.05;
    camera.position.set(
      target.x + Math.sin(-yaw) * Math.cos(pitch) * dist,
      target.y + Math.sin(pitch) * dist,
      target.z + Math.cos(yaw) * Math.cos(pitch) * dist,
    );
    camera.lookAt(target);
  };
  const draw = () => {
    model.applyExplode(u);
    const fade = 1 - 0.88 * smooth(0.02, 0.45, u); // the hive steps back as the parts come apart
    for (const m of hiveMats) { m.opacity = fade; m.depthWrite = fade > 0.99; }
    for (const m of standMats) { m.opacity = fade; m.depthWrite = fade > 0.99; }
    place();
    renderer.render(scene, camera);
  };
  const tick = () => {
    raf = 0;
    const d = goal - u;
    u = Math.abs(d) < 0.002 ? goal : u + d * 0.12;
    draw();
    if (u !== goal) raf = requestAnimationFrame(tick);
  };
  const kick = () => { if (!raf && visible) raf = requestAnimationFrame(tick); };

  const onScroll = () => {
    const r = root.getBoundingClientRect();
    const vh = innerHeight || 1;
    const centre = (r.top + r.height / 2) / vh; // 1 = at the bottom, 0 = at the top
    p = Math.min(1, Math.max(0, 1 - centre));
    goal = smooth(0.25, 0.7, p);
    kick();
  };
  const resize = () => {
    const r = root.getBoundingClientRect();
    size = { w: Math.max(1, r.width), h: Math.max(1, r.height) };
    renderer.setSize(size.w, size.h, false);
    camera.aspect = size.w / size.h;
    camera.updateProjectionMatrix();
    draw();
  };
  new ResizeObserver(resize).observe(root);
  new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
    if (visible) onScroll();
  }, { rootMargin: '100px' }).observe(root);
  addEventListener('scroll', onScroll, { passive: true });
  resize();
  onScroll();
  u = goal;
  draw();
  root.classList.add('eo-showcase-ready'); // hides the fallback image
}

export function mountShowcases() {
  const roots = document.querySelectorAll('[data-eo-showcase]');
  if (!roots.length) return;
  // WebGL check: without it the static image simply stays.
  const probe = document.createElement('canvas');
  if (!(probe.getContext('webgl2') || probe.getContext('webgl'))) return;
  const start = (root) => {
    if (root.dataset.mounted) return;
    root.dataset.mounted = '1';
    try { mountShowcase(root); } catch (err) { console.warn('Entrance Observer showcase failed:', err); }
  };
  // Build the scene only when the showcase is about to scroll into view.
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) if (e.isIntersecting) { io.unobserve(e.target); start(e.target); }
  }, { rootMargin: '400px' });
  roots.forEach((r) => io.observe(r));
}
