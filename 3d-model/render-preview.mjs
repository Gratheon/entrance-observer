// Renders product images from index.html with headless Chrome (WebGL through
// SwiftShader), using the viewer's #shot hash options.
//   node render-preview.mjs            # ../docs/preview.png + ../docs/preview-*.png
//   CHROME=/path/to/chrome node render-preview.mjs
import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const chrome = process.env.CHROME || [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
].find(existsSync);
if (!chrome) throw new Error('Chrome not found; set CHROME=/path/to/chrome');

const shots = [
  ['hero.png', 'hive=solid&cam=hero&inset=0', [1400, 1200]],
  ['preview.png', 'hive=off&cam=close&explode=1&inset=0', [1600, 1100]],
  ['preview-installed.png', 'hive=solid', [1600, 1100]],
  ['preview-fov.png', 'hive=ghost&cam=side&fov=1&inset=0', [1400, 1000]],
  ['preview-camera.png', 'hive=solid&cam=front', [1400, 1000]],
  ['preview-scale.png', 'context=scale&hive=solid', [1400, 1000]],
  ['preview-robot.png', 'context=robot&hive=ghost', [1400, 1000]],
  ['preview-solar.png', 'power=solar&hive=solid&cam=hero', [1400, 1000]],
  ['preview-gate.png', 'hive=solid&cam=gate&gate=guard&inset=0', [1400, 1000]],
];
const page = pathToFileURL(join(here, 'index.html')).href;
for (const [file, opts, [w, h]] of shots) {
  const out = join(here, '..', 'docs', file);
  execFileSync(chrome, [
    '--headless=new', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--hide-scrollbars',
    `--window-size=${w},${h}`, '--virtual-time-budget=9000', `--screenshot=${out}`,
    `${page}#shot&theme=light&${opts}`,
  ], { stdio: 'ignore' });
  console.log(`wrote docs/${file}`);
}
