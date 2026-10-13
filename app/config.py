"""Configuration settings for document processing pipeline."""

import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    project_id: str = Field(
        default_factory=lambda: os.getenv("GCP_PROJECT", os.getenv("GOOGLE_CLOUD_PROJECT", ""))
    )
    bigquery_dataset: str = Field(
        default_factory=lambda: os.getenv("BIGQUERY_DATASET", "document_processing")
    )
    bigquery_table: str = Field(
        default_factory=lambda: os.getenv("BIGQUERY_TABLE", "documents_metadata")
    )
    port: int = Field(
        default_factory=lambda: int(os.getenv("PORT", "8080"))
    )
    log_level: str = Field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )
    # Allows offline local testing without GCP credentials
    mock_mode: bool = Field(
        default_factory=lambda: os.getenv("MOCK_MODE", "false").lower() in ("true", "1", "yes")
    )

    @property
    def full_table_id(self) -> str:
        """Returns the fully-qualified BigQuery table ID if project_id is available."""
        if self.project_id:
            return f"{self.project_id}.{self.bigquery_dataset}.{self.bigquery_table}"
        return f"{self.bigquery_dataset}.{self.bigquery_table}"


settings = Settings()
