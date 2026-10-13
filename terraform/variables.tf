variable "project_id" {
  description = "The Google Cloud Project ID where resources will be deployed."
  type        = string
}

variable "region" {
  description = "The Google Cloud region for deployment (e.g., us-central1, europe-west1)."
  type        = string
  default     = "us-central1"
}

variable "bucket_name" {
  description = "The globally unique name for the GCS ingestion bucket."
  type        = string
  default     = "doc-ingest-bucket"
}

variable "dataset_id" {
  description = "The BigQuery dataset ID for document metadata."
  type        = string
  default     = "document_processing"
}

variable "table_id" {
  description = "The BigQuery table ID for document metadata."
  type        = string
  default     = "documents_metadata"
}

variable "service_name" {
  description = "The name of the Cloud Run processor service."
  type        = string
  default     = "document-processor"
}

variable "container_image" {
  description = "The container image URI to deploy to Cloud Run."
  type        = string
  default     = "gcr.io/cloudrun/hello" # Replace with your Artifact Registry image after docker push
}
