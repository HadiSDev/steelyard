"""Read a fetched document and return the lines it states."""
from __future__ import annotations

import logging

from web_api.connectors.base import DocumentPayload
from web_api.vat import international_vat
from web_api.website import site_root

from ..agents import make_extractor
from ..models import ExtractedInvoice
from ..parsing import json_format_hint, parse_model
from ..pdf_loader import extract_text_from_bytes
from .content import DocumentContent, ExtractedLines
from .errors import EmptyDocumentError, UnsupportedMediaError
from .images import (
    IMAGE_MEDIA_TYPES,
    ImageDecodeError,
    image_from_bytes,
    pdf_page_images,
)
from .numbers import normalize_numbers
from .prompts import SUPPLIER_WEBSITE, TOTALS_BLOCK_CHARGES
from .vision import look_at

logger = logging.getLogger("ai_api.documents")

_PDF_MEDIA_TYPES = {"application/pdf", "application/x-pdf"}


def _media_type(payload: DocumentPayload) -> str:
    return (payload.media_type or "").split(";")[0].strip().lower()


def document_text(payload: DocumentPayload) -> str:
    """The document's text layer."""
    media_type = _media_type(payload)
    if media_type not in _PDF_MEDIA_TYPES:
        raise UnsupportedMediaError(
            f"{payload.filename}: no extractor for media type {media_type or 'unknown'!r}"
        )
    text = extract_text_from_bytes(payload.content)
    if not text.strip():
        raise EmptyDocumentError(
            f"{payload.filename}: the PDF has no extractable text layer "
            "(a scan or photo needs a vision model)"
        )
    return normalize_numbers(text)


def document_content(payload: DocumentPayload) -> DocumentContent:
    """Whatever this document can give a model, by the cheapest route available."""
    media_type = _media_type(payload)

    if media_type in _PDF_MEDIA_TYPES:
        text = extract_text_from_bytes(payload.content)
        if text.strip():
            return DocumentContent(text=normalize_numbers(text))
        pages = pdf_page_images(payload.content)
        if not pages:
            raise EmptyDocumentError(
                f"{payload.filename}: the PDF has no text layer and no pages to render"
            )
        logger.info("%s: no text layer, reading %d page(s) as images",
                    payload.filename, len(pages))
        return DocumentContent(images=tuple(pages))

    if media_type in IMAGE_MEDIA_TYPES:
        try:
            image = image_from_bytes(payload.content)
        except ImageDecodeError as exc:
            raise UnsupportedMediaError(
                f"{payload.filename}: declared {media_type} but the image "
                f"could not be opened ({exc})"
            ) from exc
        return DocumentContent(images=(image,))

    raise UnsupportedMediaError(
        f"{payload.filename}: no extractor for media type {media_type or 'unknown'!r}"
    )


def country_code(value: str | None) -> str | None:
    """A two-letter country code as read, upper-cased, or None when it is not one."""
    code = (value or "").strip().upper()
    if len(code) == 2 and code.isalpha():
        return code
    return None


def extract_lines(payload: DocumentPayload, *, kickoff=None, look=None) -> ExtractedLines:
    """Extract the document's invoice lines, by whichever route it supports."""
    content = document_content(payload)

    if content.text is not None:
        run = kickoff or _kickoff_extractor
        extracted = run(
            "Extract the structured invoice data from the following invoice text. "
            "Leave any missing field null.\n\n"
            + TOTALS_BLOCK_CHARGES
            + "\n\n" + SUPPLIER_WEBSITE
            + "\n\n" + content.text
        )
    else:
        see = look or look_at
        extracted = see(
            "Extract the structured invoice data from the invoice shown in the "
            "following image(s). Leave any missing field null.",
            list(content.images),
        )

    return ExtractedLines(
        lines=list(extracted.line_items),
        currency=extracted.currency,
        invoice_number=(extracted.invoice_number or "").strip() or None,
        supplier_website=site_root(extracted.supplier_website),
        supplier_country_code=country_code(extracted.supplier_country_code),
        supplier_vat_number=international_vat(
            extracted.supplier_vat_number, country_code(extracted.supplier_country_code)
        ),
        total=extracted.total,
        tax=extracted.tax,
        subtotal=extracted.subtotal,
    )


def _kickoff_extractor(prompt: str) -> ExtractedInvoice:
    agent = make_extractor()
    result = agent.kickoff(prompt + "\n\n" + json_format_hint(ExtractedInvoice))
    return parse_model(result.raw, ExtractedInvoice)
