"""BigQuery streaming insertion service."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional
from google.cloud import bigquery
from google.auth.exceptions import DefaultCredentialsError

from app.config import settings

logger = logging.getLogger(__name__)


class BigQueryService:
    def __init__(self):
        self._client: Optional[bigquery.Client] = None
        self._mock_mode = settings.mock_mode
        self._mock_inserted_rows: List[Dict] = []

        if not self._mock_mode:
            try:
                self._client = bigquery.Client(project=settings.project_id or None)
                logger.info("Initialized BigQuery client successfully.")
            except DefaultCredentialsError:
                logger.warning(
                    "Default Google credentials not found. Falling back to BigQuery mock mode for local testing."
                )
                self._mock_mode = True

    @property
    def is_mock(self) -> bool:
        return self._mock_mode

    @property
    def mock_inserted_rows(self) -> List[Dict]:
        return self._mock_inserted_rows

    def insert_document_metadata(self, row: Dict) -> bool:
        """
        Streams a single document metadata row into the configured BigQuery table.
        Returns True on success, or raises RuntimeError on BigQuery streaming error.
        """
        table_ref = settings.full_table_id

        if self._mock_mode:
            logger.info(f"[MOCK BIGQUERY] Streamed row into table {table_ref}: {row}")
            self._mock_inserted_rows.append(row)
            return True

        if not self._client:
            raise RuntimeError("BigQuery client is not initialized.")

        # Streaming insert into BigQuery
        errors = self._client.insert_rows_json(table_ref, [row])
        if errors:
            err_msg = f"BigQuery streaming insert failed with errors: {errors}"
            logger.error(err_msg)
            raise RuntimeError(err_msg)

        logger.info(f"Successfully inserted metadata for '{row.get('filename')}' into BigQuery {table_ref}")
        return True


bigquery_service = BigQueryService()
