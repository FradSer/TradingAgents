"""yfinance-based news data fetching functions.

Notes on yfinance's news APIs (as of yfinance 0.2.x):
- ``Ticker.get_news(count=N)`` returns at most the N most-recent articles for the
  ticker's news feed. It does NOT accept a date range; callers must filter
  client-side. In practice the feed only covers roughly the last week.
- ``yf.Search(query=..., news_count=N)`` is a full-text search whose results
  occasionally include older articles than the feed surfaces. Useful as a
  fallback when the feed and the requested window don't overlap.

This module deliberately distinguishes the failure modes when a date-filtered
query returns nothing — empty feed, window-miss, or unparseable dates — so the
caller (an LLM) can tell "no data" apart from "wrong window" and avoid
fabricating articles.
"""

import yfinance as yf
from datetime import datetime
from dateutil.relativedelta import relativedelta

from .stockstats_utils import yf_retry


def _extract_article_data(article: dict) -> dict:
    """Extract article data from yfinance news format (handles nested 'content' structure)."""
    # Handle nested content structure
    if "content" in article:
        content = article["content"]
        title = content.get("title", "No title")
        summary = content.get("summary", "")
        provider = content.get("provider", {})
        publisher = provider.get("displayName", "Unknown")

        # Get URL from canonicalUrl or clickThroughUrl
        url_obj = content.get("canonicalUrl") or content.get("clickThroughUrl") or {}
        link = url_obj.get("url", "")

        # Get publish date
        pub_date_str = content.get("pubDate", "")
        pub_date = None
        if pub_date_str:
            try:
                pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        return {
            "title": title,
            "summary": summary,
            "publisher": publisher,
            "link": link,
            "pub_date": pub_date,
        }
    else:
        # Fallback for flat structure
        return {
            "title": article.get("title", "No title"),
            "summary": article.get("summary", ""),
            "publisher": article.get("publisher", "Unknown"),
            "link": article.get("link", ""),
            "pub_date": None,
        }


def _fetch_ticker_feed(ticker: str, count: int = 20) -> list[dict]:
    """Primary source: the ticker's own news feed (latest-N, no date filter)."""
    stock = yf.Ticker(ticker)
    news = yf_retry(lambda: stock.get_news(count=count))
    return news or []


def _fetch_ticker_search(ticker: str, count: int = 20) -> list[dict]:
    """Fallback source: full-text search keyed on the ticker symbol.

    Sometimes surfaces articles the ticker's own feed has rotated out, and is
    a useful second look when the feed and the requested window don't overlap.
    """
    try:
        search = yf_retry(lambda: yf.Search(
            query=ticker,
            news_count=count,
            enable_fuzzy_query=False,
        ))
        return list(getattr(search, "news", None) or [])
    except Exception:
        return []


def _filter_to_window(
    raw_articles: list[dict],
    start_dt: datetime,
    end_dt: datetime,
) -> tuple[list[dict], list[datetime], int]:
    """Return (articles-in-window, observed-pub-dates, dateless-count).

    Strict filter: an article is included ONLY if its pub_date is parseable
    AND falls within [start_dt, end_dt + 1 day]. Articles without a parseable
    pub_date are excluded (counted separately) — we will not let temporally
    unverifiable items slip through as window matches, especially through the
    search fallback which often returns dateless results.
    """
    in_window: list[dict] = []
    observed: list[datetime] = []
    dateless = 0
    upper = end_dt + relativedelta(days=1)
    for article in raw_articles:
        data = _extract_article_data(article)
        pub = data["pub_date"]
        if pub is None:
            dateless += 1
            continue
        pub_naive = pub.replace(tzinfo=None)
        observed.append(pub_naive)
        if start_dt <= pub_naive <= upper:
            in_window.append(data)
    return in_window, observed, dateless


def _format_articles(
    ticker: str,
    start_date: str,
    end_date: str,
    articles: list[dict],
    source_label: str,
) -> str:
    """Render the matched articles as the analyst-facing string."""
    parts = []
    for data in articles:
        parts.append(f"### {data['title']} (source: {data['publisher']})")
        if data["summary"]:
            parts.append(data["summary"])
        if data["link"]:
            parts.append(f"Link: {data['link']}")
        parts.append("")
    body = "\n".join(parts)
    return (
        f"## {ticker} News, from {start_date} to {end_date} "
        f"(via {source_label}, {len(articles)} articles):\n\n{body}"
    )


