from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities import FileProcessingActivities, SeqeraActivities, MonitoringActivities


@workflow.defn
class MonitorSequencerDirectory:
    @workflow.run
    async def run(self, monitor_path: str) -> None:
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            maximum_interval=timedelta(hours=1),
        )

        # Continuously check for unprocessed files
        while True:
            run_list: list[str] | None = await workflow.execute_activity_method(
                MonitoringActivities.check_unprocessed_files,
                start_to_close_timeout=timedelta(seconds=5),
                retry_policy=retry_policy,
            )

            if run_list:
                # For each run found, start a new GenomeSequenceWorkflow
                for run_id in run_list:
                    await workflow.start_child_workflow(
                        GenomeSequenceWorkflow.run,
                        run_id,
                        id=f"genome-sequence-{run_id}",
                    )
            
            workflow.logger.info("Checking again in 10 seconds")
            await workflow.sleep(10)  # Sleep for 10 seconds before checking again


@workflow.defn
class GenomeSequenceWorkflow:
    @workflow.run
    async def run(self, run_id: str) -> str:
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            maximum_interval=timedelta(hours=1),
        )

        # Download the metadata CSV files
        _ = await workflow.execute_activity_method(
            FileProcessingActivities.download_csv,
            run_id,
            start_to_close_timeout=timedelta(seconds=5),
            retry_policy=retry_policy,
        )

        # Upload the files to S3
        samplesheet_path: str = await workflow.execute_activity_method(
            FileProcessingActivities.upload_to_s3,
            run_id,
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=retry_policy,
        )

        # Trigger the nextflow workflow using the Seqera Platform API
        seqera_run_id: str = await workflow.execute_activity_method(
            SeqeraActivities.trigger_workflow,
            samplesheet_path,
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=retry_policy,
        )

        # Monitor the workflow progress until completion
        try:
            status = await workflow.execute_activity_method(
                SeqeraActivities.monitor_workflow_progress,
                seqera_run_id,
                start_to_close_timeout=timedelta(hours=1),
                retry_policy=retry_policy,
            )
            
            # Process the workflow completion
            await workflow.execute_activity_method(
                SeqeraActivities.process_workflow_completion,
                seqera_run_id,
                status,
                start_to_close_timeout=timedelta(seconds=120),
                retry_policy=retry_policy,
            )
        except Exception as e:
            workflow.logger.error(f"Error handling workflow {seqera_run_id}: {str(e)}")
            # Continue processing even if this workflow fails

        return f"Workflow completed for run {run_id}"