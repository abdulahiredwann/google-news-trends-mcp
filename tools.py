import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from contextlib import AsyncContextDecorator, asynccontextmanager
from typing import Annotated, Any, Optional, TYPE_CHECKING, cast, Literal, overload

import cloudscraper
import newspaper
from fastmcp import Context, FastMCP
from gnews import GNews
from googlenewsdecoder import gnewsdecoder
from mcp.types import TextContent
from newspaper import settings as newspaper_settings
from newspaper.article import Article
from playwright.async_api import async_playwright, Browser, Playwright
from pydantic import BaseModel, Field, model_serializer
from trendspy import Trends, TrendKeywordLite


class BaseModelClean(BaseModel):
    @model_serializer
    def serializer(self, **kwargs) -> dict[str, Any]:
        return {
            field: self.__getattribute__(field)
            for field in self.model_fields_set
            if self.__getattribute__(field) is not None
        }

    if TYPE_CHECKING:

        def model_dump(self, **kwargs) -> dict[str, Any]: ...


class ArticleOut(BaseModelClean):
    title: Annotated[str, Field(description="Title of the article.")]
    url: Annotated[str, Field(description="Original article URL.")]
    read_more_link: Annotated[Optional[str], Field(description="Link to read more about the article.")] = None
    language: Annotated[Optional[str], Field(description="Language code of the article.")] = None
    meta_img: Annotated[Optional[str], Field(description="Meta image URL.")] = None
    movies: Annotated[Optional[list[str]], Field(description="List of movie URLs or IDs.")] = None
    meta_favicon: Annotated[Optional[str], Field(description="Favicon URL from meta data.")] = None
    meta_site_name: Annotated[Optional[str], Field(description="Site name from meta data.")] = None
    authors: Annotated[Optional[list[str]], Field(description="list of authors.")] = None
    publish_date: Annotated[Optional[str], Field(description="Publish date in ISO format.")] = None
    top_image: Annotated[Optional[str], Field(description="URL of the top image.")] = None
    images: Annotated[Optional[list[str]], Field(description="list of image URLs.")] = None
    text: Annotated[Optional[str], Field(description="Full text of the article.")] = None
    summary: Annotated[Optional[str], Field(description="Summary of the article.")] = None
    keywords: Annotated[Optional[list[str]], Field(description="Extracted keywords.")] = None
    tags: Annotated[Optional[list[str]], Field(description="Tags for the article.")] = None
    meta_keywords: Annotated[Optional[list[str]], Field(description="Meta keywords from the article.")] = None
    meta_description: Annotated[Optional[str], Field(description="Meta description from the article.")] = None
    canonical_link: Annotated[Optional[str], Field(description="Canonical link for the article.")] = None
    meta_data: Annotated[Optional[dict[str, str | int]], Field(description="Meta data dictionary.")] = None
    meta_lang: Annotated[Optional[str], Field(description="Language of the article.")] = None
    source_url: Annotated[Optional[str], Field(description="Source URL if different from original.")] = None


class TrendingTermArticleOut(BaseModelClean):
    title: Annotated[str, Field(description="Article title.")] = ""
    url: Annotated[str, Field(description="Article URL.")] = ""
    source: Annotated[Optional[str], Field(description="News source name.")] = None
    picture: Annotated[Optional[str], Field(description="URL to article image.")] = None
    time: Annotated[Optional[str | int], Field(description="Publication time or timestamp.")] = None
    snippet: Annotated[Optional[str], Field(description="Article preview text.")] = None


class TrendingTermOut(BaseModelClean):
    keyword: Annotated[str, Field(description="Trending keyword.")]
    volume: Annotated[Optional[str], Field(description="Search volume.")] = None
    trend_keywords: Annotated[Optional[list[str]], Field(description="Related keywords.")] = None
    link: Annotated[Optional[str], Field(description="URL to more information.")] = None
    started: Annotated[Optional[int], Field(description="Unix timestamp when the trend started.")] = None
    picture: Annotated[Optional[str], Field(description="URL to related image.")] = None
    picture_source: Annotated[Optional[str], Field(description="Source of the picture.")] = None
    news: Annotated[
        Optional[list[TrendingTermArticleOut]],
        Field(description="Related news articles."),
    ] = None


