"""Cloud end-to-end verification script for GCS -> Pub/Sub -> Cloud Run -> BigQuery pipeline."""

import argparse
from datetime import datetime, timezone
import sys
import time
from google.cloud import storage, bigquery


def run_e2e_verification(project_id: str, bucket_name: str, dataset_id: str, table_id: str):
    print(f"[*] Starting Cloud E2E verification...")
    print(f"    Project: {project_id}")
    print(f"    GCS Bucket: {bucket_name}")
    print(f"    BigQuery Table: {project_id}.{dataset_id}.{table_id}")

    storage_client = storage.Client(project=project_id)
    bq_client = bigquery.Client(project=project_id)

    # 1. Create a unique test file
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    object_name = f"e2e_tests/test_document_{timestamp}.txt"
    test_content = (
        f"Serverless End-to-End Pipeline Verification File.\n"
        f"Uploaded at {timestamp}.\n"
        f"Contains financial invoice terms, compliance contract clauses, and python architecture tags.\n"
    )

    print(f"[*] Uploading test object gs://{bucket_name}/{object_name}...")
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_string(test_content, content_type="text/plain")
    print(f"[+] Successfully uploaded test file to Cloud Storage.")

    # 2. Poll BigQuery for the row
    full_table = f"`{project_id}.{dataset_id}.{table_id}`"
    expected_filename = f"test_document_{timestamp}.txt"
    print(f"[*] Polling BigQuery for filename '{expected_filename}' (waiting up to 60s)...")

    start_time = time.time()
    found = False

    while time.time() - start_time < 60:
        query = f"""
            SELECT filename, gcs_uri, processed_at, word_count, tags, ocr_preview
            FROM {full_table}
            WHERE filename = @filename
            LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("filename", "STRING", expected_filename)
            ]
        )
        try:
            query_job = bq_client.query(query, job_config=job_config)
            results = list(query_job.result())
            if results:
                row = results[0]
                elapsed = round(time.time() - start_time, 2)
                print(f"\n[SUCCESS] Document metadata found in BigQuery after {elapsed}s!")
                print(f"  Filename:     {row['filename']}")
                print(f"  GCS URI:      {row['gcs_uri']}")
                print(f"  Processed At: {row['processed_at']}")
                print(f"  Word Count:   {row['word_count']}")
                print(f"  Tags:         {row['tags']}")
                print(f"  Preview:      {row['ocr_preview']}")
                found = True
                break
        except Exception as e:
            print(f"[!] Query exception (retrying): {e}")

        time.sleep(3)
        print(".", end="", flush=True)

    if not found:
        print(f"\n[-] Verification TIMEOUT: Metadata was not found in BigQuery within 60 seconds.")
        print("    Troubleshooting steps:")
        print("    1. Check Cloud Run logs in GCP Console for document-processor.")
        print("    2. Verify Pub/Sub subscription status and dead-letter backlog.")
        print("    3. Confirm GCS bucket notification configuration.")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="End-to-end verification script for Google Cloud serverless pipeline.")
    parser.add_argument("--project", required=True, help="GCP Project ID")
    parser.add_argument("--bucket", required=True, help="GCS Bucket Name (without gs://)")
    parser.add_argument("--dataset", default="document_processing", help="BigQuery Dataset ID (default: document_processing)")
    parser.add_argument("--table", default="documents_metadata", help="BigQuery Table ID (default: documents_metadata)")

    args = parser.parse_args()
    run_e2e_verification(args.project, args.bucket, args.dataset, args.table)
