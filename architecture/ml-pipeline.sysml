package MLPipelineArchitecture {
	doc /*
	 * Component-and-connector view of the Perception ML Training Pipeline
	 * (../ml-pipeline/). A pipe-and-filter chain over a shared repository (recorded
	 * frames/labels, then a checkpoint, both plain files on disk) -- the blackboard-adjacent
	 * style called out from the start in the root README, deliberately distinct from AV Sim's
	 * robotic-control/pub-sub style and the fleet service's N-tier client/server style.
	 * Reflects what was built and verified 2026-10-08 (standalone pieces run end-to-end against
	 * a synthetic dataset; see ../ml-pipeline/README.md for exactly what is and isn't verified).
	 */

	private import CCLibrary::*;

	/* =====================================================================
	 * Components
	 * ===================================================================== */

	part def RecordingWorld {
		doc /*
		 * ml-pipeline/bridge/recording_world.py, hooking MetaDriveWorld.apply_controls -- the
		 * same AV Sim components as av-sim.sysml's SimBridge/MetaDriveSimulator, reused rather
		 * than duplicated. Every applied control gets written out alongside the camera frame it
		 * was applied to.
		 */
		port datasetOut : SourcePort;
	}

	part def Dataset {
		doc /* frames/*.png + labels.csv on disk -- one recorded session. The shared repository this pipeline is built around. */
		port writeIn : ~SourcePort;
		port readOut : SourcePort;
	}

	part def Trainer {
		doc /*
		 * ml-pipeline/train.py + dataset.py + model.py. Standalone -- no openpilot or MetaDrive
		 * imports, runs anywhere torch is installed. The main student-tunable surface: lr,
		 * epochs, batch size, model capacity, dataset size are all CLI flags.
		 */
		port datasetIn : ~SourcePort;
		port checkpointOut : SourcePort;
	}

	part def Checkpoint {
		doc /* checkpoint.pt -- a trained model's weights. The second shared-repository artifact in the chain. */
		port writeIn : ~SourcePort;
		port readOut : SourcePort;
	}

	part def TrainedPolicyRunner {
		doc /*
		 * ml-pipeline/bridge/run_trained_policy.py. Loads a checkpoint and drives MetaDrive
		 * directly via WaypointMetaDriveBridge.spawn_world(), bypassing openpilot's own control
		 * stack entirely -- the course artifact worth drawing out here: a trained model as a
		 * complete, decoupled replacement for the "robotic control" component in av-sim.sysml.
		 */
		port checkpointIn : ~SourcePort;
		port controlOut : SourcePort;
	}

	part def MetaDriveSimulator {
		doc /* The same MetaDrive engine as av-sim.sysml -- reused, not reimplemented. */
		port controlIn : ~SourcePort;
	}

	/* =====================================================================
	 * The system: composition and connectors
	 * ===================================================================== */

	part def MLPipelineSystem {
		doc /* Record -> train -> replace the driving policy, with two file-backed handoffs in between. */

		part recorder : RecordingWorld;
		part dataset : Dataset;
		part trainer : Trainer;
		part checkpoint : Checkpoint;
		part runner : TrainedPolicyRunner;
		part sim : MetaDriveSimulator;

		interface record : RepositoryConnector connect recorder.datasetOut to dataset.writeIn;
		interface trainInput : RepositoryConnector connect dataset.readOut to trainer.datasetIn;
		interface save : RepositoryConnector connect trainer.checkpointOut to checkpoint.writeIn;
		interface load : RepositoryConnector connect checkpoint.readOut to runner.checkpointIn;

		// the one connector that is NOT file-backed: the trained policy drives the live simulator
		interface drive : ProcedureCallConnector connect runner.controlOut to sim.controlIn;
	}
}
