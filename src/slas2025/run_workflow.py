import asyncio
import traceback

from temporalio.client import Client, WorkflowFailureError

from shared import SEQUENCER_TASK_QUEUE_NAME
from workflows import GenomeSequenceWorkflow

from config import settings


async def main() -> None:
    # Create client connected to server at the given address
    client: Client = await Client.connect(str(settings.temporal_server_url), namespace=settings.temporal_namespace)

    try:
        result = await client.execute_workflow(
            GenomeSequenceWorkflow.run,
            str(settings.sequencer_monitor_path),
            id="genome-sequence-workflow",
            task_queue=SEQUENCER_TASK_QUEUE_NAME,
        )

        print(f"Result: {result}")

    except WorkflowFailureError:
        print("Got expected exception: ", traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())
