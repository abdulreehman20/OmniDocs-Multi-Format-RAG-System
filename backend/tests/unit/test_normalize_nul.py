from src.ai.ingestion.normalize import normalize_extracted, normalize_text
from src.ai.ingestion.contracts import ExtractedDocument, ExtractedUnit


def test_normalize_text_strips_nul_bytes() -> None:
    # PDF extractors often drop ligature glyphs as NUL (fi → \x00).
    raw = "Vehicle Speci\x00cations\nNo Issues Found"
    cleaned = normalize_text(raw)
    assert "\x00" not in cleaned
    assert cleaned == "Vehicle Specications\nNo Issues Found"


def test_normalize_extracted_strips_nul_in_units() -> None:
    doc = ExtractedDocument(
        units=[
            ExtractedUnit(text="Speci\x00cations page one", locator={"page": 0}),
            ExtractedUnit(text="\x00", locator={"page": 1}),
        ],
        parser_version="test",
        warnings=[],
        source_metadata={},
    )
    out = normalize_extracted(doc)
    assert len(out.units) == 1
    assert out.units[0].text == "Specications page one"
    assert "\x00" not in out.units[0].text
