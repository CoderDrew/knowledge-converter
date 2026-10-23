from pathlib import Path

from knowledge_engine.model import Heading, ListBlock, Paragraph, Section, Table, plain_text
from knowledge_engine.pipeline import read_document
from knowledge_engine.profiles import PROFILES


def slides(path: Path) -> list[Section]:
    return [b for b in read_document(path, path.name).blocks if isinstance(b, Section)]


def test_sample_deck_extracts_title_and_image(sample_pptx: Path):
    document = read_document(sample_pptx, sample_pptx.name)
    assert document.stats.slides == 1
    assert len(document.assets) == 1
    assert document.assets[0].filename == "slide-001-image-01.png"
    assert document.assets[0].slide == 1
    assert plain_text(document.blocks[1].title) == "Cash Management"
    assert document.title == "Cash Management"


def test_slides_become_sections_in_order(rich_pptx: Path):
    document = read_document(rich_pptx, rich_pptx.name)
    assert isinstance(document.blocks[0], Heading) and document.blocks[0].level == 1
    assert plain_text(document.blocks[0].inlines) == "Quarterly Review"
    assert all(isinstance(b, Section) for b in document.blocks[1:])
    titles = [plain_text(b.title) for b in document.blocks[1:]]
    assert titles == ["Quarterly Review", "Agenda", "Free-form Title", "Figures"]
    html = PROFILES["clean"].build(document).html
    assert html.index("Quarterly Review") < html.index("Agenda") < html.index("Figures")
    assert '<section id="slide-2">' in html


def test_body_placeholder_bullets_nest_by_level(rich_pptx: Path):
    agenda = slides(rich_pptx)[1]
    lists = [b for b in agenda.blocks if isinstance(b, ListBlock)]
    assert len(lists) == 1
    assert [plain_text(i.inlines) for i in lists[0].items] == ["Results", "Next steps"]
    assert plain_text(lists[0].items[0].children[0].items[0].inlines) == "Revenue detail"


def test_speaker_notes_are_included(rich_pptx: Path):
    document = read_document(rich_pptx, rich_pptx.name)
    assert plain_text(document.blocks[2].notes[0]) == "Remember to pause for questions."
    assert "Speaker notes" in PROFILES["assets"].build(document).html


def test_textbox_only_slide_uses_prominent_text_as_title_and_visual_order(rich_pptx: Path):
    free = slides(rich_pptx)[2]
    assert plain_text(free.title) == "Free-form Title"
    texts = [plain_text(b.inlines) for b in free.blocks if isinstance(b, Paragraph) and plain_text(b.inlines)]
    assert texts == ["Body copy placed lower on the slide.", "Grouped caption"]
    assert any(isinstance(b, Paragraph) and b.inlines and type(b.inlines[0]).__name__ == "ImageRef" for b in free.blocks)


def test_tables_with_merged_cells(rich_pptx: Path):
    figures = slides(rich_pptx)[3]
    table = next(b for b in figures.blocks if isinstance(b, Table))
    assert table.rows[0].header
    assert table.rows[1].cells[0].colspan == 2 and len(table.rows[1].cells) == 1
    assert plain_text(table.rows[2].cells[1].lines[0]) == "99.9%"
