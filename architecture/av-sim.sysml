package AVSimArchitecture {
	doc /*
	 * Component-and-connector view of the AV Sim subsystem (../av-sim/), including openpilot
	 * itself as a first-class component rather than an opaque black box -- the whole point of
	 * this course project is to make its internal seams visible. Reflects what was actually
	 * built and verified end-to-end 2026-10-09 (see ../av-sim/README.md), not an idealized design.
	 */

	private import CCLibrary::*;

	/* =====================================================================
	 * Components
	 * ===================================================================== */

	part def MetaDriveSimulator {
		doc /*
		 * The MetaDrive physics/rendering engine itself, running in its own OS process
		 * (spawned by WaypointMetaDriveBridge.spawn_world -- av-sim/bridge/waypoint_bridge.py).
		 * Owns the road network, vehicle dynamics, and the rendered camera frame.
		 */
		port controlIn : ~SourcePort;   // steer/throttle/brake applied each tick
		port stateOut : SourcePort;     // position/velocity/bearing/camera frame, via shared memory
	}

	part def SimBridge {
		doc /*
		 * av-sim/bridge/waypoint_bridge.py and the openpilot SimulatorBridge loop it extends.
		 * The seam between the simulator and the real driving stack: translates MetaDrive's
		 * state into simulated CAN/IMU/GPS messages for openpilot, and openpilot's control
		 * output back into MetaDrive's control API.
		 */
		port toSim : SourcePort;        // controls, in-process call into MetaDrive
		port fromSim : ~SourcePort;     // vehicle state, in-process, from MetaDrive
		port canOut : SourcePort;       // simulated CAN/pandaStates/gpsLocationExternal, published
		port controlIn : ~SourcePort;   // carControl, subscribed from openpilot
	}

	part def OpenpilotStack {
		doc /*
		 * The real, unmodified openpilot driving stack -- controlsd, plannerd, locationd, and
		 * the rest of the daemons launch_openpilot.sh's manager spawns, communicating entirely
		 * over the `cereal` publish-subscribe bus. Not a stub: this is comma.ai's actual code,
		 * genuinely engaging and driving the simulated vehicle (verified 2026-10-09).
		 */
		port canIn : ~SourcePort;
		port controlOut : SourcePort;
		port telemetryOut : SourcePort;   // gpsLocationExternal, selfdriveState
	}

	part def TelemetryServer {
		doc /*
		 * av-sim/bridge/telemetry_server.py. An independent cereal subscriber -- the same
		 * non-invasive pattern openpilot's own UI and cabana use -- republishing state as JSON
		 * over a WebSocket. Deliberately decoupled: it doesn't know SimBridge or MetaDrive exist.
		 */
		port cerealIn : ~SourcePort;
		port wsOut : SourcePort;
	}

	part def BrowserViewer {
		doc /*
		 * av-sim/viewer/ -- a build-free three.js page. N-tier client of TelemetryServer; the
		 * presentation tier this whole seam exists to feed.
		 */
		port wsIn : ~SourcePort;
	}

	/* =====================================================================
	 * The system: composition and connectors
	 * ===================================================================== */

	part def AVSimSystem {
		doc /* The whole AV Sim subsystem as deployed: five components, four connector types. */

		part sim : MetaDriveSimulator;
		part bridge : SimBridge;
		part openpilot : OpenpilotStack;
		part telemetry : TelemetryServer;
		part viewer : BrowserViewer;

		// SimBridge <-> MetaDrive: same-process, direct calls (not a network or IPC boundary)
		interface simControl : ProcedureCallConnector connect bridge.toSim to sim.controlIn;
		interface simFeedback : ProcedureCallConnector connect sim.stateOut to bridge.fromSim;

		// SimBridge <-> openpilot: openpilot's own cereal bus, exactly as it runs on real hardware
		interface canBus : PublishSubscribeConnector connect bridge.canOut to openpilot.canIn;
		interface controlBus : PublishSubscribeConnector connect openpilot.controlOut to bridge.controlIn;

		// openpilot -> TelemetryServer: a second, independent cereal subscriber
		interface telemetryBus : PublishSubscribeConnector connect openpilot.telemetryOut to telemetry.cerealIn;

		// TelemetryServer -> browser: the actual presentation-tier seam
		interface liveFeed : StreamConnector connect telemetry.wsOut to viewer.wsIn;
	}
}
