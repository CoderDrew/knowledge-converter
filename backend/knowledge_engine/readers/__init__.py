from __future__ import annotations

from knowledge_engine.readers.docx_reader import DocxReader
from knowledge_engine.readers.pptx_reader import PptxReader


READERS = {"docx": DocxReader, "pptx": PptxReader}

__all__ = ["READERS", "DocxReader", "PptxReader"]
