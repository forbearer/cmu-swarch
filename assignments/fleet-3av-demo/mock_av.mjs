#!/usr/bin/env node
// Emits the exact telemetry contract av-sim/bridge/telemetry_server.py produces
// (t, lat, lon, alt, yaw, speed, engaged), over a WebSocket server, so fleet-service can't tell
// the difference between this and a real AV Sim instance -- it's a stand-in for the simulator,
// not for the fleet service itself.
//
// Deliberately NOT three real openpilot+MetaDrive stacks: each one needs its own 4-terminal
// setup (openpilot, bridge, telemetry relay, venv) and real CPU/GPU budget. For illustrating the
// *fleet management service's* architecture specifically -- aggregation, derived status,
// N-tier client/server -- three lightweight stand-ins emitting the real contract shape make the
// point without the cost. Swap any one of these for `python3 av-sim/bridge/telemetry_server.py`
// (pointed at a real running AV Sim) and fleet-service won't know the difference.
//
// Usage: node mock_av.mjs --port 8765 --lat 40.4433 --lon -79.9436 --pattern loop
import { WebSocketServer } from 'ws';

function parseArgs(argv) {
  const args = { port: 8765, lat: 40.4433, lon: -79.9436, speed: 8.0, pattern: 'loop' };
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i].replace(/^--/, '');
    args[key] = argv[i + 1];
  }
  args.port = Number(args.port);
  args.lat = Number(args.lat);
  args.lon = Number(args.lon);
  args.speed = Number(args.speed);
  return args;
}

const args = parseArgs(process.argv.slice(2));
const METERS_PER_DEG_LAT = 111_320;

// Three patterns, picked to exercise every fleet-service status (see fleetStore.js):
// - loop: drives a small circular route forever -> stays "driving"
// - idle: engaged=false, sits still -> "idle"
// - disconnect: drives briefly, then closes the connection -> demonstrates "offline"
function nextTelemetry(t, origin) {
  switch (args.pattern) {
    case 'idle':
      return { lat: origin.lat, lon: origin.lon, alt: 280, yaw: 0, speed: 0, engaged: false };
    case 'disconnect':
    case 'loop':
    default: {
      const angularSpeed = args.speed / 50; // radians/sec around a ~50m-radius loop
      const theta = t * angularSpeed;
      const radiusDeg = 50 / METERS_PER_DEG_LAT;
      const lat = origin.lat + radiusDeg * Math.sin(theta);
      const lon = origin.lon + radiusDeg * Math.cos(theta) / Math.cos(origin.lat * Math.PI / 180);
      const yaw = theta + Math.PI / 2;
      return { lat, lon, alt: 280, yaw, speed: args.speed, engaged: true };
    }
  }
}

const wss = new WebSocketServer({ port: args.port });
console.log(`mock AV [pattern=${args.pattern}] listening on ws://localhost:${args.port}`);

wss.on('connection', (ws) => {
  const origin = { lat: args.lat, lon: args.lon };
  const start = Date.now() / 1000;
  let disconnectTimer = null;

  if (args.pattern === 'disconnect') {
    // Exit the whole process, not just this one connection -- fleet-service's avConnector
    // auto-reconnects within 2s (correct, resilient behavior for a real flaky link), so just
    // closing the socket while this server keeps listening makes "offline" flash by almost
    // invisibly. A crashed/stopped AV Sim is a closer real-world match anyway: the process is
    // actually gone, so reconnect attempts genuinely fail and "offline" sticks.
    disconnectTimer = setTimeout(() => {
      console.log(`[port ${args.port}] simulating a crashed AV Sim -- exiting`);
      process.exit(0);
    }, 15_000); // drive for 15s, long enough to see "driving" before it flips
  }

  const interval = setInterval(() => {
    const t = Date.now() / 1000 - start;
    const telemetry = { t: Date.now() / 1000, ...nextTelemetry(t, origin) };
    ws.send(JSON.stringify(telemetry));
  }, 50); // 20Hz, matching telemetry_server.py's real rate

  ws.on('close', () => {
    clearInterval(interval);
    if (disconnectTimer) clearTimeout(disconnectTimer);
  });
});
