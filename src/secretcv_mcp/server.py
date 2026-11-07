"""MCP server: unofficial read-only access to secretcv.com job listings."""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from . import http as _http
from . import jobs as _J

mcp = FastMCP("secretcv-mcp")

INSTRUCTIONS = """\
Unofficial read-only MCP server for secretcv.com, Türkiye's job board
(blue-collar focus; ~18,000 live listings). Data comes from the site's
server-rendered pages — no login, no API key. Keyword search:
"/is-ilanlari/<keyword>-is-ilanlari" (e.g. barista -> 220 jobs);
city listing: "/is-ilanlari/<city>-is-ilanlari" (e.g. istanbul ->
2,397 jobs); city + keyword: "/is-ilanlari/<city>/<keyword>-is-ilanlari".
Job detail pages carry schema.org JobPosting JSON-LD (title, company,
city/region, date posted, employment type, salary when disclosed,
full description with "Genel Yetkinlikler" + "İŞ TANIMI"). Listing
pages show 20 jobs each (first page only — the site has no server-side
pagination links); use secretcv_search_jobs to narrow results.
City names are slugified (İstanbul -> istanbul; İstanbul Anadolu /
İstanbul Avrupa are separate regions). Read-only; transport uses
Chrome TLS impersonation; requests are spaced ~0.8s apart.
Built by Mohammad Abbasi (mohammad-abbasi-sh) — Turkey MCP
factory.\
"""


def _err(e: Exception) -> str:
    return json.dumps({"error": str(e)}, ensure_ascii=False)


def _validate_limit(limit: int, lo: int = 1, hi: int = 20) -> int:
    if not lo <= limit <= hi:
        raise ValueError(f"limit must be between {lo} and {hi}")
    return limit


@mcp.tool()
def secretcv_search_jobs(query: str | None = None, city: str | None = None,
                         limit: int = 10) -> str:
    """Search secretcv.com jobs by keyword and/or city. query: e.g.
    "barista", "garson", "şoför", "muhasebeci" (Turkish job titles work
    best); city: e.g. "İstanbul", "Ankara", "İzmir" ("İstanbul Anadolu"
    and "İstanbul Avrupa" are separate regions). At least one of query
    / city is required. limit 1..20. Returns the total matching-job
    count plus jobs (title, company, city, district, relative post
    date, job URL). Only the first results page (20 jobs) is listed."""
    try:
        _validate_limit(limit)
        q = (query or "").strip()
        c = (city or "").strip()
        if not q and not c:
            raise ValueError("pass query, city, or both")
        if q and c:
            html_text = _http.fetch_city_search_html(_J.slugify(c), _J.slugify(q))
        elif q:
            html_text = _http.fetch_search_html(_J.slugify(q))
        else:
            html_text = _http.fetch_city_html(_J.slugify(c))
        data = _J.parse_listing(html_text)
    except (ValueError, _http.SecretcvError) as e:
        return _err(e)
    return json.dumps(
        {
            "query": q or None,
            "city": c or None,
            "total": data["total"],
            "count": min(limit, len(data["jobs"])),
            "jobs": data["jobs"][:limit],
        },
        ensure_ascii=False,
    )


@mcp.tool()
def secretcv_latest_jobs(limit: int = 10) -> str:
    """Newest job listings on secretcv.com (the /is-ilanlari front page,
    ~18,000 live jobs). limit 1..20. Returns the total live-job count
    plus jobs (title, company, city, district, relative post date,
    job URL)."""
    try:
        _validate_limit(limit)
        html_text = _http.fetch_listing_html()
        data = _J.parse_listing(html_text)
    except (ValueError, _http.SecretcvError) as e:
        return _err(e)
    return json.dumps(
        {
            "total": data["total"],
            "count": min(limit, len(data["jobs"])),
            "jobs": data["jobs"][:limit],
        },
        ensure_ascii=False,
    )


@mcp.tool()
def secretcv_get_job(job_url: str) -> str:
    """Full detail for one job posting. job_url: the job's secretcv.com
    URL (as returned by the search/latest tools, e.g.
    "https://www.secretcv.com/coffy-11372/barista-tuzla-sabanci-universitesi-is-ilanlari-1884564").
    Returns title, company (+ company page URL), city/region, date
    posted, employment type, salary in TRY/month when disclosed, and
    the full description + qualifications."""
    try:
        if not job_url or not job_url.strip():
            raise ValueError("job_url must not be empty")
        html_text = _http.fetch_job_html(job_url.strip())
        data = _J.parse_job_detail(html_text)
    except (ValueError, _http.SecretcvError) as e:
        return _err(e)
    return json.dumps(data, ensure_ascii=False)


@mcp.tool()
def secretcv_list_sectors(limit: int = 20) -> str:
    """Job sectors on secretcv.com (e.g. "Bankacılık / Finans",
    "Bilgisayar / BT / İnternet", "Çağrı Merkezi"), each with its URL
    slug and listing URL. limit 1..50. Source: the site's sectors
    index (/sektore-gore-is-ilanlari); city entries are filtered out.
    Use a sector slug as the query in secretcv_search_jobs."""
    try:
        _validate_limit(limit, 1, 50)
        html_text = _http.fetch_sectors_html()
        rows = _J.parse_sectors(html_text)
    except (ValueError, _http.SecretcvError) as e:
        return _err(e)
    return json.dumps(
        {"count": min(limit, len(rows)), "sectors": rows[:limit]},
        ensure_ascii=False,
    )


@mcp.tool()
def secretcv_list_cities(limit: int = 20) -> str:
    """Turkish cities/regions with secretcv.com listings (81 provinces;
    İstanbul split into İstanbul Anadolu / İstanbul Avrupa), each with
    its URL slug and listing URL. limit 1..50. Source: the site's index
    pages. Use a city slug in secretcv_search_jobs."""
    try:
        _validate_limit(limit, 1, 50)
        html_text = _http.fetch_sectors_html()
        rows = _J.complete_cities(_J.parse_cities(html_text))
    except (ValueError, _http.SecretcvError) as e:
        return _err(e)
    return json.dumps(
        {"count": min(limit, len(rows)), "cities": rows[:limit]},
        ensure_ascii=False,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
