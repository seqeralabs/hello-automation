terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  # AWS credentials will be pulled from environment variables:
  # AWS_ACCESS_KEY_ID
  # AWS_SECRET_ACCESS_KEY
  # AWS_ASSUME_ROLE_ARN
  # AWS_DEFAULT_REGION
}

# S3 bucket for SLAS 2025 data
resource "aws_s3_bucket" "slas_2025" {
  bucket = "slas-2025"  # From DESTINATION_BUCKET environment variable

  tags = {
    Project = "SLAS2025"
    Purpose = "Event-driven bioinformatics data storage"
  }
}

# Enable versioning
resource "aws_s3_bucket_versioning" "slas_2025" {
  bucket = aws_s3_bucket.slas_2025.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "slas_2025" {
  bucket = aws_s3_bucket.slas_2025.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "slas_2025" {
  bucket = aws_s3_bucket.slas_2025.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
} 