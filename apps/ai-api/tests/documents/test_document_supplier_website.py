"""The supplier's website as its invoice prints it: read on either path, reduced to the site, kept on the invoice."""
from __future__ import annotations

import io
import json

from reportlab.pdfgen import canvas

from ai_api.documents.extractor import extract_lines
from ai_api.documents.images import DocumentImage
from ai_api.documents.vision import build_messages, look_at
from ai_api.models import ExtractedInvoice, LineItem
from web_api.connectors.base import DocumentPayload


def _pdf(lines: list[str]) -> DocumentPayload:
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer)
    for row, text in enumerate(lines):
        page.drawString(100, 750 - 20 * row, text)
    page.save()
    return DocumentPayload(content=buffer.getvalue(), media_type="application/pdf",
                           filename="invoice.pdf")


def _image(n: int) -> DocumentImage:
    return DocumentImage(media_type="image/png", content=f"page-{n}".encode())


def _replies(*bodies):
    queue = [json.dumps(body) for body in bodies]

    def complete(messages):
        return queue.pop(0)

    return complete


def test_the_vision_prompt_asks_for_the_suppliers_own_website():
    text = build_messages(_image(1))[0]["content"][0]["text"]

    assert "supplier's own website" in text
    assert "supplier_website" in text


def test_the_first_page_that_prints_a_website_states_it():
    merged = look_at("", [_image(1), _image(2)], complete=_replies(
        {"vendor_name": "Dansk Kaffe ApS", "line_items": []},
        {"supplier_website": "www.danskkaffe.dk", "line_items": []},
    ))

    assert merged.supplier_website == "www.danskkaffe.dk"


def test_the_text_path_reduces_the_website_to_its_site():
    seen: list[str] = []

    def kickoff(prompt: str) -> ExtractedInvoice:
        seen.append(prompt)
        return ExtractedInvoice(
            vendor_name="Dansk Kaffe ApS", supplier_website="DanskKaffe.dk/kontakt",
            line_items=[LineItem(description="Beans", amount=100.0)],
        )

    result = extract_lines(_pdf(["INVOICE", "Beans 100"]), kickoff=kickoff)

    assert result.supplier_website == "https://danskkaffe.dk/"
    assert "supplier's own website" in seen[0]


def test_an_email_address_is_not_a_website():
    def kickoff(prompt: str) -> ExtractedInvoice:
        return ExtractedInvoice(vendor_name="Dansk Kaffe ApS", supplier_website="info@danskkaffe.dk")

    result = extract_lines(_pdf(["INVOICE"]), kickoff=kickoff)

    assert result.supplier_website is None
