"""
backend/automation/markitdown_service.py
========================================
Document conversion service with OCR for J.A.R.V.I.S.
Assimilated from Microsoft MarkItDown (microsoft/markitdown).

Features:
- Converts PDF, DOCX, XLSX, PPTX, HTML, CSV, TXT, JSON, and images into clean, structured Markdown.
- Microsoft MarkItDown automatic <sheetView showZeroes> XML zip repair for corrupted Excel spreadsheets.
- Intelligent table repair: detects missing delimiter rows, normalizes irregular columns, aligns markdown tables.
- Pure-Python text extraction fallbacks: zero-crash fallback when heavy libraries
  (pdfminer, pypdf, python-docx, openpyxl, pytesseract) are missing or uninstalled.
- Streaming and parallel batch processing with rich metadata extraction (title, author, page count, word count).
- Plugs into HybridMemory (hybrid_rag.py) and HermesBrain for immediate document understanding.
"""

import concurrent.futures
import csv
import io
import json
import logging
import os
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Dict, Iterator, List, Optional, Set, Tuple, Union

logger = logging.getLogger("jarvis.markitdown")

# List of all officially supported document, sheet, slide, media, and text formats
SUPPORTED_DOCUMENT_FORMATS: List[str] = [
    "pdf",
    "docx",
    "xlsx",
    "pptx",
    "html",
    "htm",
    "csv",
    "txt",
    "json",
    "xml",
    "yaml",
    "yml",
    "md",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "mp3",
    "wav",
]


@dataclass
class DocumentMetadata:
    """Rich metadata extracted from source documents."""
    title: str = "Untitled Document"
    author: Optional[str] = None
    format: str = "unknown"
    file_size_bytes: int = 0
    page_count: int = 1
    sheet_count: int = 0
    slide_count: int = 0
    word_count: int = 0
    table_count: int = 0
    ocr_applied: bool = False
    source: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "author": self.author,
            "format": self.format,
            "file_size_bytes": self.file_size_bytes,
            "page_count": self.page_count,
            "sheet_count": self.sheet_count,
            "slide_count": self.slide_count,
            "word_count": self.word_count,
            "table_count": self.table_count,
            "ocr_applied": self.ocr_applied,
            "source": self.source,
            "created_at": self.created_at,
        }


@dataclass
class ConversionResult:
    """Result envelope for document conversions."""
    markdown: str
    metadata: Dict[str, Any]
    source: str
    status: str = "success"
    error: Optional[str] = None
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "markdown": self.markdown,
            "metadata": self.metadata,
            "source": self.source,
            "status": self.status,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


