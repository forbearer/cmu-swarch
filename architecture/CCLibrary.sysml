package CCLibrary {
	doc /*
	 * Shared connector vocabulary for the CMU SWArch AV Sim project's component-and-connector
	 * models, following David Garlan's C&C architectural style: a connector is a first-class,
	 * explicitly typed element -- not just an arrow -- carrying the interaction protocol it
	 * represents (procedure call, publish-subscribe, event stream, shared repository,
	 * request-reply). Each of the three system models (av-sim, fleet-service, ml-pipeline)
	 * imports this package and instantiates these connector types between its own components.
	 */

	item def Payload {
		doc /*
		 * Stand-in for whatever data a connector actually carries -- JSON telemetry, a cereal
		 * message, a function call's arguments, bytes on disk. Each system's own model names the
		 * real payload where it matters for that view (e.g. av-sim.sysml's GpsFix).
		 */
	}

	port def SourcePort {
		doc /* Supplier side of any connector in this library. The conjugated ~SourcePort is the receiver. */
		out item data : Payload;
	}

	interface def ProcedureCallConnector {
		doc /*
		 * Garlan connector type: Procedure Call. Synchronous, in-process invocation -- the
		 * caller's own thread executes the callee's code directly.
		 */
		end caller : SourcePort;
		end callee : ~SourcePort;
		flow of Payload from caller.data to callee.data;
	}

	interface def PublishSubscribeConnector {
		doc /*
		 * Garlan connector type: Publish-Subscribe. Publisher and subscriber(s) are decoupled in
		 * time and identity. This project's instance is openpilot's own `cereal` messaging bus.
		 */
		end publisher : SourcePort;
		end subscriber : ~SourcePort;
		flow of Payload from publisher.data to subscriber.data;
	}

	interface def StreamConnector {
		doc /*
		 * Garlan connector type: Event/Stream (push). Ordered, asynchronous, producer-initiated.
		 * This project's instance is a plain WebSocket: the producer pushes to any connected
		 * consumer without waiting to be asked.
		 */
		end producer : SourcePort;
		end consumer : ~SourcePort;
		flow of Payload from producer.data to consumer.data;
	}

	interface def RepositoryConnector {
		doc /*
		 * Garlan connector type: Repository (shared persistent data). Writer and reader never
		 * interact directly, only through the store's current state. This project's instances
		 * are plain files on disk (recorded frames/labels, trained-model checkpoints).
		 */
		end writer : SourcePort;
		end reader : ~SourcePort;
		flow of Payload from writer.data to reader.data;
	}

	interface def RequestReplyConnector {
		doc /*
		 * Garlan connector type: Request-Reply, over a network boundary. This project's instance
		 * is plain HTTP/REST: the client polls, the server responds synchronously.
		 */
		end client : SourcePort;
		end server : ~SourcePort;
		flow of Payload from client.data to server.data;
	}
}
