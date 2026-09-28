// Studio look for the marketing showcases on a black page: product-render style
// lighting (key, fill, two rim lights so edges separate from the black), sharper
// reflections, soft shadows on a dark glossy floor that fades into the page, and
// procedural surface detail (wood grain, brushed metal, fine plastic texture).
//
// Detail is computed in the shader from world position and normal, so it needs no
// UVs or texture files and the procedural geometry stays as it is. Only the
// showcase uses this; the interactive viewer keeps its own daylight scene.
//
// Kept identical in entrance-observer/3d-model/studio.js and
// beehive-sensors/model/studio.js.
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';

export function setupStudio(renderer, scene, { shadowBox }) {
  renderer.setClearColor(0x000000, 1);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap; // PCFSoftShadowMap is removed in r18x; PCF honours shadow.radius
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;

  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.01).texture;
  scene.environmentIntensity = 0.85;
  pmrem.dispose();

  const key = new THREE.DirectionalLight(0xfff3e0, 3.2);
  key.position.set(-1.4, 2.6, 2.0);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.radius = 4;
  key.shadow.bias = -0.0004;
  key.shadow.normalBias = 0.002;
  Object.assign(key.shadow.camera, { near: 0.5, far: 6, ...shadowBox });
  const fill = new THREE.DirectionalLight(0xdfe8ff, 0.7);
  fill.position.set(2.2, 1.0, 1.6);
  const rimL = new THREE.DirectionalLight(0xffffff, 2.4);
  rimL.position.set(-2.0, 1.6, -2.4);
  const rimR = new THREE.DirectionalLight(0xfff0d8, 2.0);
  rimR.position.set(2.2, 1.2, -2.0);
  scene.add(key, fill, rimL, rimR, new THREE.HemisphereLight(0xffffff, 0x202020, 0.35));

  // Dark satin floor: catches the shadows and a soft sheen, and fades out radially
  // so it has no visible edge against the black page.
  const floor = new THREE.Mesh(
    new THREE.CircleGeometry(1.1, 96),
    new THREE.MeshStandardMaterial({ color: 0x0a0a0a, roughness: 0.7, metalness: 0, envMapIntensity: 0.25, transparent: true, alphaMap: radialFade(), depthWrite: false }),
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.0005;
  floor.receiveShadow = true;
  floor.renderOrder = -1;
  scene.add(floor);
  return { key, floor };
}

function radialFade() {
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const g = c.getContext('2d');
  const grd = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  grd.addColorStop(0, '#fff');
  grd.addColorStop(0.3, '#999');
  grd.addColorStop(0.65, '#2a2a2a');
  grd.addColorStop(1, '#000');
  g.fillStyle = grd;
  g.fillRect(0, 0, 256, 256);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.NoColorSpace;
  return t;
}

// ---- procedural surface detail ------------------------------------------------

const hueOf = (m) => { const hsl = {}; m.color.getHSL(hsl); return hsl; };
// Classify by what the material looks like, so both models work without tagging:
// warm, not too saturated, non-metal, rough -> wood; metal -> brushed; rest -> plastic/paint.
function kindOf(m) {
  if (m.metalness >= 0.5) return 'metal';
  const { h, s, l } = hueOf(m);
  if (m.roughness >= 0.75 && h > 0.04 && h < 0.13 && s > 0.2 && s < 0.75 && l > 0.15 && l < 0.75) return 'wood';
  return 'plastic';
}

const NOISE = /* glsl */ `
float st_hash(vec3 p) { p = fract(p * 0.3183099 + 0.1); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
float st_noise(vec3 x) {
  vec3 i = floor(x); vec3 f = fract(x); f = f * f * (3.0 - 2.0 * f);
  return mix(mix(mix(st_hash(i), st_hash(i + vec3(1,0,0)), f.x), mix(st_hash(i + vec3(0,1,0)), st_hash(i + vec3(1,1,0)), f.x), f.y),
             mix(mix(st_hash(i + vec3(0,0,1)), st_hash(i + vec3(1,0,1)), f.x), mix(st_hash(i + vec3(0,1,1)), st_hash(i + vec3(1,1,1)), f.x), f.y), f.z);
}
float st_fbm(vec3 p) { float a = 0.5, s = 0.0; for (int i = 0; i < 4; i++) { s += a * st_noise(p); p *= 2.03; a *= 0.5; } return s; }
`;

