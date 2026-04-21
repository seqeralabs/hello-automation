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
    publishDir "${params.outdir}/${params.run_id}", mode: 'copy'

    input:
    val run_id

    output:
    path 'samplesheet.csv'

    script:
    def csv_url    = "${params.metadata_url}/${run_id}.csv"
    def input_base = params.input_base
    """
    curl -fsSL -o metadata.csv '${csv_url}'

    head -1 metadata.csv > samplesheet.csv

    tail -n +2 metadata.csv | while IFS=, read -r patient sex status sample lane _fq1 _fq2; do
        echo "\${patient},\${sex},\${status},\${sample},\${lane},${input_base}/${run_id}_1.fastq.gz,${input_base}/${run_id}_2.fastq.gz" >> samplesheet.csv
    done
    """
}

process TRIGGER_SAREK_ACTION {
    input:
    path samplesheet

    when:
    params.sarek_action_endpoint && params.seqera_access_token

    script:
    def endpoint = params.sarek_action_endpoint
    def token = params.seqera_access_token
    def samplesheetPath = "${params.outdir}/${params.run_id}/samplesheet.csv"
    """
    curl -fsSL -X POST \
      -H "Authorization: Bearer ${token}" \
      -H 'Content-Type: application/json' \
      -d '{"params":{"input":"${samplesheetPath}"}}' \
      '${endpoint}'
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
