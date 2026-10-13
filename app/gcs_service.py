"""Google Cloud Storage service wrapper."""

from __future__ import annotations

import logging
from typing import Optional, Tuple
from google.cloud import storage
from google.auth.exceptions import DefaultCredentialsError

from app.config import settings

logger = logging.getLogger(__name__)


class GCSService:
    def __init__(self):
        self._client: Optional[storage.Client] = None
        self._mock_mode = settings.mock_mode

        if not self._mock_mode:
            try:
                self._client = storage.Client(project=settings.project_id or None)
                logger.info("Initialized Google Cloud Storage client successfully.")
            except DefaultCredentialsError:
                logger.warning(
                    "Default Google credentials not found. Falling back to GCS mock mode for local testing."
                )
                self._mock_mode = True

    @property
    def is_mock(self) -> bool:
        return self._mock_mode

    def download_blob_bytes(self, bucket_name: str, object_name: str) -> Tuple[bytes, dict]:
        """
        Downloads the specified object bytes and returns (bytes, metadata_dict).
        In mock mode, returns simulated file content.
        """
        if self._mock_mode:
            logger.info(f"[MOCK GCS] Simulating download for gs://{bucket_name}/{object_name}")
            sample_content = (
                f"Simulated document content for {object_name}.\n"
                f"Contains financial invoice and contract terms for architecture verification.\n"
                f"Cloud Run serverless pipeline test."
            ).encode("utf-8")
            metadata = {
                "content_type": "text/plain",
                "size": len(sample_content),
                "bucket": bucket_name,
                "name": object_name,
            }
            return sample_content, metadata

        if not self._client:
            raise RuntimeError("GCS Client is not initialized.")

        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(object_name)

        if not blob.exists():
            raise FileNotFoundError(f"Blob gs://{bucket_name}/{object_name} does not exist.")

        content_bytes = blob.download_as_bytes()
        metadata = {
            "content_type": blob.content_type or "application/octet-stream",
            "size": blob.size or len(content_bytes),
            "bucket": bucket_name,
            "name": object_name,
            "time_created": str(blob.time_created) if blob.time_created else None,
        }
        logger.info(f"Successfully downloaded {len(content_bytes)} bytes from gs://{bucket_name}/{object_name}")
        return content_bytes, metadata


gcs_service = GCSService()
