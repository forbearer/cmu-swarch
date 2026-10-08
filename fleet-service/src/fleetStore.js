// In-memory table of AVs, their whereabouts, and latest travel status.
//
// Deliberately in-memory, not a database: this is the fleet management teaching artifact, and
// the point is the N-tier client/server shape (AV Sims -> this aggregator -> dashboard/API
// clients), not persistence. Swapping in real storage later is a reasonable course exercise,
// not something to pre-build here.

const STALE_MS = 3000; // no telemetry in this long -> flag as stale even if still "connected"

export class FleetStore {
  constructor(vehicles) {
    this.vehicles = new Map();
    for (const v of vehicles) {
      this.vehicles.set(v.id, {
        id: v.id,
        name: v.name || v.id,
        wsUrl: v.wsUrl,
        connected: false,
        lastSeen: null,
        lat: null,
        lon: null,
        alt: null,
        yaw: null,
        speed: null,
        engaged: false,
      });
    }
  }

  setConnectionState(id, connected) {
    const v = this.vehicles.get(id);
    if (!v) return;
    v.connected = connected;
  }

  upsertTelemetry(id, telemetry) {
    const v = this.vehicles.get(id);
    if (!v) return;

    v.connected = true;
    v.lastSeen = Date.now();
    if (telemetry.lat !== undefined) v.lat = telemetry.lat;
    if (telemetry.lon !== undefined) v.lon = telemetry.lon;
    if (telemetry.alt !== undefined) v.alt = telemetry.alt;
    if (telemetry.yaw !== undefined) v.yaw = telemetry.yaw;
    if (telemetry.speed !== undefined) v.speed = telemetry.speed;
    if (telemetry.engaged !== undefined) v.engaged = telemetry.engaged;
  }

  status(v) {
    if (!v.connected) return 'offline';
    if (v.lastSeen === null || Date.now() - v.lastSeen > STALE_MS) return 'stale';
    return v.engaged ? 'driving' : 'idle';
  }

  toJSON(v) {
    return {
      id: v.id,
      name: v.name,
      status: this.status(v),
      lat: v.lat,
      lon: v.lon,
      alt: v.alt,
      yaw: v.yaw,
      speed: v.speed,
      lastSeen: v.lastSeen,
    };
  }

  list() {
    return [...this.vehicles.values()].map((v) => this.toJSON(v));
  }

  get(id) {
    const v = this.vehicles.get(id);
    return v ? this.toJSON(v) : null;
  }
}
