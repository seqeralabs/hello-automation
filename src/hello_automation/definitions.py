"""Dagster definitions for the hello-automation genome sequencing pipeline.

This module defines the complete Dagster project including:
- Assets for the genome sequencing pipeline
- Resources for Seqera Platform and S3 integration
- Sensors for monitoring the sequencer directory
- Jobs for running the pipeline
"""

import os

import dagster as dg

from hello_automation.assets import (
    fetch_metadata,
    upload_to_s3,
    seqera_workflow,
    data_studio,
    genome_sequence_job,
)
from hello_automation.resources import SeqeraResource, S3Resource
from hello_automation.sensors import sequencer_directory_sensor


# Configure resources using environment variables
seqera_resource = SeqeraResource(
    api_endpoint=os.getenv("TOWER_API_ENDPOINT", "https://api.cloud.seqera.io"),
    access_token=dg.EnvVar("TOWER_ACCESS_TOKEN"),
    workspace_id=dg.EnvVar("TOWER_WORKSPACE_ID"),
    action_id=dg.EnvVar("SEQERA_ACTION_ID"),
    data_studio_tool_url=os.getenv(
        "DATA_STUDIO_TOOL_URL", "https://studio.cloud.seqera.io"
    ),
    compute_env_id=dg.EnvVar("COMPUTE_ENV_ID"),
    studio_cpu=int(os.getenv("STUDIO_CPU", "2")),
    studio_memory=int(os.getenv("STUDIO_MEMORY", "8")),
    studio_conda_env=os.getenv("STUDIO_CONDA_ENV", "base"),
)

s3_resource = S3Resource(
    destination_bucket=dg.EnvVar("DESTINATION_BUCKET"),
    destination_prefix=os.getenv("DESTINATION_PREFIX", "event-driven-bioinformatics"),
)


# Create the Dagster Definitions
defs = dg.Definitions(
    assets=[fetch_metadata, upload_to_s3, seqera_workflow, data_studio],
    jobs=[genome_sequence_job],
    sensors=[sequencer_directory_sensor],
    resources={
        "seqera_resource": seqera_resource,
        "s3_resource": s3_resource,
    },
)
