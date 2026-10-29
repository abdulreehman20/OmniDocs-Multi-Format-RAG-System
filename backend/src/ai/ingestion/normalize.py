import re

from src.ai.ingestion.contracts import ExtractedDocument, ExtractedUnit

_WS = re.compile(r"[ \t]+")
_BLANK = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WS.sub(" ", text)
    text = _BLANK.sub("\n\n", text)
    return text.strip()


def normalize_extracted(doc: ExtractedDocument) -> ExtractedDocument:
    units = [
        ExtractedUnit(text=normalize_text(u.text), locator=dict(u.locator))
        for u in doc.units
        if normalize_text(u.text)
    ]
    return ExtractedDocument(
        units=units,
        parser_version=doc.parser_version,
        warnings=list(doc.warnings),
        source_metadata=dict(doc.source_metadata),
    )