tr = Trends()

scraper = cloudscraper.create_scraper(
    interpreter="js2py",
    delay=5,
    browser="chrome",
    debug=False,
)

google_news = GNews(
    language="en",
)

ProgressCallback = Callable[[float, Optional[float]], Awaitable[None]]


class BrowserManager(AsyncContextDecorator):
    _playwright: Optional[Playwright] = None
    _browser: Optional[Browser] = None
    _lock = asyncio.Lock()
    _class_contexts: int = 0

    @classmethod
    async def _get_browser(cls) -> Optional[Browser]:
        if cls._browser is None:
            async with cls._lock:
                if cls._browser is None:
                    try:
                        cls._playwright = await async_playwright().start()
                        cls._browser = await cls._playwright.chromium.launch(headless=True)
                    except Exception:
                        cls._browser = None
        return cls._browser

    @classmethod
    async def _shutdown(cls):
        if cls._browser:
            await cls._browser.close()
            cls._browser = None
        if cls._playwright:
            await cls._playwright.stop()
            cls._playwright = None

    @classmethod
    def browser_context(cls):
        @asynccontextmanager
        async def _browser_context_cm():
            if cls._class_contexts == 0:
                raise RuntimeError("BrowserManager used without context. Wrap in 'async with BrowserManager()'.")
            browser_inst = await cls._get_browser()
            if browser_inst is None:
                yield None
                return
            context = await browser_inst.new_context()
            try:
                yield context
            finally:
                await context.close()

        return _browser_context_cm()

    async def __aenter__(self):
        type(self)._class_contexts += 1
        return self

    async def __aexit__(self, *exc):
        type(self)._class_contexts -= 1
        await self._shutdown()
        return False


async def download_article_with_playwright(url) -> newspaper.Article | None:
    """
    Download an article using Playwright to handle complex websites (async).
    """
    async with BrowserManager.browser_context() as context:
        try:
            if context is None:
                return None
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            content = await page.content()
            article = newspaper.article(url, input_html=content)
            return article
        except Exception:
            return None


def download_article_with_scraper(url) -> newspaper.Article | None:
    article = None
    try:
        article = newspaper.article(url)
    except Exception:
        try:
            response = scraper.get(url)
            if response.status_code < 400:
                article = newspaper.article(url, input_html=response.text)
        except Exception:
            return None
    return article


def decode_url(url: str) -> str:
    if url.startswith("https://news.google.com/rss/"):
        try:
            decoded_url = gnewsdecoder(url)
            if decoded_url.get("status"):
                return decoded_url["decoded_url"]
        except Exception:
            return ""
    return ""


async def download_article(url: str) -> newspaper.Article | None:
    """
    Download an article from a given URL using newspaper4k and cloudscraper (async).
    """
    if not (url := decode_url(url)):
        return None
    article = download_article_with_scraper(url)
    if article is None or not article.text:
        article = await download_article_with_playwright(url)
    return article


async def process_gnews_articles(
    gnews_articles: list[dict],
    nlp: bool = True,
    report_progress: Optional[ProgressCallback] = None,
) -> list[newspaper.Article]:
    """
    Process a list of Google News articles and download them (async).
    Optionally report progress via report_progress callback.
    """
    articles = []
    total = len(gnews_articles)
    for idx, gnews_article in enumerate(gnews_articles):
        article = await download_article(gnews_article["url"])
        if article is None or not article.text:
            continue
        article.parse()
        if nlp:
            article.nlp()
        articles.append(article)
        if report_progress:
            await report_progress(idx, total)
    return articles


async def fetch_news_by_keyword(
    keyword: str,
    period=7,
    max_results: int = 10,
    nlp: bool = True,
    report_progress: Optional[ProgressCallback] = None,
) -> list[newspaper.Article]:
    """
    Find articles by keyword using Google News.
    """
    google_news.period = f"{period}d"
    google_news.max_results = max_results
    gnews_articles = google_news.get_news(keyword)
    if not gnews_articles:
        return []
    return await process_gnews_articles(gnews_articles, nlp=nlp, report_progress=report_progress)


