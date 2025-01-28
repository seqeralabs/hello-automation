# @@@SNIPSTART python-money-transfer-project-template-run-worker
import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from activities import MonitoringActivities, FileProcessingActivities, SeqeraActivities
from shared import SEQUENCER_TASK_QUEUE_NAME
from workflows import MonitorSequencerDirectory,GenomeSequenceWorkflow

from config import settings


async def main() -> None:
    client: Client = await Client.connect(str(settings.temporal_server_url), namespace=settings.temporal_namespace)
    # Run the worker
    monitoring_activities = MonitoringActivities()
    file_processing_activities = FileProcessingActivities()
    seqera_activities = SeqeraActivities()
    worker: Worker = Worker(
        client,
        task_queue=SEQUENCER_TASK_QUEUE_NAME,
        workflows=[MonitorSequencerDirectory,GenomeSequenceWorkflow],
        activities=[
            monitoring_activities.check_unprocessed_files,
            file_processing_activities.download_csv,
            file_processing_activities.upload_to_s3,
            seqera_activities.trigger_workflow,
            seqera_activities.monitor_workflow_progress,
            seqera_activities.process_workflow_completion,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    print("Starting worker")
    asyncio.run(main())
