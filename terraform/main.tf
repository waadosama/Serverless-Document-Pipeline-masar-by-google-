terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.20"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Cloud Storage - Document Ingestion Bucket
resource "google_storage_bucket" "ingest_bucket" {
  name                        = "${var.bucket_name}-${var.project_id}"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true

  versioning {
    enabled = false
  }
}

# 2. Pub/Sub Topic for GCS notifications
resource "google_pubsub_topic" "gcs_notifications" {
  name = "document-upload-topic"
}

# Fetch the Cloud Storage Service Account so it can publish to Pub/Sub
data "google_storage_project_service_account" "gcs_account" {
  project = var.project_id
}

# Allow GCS Service Account to publish to the Pub/Sub topic
resource "google_pubsub_topic_iam_member" "gcs_publisher" {
  topic  = google_pubsub_topic.gcs_notifications.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${data.google_storage_project_service_account.gcs_account.email_address}"
}

# Configure GCS to publish an event on OBJECT_FINALIZE
resource "google_storage_notification" "upload_notification" {
  bucket         = google_storage_bucket.ingest_bucket.name
  payload_format = "JSON_API_V1"
  topic          = google_pubsub_topic.gcs_notifications.id
  event_types    = ["OBJECT_FINALIZE"]

  depends_on = [google_pubsub_topic_iam_member.gcs_publisher]
}

# 3. BigQuery Dataset & Table for Metadata Storage
resource "google_bigquery_dataset" "dataset" {
  dataset_id                  = var.dataset_id
  location                    = var.region
  description                 = "Dataset containing extracted document processing metadata"
  delete_contents_on_destroy  = true
}

resource "google_bigquery_table" "metadata_table" {
  dataset_id          = google_bigquery_dataset.dataset.dataset_id
  table_id            = var.table_id
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "processed_at"
  }

  schema = jsonencode([
    {
      name        = "filename"
      type        = "STRING"
      mode        = "REQUIRED"
      description = "Base filename of the uploaded document"
    },
    {
      name        = "gcs_uri"
      type        = "STRING"
      mode        = "REQUIRED"
      description = "GCS URI (gs://bucket/object)"
    },
    {
      name        = "processed_at"
      type        = "TIMESTAMP"
      mode        = "REQUIRED"
      description = "Timestamp when the document was processed"
    },
    {
      name        = "file_size_bytes"
      type        = "INTEGER"
      mode        = "NULLABLE"
      description = "Size of the file in bytes"
    },
    {
      name        = "word_count"
      type        = "INTEGER"
      mode        = "NULLABLE"
      description = "Extracted or simulated word count"
    },
    {
      name        = "tags"
      type        = "STRING"
      mode        = "REPEATED"
      description = "List of topic tags extracted from the document"
    },
    {
      name        = "ocr_preview"
      type        = "STRING"
      mode        = "NULLABLE"
      description = "Preview snippet of extracted/simulated OCR text"
    }
  ])
}

# 4. Dedicated Service Account for Cloud Run Processor
resource "google_service_account" "processor_sa" {
  account_id   = "doc-processor-sa"
  display_name = "Cloud Run Document Processor Service Account"
}

# Grant Cloud Run SA read access to GCS
resource "google_storage_bucket_iam_member" "sa_storage_viewer" {
  bucket = google_storage_bucket.ingest_bucket.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.processor_sa.email}"
}

# Grant Cloud Run SA write access to BigQuery dataset
resource "google_bigquery_dataset_iam_member" "sa_bq_editor" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.processor_sa.email}"
}

# Grant BigQuery job user to execute queries/streaming if needed
resource "google_project_iam_member" "sa_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.processor_sa.email}"
}

# 5. Cloud Run v2 Service
resource "google_cloud_run_v2_service" "processor" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.processor_sa.email

    containers {
      image = var.container_image

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "GCP_PROJECT"
        value = var.project_id
      }
      env {
        name  = "BIGQUERY_DATASET"
        value = var.dataset_id
      }
      env {
        name  = "BIGQUERY_TABLE"
        value = var.table_id
      }

      ports {
        container_port = 8080
      }
    }
  }
}

# Allow unauthenticated invocations for Cloud Run (as chosen during setup)
resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  name     = google_cloud_run_v2_service.processor.name
  location = google_cloud_run_v2_service.processor.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# 6. Pub/Sub Push Subscription routing events to Cloud Run
resource "google_pubsub_subscription" "push_subscription" {
  name  = "document-processor-subscription"
  topic = google_pubsub_topic.gcs_notifications.id

  ack_deadline_seconds = 60

  push_config {
    push_endpoint = google_cloud_run_v2_service.processor.uri
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  depends_on = [google_cloud_run_v2_service_iam_member.public_invoker]
}
