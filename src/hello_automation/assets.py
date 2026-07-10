"""Dagster assets for the genome sequencing pipeline."""

from pathlib import Path

import httpx
import dagster as dg

from hello_automation.resources import SeqeraResource, S3Resource


class GenomeSequenceConfig(dg.Config):
    """Configuration for a genome sequencing run."""

    run_id: str
    sequencer_path: str = "./sequencer"
    metadata_download_url: str = (
        "https://raw.githubusercontent.com/nf-core/sarek/refs/tags/3.5.0/tests/csv/3.0"
    )
    data_suffixes: list[str] = ["_1.fastq.gz", "_2.fastq.gz"]


@dg.asset(
    description="Fetch metadata CSV for a sequencing run from the remote repository.",
    kinds={"python", "http"},
)
def fetch_metadata(
    context: dg.AssetExecutionContext,
    config: GenomeSequenceConfig,
) -> str:
    """Download the metadata CSV file for a sequencing run.

    Returns:
        The run_id after successful download.
    """
    run_id = config.run_id
    csv_url = f"{config.metadata_download_url}/{run_id}.csv"
    local_path = Path(config.sequencer_path) / f"{run_id}.csv"

    # Check if already downloaded
    if local_path.exists():
        context.log.info(f"Metadata CSV already exists at {local_path}")
        return run_id

    context.log.info(f"Downloading metadata from {csv_url}")

    with httpx.Client() as client:
        with client.stream("GET", csv_url) as response:
            response.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)

    context.log.info(f"Downloaded metadata CSV to {local_path}")
    return run_id


@dg.asset(
    deps=[fetch_metadata],
    description="Upload sequencing data and metadata to S3.",
    kinds={"python", "s3"},
)
def upload_to_s3(
    context: dg.AssetExecutionContext,
    config: GenomeSequenceConfig,
    s3_resource: S3Resource,
) -> str:
    """Upload data files and metadata CSV to S3.

    Returns:
        The S3 URI of the uploaded samplesheet CSV.
    """
    run_id = config.run_id
    sequencer_path = Path(config.sequencer_path)

    # Check if already uploaded
    csv_key = s3_resource.get_destination_key(f"{run_id}.csv")
    if s3_resource.file_exists(csv_key):
        context.log.info(f"Files already uploaded for run {run_id}")
        return s3_resource.get_destination_uri(f"{run_id}.csv")

    # Upload data files and CSV
    suffixes = config.data_suffixes + [".csv"]
    for suffix in suffixes:
        filename = f"{run_id}{suffix}"
        local_path = sequencer_path / filename
        key = s3_resource.get_destination_key(filename)

        context.log.info(f"Uploading {local_path} to s3://{s3_resource.destination_bucket}/{key}")
        s3_resource.upload_file(str(local_path), key)

    # Create uploaded marker
    marker_key = s3_resource.get_destination_key(f"{run_id}.uploaded")
    s3_resource.put_marker(marker_key)

    samplesheet_uri = s3_resource.get_destination_uri(f"{run_id}.csv")
    context.log.info(f"Upload complete. Samplesheet at {samplesheet_uri}")

    return samplesheet_uri


@dg.asset(
    deps=[upload_to_s3],
    description="Trigger and monitor a Nextflow workflow on Seqera Platform.",
    kinds={"python", "seqera"},
)
def seqera_workflow(
    context: dg.AssetExecutionContext,
    config: GenomeSequenceConfig,
    s3_resource: S3Resource,
    seqera_resource: SeqeraResource,
) -> dict:
    """Trigger and monitor a Seqera Platform workflow.

    Returns:
        A dict with workflow_id and final status.
    """
    run_id = config.run_id
    samplesheet_path = s3_resource.get_destination_uri(f"{run_id}.csv")

    # Trigger the workflow
    context.log.info(f"Triggering Seqera workflow with samplesheet: {samplesheet_path}")
    workflow_id = seqera_resource.trigger_workflow(samplesheet_path)
    context.log.info(f"Seqera workflow started with ID: {workflow_id}")

    # Monitor until completion
    context.log.info("Monitoring workflow progress...")
    status = seqera_resource.monitor_workflow_until_complete(workflow_id, poll_interval=30)
    context.log.info(f"Workflow {workflow_id} completed with status: {status}")

    return {"workflow_id": workflow_id, "status": status}


@dg.asset(
    deps=[seqera_workflow],
    description="Create a Data Studio for analyzing completed workflow results.",
    kinds={"python", "seqera"},
)
def data_studio(
    context: dg.AssetExecutionContext,
    config: GenomeSequenceConfig,
    seqera_resource: SeqeraResource,
    seqera_workflow: dict,
) -> dict | None:
    """Create a Data Studio for the completed workflow.

    Returns:
        The created studio data, or None if workflow failed.
    """
    workflow_id = seqera_workflow["workflow_id"]
    status = seqera_workflow["status"]

    if status != "COMPLETED":
        context.log.warning(
            f"Workflow {workflow_id} ended with status {status}, skipping studio creation"
        )
        return None

    context.log.info(f"Creating Data Studio for workflow {workflow_id}")
    studio = seqera_resource.create_studio(workflow_id)
    context.log.info(f"Data Studio created: {studio}")

    return studio


# Define the job that runs all assets for a genome sequence run
genome_sequence_job = dg.define_asset_job(
    name="genome_sequence_job",
    selection=[fetch_metadata, upload_to_s3, seqera_workflow, data_studio],
    description="Process a genome sequencing run through the full pipeline.",
)
