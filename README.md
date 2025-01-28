# Hello Automation

This is a simple example of event-driven bioinformatics workflows using Temporal, Nextflow and Seqera Platform.

## Requirements

- [Temporal](https://learn.temporal.io/getting_started/python/dev_environment/#set-up-a-local-temporal-service-for-development-with-temporal-cli)
- [uv](https://docs.astral.sh/uv/)
- [seqerakit](https://github.com/seqeralabs/seqera-kit)
- [Seqera Platform CLI](https://github.com/seqeralabs/tower-cli#1-installation))

## Usage

### Deploy the Seqera Platform resources

[Create a token for the Seqera Platform programmatic access](https://docs.seqera.io/wave/get-started#create-your-seqera-access-token) and set it in the `TOWER_ACCESS_TOKEN` environment variable.

Customize then deploy the resources in the `platform` directory:

```bash
seqerakit platform/*.yml
```

The necessary environment variables will be set in the `platform/.envrc` file.

### Run the temporal automation

Copy the `.env.TEMPLATE` file to `.env` and fill in the values for the environment variables.

In separate terminal windows, run the following commands:

```bash
make run-temporal
make run-worker
make run-workflow
make trigger-workflow
```

These commands will start the Temporal server, the worker and the workflow.
