"""
backend/senses/crawl4ai_service.py
==================================
Noise-free Web Scraping and Markdown Extraction Service for J.A.R.V.I.S.
Assimilated from unclecode/crawl4ai.

Features:
- Fast, noise-free Markdown extraction from web URLs and HTML strings.
- HTML cleanup: boilerplate removal, ad/cookie container stripping, semantic tag conversion.
- Dual-engine architecture:
  * Primary: AsyncWebCrawler with PruningContentFilterLXML and BM25 filtering.
  * Fallback: Headless Playwright / urllib + BeautifulSoup pure-Python extraction.
- Rate limiting, user-agent rotation, timeout handling, and CSS selector filtering.
- Plugs directly into ToolDispatcher and HybridMemory.
"""

import asyncio
import concurrent.futures
import logging
import os
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("jarvis.crawl4ai")

# Check if official crawl4ai is installed
try:
    import crawl4ai
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
    from crawl4ai.content_filter_strategy import PruningContentFilterLXML, BM25ContentFilter
    _HAS_CRAWL4AI = True
except ImportError:
    _HAS_CRAWL4AI = False

# Check if Playwright is installed
try:
    from playwright.sync_api import sync_playwright
    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False

# Check if BeautifulSoup is installed
try:
    from bs4 import BeautifulSoup, Comment
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False


# Standard modern desktop User-Agents for rotation
DEFAULT_USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
]

# Noise element tags and attribute patterns
NOISE_TAGS: Set[str] = {
    "script", "style", "noscript", "svg", "nav", "footer",
    "header", "aside", "iframe", "form", "button", "dialog"
}
NOISE_CLASS_PATTERNS = re.compile(
    r"cookie|banner|advert|popup|modal|newsletter|social-share|sidebar|promo|overlay",
    re.IGNORECASE
)


@dataclass
class CrawlResult:
    """Result envelope for web crawling operations."""
    url: str
    markdown: str
    fit_markdown: str
    title: str = ""
    status: str = "success"
    status_code: int = 200
    links: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "markdown": self.markdown,
            "fit_markdown": self.fit_markdown,
            "title": self.title,
            "status": self.status,
            "status_code": self.status_code,
            "links": self.links,
            "images": self.images,
            "metadata": self.metadata,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


