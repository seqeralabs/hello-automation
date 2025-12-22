-include .env

.PHONY: trigger-workflow clean dev materialize

trigger-workflow: sequencer/fastq_single.sequenced

sequencer/fastq_single.sequenced: sequencer/fastq_single_1.fastq.gz sequencer/fastq_single_2.fastq.gz
	touch $@

sequencer/fastq_single_1.fastq.gz:
	wget -O $@ https://raw.githubusercontent.com/nf-core/test-datasets/modules/data/genomics/homo_sapiens/illumina/fastq/test_1.fastq.gz

sequencer/fastq_single_2.fastq.gz:
	wget -O $@ https://raw.githubusercontent.com/nf-core/test-datasets/modules/data/genomics/homo_sapiens/illumina/fastq/test_2.fastq.gz

# Dagster commands
dev:
	PYTHONPATH=src uv run dagster dev -m hello_automation.definitions

materialize:
	PYTHONPATH=src uv run dagster asset materialize -m hello_automation.definitions --select '*'

clean:
	rm -rf sequencer/*
	aws s3 rm s3://$(DESTINATION_BUCKET)/$(DESTINATION_PREFIX) --recursive