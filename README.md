# Serverless Event-Driven Document Processing Pipeline on Google Cloud

A complete serverless, event-driven document processing pipeline built on Google Cloud Platform. Files uploaded to Cloud Storage automatically trigger a Pub/Sub event, which invokes a Python Cloud Run microservice that performs OCR/metadata extraction and streams results into BigQuery.

---

## 🏛 Architecture Overview

```
                                      ┌──────────────────────┐
                                      │   Cloud Storage      │
                                      │  (Ingestion Bucket)  │
                                      └──────────┬───────────┘
                                                 │
                                                 │ 1. File Upload (OBJECT_FINALIZE)
                                                 ▼
                                      ┌──────────────────────┐
                                      │   Cloud Pub/Sub      │
                                      │       Topic          │
                                      └──────────┬───────────┘
                                                 │
                                                 │ 2. Push Subscription (HTTP POST)
                                                 ▼
┌─────────────────────────┐           ┌──────────────────────┐
│  Google Cloud BigQuery  │ ◄──────── │   Cloud Run Service  │
│  (documents_metadata)   │  4. Stream│   (FastAPI + Python) │
└─────────────────────────┘   Metadata└──────────────────────┘
                                          │
                                          │ 3. Fetch object & simulate OCR
                                          └───────► (GCS Read)
```

### Components

