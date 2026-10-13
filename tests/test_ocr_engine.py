"""Unit tests for the OCR and document extraction engine."""

from app.ocr_engine import (
    extract_tags_from_text,
    process_document,
    simulate_ocr_for_binary,
)


def test_extract_tags_from_text_finance():
    text = "The monthly invoice and payment receipt balance sheet."
    tags = extract_tags_from_text(text)
    assert "finance" in tags


def test_extract_tags_from_text_legal():
    text = "This contract agreement terms and liability clause."
    tags = extract_tags_from_text(text)
    assert "legal" in tags


def test_extract_tags_from_text_technical():
    text = "Deploying Python microservices with Docker, PubSub, and BigQuery database."
    tags = extract_tags_from_text(text)
    assert "technical" in tags


def test_extract_tags_fallback_general():
    text = "A simple sentence without any specific registered domain words."
    tags = extract_tags_from_text(text)
    assert "general" in tags


def test_process_document_plain_text():
    content = b"Hello world! This is a test file for the serverless pipeline architecture."
    result = process_document("sample_doc.txt", content)

    assert result["filename"] == "sample_doc.txt"
    assert result["file_size_bytes"] == len(content)
    assert result["word_count"] == 12
    assert "technical" in result["tags"]
    assert "text-extracted" in result["tags"]
    assert "Hello world!" in result["ocr_preview"]


def test_process_document_simulated_pdf_invoice():
    content = b"%PDF-1.4 mock binary pdf stream bytes"
    result = process_document("invoice_2026_oct.pdf", content)

    assert result["filename"] == "invoice_2026_oct.pdf"
    assert result["file_size_bytes"] == len(content)
    assert result["word_count"] > 10
    assert "finance" in result["tags"]
    assert "invoice" in result["tags"]
    assert "simulated-ocr" in result["tags"]
    assert "[SIMULATED OCR - INVOICE]" in result["ocr_preview"]


def test_process_document_simulated_image():
    content = b"\x89PNG\r\n\x1a\n mock png binary bytes"
    result = process_document("system_architecture_diagram.png", content)

    assert result["filename"] == "system_architecture_diagram.png"
    assert "technical" in result["tags"]
    assert "architecture" in result["tags"]
    assert "simulated-ocr" in result["tags"]
    assert "[SIMULATED OCR - TECH SPEC]" in result["ocr_preview"]


def test_process_document_empty_file():
    result = process_document("empty.txt", b"")
    assert result["filename"] == "empty.txt"
    assert result["word_count"] == 0
    assert result["ocr_preview"] == ""
