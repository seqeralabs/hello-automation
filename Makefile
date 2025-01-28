-include .env

.PHONY: trigger-workflow clean

trigger-workflow: sequencer/fastq_single.sequenced

sequencer/fastq_single.sequenced: sequencer/fastq_single_1.fastq.gz sequencer/fastq_single_2.fastq.gz
	touch $@

sequencer/fastq_single_1.fastq.gz:
	wget -O $@ https://raw.githubusercontent.com/nf-core/test-datasets/modules/data/genomics/homo_sapiens/illumina/fastq/test_1.fastq.gz

sequencer/fastq_single_2.fastq.gz:
	wget -O $@ https://raw.githubusercontent.com/nf-core/test-datasets/modules/data/genomics/homo_sapiens/illumina/fastq/test_2.fastq.gz

run-temporal:
	temporal server start-dev

run-worker:
	uv run src/hello_automation/run_worker.py

run-workflow:
	uv run src/hello_automation/run_workflow.py

clean:
	rm -rf sequencer/*
	aws s3 rm s3://$(DESTINATION_BUCKET)/$(DESTINATION_PREFIX) --recursive