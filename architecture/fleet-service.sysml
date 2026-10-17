package FleetServiceArchitecture {
	doc /*
	 * Component-and-connector view of the Fleet Management Service (../fleet-service/).
	 * N-tier client/server style: a WebSocket client layer pulling in AV telemetry, an
	 * in-memory aggregator deriving fleet status, and two consumers of that aggregate state
	 * (a REST API and the dashboard it serves). Matches what was built and verified
	 * end-to-end 2026-10-08/2026-10-16 (see ../fleet-service/README.md and
	 * ../assignments/fleet-3av-demo/README.md).
	 */

	private import CCLibrary::*;

	/* =====================================================================
	 * Components
	 * ===================================================================== */

	part def AVTelemetrySource {
		doc /*
		 * Not part of this subsystem -- an AV Sim's telemetry_server.py (or, in
		 * assignments/fleet-3av-demo/, a mock emitting the identical contract). Modeled here as
		 * an external component so the fleet service's own boundary is explicit: fleet-service
		 * only ever sees this port, never the simulator behind it.
		 */
		port wsOut : SourcePort;
	}

	part def AVConnector {
		doc /*
		 * fleet-service/src/avConnector.js. One WebSocket client per configured vehicle, with
		 * automatic reconnect (2s backoff) on disconnect -- the behavior
		 * assignments/fleet-3av-demo/ specifically exercises and verified live.
		 */
		port wsIn : ~SourcePort;
		port updatesOut : SourcePort;   // in-process calls into FleetStore
	}

	part def FleetStore {
		doc /*
		 * fleet-service/src/fleetStore.js. In-memory table of vehicles; derives status
		 * (offline/stale/idle/driving) from connection state, staleness, and engagement rather
		 * than storing it directly.
		 */
		port updatesIn : ~SourcePort;
		port queryOut : SourcePort;     // in-process calls serving reads
	}

	part def ExpressAPI {
		doc /* fleet-service/src/server.js. GET /api/fleet, GET /api/fleet/:id. */
		port storeIn : ~SourcePort;
		port httpOut : SourcePort;
	}

	part def Dashboard {
		doc /* fleet-service/public/index.html. Polls the API once per second, no build step. */
		port httpIn : ~SourcePort;
	}

	/* =====================================================================
	 * The system: composition and connectors
	 * ===================================================================== */

	part def FleetServiceSystem {
		doc /*
		 * The fleet service plus the AV telemetry sources it depends on. Three or more
		 * AVTelemetrySource instances connect concurrently in the real deployment
		 * (assignments/fleet-3av-demo/ runs exactly three).
		 */

		part source1 : AVTelemetrySource;
		part connector : AVConnector;
		part store : FleetStore;
		part api : ExpressAPI;
		part dashboard : Dashboard;

		// fleet-service reaches OUT as a WebSocket client -- the AV Sim/mock never knows fleet-service exists
		interface telemetryFeed : StreamConnector connect source1.wsOut to connector.wsIn;

		// everything past the WebSocket boundary is in-process JavaScript, synchronous calls
		interface ingest : ProcedureCallConnector connect connector.updatesOut to store.updatesIn;
		interface query : ProcedureCallConnector connect store.queryOut to api.storeIn;

		// the dashboard is a genuine network client of the API, polling over plain HTTP
		interface dashboardFeed : RequestReplyConnector connect api.httpOut to dashboard.httpIn;
	}
}
