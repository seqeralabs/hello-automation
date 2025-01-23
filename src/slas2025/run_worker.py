# @@@SNIPSTART python-money-transfer-project-template-run-worker
import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from activities import FileProcessingActivities, SeqeraActivities
from shared import SEQUENCER_TASK_QUEUE_NAME
from workflows import GenomeSequenceWorkflow

from config import settings


async def main() -> None:
    client: Client = await Client.connect(str(settings.temporal_server_url), namespace=settings.temporal_namespace)
    # Run the worker
    activities = FileProcessingActivities()
    seqera_activities = SeqeraActivities()
    worker: Worker = Worker(
        client,
        task_queue=SEQUENCER_TASK_QUEUE_NAME,
        workflows=[GenomeSequenceWorkflow],
        activities=[
            activities.check_unprocessed_files,
            activities.download_csv,
            activities.upload_to_s3,
            seqera_activities.trigger_workflow
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
