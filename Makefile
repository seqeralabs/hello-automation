-include .env

.PHONY: platform launch test-local clean

platform:
	seqerakit platform/*.yml

launch:
	seqerakit platform/launch.yml

test-local:
	nextflow run main.nf \
		--run_id fastq_single \
		--metadata_url 'https://raw.githubusercontent.com/nf-core/sarek/refs/tags/3.5.0/tests/csv/3.0' \
		--input_base 's3://$(DESTINATION_BUCKET)/$(DESTINATION_PREFIX)' \
		--outdir '/tmp/hello-automation-test'

clean:
	rm -rf work/ .nextflow/ .nextflow.log* /tmp/hello-automation-test /tmp/hello-automation-test2
