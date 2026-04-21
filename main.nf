#!/usr/bin/env nextflow

/*
 * create-samplesheet pipeline
 *
 * Given a run_id, fetches a metadata CSV from a remote URL, rewrites FASTQ
 * paths to point at pre-staged S3 locations, and publishes a Sarek-compatible
 * samplesheet to a deterministic path:
 *
 *   {outdir}/{run_id}/samplesheet.csv
 *
 * When launched on Seqera Platform, this pipeline can call a Sarek action
 * endpoint directly with the run-specific samplesheet path, eliminating the
 * need for Temporal orchestration.
 */

params.run_id                = null   // e.g. "fastq_single"
params.metadata_url          = null   // base URL; CSV fetched from <url>/<run_id>.csv
params.input_base            = null   // S3 prefix where FASTQs are already staged
params.outdir                = null   // S3 prefix for outputs
params.sarek_action_endpoint = null   // full Seqera action launch URL for Sarek
params.seqera_access_token   = System.getenv('TOWER_ACCESS_TOKEN')

process CREATE_SAMPLESHEET {
    container 'python:3.12-slim'
    publishDir "${params.outdir}/${params.run_id}", mode: 'copy'

    input:
    val run_id

    output:
    path 'samplesheet.csv'

    script:
    def csv_url    = "${params.metadata_url}/${run_id}.csv"
    def input_base = params.input_base
    """
    python - <<'PY'
    import csv
    import urllib.request

    csv_url = "${csv_url}"
    input_base = "${input_base}"
    run_id = "${run_id}"

    with urllib.request.urlopen(csv_url) as response:
        rows = list(csv.DictReader(line.decode() for line in response.readlines()))

    fieldnames = ["patient", "sex", "status", "sample", "lane", "fastq_1", "fastq_2"]
    with open("samplesheet.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "patient": row["patient"],
                "sex": row["sex"],
                "status": row["status"],
                "sample": row["sample"],
                "lane": row["lane"],
                "fastq_1": f"{input_base}/{run_id}_1.fastq.gz",
                "fastq_2": f"{input_base}/{run_id}_2.fastq.gz",
            })
    PY
    """
}

process TRIGGER_SAREK_ACTION {
    container 'python:3.12-slim'
    input:
    path samplesheet

    when:
    params.sarek_action_endpoint && params.seqera_access_token

    script:
    def endpoint = params.sarek_action_endpoint
    def token = params.seqera_access_token
    def samplesheetPath = "${params.outdir}/${params.run_id}/samplesheet.csv"
    """
    python - <<'PY'
    import json
    import urllib.request

    endpoint = "${endpoint}"
    token = "${token}"
    payload = json.dumps({"params": {"input": "${samplesheetPath}"}}).encode()

    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
    PY
    """
}

workflow {
    if (!params.run_id)       { error "param 'run_id' is required" }
    if (!params.metadata_url) { error "param 'metadata_url' is required" }
    if (!params.input_base)   { error "param 'input_base' is required" }
    if (!params.outdir)       { error "param 'outdir' is required" }

    samplesheet = CREATE_SAMPLESHEET(params.run_id)
    TRIGGER_SAREK_ACTION(samplesheet)
}
