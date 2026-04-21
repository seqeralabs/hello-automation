# Hello Automation

Seqera-native chaining demo: a create-samplesheet Nextflow pipeline in this repo, followed by nf-core/sarek launched through a Seqera action endpoint.

This repo no longer uses Temporal. The orchestration lives in Seqera Platform plus the create-samplesheet pipeline itself.

## Architecture

```text
┌─────────────────────┐   POST /actions/<sarek>/launch   ┌──────────────────┐
│ create-samplesheet  │─────────────────────────────────▶│  nf-core/sarek   │
│ (this repo)         │   params.input=samplesheet.csv   │  (variant call)  │
└─────────────────────┘                                  └──────────────────┘
```

Flow:
1. create-samplesheet fetches a metadata CSV
2. it rewrites FASTQ paths to deterministic S3 paths
3. it publishes `{outdir}/{run_id}/samplesheet.csv`
4. if `sarek_action_endpoint` is configured, it calls the Seqera action launch API with that exact samplesheet path

This is the important difference from `pipeline_status` actions: the action launch endpoint can receive run-specific params, while `pipeline_status` actions launch a static template.

## Requirements

- Nextflow >= 23.10
- seqerakit
- Seqera Platform workspace with a compute environment
- curl

## Key parameters

| Parameter | Description | Required |
|---|---|---|
| `run_id` | Sequencing run identifier, e.g. `fastq_single` | yes |
| `metadata_url` | Base URL for metadata CSVs | yes |
| `input_base` | S3 prefix where FASTQs are already staged | yes |
| `outdir` | S3 prefix for outputs | yes |
| `sarek_action_endpoint` | Full Seqera action launch URL for the Sarek action | no |
| `TOWER_ACCESS_TOKEN` | Bearer token used by create-samplesheet when calling the Sarek action endpoint | required for chaining |

## Setup

### 1. Configure environment

```bash
cp .env.TEMPLATE .env
# Edit .env with your Platform token, workspace ID, compute env ID, bucket/prefix,
# and the Sarek action endpoint once it exists.
```

### 2. Deploy Seqera resources

```bash
make platform
```

This deploys:
- pipeline definitions for `create-samplesheet` and `nf-core-sarek`
- a `create-samplesheet-action`
- a `sarek-action`
- workspace / compute-environment config from `platform/*.yml`

### 3. Discover the Sarek action endpoint

After deploying actions, inspect the Sarek action in Seqera Platform or via API/CLI and copy its launch endpoint into `.env` as `SAREK_ACTION_ENDPOINT`.

For the PR preview environment you pointed me at, the current pipeline-status proof-of-concept action is:
- UI: `https://pr-10898.dev-seqera.io/orgs/scidev/workspaces/playground/actions/kkR2PhY3hlczDTijW0uaI`

But for dynamic handoff of a run-specific samplesheet, you want the launch endpoint of a normal `sarek-action`, not only a `pipeline_status` watcher.

The endpoint format is:

```text
https://<seqera-host>/api/actions/<ACTION_ID>/launch
```

### 4. Launch the chain

```bash
make launch
```

That launches `create-samplesheet`. If `sarek_action_endpoint` and `TOWER_ACCESS_TOKEN` are present, the pipeline will call the Sarek action endpoint automatically with:

```json
{"params":{"input":"s3://.../<run_id>/samplesheet.csv"}}
```

## Local smoke test

```bash
make test-local
```

This runs the create-samplesheet pipeline locally and writes:

```text
/tmp/hello-automation-test/<run_id>/samplesheet.csv
```

## Platform config files

- `main.nf` — repo-root create-samplesheet workflow for Seqera launches
- `nextflow.config` — manifest and params defaults
- `platform/pipelines.yml` — create-samplesheet + nf-core/sarek pipeline definitions
- `platform/action.yml` — `create-samplesheet-action` and `sarek-action`
- `platform/launch.yml` — example launch for create-samplesheet
- `platform/compute-envs.yml` — AWS Batch compute environment

## Why not just pipeline_status?

I inspected the new backend implementation in the Platform repo and the PR action you linked. `pipeline_status` actions are useful when the downstream launch can be static, but they do not inherit run-specific params from the completed workflow. In contrast, `POST /actions/{actionId}/launch` accepts a body like:

```json
{"params":{"input":"s3://.../samplesheet.csv"}}
```

That makes the action endpoint the better fit for replacing the old Temporal handoff.
