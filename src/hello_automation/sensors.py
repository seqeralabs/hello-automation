"""Dagster sensors for monitoring sequencer directory."""

import json
from pathlib import Path

import dagster as dg

from hello_automation.assets import genome_sequence_job


class SequencerSensorConfig(dg.Config):
    """Configuration for the sequencer monitoring sensor."""

    sequencer_path: str = "./sequencer"
    data_suffixes: list[str] = ["_1.fastq.gz", "_2.fastq.gz"]
    metadata_download_url: str = (
        "https://raw.githubusercontent.com/nf-core/sarek/refs/tags/3.5.0/tests/csv/3.0"
    )


@dg.sensor(
    job=genome_sequence_job,
    minimum_interval_seconds=10,
    description="Monitor the sequencer directory for new sequencing runs.",
)
def sequencer_directory_sensor(
    context: dg.SensorEvaluationContext,
) -> dg.SensorResult:
    """Sensor that monitors a directory for new sequencing runs.

    Looks for .sequenced marker files and triggers a job for each
    unprocessed run that has all required data files.
    """
    # Load configuration from environment or use defaults
    sequencer_path = Path(
        context.instance.run_storage.get_run_records(limit=0) or "./sequencer"
    )

    # Use default paths - in production these would come from config
    sequencer_path = Path("./sequencer")
    data_suffixes = ["_1.fastq.gz", "_2.fastq.gz"]
    metadata_download_url = (
        "https://raw.githubusercontent.com/nf-core/sarek/refs/tags/3.5.0/tests/csv/3.0"
    )

    # Load cursor to track processed runs
    processed_runs: set[str] = set()
    if context.cursor:
        try:
            processed_runs = set(json.loads(context.cursor))
        except json.JSONDecodeError:
            processed_runs = set()

    run_requests = []
    new_processed_runs = set(processed_runs)

    # Check for .sequenced marker files
    for sequenced_file in sequencer_path.glob("*.sequenced"):
        run_id = sequenced_file.stem

        # Skip if already processed
        if run_id in processed_runs:
            continue

        # Check if all data files exist
        all_files_present = all(
            (sequencer_path / f"{run_id}{suffix}").exists() for suffix in data_suffixes
        )

        if not all_files_present:
            context.log.debug(f"Run {run_id} missing some data files, skipping")
            continue

        # Check if already marked as processed locally
        processed_marker = sequencer_path / f"{run_id}.processed"
        if processed_marker.exists():
            new_processed_runs.add(run_id)
            continue

        context.log.info(f"Found new sequencing run: {run_id}")

        # Create .processed marker
        processed_marker.touch()

        # Create run request with config
        run_requests.append(
            dg.RunRequest(
                run_key=f"genome-sequence-{run_id}",
                run_config={
                    "ops": {
                        "fetch_metadata": {
                            "config": {
                                "run_id": run_id,
                                "sequencer_path": str(sequencer_path),
                                "metadata_download_url": metadata_download_url,
                                "data_suffixes": data_suffixes,
                            }
                        },
                        "upload_to_s3": {
                            "config": {
                                "run_id": run_id,
                                "sequencer_path": str(sequencer_path),
                                "metadata_download_url": metadata_download_url,
                                "data_suffixes": data_suffixes,
                            }
                        },
                        "seqera_workflow": {
                            "config": {
                                "run_id": run_id,
                                "sequencer_path": str(sequencer_path),
                                "metadata_download_url": metadata_download_url,
                                "data_suffixes": data_suffixes,
                            }
                        },
                        "data_studio": {
                            "config": {
                                "run_id": run_id,
                                "sequencer_path": str(sequencer_path),
                                "metadata_download_url": metadata_download_url,
                                "data_suffixes": data_suffixes,
                            }
                        },
                    }
                },
            )
        )
        new_processed_runs.add(run_id)

    return dg.SensorResult(
        run_requests=run_requests,
        cursor=json.dumps(list(new_processed_runs)),
    )
