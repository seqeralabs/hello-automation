# @@@SNIPSTART python-money-transfer-project-template-workflows
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities import FileProcessingActivities, SeqeraActivities


@workflow.defn
class GenomeSequenceWorkflow:
    @workflow.run
    async def run(self, monitor_path: str) -> str:
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            maximum_interval=timedelta(hours=1),
        )

        # Continuously check for unprocessed files every 10 seconds
        while True:
            run_list: list[str] | None = await workflow.execute_activity_method(
                FileProcessingActivities.check_unprocessed_files,
                start_to_close_timeout=timedelta(seconds=5),
                retry_policy=retry_policy,
            )

            if run_list:
                break  # Exit the loop when files are found
            
            workflow.logger.info("No unprocessed files found, checking again in 10 seconds")
            await workflow.sleep(10)  # Sleep for 10 seconds before checking again

        # Download the metadata CSV files
        for run_id in run_list:
            _ = await workflow.execute_activity_method(
                FileProcessingActivities.download_csv,
                run_id,
                start_to_close_timeout=timedelta(seconds=5),
                retry_policy=retry_policy,
            )

            # Upload the files to S3
            samplesheet_path: str | None = await workflow.execute_activity_method(
                FileProcessingActivities.upload_to_s3,
                run_id,
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=retry_policy,
            )

            # Trigger the nextflow workflow using the Seqera Platform API
            seqera_run_id = await workflow.execute_activity_method(
                SeqeraActivities.trigger_workflow,
                samplesheet_path,
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=retry_policy,
            )

        return "Workflow completed"