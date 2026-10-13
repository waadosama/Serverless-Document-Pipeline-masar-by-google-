"""FastAPI service entrypoint for Google Cloud Run Pub/Sub push receiver."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.bigquery_service import bigquery_service
from app.config import settings
from app.gcs_service import gcs_service
from app.ocr_engine import process_document

logging.basicConfig(level=settings.log_level, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger("document-processor")

app = FastAPI(
    title="Serverless Document Processing Pipeline",
    description="Processes documents uploaded to Cloud Storage via Pub/Sub push events, performs simulated OCR, and streams metadata to BigQuery.",
    version="1.0.0",
)


class PubSubMessage(BaseModel):
    data: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    messageId: Optional[str] = None
    publishTime: Optional[str] = None


class PubSubPushPayload(BaseModel):
    message: PubSubMessage
    subscription: Optional[str] = None


class DirectProcessRequest(BaseModel):
    bucket: str = Field(..., description="GCS bucket name")
    object_name: str = Field(..., description="GCS object path/name")


@app.get("/")
def root():
    return {
        "service": "serverless-document-processor",
        "status": "healthy",
        "mock_mode": gcs_service.is_mock or bigquery_service.is_mock,
        "table": settings.full_table_id,
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


def _extract_bucket_and_object(payload: PubSubPushPayload) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extracts bucket, object name, and eventType from Pub/Sub payload.
    Supports both JSON_API_V1 data payload and GCS notification attributes.
    """
    msg = payload.message
    attrs = msg.attributes or {}
    event_type = attrs.get("eventType")
    bucket = attrs.get("bucketId")
    object_name = attrs.get("objectId")

    # If data is present, try decoding base64 JSON payload
    if msg.data:
        try:
            decoded_bytes = base64.b64decode(msg.data)
            data_json = json.loads(decoded_bytes.decode("utf-8"))
            bucket = data_json.get("bucket") or bucket
            object_name = data_json.get("name") or object_name
            event_type = data_json.get("kind") or event_type
        except Exception as e:
            logger.warning(f"Could not parse Pub/Sub data field as JSON: {e}")

    return bucket, object_name, event_type


def _process_and_store(bucket: str, object_name: str) -> Dict[str, Any]:
    """Helper to download, process, and stream document metadata to BigQuery."""
    logger.info(f"Processing object gs://{bucket}/{object_name}")

    # 1. Download file content & attributes from GCS
    content_bytes, _ = gcs_service.download_blob_bytes(bucket, object_name)

    # 2. Perform simulated OCR and metadata extraction
    extracted = process_document(object_name, content_bytes)

    # 3. Construct BigQuery row matching required schema
    gcs_uri = f"gs://{bucket}/{object_name}"
    row = {
        "filename": extracted["filename"],
        "gcs_uri": gcs_uri,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "file_size_bytes": extracted["file_size_bytes"],
        "word_count": extracted["word_count"],
        "tags": extracted["tags"],
        "ocr_preview": extracted["ocr_preview"],
    }

    # 4. Stream metadata into BigQuery
    bigquery_service.insert_document_metadata(row)

    logger.info(f"Completed processing for {gcs_uri}: {extracted['word_count']} words, tags={extracted['tags']}")
    return row


@app.post("/", status_code=status.HTTP_200_OK)
async def handle_pubsub_push(payload: PubSubPushPayload, response: Response):
    """
    Receives Pub/Sub push notification triggered by GCS object finalize event.
    Returns HTTP 200/204 to acknowledge the message to Pub/Sub.
    """
    bucket, object_name, event_type = _extract_bucket_and_object(payload)

    # Ignore delete/archive events
    if event_type in ("OBJECT_DELETE", "OBJECT_ARCHIVE"):
        logger.info(f"Ignored non-creation event: {event_type} for gs://{bucket}/{object_name}")
        return {"status": "ignored", "event_type": event_type}

    if not bucket or not object_name:
        logger.warning(f"Missing bucket or object name in Pub/Sub message: {payload.model_dump()}")
        # Acknowledge to prevent infinite retry loops on malformed messages
        return {"status": "skipped", "reason": "missing bucket or object name"}

    # Avoid infinite loop if an output file or directory is ignored
    if object_name.endswith("/") or object_name.startswith("."):
        logger.info(f"Skipping folder or hidden object: {object_name}")
        return {"status": "skipped", "reason": "directory or hidden file"}

    try:
        result = _process_and_store(bucket, object_name)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.exception(f"Error processing document gs://{bucket}/{object_name}: {e}")
        # Raising 500 prompts Pub/Sub to retry if transient, or we return 500
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-direct", status_code=status.HTTP_200_OK)
async def handle_direct_process(req: DirectProcessRequest):
    """
    Direct endpoint for testing document extraction without going through Pub/Sub.
    """
    try:
        result = _process_and_store(req.bucket, req.object_name)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.exception(f"Error during direct processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))
