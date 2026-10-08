// Minimal browser viewer for the AV Sim's telemetry stream.
//
// Deliberately not chasing "Unreal-engine" visual fidelity -- this is a lightweight
// presentation-tier client over three.js, fed by telemetry_server.py's WebSocket stream. See
// README.md for why (openpilot's own simulator only bridges to MetaDrive, not Unreal).
//
// Position arrives as lat/lon from openpilot's liveLocationKalman. We convert it to local
// meters with a flat-earth (equirectangular) approximation anchored at the first fix -- fine
// at the scale of one generated MetaDrive map, not meant for real-world distances.

import * as THREE from "three";

const WS_URL = "ws://localhost:8765";
const EARTH_RADIUS_M = 6378137;

const hud = document.getElementById("hud");

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x202030);

const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 2000);
camera.position.set(0, 40, 40);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

scene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 1.2));
const sun = new THREE.DirectionalLight(0xffffff, 0.8);
sun.position.set(50, 100, 50);
scene.add(sun);

const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(2000, 2000),
  new THREE.MeshStandardMaterial({ color: 0x2a2a2a })
);
ground.rotation.x = -Math.PI / 2;
scene.add(ground);

const grid = new THREE.GridHelper(2000, 200, 0x444444, 0x333333);
scene.add(grid);

const car = new THREE.Mesh(
  new THREE.BoxGeometry(1.9, 1.4, 4.5),
  new THREE.MeshStandardMaterial({ color: 0x4da3ff })
);
car.position.y = 0.7;
scene.add(car);

const trail = [];
const trailGeom = new THREE.BufferGeometry();
const trailMat = new THREE.LineBasicMaterial({ color: 0xffcc00 });
const trailLine = new THREE.Line(trailGeom, trailMat);
scene.add(trailLine);

let origin = null; // {lat, lon} of the first fix

function latLonToLocalMeters(lat, lon) {
  if (origin === null) origin = { lat, lon };
  const dLat = (lat - origin.lat) * (Math.PI / 180);
  const dLon = (lon - origin.lon) * (Math.PI / 180);
  const x = dLon * EARTH_RADIUS_M * Math.cos(origin.lat * Math.PI / 180);
  const z = -dLat * EARTH_RADIUS_M; // north is -z in this view
  return { x, z };
}

function updateTrail(x, z) {
  trail.push(new THREE.Vector3(x, 0.05, z));
  if (trail.length > 2000) trail.shift();
  trailGeom.setFromPoints(trail);
}

function connect() {
  const ws = new WebSocket(WS_URL);

  ws.onopen = () => { hud.textContent = "connected, waiting for telemetry..."; };
  ws.onclose = () => { hud.textContent = "disconnected, retrying..."; setTimeout(connect, 1000); };
  ws.onerror = () => ws.close();

  ws.onmessage = (ev) => {
    const state = JSON.parse(ev.data);
    if (state.lat === undefined || state.lon === undefined) {
      hud.textContent = "connected, no position fix yet";
      return;
    }

    const { x, z } = latLonToLocalMeters(state.lat, state.lon);
    car.position.x = x;
    car.position.z = z;
    if (state.yaw !== undefined) car.rotation.y = -state.yaw;
    updateTrail(x, z);

    camera.position.set(x, 40, z + 40);
    camera.lookAt(x, 0, z);

    const speed = state.speed !== undefined ? state.speed.toFixed(1) : "?";
    const engaged = state.engaged ? "ENGAGED" : "manual";
    hud.textContent = `status: ${engaged}\nspeed: ${speed} m/s\nx: ${x.toFixed(1)}  z: ${z.toFixed(1)}`;
  };
}

connect();

function animate() {
  requestAnimationFrame(animate);
  renderer.render(scene, camera);
}
animate();