async def fetch_top_news(
    period: int = 3,
    max_results: int = 10,
    nlp: bool = True,
    report_progress: Optional[ProgressCallback] = None,
) -> list[newspaper.Article]:
    """
    Get top news stories from Google News.
    """
    google_news.period = f"{period}d"
    google_news.max_results = max_results
    gnews_articles = google_news.get_top_news()
    if not gnews_articles:
        return []
    return await process_gnews_articles(gnews_articles, nlp=nlp, report_progress=report_progress)


async def fetch_news_by_location(
    location: str,
    period=7,
    max_results: int = 10,
    nlp: bool = True,
    report_progress: Optional[ProgressCallback] = None,
) -> list[newspaper.Article]:
    """Find articles by location using Google News."""
    google_news.period = f"{period}d"
    google_news.max_results = max_results
    gnews_articles = google_news.get_news_by_location(location)
    if not gnews_articles:
        return []
    return await process_gnews_articles(gnews_articles, nlp=nlp, report_progress=report_progress)


async def fetch_news_by_topic(
    topic: str,
    period=7,
    max_results: int = 10,
    nlp: bool = True,
    report_progress: Optional[ProgressCallback] = None,
) -> list[newspaper.Article]:
    """Find articles by topic using Google News.
    topic is one of
    WORLD, NATION, BUSINESS, TECHNOLOGY, ENTERTAINMENT, SPORTS, SCIENCE, HEALTH,
    POLITICS, CELEBRITIES, TV, MUSIC, MOVIES, THEATER, SOCCER, CYCLING, MOTOR SPORTS,
    TENNIS, COMBAT SPORTS, BASKETBALL, BASEBALL, FOOTBALL, SPORTS BETTING, WATER SPORTS,
    HOCKEY, GOLF, CRICKET, RUGBY, ECONOMY, PERSONAL FINANCE, FINANCE, DIGITAL CURRENCIES,
    MOBILE, ENERGY, GAMING, INTERNET SECURITY, GADGETS, VIRTUAL REALITY, ROBOTICS, NUTRITION,
    PUBLIC HEALTH, MENTAL HEALTH, MEDICINE, SPACE, WILDLIFE, ENVIRONMENT, NEUROSCIENCE, PHYSICS,
    GEOLOGY, PALEONTOLOGY, SOCIAL SCIENCES, EDUCATION, JOBS, ONLINE EDUCATION, HIGHER EDUCATION,
    VEHICLES, ARTS-DESIGN, BEAUTY, FOOD, TRAVEL, SHOPPING, HOME, OUTDOORS, FASHION.
    """
    google_news.period = f"{period}d"
    google_news.max_results = max_results
    gnews_articles = google_news.get_news_by_topic(topic)
    if not gnews_articles:
        return []
    return await process_gnews_articles(gnews_articles, nlp=nlp, report_progress=report_progress)


@overload
async def fetch_trending_terms(geo: str = "US", full_data: Literal[False] = False) -> list[dict[str, str]]: ...


@overload
async def fetch_trending_terms(geo: str = "US", full_data: Literal[True] = True) -> list[TrendKeywordLite]: ...


async def fetch_trending_terms(geo: str = "US", full_data: bool = False) -> list[dict[str, str]] | list[TrendKeywordLite]:
    """
    Returns google trends for a specific geo location.
    """
    try:
        trends = cast(list[TrendKeywordLite], tr.trending_now_by_rss(geo=geo))
        trends = sorted(trends, key=lambda tt: int(tt.volume[:-1]), reverse=True)
        if not full_data:
            return [{"keyword": trend.keyword, "volume": trend.volume} for trend in trends]
        return trends
    except Exception:
        return []


