import pytest

from app import build_preview_document, normalize_url


def test_adds_https_scheme_when_missing():
    assert normalize_url("example.com") == "https://example.com"


def test_preserves_existing_scheme():
    assert normalize_url("https://example.com") == "https://example.com"


def test_rejects_invalid_url_without_host():
    with pytest.raises(ValueError):
        normalize_url("https://")


def test_build_preview_document_removes_media_and_scripts():
    html = "<html><head><script>alert('x')</script></head><body><h1>Example</h1><p>Visible text</p><img src='x' /><video controls><source src='v.mp4' /></video></body></html>"
    preview = build_preview_document("https://example.com", html)

    assert "Example" in preview
    assert "Visible text" in preview
    assert "<script" not in preview.lower()
    assert "<img" not in preview.lower()
    assert "<video" not in preview.lower()
