import re

from src.ai.ingestion.contracts import ExtractedDocument, ExtractedUnit

_WS = re.compile(r"[ \t]+")
_BLANK = re.compile(r"\n{3,}")
# PDF extractors often emit NUL (e.g. broken ligatures: "Speci\x00cations").
# Postgres text/varchar reject 0x00.
_NUL = re.compile(r"\x00+")


def normalize_text(text: str) -> str:
    text = _NUL.sub("", text)
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