def save_article_to_json(article: newspaper.Article, filename: str = "") -> None:
    def sanitize_filename(title: str) -> str:
        """
        # save Article to json file
        # filename is based on the article title
        # if the title is too long, it will be truncated to 50 characters
        # and replaced with underscores if it contains any special characters
        """
        sanitized_title = re.sub(r"[\\/*?:\"<>|\s]", "_", title)[:50]
        return sanitized_title + ".json"

    """
    Save an article to a JSON file.
    """
    article_data = {
        "title": article.title,
        "authors": article.authors,
        "publish_date": str(article.publish_date) if article.publish_date else None,
        "top_image": article.top_image,
        "images": article.images,
        "text": article.text,
        "url": article.original_url,
        "summary": article.summary,
        "keywords": article.keywords,
        "keyword_scores": article.keyword_scores,
        "tags": article.tags,
        "meta_keywords": article.meta_keywords,
        "meta_description": article.meta_description,
        "canonical_link": article.canonical_link,
        "meta_data": article.meta_data,
        "meta_lang": article.meta_lang,
        "source_url": article.source_url,
    }

    if not filename:
        filename = sanitize_filename(article.title)
    else:
        if not filename.endswith(".json"):
            filename += ".json"
    with open(filename, "w") as f:
        json.dump(article_data, f, indent=4)


def set_newspaper_article_fields(full_data: bool = False):
    if full_data:
        newspaper_settings.article_json_fields = [
            "url",
            "read_more_link",
            "language",
            "title",
            "top_image",
            "meta_img",
            "images",
            "movies",
            "keywords",
            "keyword_scores",
            "meta_keywords",
            "tags",
            "authors",
            "publish_date",
            "summary",
            "meta_description",
            "meta_lang",
            "meta_favicon",
            "meta_site_name",
            "canonical_link",
            "text",
        ]
    else:
        newspaper_settings.article_json_fields = [
            "url",
            "title",
            "publish_date",
            "summary",
        ]


async def llm_summarize_article(article: Article, ctx: Context) -> None:
    if article.text:
        prompt = f"Please provide a concise summary of the following news article:\n\n{article.text}"
        response = await ctx.sample(prompt)
        if isinstance(response, TextContent) and response.text:
            article.summary = response.text
        else:
            article.summary = "No summary available."
    else:
        article.summary = "No summary available."


async def summarize_articles(articles: list[Article], ctx: Context) -> None:
    total_articles = len(articles)
    try:
        for idx, article in enumerate(articles):
            await llm_summarize_article(article, ctx)
            await ctx.report_progress(idx, total_articles)
    except Exception:
        for idx, article in enumerate(articles):
            article.nlp()
            await ctx.report_progress(idx, total_articles)


async def get_news_by_keyword(
    ctx: Context,
    keyword: Annotated[str, Field(description="Search term to find articles.")],
    period: Annotated[int, Field(description="Number of days to look back for articles.", ge=1)] = 7,
    max_results: Annotated[int, Field(description="Maximum number of results to return.", ge=1)] = 10,
    full_data: Annotated[
        bool,
        Field(
            description="Return full data for each article. If False a summary should be created by setting the summarize flag"
        ),
    ] = False,
    summarize: Annotated[
        bool,
        Field(
            description="Generate a summary of the article, will first try LLM Sampling but if unavailable will use nlp"
        ),
    ] = True,
) -> list[ArticleOut]:
    set_newspaper_article_fields(full_data)
    articles = await fetch_news_by_keyword(
        keyword=keyword,
        period=period,
        max_results=max_results,
        nlp=False,
        report_progress=ctx.report_progress,
    )
    if summarize:
        await summarize_articles(articles, ctx)
    await ctx.report_progress(progress=len(articles), total=len(articles))
    return [ArticleOut(**a.to_json(False)) for a in articles]


async def get_news_by_location(
    ctx: Context,
    location: Annotated[str, Field(description="Name of city/state/country.")],
    period: Annotated[int, Field(description="Number of days to look back for articles.", ge=1)] = 7,
    max_results: Annotated[int, Field(description="Maximum number of results to return.", ge=1)] = 10,
    full_data: Annotated[
        bool,
        Field(
            description="Return full data for each article. If False a summary should be created by setting the summarize flag"
        ),
    ] = False,
    summarize: Annotated[
        bool,
        Field(
            description="Generate a summary of the article, will first try LLM Sampling but if unavailable will use nlp"
        ),
    ] = True,
) -> list[ArticleOut]:
    set_newspaper_article_fields(full_data)
    articles = await fetch_news_by_location(
        location=location,
        period=period,
        max_results=max_results,
        nlp=False,
        report_progress=ctx.report_progress,
    )
    if summarize:
        await summarize_articles(articles, ctx)
    await ctx.report_progress(progress=len(articles), total=len(articles))
    return [ArticleOut(**a.to_json(False)) for a in articles]


