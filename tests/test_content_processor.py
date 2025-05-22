import pytest

pytest.importorskip("app.processors.content", reason="ContentProcessor module is not yet implemented")

from app.processors.content import ContentProcessor


SAMPLE_MD = """# Title\n\n## Chapter 1\nfoo\n\n### Section 1.1\nbar\n\n## Chapter 2\n### Section 2.1\nbaz\n"""


def test_split_chapters():
    cp = ContentProcessor()
    chapters = cp.split_chapters(SAMPLE_MD)
    assert len(chapters) == 2


def test_split_sections():
    cp = ContentProcessor()
    chapters = cp.split_chapters(SAMPLE_MD)
    sections = cp.split_sections(chapters[0])
    assert sections, "sections should not be empty"


def test_analyze_structure_returns_dict(monkeypatch):
    cp = ContentProcessor()

    monkeypatch.setattr(cp, "_call_structure_api", lambda *args, **kwargs: {"ok": True}, raising=False)

    structure = cp.analyze_structure("Some section text")
    assert isinstance(structure, dict) 