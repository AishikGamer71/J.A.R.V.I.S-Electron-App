---
name: deep_research
description: High-speed noise-free web extraction and multi-source cited research reporting.
trigger: research topic, summarize web page, read article online, investigate query, generate report
tools:
  - crawl4ai_extract
  - gpt_researcher_report
---

# Deep Research Skill

## Purpose & Overview
Provides two levels of web intelligence: instantaneous noise-free single-page Markdown extraction, and comprehensive autonomous multi-source research report generation.

## Tool Selection & Usage

### 1. Fast Single-Page Extraction: `crawl4ai_extract(url, query="")`
- Use when the user provides a specific URL or when reading articles, documentation pages, or blog posts.
- Employs `PruningContentFilterLXML` with cosine/BM25 relevance scoring to strip navigation bars, advertisement containers, cookie banners, and footers.
- Returns clean, dense `fit_markdown` in milliseconds.

### 2. Multi-Source Synthesis: `gpt_researcher_report(query, report_type="research_report")`
- Use when the user requests comprehensive research, market comparison, technical synthesis, or literature review on a topic.
- Pipeline: Planner generates sub-queries -> Executor scrapes sources using Crawl4AI -> Publisher filters context via local BM25 (`context/lexical.py`) and compiles cited Markdown report.
- Telemetry: Streams real-time progress events (`tool.start`, `jarvis-terminal-log`) to the UI `WORKSPACE`, `NOTES`, and `TERMINAL` tabs.
