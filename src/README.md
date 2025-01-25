# Event-Driven Bioinformatics Pipeline

This project demonstrates an event-driven bioinformatics pipeline using Temporal workflows to process genome sequencing data and trigger Nextflow pipelines on the Seqera Platform.

## Prerequisites

- Python 3.10+
- [Temporal CLI](https://learn.temporal.io/getting_started/python/dev_environment/)
- AWS credentials configured for S3 access
- Seqera Platform account and API token
- `uv` package installer

## Installation

1. Install Temporal following the [official guide](https://learn.temporal.io/getting_started/python/dev_environment/)

2. Install Python dependencies using `uv`:
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -r requirements.txt
   ```

3. Start the Temporal development server:
   ```bash
   temporal server start-dev
   ```

4. Start the workflow process:
   ```bash
   make run-workflow
   ```

5. Start a worker process in a new terminal:
   ```bash
   make run-worker
   ```

6. Trigger the workflow execution:
   ```bash
   make trigger-workflow
   ```

## Configuration

The project requires the configuration of settings that can be set in a `.env` file or set in the environment.
An example `.env.TEMPLATE` file is provided in the root of the repository.
