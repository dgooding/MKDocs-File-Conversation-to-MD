import base64
import re
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from docs_to_markdown import convert_pdf
from docs_to_markdown.api import app
from docs_to_markdown.pdf_converter import _list_match, _table_markdown


def _build_pdf(objects: list[bytes]) -> bytes:
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(output)


def make_fidelity_pdf() -> bytes:
    content = b"\n".join(
        [
            b"BT /F1 20 Tf 72 720 Td (PDF Fidelity Guide) Tj ET",
            b"BT /F1 16 Tf 72 680 Td (Contact) Tj ET",
            b"BT /F1 12 Tf 72 650 Td (<test@example.com>) Tj ET",
            b"BT /F1 12 Tf 72 620 Td (Reference Guide) Tj ET",
            b"q 40 0 0 40 72 570 cm /Im1 Do Q",
            b"q 40 0 0 40 140 570 cm /Im1 Do Q",
            b"0.5 w 72 500 m 300 500 l S 72 480 m 300 480 l S 72 460 m 300 460 l S",
            b"72 460 m 72 500 l S 180 460 m 180 500 l S 300 460 m 300 500 l S",
            b"BT /F1 12 Tf 78 486 Td (Name) Tj 108 0 Td (Status) Tj ET",
            b"BT /F1 12 Tf 78 466 Td (Native PDF) Tj 102 0 Td (Working) Tj ET",
        ]
    )
    pixels = bytes([220, 30, 30, 30, 120, 220, 30, 180, 80, 240, 200, 40])
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> /XObject << /Im1 6 0 R >> >> "
        b"/Contents 5 0 R /Annots [7 0 R 8 0 R] >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 /ColorSpace /DeviceRGB "
        b"/BitsPerComponent 8 /Length " + str(len(pixels)).encode("ascii") + b" >>\nstream\n" + pixels + b"\nendstream",
        b"<< /Type /Annot /Subtype /Link /Rect [72 640 300 660] "
        b"/A << /S /URI /URI (mailto:test@example.com) >> >>",
        b"<< /Type /Annot /Subtype /Link /Rect [72 610 180 630] "
        b"/A << /S /URI /URI (https://example.com/guide) >> >>",
    ]
    return _build_pdf(objects)


def test_preserves_native_pdf_structure() -> None:
    markdown = convert_pdf(make_fidelity_pdf())

    assert "# PDF Fidelity Guide" in markdown
    assert "## Contact" in markdown
    assert "[test@example.com](mailto:test@example.com)" in markdown
    assert "[Reference Guide](https://example.com/guide)" in markdown
    assert markdown.count("data:image/png;base64,") == 1
    assert "| Name | Status |" in markdown
    assert "| Native PDF | Working |" in markdown

    encoded = re.search(r"data:image/png;base64,([^)]+)", markdown)
    assert encoded is not None
    with Image.open(BytesIO(base64.b64decode(encoded.group(1)))) as image:
        assert image.size == (53, 53)


def test_normalizes_sparse_and_single_column_tables() -> None:
    sparse = _table_markdown(
        [
            [None, "Section", None, None, None, None],
            [None, "Customer Type", None, None, "Requirement", None],
            ["Campus", None, None, "Specific title", None, None],
        ]
    )
    callout = _table_markdown([["First warning line"], ["Second warning line"]])

    assert "**Section**" in sparse
    assert "| Customer Type | Requirement |" in sparse
    assert "| Campus | Specific title |" in sparse
    assert callout == "> First warning line\n>\n> Second warning line"
    assert _table_markdown([["Mitchell", "ClaimPro"]]) == "|  |  |\n| --- | --- |\n| Mitchell | ClaimPro |"


def test_recognizes_pdf_bullet_glyphs() -> None:
    assert _list_match("\uf0b7 Private font bullet", 90, 72) == ("*", "Private font bullet")
    assert _list_match("□ Square bullet", 90, 72) == ("*", "Square bullet")
    assert _list_match("o Nested bullet", 90, 72) == ("*", "Nested bullet")


def test_fidelity_pdf_api_matches_direct_conversion() -> None:
    pdf = make_fidelity_pdf()
    response = TestClient(app).post(
        "/api/convert",
        files={"file": ("fidelity.pdf", pdf, "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["markdown"] == convert_pdf(pdf)