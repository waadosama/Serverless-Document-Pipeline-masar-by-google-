"""Simulated OCR and document metadata extraction engine."""

from __future__ import annotations

import hashlib
import os
import re
from typing import Dict, List, Set, Tuple

# Domain keyword mapping for tagging text documents
TOPIC_KEYWORDS: Dict[str, Set[str]] = {
    "finance": {"invoice", "receipt", "payment", "tax", "balance", "revenue", "expense", "audit", "budget", "dollar", "usd", "cost"},
    "legal": {"contract", "agreement", "nda", "terms", "clause", "compliance", "liability", "party", "jurisdiction", "signature"},
    "technical": {"architecture", "api", "database", "python", "cloud", "serverless", "pubsub", "docker", "pipeline", "schema", "code"},
    "medical": {"patient", "diagnosis", "prescription", "clinical", "hospital", "doctor", "health", "treatment", "medical"},
    "hr": {"resume", "candidate", "employee", "salary", "interview", "onboarding", "recruitment", "benefits", "hiring"},
    "security": {"confidential", "vulnerability", "encryption", "auth", "token", "password", "firewall", "security", "permission"},
}

TEXT_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".log", ".xml", ".html", ".yaml", ".yml"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".webp"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".pptx"}


class ProcessedDocument(dict):
    """Processed document metadata container."""
    filename: str
    file_size_bytes: int
    word_count: int
    tags: List[str]
    ocr_preview: str


def extract_tags_from_text(text: str) -> List[str]:
    """Extract topic tags from text using keyword frequency and dictionary mapping."""
    lower_text = text.lower()
    words = set(re.findall(r"\b[a-z]{3,}\b", lower_text))
    matched_tags: List[str] = []

    for category, keywords in TOPIC_KEYWORDS.items():
        if keywords & words:
            matched_tags.append(category)

    if not matched_tags:
        matched_tags.append("general")

    return matched_tags


def simulate_ocr_for_binary(filename: str, file_bytes: bytes, file_ext: str) -> Tuple[str, int, List[str]]:
    """
    Simulates OCR processing for non-plain-text files (PDFs, images, office docs).
    Generates deterministic simulated text and tags based on file attributes.
    """
    base_name = os.path.basename(filename).lower()
    file_size = len(file_bytes)
    hasher = hashlib.md5(filename.encode("utf-8") + str(file_size).encode("utf-8")).hexdigest()

    # Determine document domain from filename hints
    if any(k in base_name for k in ["invoice", "bill", "receipt", "payment"]):
        category = "finance"
        simulated_text = (
            f"[SIMULATED OCR - INVOICE] Vendor: Acme Corp Inc. Invoice ID: INV-{hasher[:8].upper()}. "
            f"Date: 2026-10-10. Total Amount: $1,450.00 USD. Tax: $120.00. Payment Status: Pending. "
            f"Items: Cloud infrastructure consulting, Serverless pipeline configuration. Terms: Net 30."
        )
        tags = ["finance", "invoice", "simulated-ocr"]
    elif any(k in base_name for k in ["contract", "agreement", "nda", "terms"]):
        category = "legal"
        simulated_text = (
            f"[SIMULATED OCR - LEGAL AGREEMENT] Master Service Agreement Ref: MSA-{hasher[:8].upper()}. "
            f"This contract is made between Party A and Party B. Terms and compliance regulations apply. "
            f"Confidentiality clause and liability limitations are binding under applicable jurisdiction."
        )
        tags = ["legal", "contract", "simulated-ocr"]
    elif any(k in base_name for k in ["architecture", "spec", "design", "tech", "api"]):
        category = "technical"
        simulated_text = (
            f"[SIMULATED OCR - TECH SPEC] Serverless Event-Driven Document Architecture. "
            f"Components: GCS Ingestion Bucket, Cloud Pub/Sub Topic, Cloud Run Python Worker, BigQuery Storage. "
            f"Throughput target: 500 documents/sec with sub-second latency and zero cold-start overhead."
        )
        tags = ["technical", "architecture", "simulated-ocr"]
    elif any(k in base_name for k in ["resume", "cv", "candidate"]):
        category = "hr"
        simulated_text = (
            f"[SIMULATED OCR - RESUME] Senior Cloud Architect & Python Engineer. "
            f"Experience: 8+ years developing scalable GCP serverless applications, BigQuery pipelines, "
            f"and event-driven microservices. Education: B.S. in Computer Science."
        )
        tags = ["hr", "resume", "simulated-ocr"]
    else:
        # Fallback simulated scan
        ext_clean = file_ext.replace(".", "").upper()
        simulated_text = (
            f"[SIMULATED OCR - {ext_clean} DOCUMENT] Document scan hash {hasher[:12]}. "
            f"Document Title: '{filename}'. High-confidence text recognition performed across {max(1, file_size // 50000)} scanned page(s). "
            f"Extracted content includes standard alphanumeric data tables and signature blocks."
        )
        tags = ["scanned-document", ext_clean.lower(), "simulated-ocr"]

    words = re.findall(r"\b\w+\b", simulated_text)
    # Estimate total words proportional to file size for realism (min 35 words)
    estimated_word_count = max(len(words), (file_size // 150) + len(words))

    return simulated_text, estimated_word_count, tags


def process_document(filename: str, content_bytes: bytes) -> Dict:
    """
    Main processing entrypoint. Analyzes content bytes and produces metadata.
    """
    file_ext = os.path.splitext(filename)[1].lower()
    file_size = len(content_bytes)

    if file_ext in TEXT_EXTENSIONS:
        try:
            text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = content_bytes.decode("latin-1", errors="replace")

        words = re.findall(r"\b\w+\b", text)
        word_count = len(words)
        tags = extract_tags_from_text(text)
        tags.append("text-extracted")
        preview = text.strip()[:300].replace("\n", " ")
        if len(text.strip()) > 300:
            preview += "..."
    else:
        preview, word_count, tags = simulate_ocr_for_binary(filename, content_bytes, file_ext)

    return {
        "filename": os.path.basename(filename),
        "file_size_bytes": file_size,
        "word_count": word_count,
        "tags": sorted(list(set(tags))),
        "ocr_preview": preview,
    }