1. **Ingestion**: [Cloud Storage](https://cloud.google.com/storage) bucket with `google_storage_notification` publishing `OBJECT_FINALIZE` events.
2. **Event Router**: [Cloud Pub/Sub](https://cloud.google.com/pubsub) Topic with a Push Subscription sending JSON payloads via HTTP POST to the Cloud Run endpoint.
3. **Processor**: Containerized [Cloud Run](https://cloud.google.com/run) service (FastAPI + Uvicorn) that extracts text/metadata (word count, domain tags, preview, file size) with simulated OCR for binary files (PDFs, images).
4. **Storage**: [BigQuery](https://cloud.google.com/bigquery) dataset and time-partitioned table receiving metadata via streaming inserts (`insert_rows_json`).

---

## 📂 Project Structure

```
google-cloud-serverless-app/
├── app/
│   ├── __init__.py
│   ├── config.py              # Configuration & environment settings
│   ├── ocr_engine.py          # Simulated OCR & tag extraction engine
│   ├── gcs_service.py         # Cloud Storage client with mock fallback
│   ├── bigquery_service.py    # BigQuery streaming insert client with mock fallback
│   └── main.py                # FastAPI receiver & Pub/Sub push handler
├── terraform/
│   ├── main.tf                # GCS, Pub/Sub, BigQuery, IAM & Cloud Run
│   ├── variables.tf           # Configurable variables
│   ├── outputs.tf             # Outputs (URLs, bucket names, topic IDs)
│   └── terraform.tfvars.example
├── tests/
│   ├── __init__.py
│   ├── test_ocr_engine.py     # Unit tests for OCR and tag extraction
│   ├── test_api.py            # API tests for FastAPI endpoints
│   └── simulate_local_push.py # CLI utility to simulate Pub/Sub push locally
├── scripts/
│   └── verify_cloud_e2e.py    # End-to-end cloud validation script
├── Dockerfile                 # Cloud Run container definition
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Testing dependencies
└── README.md
```

---

## 📊 BigQuery Table Schema (`documents_metadata`)

| Field Name | Type | Mode | Description |
|---|---|---|---|
| `filename` | `STRING` | REQUIRED | Base file name (e.g., `invoice_99.pdf`) |
| `gcs_uri` | `STRING` | REQUIRED | Full GCS URI (`gs://bucket/path`) |
| `processed_at` | `TIMESTAMP` | REQUIRED | Processing timestamp (Partitioning Key) |
| `file_size_bytes` | `INTEGER` | NULLABLE | File size in bytes |
| `word_count` | `INTEGER` | NULLABLE | Extracted or simulated word count |
| `tags` | `STRING` | REPEATED | Extracted topic categories (`finance`, `legal`, etc.) |
| `ocr_preview` | `STRING` | NULLABLE | Preview snippet of extracted text |

---

## 🚀 Quickstart & Local Development

### 1. Set Up Python Environment

```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

pip install -r requirements-dev.txt
```

### 2. Run Unit & Integration Tests

The test suite runs completely offline with mocked GCP services:

```bash
pytest -v
```

### 3. Run FastAPI Processor Locally

```bash
uvicorn app.main:app --port 8080 --reload
```

The service will automatically detect that GCP credentials are not configured and operate in **Mock Mode**, logging simulated actions.

### 4. Test Local Pub/Sub Push Notification

While `uvicorn` is running, in a separate terminal:

```bash
python tests/simulate_local_push.py --bucket test-bucket --object invoices/sample_invoice.pdf
```

Output:
```json
{
  "status": "success",
  "result": {
    "filename": "sample_document.txt",
    "gcs_uri": "gs://<BUCKET_NAME>/sample_document.txt",
    "processed_at": "2026-01-01T00:00:00.000000+00:00",
    "file_size_bytes": 128,
    "word_count": 24,
    "tags": ["general", "text-extracted"],
    "ocr_preview": "Extracted document text preview..."
  }
}
```

---

## 🐳 Docker Deployment

### Build Container

```bash
docker build -t document-processor:latest .
```

### Run Locally

```bash
docker run -p 8080:8080 -e MOCK_MODE=true document-processor:latest
```

---

## ☁️ Google Cloud Deployment with Terraform

### 1. Build and Push Container to Google Artifact Registry

```bash
export PROJECT_ID="<YOUR_PROJECT_ID>"
export REGION="<YOUR_REGION>" # e.g. us-central1
export REPO="serverless-apps"
export IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/document-processor:latest"

# Authenticate & create repository
gcloud artifacts repositories create $REPO --repository-format=docker --location=$REGION

# Build and push with Cloud Build
gcloud builds submit --tag $IMAGE .
```

### 2. Deploy Infrastructure via Terraform

```bash
cd terraform

# Create your variables configuration
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
project_id      = "<YOUR_PROJECT_ID>"
region          = "us-central1"
bucket_name     = "<YOUR_BUCKET_NAME>"
container_image = "<YOUR_REGION>-docker.pkg.dev/<YOUR_PROJECT_ID>/serverless-apps/document-processor:latest"
```

Initialize and apply:
```bash
terraform init
terraform apply -auto-approve
```

Terraform outputs will display:
- `gcs_bucket_name`: The bucket created for your uploads.
- `cloud_run_service_url`: The deployed Cloud Run URL.
- `bigquery_table_id`: The BigQuery table receiving records.

---

## 🔍 Cloud End-to-End Verification

To verify the deployed pipeline in Google Cloud:

```bash
python scripts/verify_cloud_e2e.py \
  --project <YOUR_PROJECT_ID> \
  --bucket <YOUR_BUCKET_NAME> \
  --dataset document_processing \
  --table documents_metadata
```

This script:
1. Uploads a sample file to your GCS bucket.
2. Waits for GCS -> Pub/Sub -> Cloud Run -> BigQuery event propagation.
3. Queries BigQuery to verify that the metadata record was inserted.

---

## 📈 Querying BigQuery

Once files have been processed, query the metadata table in BigQuery:

```sql
SELECT
  filename,
  gcs_uri,
  word_count,
  tags,
  ocr_preview,
  processed_at
FROM
  `<YOUR_PROJECT_ID>.document_processing.documents_metadata`
WHERE
  "technical" IN UNNEST(tags)
ORDER BY
  processed_at DESC
LIMIT 20;
```

---

## 🔒 Security & Sensitive Data Hygiene

- **No Hardcoded Credentials**: This project uses Google Cloud Application Default Credentials (ADC) and IAM service accounts (`doc-processor-sa`). Never commit service account JSON keys or tokens.
- **Production Invocation Auth**: In production environments, remove `allUsers` invoker permissions on Cloud Run and configure Pub/Sub Push Subscriptions with an OIDC service account token.
- **Data Privacy**: Ensure that documents uploaded to the GCS ingestion bucket comply with your data classification and retention policies.

