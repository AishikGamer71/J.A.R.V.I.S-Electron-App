---
name: document_reader
description: Universal document conversion to clean Markdown with OCR and table repair.
trigger: read document, parse PDF, inspect Excel sheet, read Word doc, analyze presentation, transcribe audio file
tools:
  - markitdown_convert
---

# Document Reader Skill

## Purpose & Overview
Converts heterogeneous document formats, local files, and multimedia assets into high-fidelity clean Markdown for direct consumption by the LLM reasoning loop or persistent RAG storage.

## Capabilities & Supported Formats
- **PDF Documents (`.pdf`)**: Extracts text, headers, and footnotes; automatically runs OCR on embedded images.
- **Word Documents (`.docx`)**: Preserves heading hierarchy, bullet structures, and embedded tables.
- **Excel Spreadsheets (`.xlsx`)**: Converts spreadsheets into clean Markdown tables with automatic repair of corrupted `<sheetView showZeroes>` XML tags.
- **PowerPoint Presentations (`.pptx`)**: Extracts slide text, presenter notes, and visual captions.
- **Audio Files (`.mp3`, `.wav`)**: Transcribes audio content via localized Whisper pipeline.
- **Images (`.png`, `.jpg`, `.webp`)**: Extracts embedded text via OCR.
- **YouTube URLs**: Fetches video transcripts with timestamp anchors.

## Execution Pattern
Call `markitdown_convert(source_path_or_url)`. The resulting Markdown string is returned directly to the context for reasoning, summarization, or ingestion into `backend/memory/hybrid_rag.py`.