async def get_news_by_topic(
    ctx: Context,
    topic: Annotated[str, Field(description="Topic to search for articles.")],
    period: Annotated[int, Field(description="Number of days to look back for articles.", ge=1)] = 7,
    max_results: Annotated[int, Field(description="Maximum number of results to return.", ge=1)] = 10,
    full_data: Annotated[
        bool,
        Field(
            description="Return full data for each article. If False a summary should be created by setting the summarize flag"
        ),
    ] = False,
    summarize: Annotated[
        bool,
        Field(
            description="Generate a summary of the article, will first try LLM Sampling but if unavailable will use nlp"
        ),
    ] = True,
) -> list[ArticleOut]:
    set_newspaper_article_fields(full_data)
    articles = await fetch_news_by_topic(
        topic=topic,
        period=period,
        max_results=max_results,
        nlp=False,
        report_progress=ctx.report_progress,
    )
    if summarize:
        await summarize_articles(articles, ctx)
    await ctx.report_progress(progress=len(articles), total=len(articles))
    return [ArticleOut(**a.to_json(False)) for a in articles]


async def get_top_news(
    ctx: Context,
    period: Annotated[int, Field(description="Number of days to look back for top articles.", ge=1)] = 3,
    max_results: Annotated[int, Field(description="Maximum number of results to return.", ge=1)] = 10,
    full_data: Annotated[
        bool,
        Field(
            description="Return full data for each article. If False a summary should be created by setting the summarize flag"
        ),
    ] = False,
    summarize: Annotated[
        bool,
        Field(
            description="Generate a summary of the article, will first try LLM Sampling but if unavailable will use nlp"
        ),
    ] = True,
) -> list[ArticleOut]:
    set_newspaper_article_fields(full_data)
    articles = await fetch_top_news(
        period=period,
        max_results=max_results,
        nlp=False,
        report_progress=ctx.report_progress,
    )
    if summarize:
        await summarize_articles(articles, ctx)
    await ctx.report_progress(progress=len(articles), total=len(articles))
    return [ArticleOut(**a.to_json(False)) for a in articles]


async def get_trending_terms(
    geo: Annotated[str, Field(description="Country code, e.g. 'US', 'GB', 'IN', etc.")] = "US",
    full_data: Annotated[
        bool,
        Field(description="Return full data for each trend. Should be False for most use cases."),
    ] = False,
) -> list[TrendingTermOut]:
    if not full_data:
        trends = await fetch_trending_terms(geo=geo, full_data=False)
        return [TrendingTermOut(keyword=str(tt["keyword"]), volume=tt["volume"]) for tt in trends]
    trends = await fetch_trending_terms(geo=geo, full_data=True)
    trends_out = []
    for trend in trends:
        trend = trend.__dict__
        if "news" in trend:
            trend["news"] = [TrendingTermArticleOut(**article.__dict__) for article in trend["news"]]
        trends_out.append(TrendingTermOut(**trend))
    return trends_out


def register_tools(mcp: FastMCP) -> None:
    mcp.tool(
        description=fetch_news_by_keyword.__doc__,
        tags={"news", "articles", "keyword"},
    )(get_news_by_keyword)

    mcp.tool(
        description=fetch_news_by_location.__doc__,
        tags={"news", "articles", "location"},
    )(get_news_by_location)

    mcp.tool(description=fetch_news_by_topic.__doc__, tags={"news", "articles", "topic"})(get_news_by_topic)

    mcp.tool(description=fetch_top_news.__doc__, tags={"news", "articles", "top"})(get_top_news)

    mcp.tool(description=fetch_trending_terms.__doc__, tags={"trends", "google", "trending"})(get_trending_terms)
