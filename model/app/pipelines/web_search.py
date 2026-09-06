import json
import logging
import os
import re
from typing import List

from app.config import (
    WEB_SEARCH_PROVIDER,
    WEB_SEARCH_API_KEY,
    WEB_SEARCH_MAX_RESULTS,
    WEB_SEARCH_SNIPPET_MAX_CHARS,
)
from app.schemas.web_result_schema import WebSearchResult

# Setup module logger
logger = logging.getLogger("evorag.web_search")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


def clean_text(text: str, max_chars: int = WEB_SEARCH_SNIPPET_MAX_CHARS) -> str:
    """
    Cleans raw text snippets by stripping HTML tags, collapsing whitespace,
    and truncating to maximum character limit.
    """
    if not text:
        return ""

    # Try BeautifulSoup for thorough HTML tag removal if present
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(text, "html.parser")
        text = soup.get_text()
    except Exception:
        # Regex fallback for HTML tag removal
        text = re.sub(r"<[^>]+>", "", text)

    # Collapse multiple whitespace characters into single space
    text = re.sub(r"\s+", " ", text).strip()

    # Truncate to maximum snippet length
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "..."

    return text


def execute_mock_search(query: str) -> List[WebSearchResult]:
    """
    Fallback mock web search provider for offline execution and API-key-less development.
    Returns realistic mock results clearly tagged as mock data.
    """
    logger.info(f"[WebSearch] Using Mock Provider for query: '{query}'")
    mock_items = [
        {
            "title": f"Mock Search Result 1 for '{query}'",
            "url": "https://example.com/mock-search-result-1",
            "content": f"[MOCK DATA] Latest real-time information regarding '{query}'. EvoRAG query-triggered web search captured updated dynamic details from modern web sources in 2026."
        },
        {
            "title": f"Mock Search Result 2 for '{query}'",
            "url": "https://example.com/mock-search-result-2",
            "content": f"[MOCK DATA] Recent developments and live updates about '{query}'. Includes updated parameters and real-time facts fetched dynamically."
        }
    ]

    results = []
    for idx, item in enumerate(mock_items[:WEB_SEARCH_MAX_RESULTS], 1):
        cleaned_content = clean_text(item["content"])
        results.append(
            WebSearchResult(
                query=query,
                content=cleaned_content,
                source_url=item["url"],
                title=item["title"],
                rank=idx
            )
        )
    return results


def search_web(query: str) -> List[WebSearchResult]:
    """
    Executes web search for input query, extracts text snippets, cleans HTML/formatting,
    and returns structured WebSearchResult items.

    Args:
        query (str): Search query string.

    Returns:
        List[WebSearchResult]: List of cleaned search results sorted by rank.
    """
    if not query or not query.strip():
        return []

    # If no API key is configured, seamlessly fallback to Mock Search Provider
    if not WEB_SEARCH_API_KEY:
        return execute_mock_search(query)

    try:
        raw_results = []
        provider = WEB_SEARCH_PROVIDER.lower()

        if provider == "tavily":
            try:
                from langchain_community.tools.tavily_search import TavilySearchResults
                tavily_tool = TavilySearchResults(
                    tavily_api_key=WEB_SEARCH_API_KEY,
                    max_results=WEB_SEARCH_MAX_RESULTS
                )
                raw_data = tavily_tool.invoke({"query": query})
                if isinstance(raw_data, list):
                    raw_results = raw_data
            except Exception as e:
                logger.error(f"[WebSearch] Tavily search error: {e}")
                return execute_mock_search(query)

        elif provider == "serpapi":
            try:
                from langchain_community.utilities import SerpAPIWrapper
                serp = SerpAPIWrapper(
                    serpapi_api_key=WEB_SEARCH_API_KEY,
                    params={"num": WEB_SEARCH_MAX_RESULTS}
                )
                res_dict = serp.results(query)
                organic_results = res_dict.get("organic_results", [])
                for item in organic_results[:WEB_SEARCH_MAX_RESULTS]:
                    raw_results.append({
                        "title": item.get("title", "Untitled Page"),
                        "url": item.get("link", ""),
                        "content": item.get("snippet", "")
                    })
            except Exception as e:
                logger.error(f"[WebSearch] SerpAPI search error: {e}")
                return execute_mock_search(query)

        else:
            logger.warning(f"[WebSearch] Unknown provider '{provider}'. Falling back to mock search.")
            return execute_mock_search(query)

        web_results = []
        for idx, item in enumerate(raw_results[:WEB_SEARCH_MAX_RESULTS], 1):
            if isinstance(item, dict):
                title = item.get("title") or item.get("url") or "Untitled Page"
                url = item.get("url") or item.get("link") or ""
                snippet = item.get("content") or item.get("snippet") or item.get("body") or ""
            else:
                title = "Search Snippet"
                url = ""
                snippet = str(item)

            cleaned_content = clean_text(snippet)

            web_results.append(
                WebSearchResult(
                    query=query,
                    content=cleaned_content,
                    source_url=url,
                    title=title,
                    rank=idx
                )
            )

        # Ensure results are sorted by rank
        web_results.sort(key=lambda r: r.rank)
        return web_results

    except Exception as exc:
        logger.error(f"[WebSearch] Web search pipeline failed for query '{query}': {exc}")
        return []


if __name__ == "__main__":
    print("=== EvoRAG Web Search Pipeline Manual Verification ===")

    eval_file = os.path.join(os.path.dirname(__file__), "..", "..", "eval", "test_cases.json")
    queries_to_test = ["What is the latest update on EvoRAG in 2026?", "Recent AI news today"]

    if os.path.exists(eval_file):
        try:
            with open(eval_file, "r", encoding="utf-8") as f:
                cases = json.load(f)
                queries_to_test = [c.get("query") for c in cases if c.get("query")]
        except Exception as err:
            print(f"[Warning] Could not load eval/test_cases.json: {err}")

    for test_query in queries_to_test:
        print(f"\n--- Web Search for Query: '{test_query}' ---")
        results = search_web(test_query)
        print(f"Results Count: {len(results)}")
        for res in results:
            print(f"  Rank #{res.rank} | Title: {res.title}")
            print(f"  URL:  {res.source_url}")
            print(f"  Text: {res.content}\n")
