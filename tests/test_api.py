"""Integration tests for FastAPI endpoints."""

import base64
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.bigquery_service import bigquery_service
from app.gcs_service import gcs_service


@pytest.fixture(autouse=True)
def setup_mock_environment():
    """Ensure mock mode is active for tests and clear recorded rows."""
    gcs_service._mock_mode = True
    bigquery_service._mock_mode = True
    bigquery_service._mock_inserted_rows.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_healthz_endpoint(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["mock_mode"] is True


def test_pubsub_push_with_base64_gcs_payload(client):
    # Simulate GCS JSON_API_V1 notification encoded in Pub/Sub data
    gcs_object_data = {
        "kind": "storage#object",
        "name": "invoices/2026/acme_invoice_99.pdf",
        "bucket": "test-ingest-bucket",
        "size": "45210",
        "contentType": "application/pdf",
    }
    encoded_data = base64.b64encode(json.dumps(gcs_object_data).encode("utf-8")).decode("utf-8")

    payload = {
        "message": {
            "data": encoded_data,
            "attributes": {
                "eventType": "OBJECT_FINALIZE",
                "bucketId": "test-ingest-bucket",
                "objectId": "invoices/2026/acme_invoice_99.pdf",
            },
            "messageId": "msg-12345",
            "publishTime": "2026-10-13T20:00:00Z",
        },
        "subscription": "projects/test-project/subscriptions/test-sub",
    }

    response = client.post("/", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"

    result = res_data["result"]
    assert result["filename"] == "acme_invoice_99.pdf"
    assert result["gcs_uri"] == "gs://test-ingest-bucket/invoices/2026/acme_invoice_99.pdf"
    assert "finance" in result["tags"]

    # Verify BigQuery received the row
    assert len(bigquery_service.mock_inserted_rows) == 1
    stored_row = bigquery_service.mock_inserted_rows[0]
    assert stored_row["filename"] == "acme_invoice_99.pdf"
    assert "ocr_preview" in stored_row


def test_pubsub_push_with_attributes_only(client):
    # Test payload where data is empty or absent, relying on attributes
    payload = {
        "message": {
            "attributes": {
                "eventType": "OBJECT_FINALIZE",
                "bucketId": "text-bucket",
                "objectId": "contract_draft.txt",
            },
            "messageId": "msg-9999",
        }
    }

    response = client.post("/", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert res_data["result"]["filename"] == "contract_draft.txt"


def test_pubsub_push_ignore_delete_event(client):
    payload = {
        "message": {
            "attributes": {
                "eventType": "OBJECT_DELETE",
                "bucketId": "test-bucket",
                "objectId": "deleted_file.pdf",
            },
            "messageId": "msg-delete",
        }
    }

    response = client.post("/", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    assert len(bigquery_service.mock_inserted_rows) == 0


def test_direct_process_endpoint(client):
    payload = {
        "bucket": "direct-bucket",
        "object_name": "reports/quarterly_summary.txt",
    }

    response = client.post("/process-direct", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert res_data["result"]["filename"] == "quarterly_summary.txt"
    assert res_data["result"]["gcs_uri"] == "gs://direct-bucket/reports/quarterly_summary.txt"
