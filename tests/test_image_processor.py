import pytest

pytest.importorskip("app.processors.image", reason="ImageProcessor module is not yet implemented")

from app.processors.image import ImageProcessor


SAMPLE_SVG = """<svg xmlns=\"http://www.w3.org/2000/svg\"><rect width=\"10\" height=\"10\"/></svg>"""
SAMPLE_DRAWIO = """<mxGraphModel><root><mxCell id="0"/></root></mxGraphModel>"""
SAMPLE_MERMAID = """graph TD; A-->B;"""


def test_extract_images(monkeypatch):
    ip = ImageProcessor()
    monkeypatch.setattr(ip, "_regex_extract", lambda *args, **kwargs: [SAMPLE_SVG], raising=False)
    images = ip.extract_images("<img src='foo.svg'/>")
    assert images


def test_process_svg_returns_bytes(monkeypatch):
    ip = ImageProcessor()
    monkeypatch.setattr(ip, "_svg_to_png", lambda svg: b"pngbytes", raising=False)
    data = ip.process_svg(SAMPLE_SVG)
    assert isinstance(data, bytes)


def test_process_drawio_returns_bytes(monkeypatch):
    ip = ImageProcessor()
    monkeypatch.setattr(ip, "_drawio_to_png", lambda xml: b"drawio_png_bytes", raising=False)
    data = ip.process_drawio(SAMPLE_DRAWIO)
    assert isinstance(data, bytes)


def test_process_mermaid_returns_bytes(monkeypatch):
    ip = ImageProcessor()
    monkeypatch.setattr(ip, "_mermaid_to_png", lambda mermaid: b"mermaid_png_bytes", raising=False)
    data = ip.process_mermaid(SAMPLE_MERMAID)
    assert isinstance(data, bytes)


def test_upload_to_s3(monkeypatch):
    ip = ImageProcessor()
    monkeypatch.setattr(ip, "_s3_upload", lambda data, key: "https://s3.example.com/img.png", raising=False)
    url = ip.upload_to_s3(b"data", "images/img.png")
    assert isinstance(url, str)
    assert "http" in url


def test_replace_image_links():
    ip = ImageProcessor()
    content = "Here is an image ![img](foo.svg)"
    new = ip.replace_image_links(content, {"foo.svg": "https://cdn.example.com/foo.png"})
    assert "https://cdn.example.com/foo.png" in new 