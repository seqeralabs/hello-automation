apt-get install unzip

wget https://data.broadinstitute.org/igv/projects/downloads/2.19/IGV_Linux_2.19.1_WithJava.zip

unzip IGV_Linux_2.19.1_WithJava.zip

sh IGV_Linux_2.19.1_WithJava/igv.sh
Load Genome: Genomes > Load genome from URL > https://raw.githubusercontent.com/nf-core/test-datasets/modules/data//genomics/homo_sapiens/genome/genome.fasta
Load cram: File > Load from File > data > ... > preprocessing > recalibrated > test.cram
note: you can't copy and paste commands but have to type them out
