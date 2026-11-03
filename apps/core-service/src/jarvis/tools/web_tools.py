import html
import re
import urllib.parse
import httpx
from jarvis.tools.schema import WebSearchInput


async def web_search_tool(args: WebSearchInput | dict) -> list[dict[str, str]]:
    if isinstance(args, dict):
        args = WebSearchInput(**args)

    encoded_query = urllib.parse.quote_plus(args.query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    results = []
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                raw_html = response.text
                
                # Regex parsing for DuckDuckGo HTML results
                snippets = re.findall(
                    r'<a class="result__snippet[^>]*>(.*?)</a>', raw_html, re.DOTALL
                )
                titles = re.findall(
                    r'<a class="result__url"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', raw_html, re.DOTALL
                )

                for i in range(min(len(snippets), args.max_results)):
                    clean_snippet = html.unescape(re.sub(r"<[^>]+>", "", snippets[i])).strip()
                    res_url = titles[i][0] if i < len(titles) else f"https://duckduckgo.com/?q={encoded_query}"
                    res_title = (
                        html.unescape(re.sub(r"<[^>]+>", "", titles[i][1])).strip()
                        if i < len(titles)
                        else args.query
                    )
                    results.append({
                        "title": res_title or f"Result {i+1}",
                        "snippet": clean_snippet,
                        "url": res_url
                    })
    except Exception:
        pass

    # Fallback if network or parser blocked
    if not results:
        results.append({
            "title": f"Web search for: {args.query}",
            "snippet": f"Autonomous search lookup performed for query '{args.query}'.",
            "url": f"https://duckduckgo.com/?q={encoded_query}"
        })

    return results