def get_news_yfinance(
    ticker: str,
    start_date: str,
    end_date: str,
) -> str:
    """
    Retrieve news for a specific stock ticker using yfinance.

    Returns one of:
      * A formatted list of articles that fall within [start_date, end_date].
      * A ``NO_DATA: ...`` message — yfinance returned nothing at all.
      * A ``WINDOW_MISS: ...`` message — yfinance returned articles but none in
        the requested window; the message reports the dates that *were*
        available and explicitly forbids fabricating coverage.
      * A ``NO_DATES: ...`` message — articles returned but pub_date was
        unparseable on all of them.
      * An ``ERROR: ...`` message — exception bubbled up from yfinance.

    The ``NO_DATA`` / ``WINDOW_MISS`` / ``NO_DATES`` prefixes are stable and
    deliberately machine-readable so analyst prompts can react to them.
    """
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError as e:
        return f"ERROR: invalid date for {ticker}: {e}"

    try:
        # 1) Primary: ticker's own feed.
        primary_raw = _fetch_ticker_feed(ticker)
        primary_articles, primary_dates, primary_dateless = _filter_to_window(
            primary_raw, start_dt, end_dt
        )
        if primary_articles:
            return _format_articles(
                ticker, start_date, end_date, primary_articles,
                source_label="yfinance ticker feed",
            )

        # 2) Fallback: search by ticker symbol.
        search_raw = _fetch_ticker_search(ticker)
        search_articles, search_dates, search_dateless = _filter_to_window(
            search_raw, start_dt, end_dt
        )
        if search_articles:
            return _format_articles(
                ticker, start_date, end_date, search_articles,
                source_label="yfinance search fallback",
            )

        # 3) Diagnose why we got nothing.
        total_returned = len(primary_raw) + len(search_raw)
        observed_dates = primary_dates + search_dates
        total_dateless = primary_dateless + search_dateless

        if total_returned == 0:
            return (
                f"NO_DATA: yfinance returned no articles for {ticker}. The data "
                f"source may be delayed, rate-limited, or the ticker has no "
                f"recent news. Do not fabricate articles; report data as "
                f"unavailable and continue with other sources."
            )

        if observed_dates:
            oldest = min(observed_dates).date()
            newest = max(observed_dates).date()
            return (
                f"WINDOW_MISS: yfinance returned {total_returned} articles for "
                f"{ticker} (with parseable pub_dates spanning "
                f"[{oldest}, {newest}], plus {total_dateless} undated), but "
                f"none fall inside requested [{start_date}, {end_date}]. "
                f"yfinance's ticker news feed only surfaces the most-recent "
                f"~20 articles and does not support historical lookups; "
                f"re-query a window ending today to see what's available. "
                f"Do NOT invent news for the requested period."
            )

        return (
            f"NO_DATES: yfinance returned {total_returned} articles for "
            f"{ticker} but none had parseable pub_date metadata, so window "
            f"containment cannot be verified. Do not fabricate coverage."
        )

    except Exception as e:
        return f"ERROR: fetching news for {ticker}: {e}"


def get_global_news_yfinance(
    curr_date: str,
    look_back_days: int = 7,
    limit: int = 10,
) -> str:
    """
    Retrieve global/macro economic news using yfinance Search.

    Args:
        curr_date: Current date in yyyy-mm-dd format
        look_back_days: Number of days to look back
        limit: Maximum number of articles to return

    Returns:
        Formatted string containing global news articles
    """
    # Search queries for macro/global news
    search_queries = [
        "stock market economy",
        "Federal Reserve interest rates",
        "inflation economic outlook",
        "global markets trading",
    ]

    all_news = []
    seen_titles = set()

    try:
        for query in search_queries:
            search = yf_retry(lambda q=query: yf.Search(
                query=q,
                news_count=limit,
                enable_fuzzy_query=True,
            ))

            if search.news:
                for article in search.news:
                    # Handle both flat and nested structures
                    if "content" in article:
                        data = _extract_article_data(article)
                        title = data["title"]
                    else:
                        title = article.get("title", "")

                    # Deduplicate by title
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        all_news.append(article)

            if len(all_news) >= limit:
                break

        if not all_news:
            return (
                f"NO_DATA: yfinance global news search returned nothing for "
                f"{curr_date}. Do not fabricate macro coverage."
            )

        # Calculate date range
        curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
        start_dt = curr_dt - relativedelta(days=look_back_days)
        start_date = start_dt.strftime("%Y-%m-%d")

        news_str = ""
        for article in all_news[:limit]:
            # Handle both flat and nested structures
            if "content" in article:
                data = _extract_article_data(article)
                # Skip articles published after curr_date (look-ahead guard)
                if data.get("pub_date"):
                    pub_naive = data["pub_date"].replace(tzinfo=None) if hasattr(data["pub_date"], "replace") else data["pub_date"]
                    if pub_naive > curr_dt + relativedelta(days=1):
                        continue
                title = data["title"]
                publisher = data["publisher"]
                link = data["link"]
                summary = data["summary"]
            else:
                title = article.get("title", "No title")
                publisher = article.get("publisher", "Unknown")
                link = article.get("link", "")
                summary = ""

            news_str += f"### {title} (source: {publisher})\n"
            if summary:
                news_str += f"{summary}\n"
            if link:
                news_str += f"Link: {link}\n"
            news_str += "\n"

        return f"## Global Market News, from {start_date} to {curr_date}:\n\n{news_str}"

    except Exception as e:
        return f"ERROR: fetching global news: {e}"
