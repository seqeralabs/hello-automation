"""Dagster resources for Seqera Platform and S3 integration."""

import time
from typing import Any

import boto3
import httpx
import dagster as dg


class SeqeraResource(dg.ConfigurableResource):
    """Resource for interacting with the Seqera Platform API."""

    api_endpoint: str = "https://api.cloud.seqera.io"
    access_token: str
    workspace_id: str
    action_id: str
    data_studio_tool_url: str = "https://studio.cloud.seqera.io"
    compute_env_id: str
    studio_cpu: int = 2
    studio_memory: int = 8
    studio_conda_env: str = "base"

    def _get_client(self) -> httpx.Client:
        """Create an HTTP client configured for Seqera API."""
        return httpx.Client(
            base_url=self.api_endpoint,
            headers={"Authorization": f"Bearer {self.access_token}"},
            timeout=30.0,
        )

    def trigger_workflow(self, samplesheet_path: str) -> str:
        """Trigger a workflow using a Seqera Platform action.

        Args:
            samplesheet_path: S3 path to the samplesheet CSV.

        Returns:
            The workflow ID from Seqera Platform.
        """
        with self._get_client() as client:
            response = client.post(
                f"/actions/{self.action_id}/launch",
                params={"workspaceId": self.workspace_id},
                json={"params": {"input": samplesheet_path}},
            )
            response.raise_for_status()
            return response.json()["workflowId"]

    def get_workflow_progress(self, workflow_id: str) -> dict[str, Any]:
        """Get the progress of a workflow.

        Args:
            workflow_id: The Seqera workflow ID.

        Returns:
            The workflow progress data.
        """
        with self._get_client() as client:
            response = client.get(
                f"/workflow/{workflow_id}/progress",
                params={"workspaceId": self.workspace_id},
            )
            response.raise_for_status()
            return response.json()

    def monitor_workflow_until_complete(
        self, workflow_id: str, poll_interval: int = 30
    ) -> str:
        """Monitor a workflow until it reaches a terminal state.

        Args:
            workflow_id: The Seqera workflow ID.
            poll_interval: Seconds between polling attempts.

        Returns:
            The final workflow status (COMPLETED, FAILED, or ERROR).
        """
        terminal_states = {"COMPLETED", "FAILED", "ERROR", "CANCELLED"}

        while True:
            progress_data = self.get_workflow_progress(workflow_id)
            status = progress_data.get("progress", {}).get("workflowProgress", {}).get("status")

            if status in terminal_states:
                return status

            time.sleep(poll_interval)

    def create_studio(self, workflow_id: str, name: str | None = None) -> dict[str, Any]:
        """Create a Data Studio for analyzing workflow results.

        Args:
            workflow_id: The workflow ID to mount data from.
            name: Optional name for the studio.

        Returns:
            The created studio data.
        """
        studio_name = name or f"Analysis Studio - {workflow_id}"

        with self._get_client() as client:
            response = client.post(
                "/studios",
                params={"workspaceId": self.workspace_id},
                json={
                    "name": studio_name,
                    "description": f"Analysis studio for workflow {workflow_id}",
                    "dataStudioToolUrl": self.data_studio_tool_url,
                    "computeEnvId": self.compute_env_id,
                    "configuration": {
                        "gpu": 0,
                        "cpu": self.studio_cpu,
                        "memory": self.studio_memory,
                        "mountData": [workflow_id],
                        "condaEnvironment": self.studio_conda_env,
                    },
                },
            )
            response.raise_for_status()
            return response.json()


class S3Resource(dg.ConfigurableResource):
    """Resource for interacting with AWS S3."""

    destination_bucket: str
    destination_prefix: str

    def _get_client(self):
        """Get an S3 client."""
        return boto3.client("s3")

    def file_exists(self, key: str) -> bool:
        """Check if a file exists in S3.

        Args:
            key: The S3 object key.

        Returns:
            True if the file exists.
        """
        client = self._get_client()
        try:
            client.head_object(Bucket=self.destination_bucket, Key=key)
            return True
        except client.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def upload_file(self, local_path: str, key: str) -> str:
        """Upload a file to S3.

        Args:
            local_path: Local file path.
            key: S3 object key.

        Returns:
            The S3 URI of the uploaded file.
        """
        client = self._get_client()
        client.upload_file(local_path, self.destination_bucket, key)
        return f"s3://{self.destination_bucket}/{key}"

    def put_marker(self, key: str) -> None:
        """Create a marker file in S3.

        Args:
            key: The S3 object key for the marker.
        """
        client = self._get_client()
        client.put_object(Bucket=self.destination_bucket, Key=key, Body=b"")

    def get_destination_key(self, filename: str) -> str:
        """Get the full S3 key for a file.

        Args:
            filename: The filename.

        Returns:
            The full S3 key including prefix.
        """
        return f"{self.destination_prefix}/{filename}"

    def get_destination_uri(self, filename: str) -> str:
        """Get the full S3 URI for a file.

        Args:
            filename: The filename.

        Returns:
            The full S3 URI.
        """
        return f"s3://{self.destination_bucket}/{self.get_destination_key(filename)}"
