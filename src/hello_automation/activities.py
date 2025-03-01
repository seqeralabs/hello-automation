import asyncio
import boto3
import httpx
from temporalio import activity
from pathlib import Path
from config import settings

class MonitoringActivities:
    @activity.defn
    async def check_unprocessed_files(self) -> list[str] | None:
        """For each *.done file check if all files with settings.data_suffix exist"""
        try:
            folder = Path(settings.sequencer_monitor_path)
            run_list = []
            for file in folder.glob("*.sequenced"):
                run_id = file.stem
                for suffix in settings.data_suffix:
                    if (folder / f"{run_id}{suffix}").exists():
                        continue
                    else:
                        break
                # Create a ".processed" marker file
                processed_marker = Path(settings.sequencer_monitor_path) / f"{run_id}.processed"
                processed_marker.touch()
                run_list.append(run_id)

            return run_list
        except Exception:
            activity.logger.exception("File monitoring failed")
            raise

class FileProcessingActivities:
    def __init__(self):
        self.s3_client = boto3.client('s3')

    @activity.defn
    async def fetch_metadata(self, run_id: str) -> str:
        """Downloads the corresponding CSV file from URL"""
        try:
            csv_url = f"{settings.metadata_download_url}/{run_id}.csv"
            local_path = f"{settings.sequencer_monitor_path}/{run_id}.csv"

            # Check if the file has already been downloaded
            if Path(local_path).exists():
                return run_id

            # Download the CSV file
            async with httpx.AsyncClient() as client:
                async with client.stream('GET', csv_url) as response:
                    response.raise_for_status()

                    with open(local_path, 'wb') as f:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)

            return run_id
        except Exception:
            activity.logger.exception("CSV download failed")
            raise

    @activity.defn
    async def upload_data_to_s3(self, run_id: str) -> str:
        """Uploads files to S3 and creates marker files"""
        try:
            # Check if the file has already been uploaded
            try:
                self.s3_client.head_object(Bucket=settings.destination_bucket, Key=f"{settings.destination_prefix}/{run_id}.csv")
                return f"s3://{settings.destination_bucket}/{settings.destination_prefix}/{run_id}.csv"
            except self.s3_client.exceptions.ClientError as e:
                if e.response['Error']['Code'] == '404':
                    # File does not exist, continue with upload
                    pass
                else:
                    # Some other error occurred
                    raise

            # Upload the data files to S3
            for suffix in settings.data_suffix + [".csv"]:
                self.s3_client.upload_file(
                    f"{settings.sequencer_monitor_path}/{run_id}{suffix}",
                    settings.destination_bucket,
                    f"{settings.destination_prefix}/{run_id}{suffix}"
                )

            # Create .uploaded marker in S3
            await asyncio.to_thread(
                self.s3_client.put_object,
                Bucket=settings.destination_bucket,
                Key=f"{settings.destination_prefix}/{run_id}.uploaded",
                Body=b''
            )

            # Return the destination path for the csv samplesheet
            return f"s3://{settings.destination_bucket}/{settings.destination_prefix}/{run_id}.csv"
        except Exception:
            activity.logger.exception("S3 upload failed")
            raise

class SeqeraActivities:
    def __init__(self):
        # Create an httpx client configured with httpx-auth authentication
        self.client = httpx.AsyncClient(
            base_url=str(settings.seqera_api_endpoint),
            headers={"Authorization": f"Bearer {settings.seqera_token.get_secret_value()}"},
            timeout=30.0
        )

    @activity.defn
    async def trigger_workflow(self, samplesheet_path: str) -> str:
        """Triggers the workflow for a given run ID"""
        # curl -H "Content-Type: application/json" \
        #      -H "Authorization: Bearer <YOUR TOKEN>" \
        #      https://api.cloud.seqera.io/actions/uGahsbPWNOTipp3B6uay8/launch?workspaceId=122097989272938 \
        #      --data '{"params":{"foo":"Hello world"}}'
        response = await self.client.post(
            f"/actions/{settings.seqera_action_id}/launch?workspaceId={settings.seqera_workspace_id}",
            json={"params": {"input": samplesheet_path}}
        )
        response.raise_for_status()
        return response.json()["workflowId"]

    @activity.defn
    async def monitor_workflow_progress(self, workflow_id: str) -> str:
        """Monitors workflow progress by pinging the progress endpoint every 30 seconds until completion"""
        while True:
            try:
                response = await self.client.get(
                    f"/workflow/{workflow_id}/progress?workspaceId={settings.seqera_workspace_id}"
                )
                response.raise_for_status()

                progress_data = response.json()
                activity.logger.info(f"Workflow progress: {progress_data}")

                # Check if workflow is complete
                if progress_data.get("status") in ["COMPLETED", "FAILED", "ERROR"]:
                    return progress_data["status"]

                # Wait for 30 seconds before next check
                await asyncio.sleep(30)
            except Exception as e:
                activity.logger.error(f"Error monitoring workflow progress: {str(e)}")
                raise

    @activity.defn
    async def process_workflow_completion(self, workflow_id: str, status: str) -> None:
        """Create a studio after workflow completion"""
        try:
            if status != "COMPLETED":
                activity.logger.warning(f"Workflow {workflow_id} completed with status {status}, skipping studio creation")
                return

            # Create a studio
            response = await self.client.post(
                "/studios",
                json={
                    "name": f"Analysis Studio - {workflow_id}",
                    "description": f"Analysis studio for workflow {workflow_id}",
                    "dataStudioToolUrl": settings.data_studio_tool_url,
                    "computeEnvId": settings.compute_env_id,
                    "initialCheckpointId": 0,
                    "configuration": {
                        "gpu": 0,
                        "cpu": settings.studio_cpu,
                        "memory": settings.studio_memory,
                        "mountData": [workflow_id],
                        "condaEnvironment": settings.studio_conda_env
                    }
                }
            )
            response.raise_for_status()
            activity.logger.info(f"Studio created for workflow {workflow_id}: {response.json()}")
        except Exception as e:
            activity.logger.error(f"Error creating studio for workflow {workflow_id}: {str(e)}")
            raise
