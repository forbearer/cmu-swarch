// Connects to each configured AV Sim's telemetry WebSocket (see
// av-sim/bridge/telemetry_server.py) as a client, and feeds every message into the FleetStore.
//
// Reuses the AV Sim's existing browser-telemetry contract as-is (same JSON shape the three.js
// viewer consumes) instead of inventing a second protocol -- the fleet service is just another
// consumer of that stream, same as the browser viewer is.

import WebSocket from 'ws';

const RECONNECT_DELAY_MS = 2000;

export function connectFleet(vehicles, store, { onLog = console.log } = {}) {
  for (const vehicle of vehicles) {
    connectOne(vehicle, store, onLog);
  }
}

function connectOne(vehicle, store, onLog) {
  const ws = new WebSocket(vehicle.wsUrl);

  ws.on('open', () => {
    onLog(`[${vehicle.id}] connected to ${vehicle.wsUrl}`);
    store.setConnectionState(vehicle.id, true);
  });

  ws.on('message', (data) => {
    try {
      const telemetry = JSON.parse(data.toString());
      store.upsertTelemetry(vehicle.id, telemetry);
    } catch (err) {
      onLog(`[${vehicle.id}] bad telemetry payload: ${err.message}`);
    }
  });

  const scheduleReconnect = () => {
    store.setConnectionState(vehicle.id, false);
    setTimeout(() => connectOne(vehicle, store, onLog), RECONNECT_DELAY_MS);
  };

  ws.on('close', () => {
    onLog(`[${vehicle.id}] disconnected from ${vehicle.wsUrl}, retrying in ${RECONNECT_DELAY_MS}ms`);
    scheduleReconnect();
  });

  ws.on('error', (err) => {
    onLog(`[${vehicle.id}] connection error: ${err.message}`);
    ws.close();
  });
}