class Crawl4AIService:
    """
    High-speed, noise-free web extraction service with Playwright and pure-Python fallbacks.
    """

    def __init__(
        self,
        timeout_sec: int = 30,
        filter_noise: bool = True,
        rate_limit_delay: float = 0.5,
        user_agents: Optional[List[str]] = None,
        headless: bool = True,
    ):
        self.timeout_sec: int = int(timeout_sec)
        self.filter_noise: bool = bool(filter_noise)
        self.rate_limit_delay: float = float(rate_limit_delay)
        self.user_agents: List[str] = user_agents or list(DEFAULT_USER_AGENTS)
        self.headless: bool = headless

        self._ua_index: int = 0
        self._last_request_times: Dict[str, float] = {}
        self._has_crawl4ai: bool = _HAS_CRAWL4AI
        self._has_playwright: bool = _HAS_PLAYWRIGHT
        self._has_bs4: bool = _HAS_BS4

        logger.info(
            "Crawl4AIService initialized (timeout=%ds, filter_noise=%s, crawl4ai=%s, playwright=%s, bs4=%s)",
            self.timeout_sec,
            self.filter_noise,
            self._has_crawl4ai,
            self._has_playwright,
            self._has_bs4,
        )

    def get_user_agent(self) -> str:
        """Rotates through modern desktop user agents."""
        if not self.user_agents:
            return DEFAULT_USER_AGENTS[0]
        ua = self.user_agents[self._ua_index % len(self.user_agents)]
        self._ua_index += 1
        return ua

    def is_valid_url(self, url: str) -> bool:
        """
        Validates URL scheme and structure before crawling.
        Rejects unsupported protocols (e.g., ftp://, gopher://) and malformed strings.
        """
        if not url or not isinstance(url, str):
            return False
        url_str = url.strip()
        try:
            parsed = urllib.parse.urlparse(url_str)
            return parsed.scheme.lower() in ("http", "https") and bool(parsed.netloc)
        except Exception:
            return False

    def _apply_rate_limit(self, domain: str) -> None:
        """Applies gentle rate limiting per domain to prevent triggering rate gates."""
        if not domain:
            return
        last_time = self._last_request_times.get(domain, 0.0)
        elapsed = time.time() - last_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_times[domain] = time.time()

    # -----------------------------------------------------------------------
    # HTML Cleanup and Markdown Extraction
    # -----------------------------------------------------------------------

    def html_to_markdown(self, html_content: str, preserve_links: bool = True) -> str:
        """
        Extracts clean, noise-free Markdown from an HTML string:
        - Strips scripts, styles, forms, headers, footers, navbars, and cookie modals.
        - Preserves headings (# H1, ## H2), paragraphs, lists, blockquotes, and tables.
        """
        if not html_content or not isinstance(html_content, str):
            return ""

        if not self._has_bs4:
            return self._regex_html_to_markdown(html_content)

        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # 2. Remove noise tags
        if self.filter_noise:
            for tag in soup.find_all(list(NOISE_TAGS)):
                tag.decompose()

            # Remove elements with class or id matching cookie/banner/ad patterns
            for tag in soup.find_all(True):
                class_str = " ".join(tag.get("class", [])) if isinstance(tag.get("class"), list) else str(tag.get("class", ""))
                id_str = str(tag.get("id", ""))
                combined = f"{class_str} {id_str}"
                if NOISE_CLASS_PATTERNS.search(combined):
                    tag.decompose()

        # 3. Process structural elements into Markdown equivalents
        # Headings
        for level in range(1, 7):
            for h in soup.find_all(f"h{level}"):
                text = h.get_text().strip()
                prefix = "#" * level
                h.replace_with(f"\n\n{prefix} {text}\n\n")

        # Paragraphs & Divs
        for p in soup.find_all("p"):
            text = p.get_text().strip()
            if text:
                p.replace_with(f"\n\n{text}\n\n")

        # Strong / Bold
        for b in soup.find_all(["b", "strong"]):
            b_text = b.get_text().strip()
            if b_text:
                b.replace_with(f"**{b_text}**")

        # Em / Italic
        for i in soup.find_all(["i", "em"]):
            i_text = i.get_text().strip()
            if i_text:
                i.replace_with(f"*{i_text}*")

        # Code blocks
        for pre in soup.find_all("pre"):
            code = pre.get_text()
            pre.replace_with(f"\n\n```\n{code.strip()}\n```\n\n")

        for code in soup.find_all("code"):
            c_text = code.get_text().strip()
            code.replace_with(f" `{c_text}` ")

        # Blockquotes
        for bq in soup.find_all("blockquote"):
            bq_text = bq.get_text().strip()
            bq.replace_with(f"\n\n> {bq_text}\n\n")

        # Unordered Lists
        for ul in soup.find_all("ul"):
            items = []
            for li in ul.find_all("li", recursive=False):
                item_text = li.get_text().strip()
                if item_text:
                    items.append(f"- {item_text}")
            ul.replace_with("\n" + "\n".join(items) + "\n\n")

        # Ordered Lists
        for ol in soup.find_all("ol"):
            items = []
            for idx, li in enumerate(ol.find_all("li", recursive=False), start=1):
                item_text = li.get_text().strip()
                if item_text:
                    items.append(f"{idx}. {item_text}")
            ol.replace_with("\n" + "\n".join(items) + "\n\n")

        # Links
        if preserve_links:
            for a in soup.find_all("a", href=True):
                a_text = a.get_text().strip()
                href = a.get("href", "").strip()
                if a_text and href and not href.startswith("javascript:"):
                    a.replace_with(f"[{a_text}]({href})")

        # Tables
        for table in soup.find_all("table"):
            table_md = self._html_table_to_markdown(table)
            table.replace_with(f"\n\n{table_md}\n\n")

        # 4. Extract final text and normalize whitespace
        raw_text = soup.get_text()
        cleaned_lines = []
        for line in raw_text.splitlines():
            line_str = line.strip()
            if line_str:
                cleaned_lines.append(line_str)
            elif cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")

        return "\n".join(cleaned_lines).strip()

    def extract_markdown(self, html_content: str) -> str:
        """Alias for html_to_markdown for interface completeness."""
        return self.html_to_markdown(html_content)

    def _html_table_to_markdown(self, table_elem: Any) -> str:
        """Converts an HTML table element into Markdown table syntax."""
        rows: List[List[str]] = []
        for tr in table_elem.find_all("tr"):
            cells = [c.get_text().strip() for c in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)

        if not rows:
            return ""

        max_cols = max(len(r) for r in rows)
        padded_rows = [r + [""] * (max_cols - len(r)) for r in rows]

        header = padded_rows[0]
        delimiter = ["---"] * max_cols
        body = padded_rows[1:] if len(padded_rows) > 1 else []

        md_lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(delimiter) + " |",
        ]
        for row in body:
            md_lines.append("| " + " | ".join(row) + " |")

        return "\n".join(md_lines)

    def _regex_html_to_markdown(self, html: str) -> str:
        """Pure-regex fallback when BeautifulSoup is unavailable."""
        text = html
        text = re.sub(r"<!--[\s\S]*?-->", "", text)
        if self.filter_noise:
            text = re.sub(r"<(script|style|nav|footer|header|aside)[^>]*>[\s\S]*?</\1>", "", text, flags=re.I)
            text = re.sub(r"<[a-z0-9]+[^>]*class=[\"'][^\"']*(?:cookie|banner|advert|popup|modal|newsletter)[^\"']*[\"'][^>]*>[\s\S]*?</[a-z0-9]+>", "", text, flags=re.I)
            text = re.sub(r"<(footer)[^>]*>[\s\S]*?$", "", text, flags=re.I)
        text = re.sub(r"<h1[^>]*>(.*?)(?:</h1>|(?=<[a-z/!]|\n|$))", r"\n\n# \1\n\n", text, flags=re.I)
        text = re.sub(r"<h2[^>]*>(.*?)(?:</h2>|(?=<[a-z/!]|\n|$))", r"\n\n## \1\n\n", text, flags=re.I)
        text = re.sub(r"<h3[^>]*>(.*?)(?:</h3>|(?=<[a-z/!]|\n|$))", r"\n\n### \1\n\n", text, flags=re.I)
        text = re.sub(r"<p[^>]*>(.*?)(?:</p>|(?=<[a-z/!]|\n|$))", r"\n\n\1\n\n", text, flags=re.I)
        text = re.sub(r"<li[^>]*>(.*?)(?:</li>|(?=<[a-z/!]|\n|$))", r"\n- \1", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\n{3,}", "\n\n", text).strip()

    # -----------------------------------------------------------------------
    # Crawling Execution
    # -----------------------------------------------------------------------

    def crawl(
        self,
        url: str,
        css_selector: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> CrawlResult:
        """
        Crawls a URL and returns clean Markdown.
        Supports official crawl4ai, Playwright headless, and urllib fallbacks.
        Handles offline/synthetic URLs ('about:blank', local files) deterministically.
        """
        start_time = time.perf_counter()
        effective_timeout = int(timeout) if timeout is not None else self.timeout_sec

        # 1. Handle synthetic & local endpoints
        if url == "about:blank":
            return CrawlResult(
                url=url,
                markdown="",
                fit_markdown="",
                title="Blank Page",
                status="success",
                status_code=200,
                duration_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        if url.startswith("file://") or (os.path.exists(url) and os.path.isfile(url)):
            return self._crawl_local_file(url, start_time)

        # 2. Validate URL
        if not self.is_valid_url(url):
            return CrawlResult(
                url=url,
                markdown="",
                fit_markdown="",
                title="Invalid URL",
                status="error",
                status_code=400,
                error=f"Unsupported or malformed URL: '{url}'",
                duration_ms=(time.perf_counter() - start_time) * 1000.0,
            )

        domain = urllib.parse.urlparse(url).netloc
        self._apply_rate_limit(domain)

        # 3. Attempt official Crawl4AI if installed
        if self._has_crawl4ai:
            try:
                res = self._crawl_with_crawl4ai(url, css_selector, effective_timeout)
                res.duration_ms = (time.perf_counter() - start_time) * 1000.0
                return res
            except Exception as e:
                logger.warning("Crawl4AI execution failed on %s (%s); trying Playwright fallback", url, e)

        # 4. Attempt Playwright headless if installed
        if self._has_playwright:
            try:
                res = self._crawl_with_playwright(url, css_selector, effective_timeout)
                res.duration_ms = (time.perf_counter() - start_time) * 1000.0
                return res
            except Exception as e:
                logger.warning("Playwright fallback failed on %s (%s); trying urllib fallback", url, e)

        # 5. Fallback to urllib / httpx HTTP extraction
        res = self._crawl_with_urllib(url, css_selector, effective_timeout)
        res.duration_ms = (time.perf_counter() - start_time) * 1000.0
        return res

    def _crawl_local_file(self, file_url_or_path: str, start_time: float) -> CrawlResult:
        """Reads local HTML or text files directly."""
        path_str = file_url_or_path.replace("file://", "")
        p = Path(path_str)
        if not p.exists():
            return CrawlResult(
                url=file_url_or_path,
                markdown="",
                fit_markdown="",
                status="error",
                status_code=404,
                error=f"Local file not found: {path_str}",
                duration_ms=(time.perf_counter() - start_time) * 1000.0,
            )
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            md = self.html_to_markdown(content) if p.suffix.lower() in [".html", ".htm"] else content
            return CrawlResult(
                url=file_url_or_path,
                markdown=md,
                fit_markdown=md,
                title=p.name,
                status="success",
                status_code=200,
                duration_ms=(time.perf_counter() - start_time) * 1000.0,
            )
        except Exception as e:
            return CrawlResult(
                url=file_url_or_path,
                markdown="",
                fit_markdown="",
                status="error",
                status_code=500,
                error=str(e),
                duration_ms=(time.perf_counter() - start_time) * 1000.0,
            )

    def _crawl_with_crawl4ai(
        self,
        url: str,
        css_selector: Optional[str],
        timeout: int,
    ) -> CrawlResult:
        """Executes crawl via official unclecode/crawl4ai library."""
        async def _run():
            browser_cfg = BrowserConfig(headless=self.headless)
            md_gen = DefaultMarkdownGenerator(
                content_filter=PruningContentFilterLXML(threshold=0.48, min_word_threshold=20)
            )
            run_cfg = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                remove_overlay_elements=True,
                remove_consent_popups=True,
                flatten_shadow_dom=True,
                css_selector=css_selector,
                markdown_generator=md_gen,
                page_timeout=timeout * 1000,
            )
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                return await crawler.arun(url=url, config=run_cfg)

        try:
            res = asyncio.run(_run())
            md = getattr(res.markdown, "raw_markdown", str(res.markdown))
            fit_md = getattr(res.markdown, "fit_markdown", md)
            return CrawlResult(
                url=url,
                markdown=md,
                fit_markdown=fit_md or md,
                title=getattr(res, "title", ""),
                status="success" if res.success else "error",
                status_code=getattr(res, "status_code", 200),
                links=[link.get("href", "") for link in getattr(res, "links", {}).get("internal", [])],
                images=[img.get("src", "") for img in getattr(res, "media", {}).get("images", [])],
                error=getattr(res, "error_message", None),
            )
        except Exception as e:
            raise RuntimeError(f"Crawl4AI execution error: {e}") from e

    def _crawl_with_playwright(
        self,
        url: str,
        css_selector: Optional[str],
        timeout: int,
    ) -> CrawlResult:
        """Executes crawl using Playwright headless browser."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(user_agent=self.get_user_agent())
            page = context.new_page()
            page.set_default_timeout(timeout * 1000)

            try:
                response = page.goto(url, wait_until="domcontentloaded")
                status_code = response.status if response else 200

                title = page.title()

                if css_selector:
                    elem = page.query_selector(css_selector)
                    raw_html = elem.inner_html() if elem else page.content()
                else:
                    raw_html = page.content()

                md = self.html_to_markdown(raw_html)

                # Extract outgoing links
                links = []
                for a in page.query_selector_all("a[href]"):
                    href = a.get_attribute("href")
                    if href:
                        links.append(href)

                return CrawlResult(
                    url=url,
                    markdown=md,
                    fit_markdown=md,
                    title=title,
                    status="success",
                    status_code=status_code,
                    links=links[:50],
                )
            finally:
                browser.close()

    def _crawl_with_urllib(
        self,
        url: str,
        css_selector: Optional[str],
        timeout: int,
    ) -> CrawlResult:
        """Standard HTTP GET extraction fallback using urllib."""
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.get_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status_code = resp.getcode()
                raw_bytes = resp.read()
                encoding = resp.headers.get_content_charset("utf-8")
                html = raw_bytes.decode(encoding, errors="replace")

            title = ""
            if self._has_bs4:
                soup = BeautifulSoup(html, "html.parser")
                title = soup.title.string.strip() if soup.title and soup.title.string else ""
                if css_selector:
                    selected = soup.select(css_selector)
                    if selected:
                        html = "".join(str(s) for s in selected)

            md = self.html_to_markdown(html)
            return CrawlResult(
                url=url,
                markdown=md,
                fit_markdown=md,
                title=title,
                status="success",
                status_code=status_code,
            )
        except urllib.error.HTTPError as e:
            return CrawlResult(
                url=url,
                markdown="",
                fit_markdown="",
                status="error",
                status_code=e.code,
                error=f"HTTP {e.code}: {e.reason}",
            )
        except Exception as e:
            return CrawlResult(
                url=url,
                markdown="",
                fit_markdown="",
                status="error",
                status_code=500,
                error=f"Network error on {url}: {e}",
            )

    def crawl_many(
        self,
        urls: List[str],
        max_concurrent: int = 4,
        css_selector: Optional[str] = None,
    ) -> List[CrawlResult]:
        """Crawls multiple URLs concurrently using a ThreadPoolExecutor."""
        if not urls:
            return []

        results: List[CrawlResult] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            future_to_url = {
                executor.submit(self.crawl, u, css_selector): u for u in urls
            }
            for future in concurrent.futures.as_completed(future_to_url):
                u = future_to_url[future]
                try:
                    res = future.result()
                    results.append(res)
                except Exception as e:
                    results.append(
                        CrawlResult(
                            url=u,
                            markdown="",
                            fit_markdown="",
                            status="error",
                            error=str(e),
                        )
                    )
        return results

    def close(self) -> None:
        """Clean shutdown hook."""
        pass
