// Project real frozen globe points for rendered hit-target regression.
const fs = require('fs');
const path = require('path');
const root = process.cwd();
const ts = require(path.join(root, 'apps/drishti-v2/node_modules/typescript'));
const THREE = require(path.join(root, 'apps/drishti-v2/node_modules/three'));
function load(file) {
  const code = ts.transpileModule(fs.readFileSync(file, 'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
  const mod = {exports:{}};
  new Function('exports', 'module', 'require', code)(mod.exports, mod, name => name === 'three' ? THREE : load(path.resolve(path.dirname(file), name) + '.ts'));
  return mod.exports;
}
const data = load(path.join(root, 'apps/drishti-v2/src/data/globe.ts'));
const geo = load(path.join(root, 'apps/drishti-v2/src/three/globe.ts'));
const f = JSON.parse(fs.readFileSync(path.join(root, 'apps/drishti-v2/src/data/fixtures/runs/agency-v2.json')));
const points = data.buildGlobeData(f, true).locatedPoints;
const aspect = Number(process.argv[2]);
const camera = new THREE.PerspectiveCamera(45, aspect, .1, 1000);
const h = 1.6 * 1.12 / Math.tan(Math.PI / 8);
camera.position.set(0, 0, Math.max(h, h/aspect)); camera.updateMatrixWorld();
const india = geo.latLonToVec3(22.5, 79, 1, new THREE.Vector3());
const yaw = Math.PI/2-Math.atan2(india.z,india.x);
const rot = new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(.32, yaw, 0));
const output = points.map(({tx,point}) => {
  const p = geo.latLonToVec3(point.lat,point.lon,1.6*1.012,new THREE.Vector3()).applyMatrix4(rot);
  const visible=p.z>.5; p.project(camera);
  return {txid:tx.txid, x:(p.x+1)/2, y:(1-p.y)/2, visible};
}).filter(p=>p.visible);
process.stdout.write(JSON.stringify(output));
