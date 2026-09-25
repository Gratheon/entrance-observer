// Builds the Entrance Observer scene in Node and writes entrance-observer.glb with the
// exploded view baked in as an animation clip ("explode": assembled →
// exploded → assembled).
//   node export-glb.mjs [--context hive|scale|robot] [--power poe|solar] [--out entrance-observer.glb]
import { writeFileSync } from 'node:fs';
import * as THREE from 'three';
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter.js';
import { buildObserver, PARTS } from './observer-model.js';

// GLTFExporter uses FileReader for binary output; Node only has Blob.
globalThis.FileReader = class {
  readAsArrayBuffer(blob) {
    blob.arrayBuffer().then((buf) => { this.result = buf; this.onloadend?.(); this.onload?.({ target: this }); });
  }
  readAsDataURL(blob) {
    blob.arrayBuffer().then((buf) => {
      this.result = `data:${blob.type || 'application/octet-stream'};base64,${Buffer.from(buf).toString('base64')}`;
      this.onloadend?.(); this.onload?.({ target: this });
    });
  }
};

const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > 0 ? process.argv[i + 1] : fallback;
};

const model = buildObserver({ context: arg('context', 'hive'), power: arg('power', 'poe') });
const { root, nodes, applyExplode } = model;
// The field-of-view helper is a viewer overlay, not part of the product.
nodes.fov.removeFromParent();

// Bake assembled → exploded → assembled into position tracks.
const FPS = 15, DURATION = 6;
const times = [];
for (let t = 0; t <= DURATION + 1e-6; t += 1 / FPS) times.push(+t.toFixed(4));
const u = (t) => (t < 1 ? 0 : t < 2.5 ? (t - 1) / 1.5 : t < 3.5 ? 1 : t < 5 ? 1 - (t - 3.5) / 1.5 : 0);
const moving = nodes.explode;
const samples = new Map(moving.map((o) => [o, []]));
for (const t of times) {
  applyExplode(u(t));
  for (const o of moving) samples.get(o).push(...o.position.toArray());
}
const tracks = [];
for (const o of moving) {
  const p = samples.get(o);
  if (p.some((v, i) => Math.abs(v - p[i % 3]) > 1e-7)) tracks.push(new THREE.VectorKeyframeTrack(`${o.name}.position`, times, p));
}
// Cables and bees do not follow the exploded parts, so they shrink away while exploded.
for (const o of [nodes.fieldCables, ...nodes.bees]) {
  tracks.push(new THREE.VectorKeyframeTrack(`${o.name}.scale`, times, times.flatMap((t) => (u(t) < 0.02 ? [1, 1, 1] : [1e-4, 1e-4, 1e-4]))));
}
const clip = new THREE.AnimationClip('explode', DURATION, tracks);
clip.optimize();
applyExplode(0);

// Attach human-readable part info as glTF extras (after baking: this drops the
// explode offsets kept in userData).
root.traverse((o) => {
  const key = o.userData.part;
  o.userData = key && PARTS[key] ? { part: key, title: PARTS[key][0], info: PARTS[key][1] } : {};
});

const scene = new THREE.Scene();
scene.add(root);
const out = arg('out', new URL('./entrance-observer.glb', import.meta.url).pathname);
new GLTFExporter().parse(
  scene,
  (glb) => {
    writeFileSync(out, Buffer.from(glb));
    console.log(`wrote ${out} (${(glb.byteLength / 1024).toFixed(0)} KB, ${tracks.length} tracks, ${DURATION} s clip)`);
  },
  (err) => { console.error(err); process.exit(1); },
  { binary: true, animations: [clip] },
);
