output "gcs_bucket_name" {
  description = "Name of the GCS bucket for document uploads"
  value       = google_storage_bucket.ingest_bucket.name
}

output "pubsub_topic_name" {
  description = "Name of the Pub/Sub topic receiving GCS notifications"
  value       = google_pubsub_topic.gcs_notifications.name
}

output "pubsub_subscription_name" {
  description = "Name of the Pub/Sub push subscription"
  value       = google_pubsub_subscription.push_subscription.name
}

output "cloud_run_service_url" {
  description = "Direct HTTP URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.processor.uri
}

output "bigquery_dataset_id" {
  description = "BigQuery dataset ID"
  value       = google_bigquery_dataset.dataset.dataset_id
}

output "bigquery_table_id" {
  description = "Full BigQuery table ID"
  value       = "${google_bigquery_dataset.dataset.dataset_id}.${google_bigquery_table.metadata_table.table_id}"
}