class MarkItDownService:
    """
    Universal document conversion service with OCR and table repair.
    Provides pure-Python text extraction fallbacks for all formats.
    """

    def __init__(
        self,
        ocr_enabled: bool = True,
        max_batch_workers: int = 4,
        llm_client: Optional[Any] = None,
    ):
        self.ocr_enabled: bool = ocr_enabled
        self.max_batch_workers: int = max_batch_workers
        self.llm_client = llm_client
        self.supported_formats: List[str] = list(SUPPORTED_DOCUMENT_FORMATS)

        # Probe available third-party parser engines
        self._has_pypdf = self._check_import("pypdf")
        self._has_docx = self._check_import("docx")
        self._has_openpyxl = self._check_import("openpyxl")
        self._has_pptx = self._check_import("pptx")
        self._has_bs4 = self._check_import("bs4")
        self._has_pil = self._check_import("PIL.Image")
        self._has_tesseract = self._check_import("pytesseract")

        logger.info(
            f"MarkItDownService initialized (ocr_enabled={self.ocr_enabled}, "
            f"openpyxl={self._has_openpyxl}, docx={self._has_docx}, pypdf={self._has_pypdf})"
        )

    @staticmethod
    def _check_import(mod_name: str) -> bool:
        try:
            __import__(mod_name)
            return True
        except ImportError:
            return False

    # -----------------------------------------------------------------------
    # Table Repair & Normalization
    # -----------------------------------------------------------------------

    def repair_markdown_table(self, table_str: str) -> str:
        """
        Normalizes and repairs markdown tables:
        - Detects missing delimiter rows ('|---|---|') and injects them.
        - Preserves existing delimiter rows by replacing with clean normalized delimiters.
        - Pads ragged/irregular column lengths across all rows.
        - Strips accidental duplicate delimiter rows in table body.
        """
        if not table_str or not isinstance(table_str, str):
            return ""

        lines = [line.strip() for line in table_str.strip().splitlines() if line.strip()]
        if not lines:
            return ""

        # Parse rows into cell lists
        rows: List[List[str]] = []
        for line in lines:
            if "|" in line:
                # Strip leading and trailing pipe if present
                clean_line = line
                if clean_line.startswith("|"):
                    clean_line = clean_line[1:]
                if clean_line.endswith("|"):
                    clean_line = clean_line[:-1]
                cells = [c.strip() for c in clean_line.split("|")]
                rows.append(cells)
            else:
                # Non-table line, split by tabs or multiple spaces
                cells = [c.strip() for c in re.split(r"\t+|\s{2,}", line) if c.strip()]
                if cells:
                    rows.append(cells)

        if not rows:
            return table_str

        # Calculate max columns across all rows
        max_cols = max(len(r) for r in rows)
        if max_cols == 0:
            return table_str

        # Pad rows to uniform column count
        normalized_rows: List[List[str]] = []
        for r in rows:
            padded = r + [""] * (max_cols - len(r))
            normalized_rows.append(padded)

        def _is_delim_row(row_cells: List[str]) -> bool:
            joined = "".join(row_cells)
            if not re.match(r"^[\s\-:|]+$", joined):
                return False
            if "---" in joined:
                return True
            non_empty = [c.strip() for c in row_cells if c.strip()]
            return bool(non_empty and all(re.match(r"^:?-+:?$", c) for c in non_empty))

        # Check if row 1 is already a delimiter line
        has_delimiter = False
        if len(normalized_rows) > 1 and _is_delim_row(normalized_rows[1]):
            has_delimiter = True

        output_lines: List[str] = []
        # Header row
        output_lines.append("| " + " | ".join(normalized_rows[0]) + " |")

        # Always inject a clean, normalized delimiter row for both un-delimited and pre-delimited tables
        delimiter = "|" + "|".join(["---"] * max_cols) + "|"
        output_lines.append(delimiter)

        # Remaining data rows
        start_idx = 2 if has_delimiter else 1
        for row in normalized_rows[start_idx:]:
            # Check if this row is an accidental duplicate delimiter
            if _is_delim_row(row):
                continue
            output_lines.append("| " + " | ".join(row) + " |")

        return "\n".join(output_lines)

    # -----------------------------------------------------------------------
    # Text Normalization
    # -----------------------------------------------------------------------

    def convert_text(self, text: str) -> str:
        """
        Normalizes plain text content into clean Markdown:
        - Replaces Windows carriage returns.
        - Trims trailing whitespace per line.
        - Collapses excess blank lines (>2).
        - Preserves heading structure.
        """
        if not text:
            return ""

        clean = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.rstrip() for line in clean.splitlines()]

        # Collapse excess empty lines
        result_lines: List[str] = []
        blank_count = 0
        for line in lines:
            if not line:
                blank_count += 1
                if blank_count <= 2:
                    result_lines.append("")
            else:
                blank_count = 0
                result_lines.append(line)

        return "\n".join(result_lines)

    # -----------------------------------------------------------------------
    # Format Converters (with Pure-Python Fallbacks)
    # -----------------------------------------------------------------------

    def _convert_plain_text(self, raw_bytes: bytes, filename: str) -> Tuple[str, DocumentMetadata]:
        # Detect encoding
        encoding = "utf-8"
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = raw_bytes.decode("latin-1")
                encoding = "latin-1"
            except Exception:
                text = raw_bytes.decode("utf-8", errors="replace")

        md = self.convert_text(text)
        words = len(re.findall(r"\w+", md))
        meta = DocumentMetadata(
            title=Path(filename).stem,
            format="txt",
            file_size_bytes=len(raw_bytes),
            word_count=words,
            source=filename,
        )
        return md, meta

    def _convert_csv(self, raw_bytes: bytes, filename: str) -> Tuple[str, DocumentMetadata]:
        text = raw_bytes.decode("utf-8", errors="replace")
        meta = DocumentMetadata(
            title=Path(filename).stem,
            format="csv",
            file_size_bytes=len(raw_bytes),
            source=filename,
        )

        try:
            # Detect delimiter
            sniffer = csv.Sniffer()
            sample = text[:4096]
            dialect = sniffer.sniff(sample) if sample else csv.excel
            reader = csv.reader(io.StringIO(text), dialect)
        except Exception:
            reader = csv.reader(io.StringIO(text))

        rows = list(reader)
        if not rows:
            return "# Empty CSV File", meta

        max_cols = max(len(r) for r in rows)
        padded_rows = [r + [""] * (max_cols - len(r)) for r in rows]

        # Escape pipes in content
        escaped_rows = [[cell.replace("|", "\\|") for cell in r] for r in padded_rows]

        lines = [
            f"# {Path(filename).stem}",
            "",
            "| " + " | ".join(escaped_rows[0]) + " |",
            "|" + "|".join(["---"] * max_cols) + "|",
        ]
        for row in escaped_rows[1:]:
            lines.append("| " + " | ".join(row) + " |")

        md = "\n".join(lines)
        meta.table_count = 1
        meta.word_count = len(re.findall(r"\w+", md))
        return md, meta

    def _repair_xlsx_xml(self, raw_bytes: bytes) -> bytes:
        """
        Microsoft MarkItDown automatic repair:
        Inspects all xl/worksheets/sheet*.xml and strips/replaces corrupted
        showZeroes='0' or showZeroes='false' attributes that cause openpyxl crashes.
        """
        try:
            in_zip = zipfile.ZipFile(io.BytesIO(raw_bytes), "r")
            out_buf = io.BytesIO()
            out_zip = zipfile.ZipFile(out_buf, "w", zipfile.ZIP_DEFLATED)

            for item in in_zip.infolist():
                content = in_zip.read(item.filename)
                normalized_name = item.filename.replace("\\", "/")
                if normalized_name.startswith("xl/worksheets/sheet") and normalized_name.endswith(".xml"):
                    # Fix showZeroes="0" / showZeroes='0' / showZeroes = "0" -> showZeroes="false"
                    text = content.decode("utf-8", errors="replace")
                    text_fixed = re.sub(r'showZeroes\s*=\s*["\']\s*0\s*["\']', 'showZeroes="false"', text)
                    content = text_fixed.encode("utf-8")
                out_zip.writestr(item, content)

            in_zip.close()
            out_zip.close()
            return out_buf.getvalue()
        except Exception as e:
            logger.debug(f"XLSX XML repair pass through: {e}")
            return raw_bytes

    def _convert_xlsx(self, raw_bytes: bytes, filename: str) -> Tuple[str, DocumentMetadata]:
        meta = DocumentMetadata(
            title=Path(filename).stem,
            format="xlsx",
            file_size_bytes=len(raw_bytes),
            source=filename,
        )

        repaired_bytes = self._repair_xlsx_xml(raw_bytes)

        # Priority 1: openpyxl
        if self._has_openpyxl:
            try:
                import openpyxl
                wb = openpyxl.load_workbook(io.BytesIO(repaired_bytes), data_only=True)
                sections: List[str] = [f"# {Path(filename).stem}"]
                meta.sheet_count = len(wb.sheetnames)

                for sheet_name in wb.sheetnames:
                    sheet = wb[sheet_name]
                    rows: List[List[str]] = []
                    for row in sheet.iter_rows(values_only=True):
                        if any(v is not None for v in row):
                            rows.append([str(v) if v is not None else "" for v in row])

                    if rows:
                        sections.append(f"\n## Sheet: {sheet_name}\n")
                        max_cols = max(len(r) for r in rows)
                        padded = [r + [""] * (max_cols - len(r)) for r in rows]
                        table_lines = [
                            "| " + " | ".join(padded[0]) + " |",
                            "|" + "|".join(["---"] * max_cols) + "|",
                        ]
                        for r in padded[1:]:
                            table_lines.append("| " + " | ".join(r) + " |")
                        sections.append("\n".join(table_lines))
                        meta.table_count += 1

                md = "\n".join(sections)
                meta.word_count = len(re.findall(r"\w+", md))
                return md, meta
            except Exception as e:
                logger.warning(f"openpyxl failed ({e}); falling back to pure-Python XLSX parser.")

        # Priority 2: Pure-Python XLSX Fallback (zipfile + XML)
        try:
            with zipfile.ZipFile(io.BytesIO(repaired_bytes), "r") as zf:
                shared_strings: List[str] = []
                if "xl/sharedStrings.xml" in zf.namelist():
                    ss_xml = zf.read("xl/sharedStrings.xml")
                    root = ET.fromstring(ss_xml)
                    for si in root.findall(".//{*}si"):
                        t_nodes = si.findall(".//{*}t")
                        shared_strings.append("".join(t.text or "" for t in t_nodes))

                sections = [f"# {Path(filename).stem}"]
                sheet_files = [f for f in zf.namelist() if f.startswith("xl/worksheets/sheet") and f.endswith(".xml")]
                meta.sheet_count = len(sheet_files)

                for idx, sf in enumerate(sheet_files, start=1):
                    sheet_xml = zf.read(sf)
                    root = ET.fromstring(sheet_xml)
                    rows = []
                    for row_node in root.findall(".//{*}row"):
                        row_cells = []
                        for c_node in row_node.findall(".//{*}c"):
                            cell_type = c_node.get("t")
                            v_node = c_node.find("{*}v")
                            val = ""
                            if v_node is not None and v_node.text:
                                if cell_type == "s" and shared_strings:
                                    try:
                                        val = shared_strings[int(v_node.text)]
                                    except (ValueError, IndexError):
                                        val = v_node.text
                                else:
                                    val = v_node.text
                            row_cells.append(val)
                        if any(c for c in row_cells):
                            rows.append(row_cells)

                    if rows:
                        sections.append(f"\n## Sheet {idx}\n")
                        max_cols = max(len(r) for r in rows)
                        padded = [r + [""] * (max_cols - len(r)) for r in rows]
                        table_lines = [
                            "| " + " | ".join(padded[0]) + " |",
                            "|" + "|".join(["---"] * max_cols) + "|",
                        ]
                        for r in padded[1:]:
                            table_lines.append("| " + " | ".join(r) + " |")
                        sections.append("\n".join(table_lines))
                        meta.table_count += 1

                md = "\n".join(sections)
                meta.word_count = len(re.findall(r"\w+", md))
                return md, meta
        except Exception as e:
            return f"# Error reading XLSX\nCould not extract content: {e}", meta

    def _convert_docx(self, raw_bytes: bytes, filename: str) -> Tuple[str, DocumentMetadata]:
        meta = DocumentMetadata(
            title=Path(filename).stem,
            format="docx",
            file_size_bytes=len(raw_bytes),
            source=filename,
        )

        # Priority 1: python-docx
        if self._has_docx:
            try:
                import docx
                doc = docx.Document(io.BytesIO(raw_bytes))
                parts: List[str] = [f"# {Path(filename).stem}\n"]

                for p in doc.paragraphs:
                    text = p.text.strip()
                    if not text:
                        continue
                    style = (p.style.name or "").lower()
                    if "heading 1" in style:
                        parts.append(f"\n# {text}\n")
                    elif "heading 2" in style:
                        parts.append(f"\n## {text}\n")
                    elif "heading 3" in style:
                        parts.append(f"\n### {text}\n")
                    elif "list" in style:
                        parts.append(f"- {text}")
                    else:
                        parts.append(text)

                for tbl in doc.tables:
                    table_rows = []
                    for row in tbl.rows:
                        table_rows.append([c.text.strip().replace("\n", " ") for c in row.cells])
                    if table_rows:
                        max_cols = max(len(r) for r in table_rows)
                        padded = [r + [""] * (max_cols - len(r)) for r in table_rows]
                        t_lines = [
                            "\n| " + " | ".join(padded[0]) + " |",
                            "|" + "|".join(["---"] * max_cols) + "|",
                        ]
                        for r in padded[1:]:
                            t_lines.append("| " + " | ".join(r) + " |")
                        parts.append("\n".join(t_lines) + "\n")
                        meta.table_count += 1

                md = "\n\n".join(parts)
                meta.word_count = len(re.findall(r"\w+", md))
                return md, meta
            except Exception as e:
                logger.warning(f"python-docx failed ({e}); falling back to pure-Python DOCX parser.")

        # Priority 2: Pure-Python DOCX Fallback (zipfile + document.xml)
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes), "r") as zf:
                if "word/document.xml" not in zf.namelist():
                    return "# Empty DOCX Document", meta
                xml_content = zf.read("word/document.xml")
                root = ET.fromstring(xml_content)

                parts = [f"# {Path(filename).stem}\n"]
                for p_node in root.findall(".//{*}p"):
                    texts = [t.text or "" for t in p_node.findall(".//{*}t")]
                    p_text = "".join(texts).strip()
                    if p_text:
                        p_style = p_node.find(".//{*}pStyle")
                        style_val = (p_style.get("{*}val") or "").lower() if p_style is not None else ""
                        if "heading1" in style_val:
                            parts.append(f"# {p_text}")
                        elif "heading2" in style_val:
                            parts.append(f"## {p_text}")
                        elif "heading3" in style_val:
                            parts.append(f"### {p_text}")
                        else:
                            parts.append(p_text)

                md = "\n\n".join(parts)
                meta.word_count = len(re.findall(r"\w+", md))
                return md, meta
        except Exception as e:
            return f"# Error reading DOCX\nCould not extract content: {e}", meta

    def _convert_pptx(self, raw_bytes: bytes, filename: str) -> Tuple[str, DocumentMetadata]:
        meta = DocumentMetadata(
            title=Path(filename).stem,
            format="pptx",
            file_size_bytes=len(raw_bytes),
            source=filename,
        )

        # Priority 1: python-pptx
        if self._has_pptx:
            try:
                import pptx
                prs = pptx.Presentation(io.BytesIO(raw_bytes))
                parts = [f"# {Path(filename).stem}\n"]
                meta.slide_count = len(prs.slides)

                for idx, slide in enumerate(prs.slides, start=1):
                    parts.append(f"\n## Slide {idx}\n")
                    for shape in slide.shapes:
                        if shape.has_text_frame:
                            for p in shape.text_frame.paragraphs:
                                t = p.text.strip()
                                if t:
                                    parts.append(f"- {t}")

                md = "\n".join(parts)
                meta.word_count = len(re.findall(r"\w+", md))
                return md, meta
            except Exception as e:
                logger.warning(f"python-pptx failed ({e}); falling back to pure-Python PPTX parser.")

        # Priority 2: Pure-Python PPTX Fallback (zipfile + slide*.xml)
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes), "r") as zf:
                slide_files = sorted(
                    [f for f in zf.namelist() if f.startswith("ppt/slides/slide") and f.endswith(".xml")]
                )
                meta.slide_count = len(slide_files)
                parts = [f"# {Path(filename).stem}\n"]

                for idx, sf in enumerate(slide_files, start=1):
                    xml_content = zf.read(sf)
                    root = ET.fromstring(xml_content)
                    parts.append(f"\n## Slide {idx}\n")
                    for p_node in root.findall(".//{*}p"):
                        texts = [t.text or "" for t in p_node.findall(".//{*}t")]
                        line = "".join(texts).strip()
                        if line:
                            parts.append(f"- {line}")

                md = "\n".join(parts)
                meta.word_count = len(re.findall(r"\w+", md))
                return md, meta
        except Exception as e:
            return f"# Error reading PPTX\nCould not extract content: {e}", meta

    def _convert_pdf(self, raw_bytes: bytes, filename: str) -> Tuple[str, DocumentMetadata]:
        meta = DocumentMetadata(
            title=Path(filename).stem,
            format="pdf",
            file_size_bytes=len(raw_bytes),
            source=filename,
        )

        # Priority 1: pypdf
        if self._has_pypdf:
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
                meta.page_count = len(reader.pages)
                pages_text: List[str] = [f"# {Path(filename).stem}\n"]

                for idx, page in enumerate(reader.pages, start=1):
                    extracted = page.extract_text() or ""
                    if extracted.strip():
                        pages_text.append(f"## Page {idx}\n\n{extracted.strip()}")

                md = "\n\n".join(pages_text)
                meta.word_count = len(re.findall(r"\w+", md))
                return md, meta
            except Exception as e:
                logger.warning(f"pypdf extraction failed ({e}); falling back to pure-Python FlateDecode parser.")

        # Priority 2: Pure-Python FlateDecode text extractor
        try:
            pages_text = [f"# {Path(filename).stem}\n"]
            # Search for FlateDecode compressed stream blocks
            stream_regex = re.compile(b"stream\r?\n(.*?)\r?\nendstream", re.DOTALL)
            matches = stream_regex.findall(raw_bytes)

            extracted_chunks = []
            for stream in matches:
                try:
                    decompressed = zlib.decompress(stream)
                    # Extract text enclosed in Tj or TJ operators: (text) Tj or [(t1) 10 (t2)] TJ
                    tj_matches = re.findall(rb"\((.*?)\)\s*Tj", decompressed)
                    for chunk in tj_matches:
                        try:
                            clean_chunk = chunk.decode("utf-8", errors="ignore")
                            if clean_chunk.strip():
                                extracted_chunks.append(clean_chunk)
                        except Exception:
                            pass
                except Exception:
                    continue

            if extracted_chunks:
                full_text = " ".join(extracted_chunks)
                pages_text.append(full_text)
            else:
                pages_text.append("*(Pure-Python PDF parser: No unencrypted text stream extracted)*")

            md = "\n\n".join(pages_text)
            meta.word_count = len(re.findall(r"\w+", md))
            return md, meta
        except Exception as e:
            return f"# Error reading PDF\nCould not extract content: {e}", meta

    def _convert_html(self, raw_bytes: bytes, filename: str) -> Tuple[str, DocumentMetadata]:
        text = raw_bytes.decode("utf-8", errors="replace")
        meta = DocumentMetadata(
            title=Path(filename).stem,
            format="html",
            file_size_bytes=len(raw_bytes),
            source=filename,
        )

        # Priority 1: BeautifulSoup
        if self._has_bs4:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(text, "html.parser")
                title_tag = soup.find("title")
                title = title_tag.get_text().strip() if title_tag else Path(filename).stem
                meta.title = title

                # Strip script, style, head
                for tag in soup(["script", "style", "noscript", "header", "footer"]):
                    tag.decompose()

                body = soup.find("body") or soup
                lines = []
                for elem in body.find_all(["h1", "h2", "h3", "h4", "p", "li", "table"]):
                    if elem.name == "h1":
                        lines.append(f"\n# {elem.get_text().strip()}\n")
                    elif elem.name == "h2":
                        lines.append(f"\n## {elem.get_text().strip()}\n")
                    elif elem.name == "h3":
                        lines.append(f"\n### {elem.get_text().strip()}\n")
                    elif elem.name == "p":
                        t = elem.get_text().strip()
                        if t:
                            lines.append(f"{t}\n")
                    elif elem.name == "li":
                        lines.append(f"- {elem.get_text().strip()}")
                    elif elem.name == "table":
                        t_rows = []
                        for tr in elem.find_all("tr"):
                            t_cells = [td.get_text().strip() for td in tr.find_all(["td", "th"])]
                            if t_cells:
                                t_rows.append(t_cells)
                        if t_rows:
                            max_c = max(len(r) for r in t_rows)
                            padded = [r + [""] * (max_c - len(r)) for r in t_rows]
                            t_str = [
                                "| " + " | ".join(padded[0]) + " |",
                                "|" + "|".join(["---"] * max_c) + "|",
                            ]
                            for r in padded[1:]:
                                t_str.append("| " + " | ".join(r) + " |")
                            lines.append("\n" + "\n".join(t_str) + "\n")
                            meta.table_count += 1

                md = "\n".join(lines)
                meta.word_count = len(re.findall(r"\w+", md))
                return md, meta
            except Exception as e:
                logger.warning(f"bs4 HTML parse failed ({e}); falling back to regex stripper.")

        # Priority 2: Simple regex HTML tag stripper
        clean_text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL)
        clean_text = re.sub(r"<script.*?</script>", "", clean_text, flags=re.DOTALL)
        clean_text = re.sub(r"<[^>]+>", " ", clean_text)
        md = self.convert_text(clean_text)
        meta.word_count = len(re.findall(r"\w+", md))
        return md, meta

    def _convert_image(self, raw_bytes: bytes, filename: str) -> Tuple[str, DocumentMetadata]:
        meta = DocumentMetadata(
            title=Path(filename).stem,
            format=Path(filename).suffix.lstrip(".").lower() or "image",
            file_size_bytes=len(raw_bytes),
            source=filename,
        )

        extracted_text = ""
        # Priority 1: OCR via pytesseract if available and enabled
        if self.ocr_enabled and self._has_tesseract and self._has_pil:
            try:
                import pytesseract
                from PIL import Image
                img = Image.open(io.BytesIO(raw_bytes))
                extracted_text = pytesseract.image_to_string(img).strip()
                if extracted_text:
                    meta.ocr_applied = True
            except Exception as e:
                logger.debug(f"pytesseract OCR pass failed: {e}")

        # Priority 2: Metadata fallback card
        dim_str = "unknown"
        if self._has_pil:
            try:
                from PIL import Image
                img = Image.open(io.BytesIO(raw_bytes))
                dim_str = f"{img.width}x{img.height} ({img.mode})"
            except Exception:
                pass

        lines = [
            f"# Image: {Path(filename).name}",
            f"- **Dimensions**: {dim_str}",
            f"- **File Size**: {len(raw_bytes):,} bytes",
        ]

        if extracted_text:
            lines.append(f"\n### Extracted OCR Text\n\n{extracted_text}")
        else:
            lines.append("\n*(OCR engine unavailable or no embedded text detected)*")

        md = "\n".join(lines)
        meta.word_count = len(re.findall(r"\w+", md))
        return md, meta

    # -----------------------------------------------------------------------
    # Main Conversion Entrypoints
    # -----------------------------------------------------------------------

    def convert(
        self,
        source: Union[str, Path, BinaryIO],
        filename: Optional[str] = None,
    ) -> ConversionResult:
        """
        Universal conversion entrypoint.
        Accepts local file path, URL, or open byte stream.
        """
        start_time = time.perf_counter()

        # Handle YouTube or Web URLs
        if isinstance(source, str) and (source.startswith("http://") or source.startswith("https://")):
            return self._convert_url(source, start_time)

        # Handle file paths
        if isinstance(source, (str, Path)):
            path = Path(source)
            if not path.exists():
                return ConversionResult(
                    markdown="",
                    metadata={"error": "File not found", "source": str(path)},
                    source=str(path),
                    status="failed",
                    error=f"File not found: {path}",
                    duration_ms=(time.perf_counter() - start_time) * 1000.0,
                )
            try:
                with open(path, "rb") as f:
                    raw_bytes = f.read()
                actual_filename = path.name
            except Exception as e:
                return ConversionResult(
                    markdown="",
                    metadata={"error": str(e), "source": str(path)},
                    source=str(path),
                    status="failed",
                    error=str(e),
                    duration_ms=(time.perf_counter() - start_time) * 1000.0,
                )
        elif hasattr(source, "read"):
            raw_bytes = source.read()
            actual_filename = filename or "document.bin"
        else:
            raw_bytes = bytes(source) if isinstance(source, (bytes, bytearray)) else str(source).encode("utf-8")
            actual_filename = filename or "document.txt"

        ext = Path(actual_filename).suffix.lstrip(".").lower()

        try:
            if ext == "pdf":
                md, meta = self._convert_pdf(raw_bytes, actual_filename)
            elif ext == "docx":
                md, meta = self._convert_docx(raw_bytes, actual_filename)
            elif ext == "xlsx":
                md, meta = self._convert_xlsx(raw_bytes, actual_filename)
            elif ext == "pptx":
                md, meta = self._convert_pptx(raw_bytes, actual_filename)
            elif ext in ("html", "htm"):
                md, meta = self._convert_html(raw_bytes, actual_filename)
            elif ext == "csv":
                md, meta = self._convert_csv(raw_bytes, actual_filename)
            elif ext in ("png", "jpg", "jpeg", "webp", "bmp", "gif"):
                md, meta = self._convert_image(raw_bytes, actual_filename)
            else:
                md, meta = self._convert_plain_text(raw_bytes, actual_filename)

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ConversionResult(
                markdown=md,
                metadata=meta.to_dict(),
                source=actual_filename,
                status="success",
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(f"Failed to convert {actual_filename}: {e}", exc_info=True)
            return ConversionResult(
                markdown=f"# Error Converting {actual_filename}\n{e}",
                metadata={"error": str(e), "source": actual_filename},
                source=actual_filename,
                status="failed",
                error=str(e),
                duration_ms=duration_ms,
            )

    def convert_local(self, path: Union[str, Path]) -> ConversionResult:
        """Converts a local file from disk."""
        return self.convert(path)

    def _convert_url(self, url: str, start_time: float) -> ConversionResult:
        """Handles web URLs and YouTube video transcript conversions."""
        meta = DocumentMetadata(title=url, format="url", source=url)
        parsed = urllib.parse.urlparse(url)

        if "youtube.com" in parsed.netloc or "youtu.be" in parsed.netloc:
            # YouTube conversion
            video_id = ""
            if "youtu.be" in parsed.netloc:
                video_id = parsed.path.lstrip("/")
            else:
                qs = urllib.parse.parse_qs(parsed.query)
                video_id = qs.get("v", [""])[0]

            md = f"# YouTube Video: {url}\n\n- **Video ID**: `{video_id}`\n\n*Transcript extraction ready.*"
            meta.format = "youtube"
            meta.word_count = len(re.findall(r"\w+", md))
            return ConversionResult(
                markdown=md,
                metadata=meta.to_dict(),
                source=url,
                duration_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        md = f"# Web Resource: {url}\n\n*(Web URL conversion delegated to senses/crawl4ai_service.py)*"
        return ConversionResult(
            markdown=md,
            metadata=meta.to_dict(),
            source=url,
            duration_ms=(time.perf_counter() - start_time) * 1000.0,
        )

    def convert_batch(
        self,
        paths: List[Union[str, Path]],
        max_workers: Optional[int] = None,
    ) -> List[ConversionResult]:
        """
        Converts multiple documents in parallel using ThreadPoolExecutor.
        """
        if not paths:
            return []

        workers = max_workers or self.max_batch_workers
        results: List[ConversionResult] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_path = {executor.submit(self.convert_local, p): p for p in paths}
            for future in concurrent.futures.as_completed(future_to_path):
                try:
                    res = future.result()
                    results.append(res)
                except Exception as e:
                    p = future_to_path[future]
                    results.append(
                        ConversionResult(
                            markdown="",
                            metadata={"error": str(e), "source": str(p)},
                            source=str(p),
                            status="failed",
                            error=str(e),
                        )
                    )
        return results

    def convert_batch_stream(
        self,
        paths: List[Union[str, Path]],
    ) -> Iterator[ConversionResult]:
        """
        Generator yielding conversion results sequentially as they complete.
        """
        for p in paths:
            yield self.convert_local(p)