function patch(m, kind) {
  if (m.userData.studio) return;
  m.userData.studio = kind;
  if (kind === 'metal') { m.roughness = Math.max(0.18, m.roughness * 0.8); m.envMapIntensity = 1.3; }
  if (kind === 'plastic') { m.roughness = Math.min(1, m.roughness); m.envMapIntensity = 1.1; }
  if (kind === 'wood') m.envMapIntensity = 0.8;
  const prev = m.onBeforeCompile;
  m.onBeforeCompile = (shader, r) => {
    prev?.call(m, shader, r);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vStWorld;\nvarying vec3 vStNormal;')
      .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvStWorld = (modelMatrix * vec4(transformed, 1.0)).xyz;\nvStNormal = normalize(mat3(modelMatrix) * objectNormal);');
    let detail;
    if (kind === 'wood') {
      // Grain runs along the board: along X on faces looking along Z/Y, along Z on faces looking along X.
      detail = `
        vec3 n = abs(vStNormal);
        vec3 p = vStWorld * 1000.0; // millimetres
        vec3 q = n.x > n.z && n.x > n.y ? p.zyx : p;
        float warp = st_fbm(vec3(q.x * 0.004, q.y * 0.05, q.z * 0.05)) * 6.0;
        float ring = sin((q.y + q.z * 0.35) * 0.9 + warp * 3.0);
        float streak = st_fbm(vec3(q.x * 0.01, q.y * 0.6, q.z * 0.6));
        float g = 0.82 + 0.1 * ring + 0.22 * (streak - 0.5);
        diffuseColor.rgb *= g;
        stRough = clamp(stRough + 0.08 * (0.5 - streak), 0.0, 1.0);`;
    } else if (kind === 'metal') {
      detail = `
        vec3 p = vStWorld * 1000.0;
        float b = st_noise(vec3(p.x * 0.02, p.y * 4.0, p.z * 4.0)) + 0.5 * st_noise(vec3(p.x * 0.05, p.y * 9.0, p.z * 9.0));
        diffuseColor.rgb *= 0.96 + 0.06 * b;
        stRough = clamp(stRough + 0.12 * (b - 0.75), 0.05, 1.0);`;
    } else {
      detail = `
        vec3 p = vStWorld * 1000.0;
        float f = st_fbm(p * 0.35);
        diffuseColor.rgb *= 0.97 + 0.06 * f;
        stRough = clamp(stRough + 0.1 * (f - 0.5), 0.05, 1.0);`;
    }
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>\nvarying vec3 vStWorld;\nvarying vec3 vStNormal;\n${NOISE}`)
      .replace('#include <map_fragment>', `#include <map_fragment>\nfloat stRough = roughness;\n{${detail}\n}`)
      .replace('#include <roughnessmap_fragment>', 'float roughnessFactor = stRough;\n#ifdef USE_ROUGHNESSMAP\n  roughnessFactor *= texture2D( roughnessMap, vRoughnessMapUv ).g;\n#endif');
  };
  m.customProgramCacheKey = () => `studio-${kind}`;
  m.needsUpdate = true;
}

// Walk the model once: shadows on every mesh, detail on every lit material.
export function dressModel(root) {
  root.traverse((o) => {
    if (!o.isMesh) return;
    o.castShadow = true;
    o.receiveShadow = true;
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
      if (!m || !m.isMeshStandardMaterial || m.emissiveIntensity > 0.2 && m.emissive?.getHex()) continue;
      patch(m, kindOf(m));
    }
  });
}
