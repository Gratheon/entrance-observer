// Marketing showcase: the Entrance Observer on a hive, exploding into its parts
// as the page scrolls. No controls, no panel. Mounts on every
// [data-eo-showcase] element; the <img> inside stays as the fallback (no JS,
// no WebGL) and as the placeholder until the first frame is drawn.
//
// Scroll mapping. Inside a pinned section ([data-eo-scrolly], a tall block
// with a sticky full-screen stage), progress runs 0 → 1 across the section:
// the camera orbits ~130° round the front of the device, the Observer explodes early,
// stays apart while the camera turns, and reassembles at the end. Without such
// a section, it explodes while the element's centre moves up the viewport.
import * as THREE from 'three';
import { setupStudio, dressModel } from './studio.js';
import { buildObserver } from './observer-model.js';

const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

export function mountShowcase(root) {
  const canvas = document.createElement('canvas');
  canvas.className = 'eo-showcase-canvas';
  canvas.setAttribute('aria-hidden', 'true');
  root.appendChild(canvas);

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));

  const scene = new THREE.Scene();
  setupStudio(renderer, scene, { shadowBox: { left: -0.8, right: 0.8, top: 1.4, bottom: -0.4 } });

  const model = buildObserver({ context: 'hive', colour: 'blue', pattern: 'dots' });
  scene.add(model.root);
  const hiveMats = model.nodes.hiveMaterials;
  const stand = model.root.getObjectByName('stand');
  const standMats = [];
  stand?.traverse((o) => { if (o.isMesh && !standMats.includes(o.material)) { o.material = o.material.clone(); standMats.push(o.material); } });
  for (const m of [...hiveMats, ...standMats]) m.transparent = true;
  model.nodes.fov.visible = false;
  dressModel(model.root);

  const camera = new THREE.PerspectiveCamera(28, 1, 0.05, 20);
  const [ox, oy, oz] = model.derived.origin.map((v) => v * 0.001);
  const target = new THREE.Vector3();

  const scrolly = root.closest('[data-eo-scrolly]');
  let p = 0; // scroll progress 0..1 asked for by the page
  let q = 0; // progress drawn (eases towards p)
  let u = 0; // explode amount drawn
  // explode curve over the progress: apart early, together again at the end
  const explodeAt = (t) => (scrolly ? smooth(0.04, 0.34, t) * (1 - smooth(0.8, 0.98, t)) : smooth(0.1, 0.55, t));
  let size = { w: 1, h: 1 };
  let raf = 0;
  let visible = false;

  const place = () => {
    const e = smooth(0, 1, u);
    // orbit: same camera path as beehive-sensors/model/showcase.js (front-left round to the service side)
    const yaw = scrolly ? -0.9 + smooth(0, 1, q) * 2.3 : -0.55 + q * 0.6;
    target.set(ox, oy + 0.16 + e * 0.2, oz + 0.05 + e * 0.05);
    const dist = (scrolly ? 1.45 : 1.55) + e * 0.55;
    const pitch = 0.26 + e * 0.12 + (scrolly ? 0.06 * Math.sin(q * Math.PI) : 0);
    camera.position.set(
      target.x + Math.sin(yaw) * Math.cos(pitch) * dist,
      target.y + Math.sin(pitch) * dist,
      target.z + Math.cos(yaw) * Math.cos(pitch) * dist,
    );
    camera.lookAt(target);
  };
  const draw = () => {
    u = explodeAt(q);
    model.applyExplode(u);
    const fade = 1 - 0.9 * smooth(0.02, 0.4, u); // the hive steps back as the parts come apart
    for (const m of hiveMats) { m.opacity = fade; m.depthWrite = fade > 0.99; }
    for (const m of standMats) { m.opacity = fade; m.depthWrite = fade > 0.99; }
    place();
    renderer.render(scene, camera);
  };
  const tick = () => {
    raf = 0;
    const d = p - q;
    q = Math.abs(d) < 0.0008 ? p : q + d * 0.1; // soft follow, so wheel steps glide
    draw();
    if (q !== p) raf = requestAnimationFrame(tick);
  };
  const kick = () => { if (!raf && visible) raf = requestAnimationFrame(tick); };

  const onScroll = () => {
    const vh = innerHeight || 1;
    if (scrolly) {
      const r = scrolly.getBoundingClientRect();
      p = Math.min(1, Math.max(0, -r.top / Math.max(1, r.height - vh)));
    } else {
      const r = root.getBoundingClientRect();
      p = Math.min(1, Math.max(0, 1 - (r.top + r.height / 2) / vh));
    }
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
  }, { rootMargin: '100px' }).observe(scrolly || root);
  addEventListener('scroll', onScroll, { passive: true });
  resize();
  onScroll();
  q = p;
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
