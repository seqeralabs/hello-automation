import asyncio
import traceback

from temporalio.client import Client, WorkflowFailureError

from shared import SEQUENCER_TASK_QUEUE_NAME
from workflows import MonitorSequencerDirectory, GenomeSequenceWorkflow

from config import settings


async def main() -> None:
    # Create client connected to server at the given address
    client: Client = await Client.connect(str(settings.temporal_server_url), namespace=settings.temporal_namespace)

    try:
        await client.execute_workflow(
            MonitorSequencerDirectory.run,
            str(settings.sequencer_monitor_path),
            id="monitor-sequencer-directory",
            task_queue=SEQUENCER_TASK_QUEUE_NAME,
        )

    except WorkflowFailureError:
        print("Got expected exception: ", traceback.format_exc())


if __name__ == "__main__":
    print("Starting workflow")
    asyncio.run(main())
