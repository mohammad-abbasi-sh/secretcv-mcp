# secretcv-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/secretcv-mcp

Unofficial **read-only** MCP server for secretcv.com, Türkiye's job board — keyword/city job search (~18,000 live listings), full job details from schema.org JobPosting data (title, company, city, date posted, employment type, salary when disclosed, description + qualifications), sector list and city list.

> Built by Mohammad Abbasi as part of the "Turkey MCP factory" (Sepehr-style pipeline). Not affiliated with secretcv.com.

## For AI agents

Add to your MCP client config (stdio):

```json
{
  "mcpServers": {
    "secretcv": {
      "command": "uvx",
      "args": ["secretcv-mcp"]
    }
  }
}
```

Or run locally: `python -m secretcv_mcp.server` (needs `mcp<2`, `curl-cffi`).

## Tools

| Tool | Description |
|------|-------------|
| `secretcv_search_jobs` | Search jobs by keyword and/or city — `query` ("barista", "garson", "şoför"), `city` ("İstanbul", "Ankara", "İzmir"; "İstanbul Anadolu" / "İstanbul Avrupa" are separate regions); returns the total matching-job count + jobs (title, company, city, district, relative post date, job URL). First results page only (20 jobs) |
| `secretcv_latest_jobs` | Newest listings on secretcv.com (`limit` 1..20); returns the total live-job count + jobs |
| `secretcv_get_job` | Full detail for one job — `job_url` (as returned by the search/latest tools); returns title, company (+ company page URL), city/region, date posted, employment type, salary in TRY/month when disclosed, full description + qualifications |
| `secretcv_list_sectors` | Job sectors (e.g. "Bankacılık / Finans", "Bilgisayar / BT / İnternet", "Çağrı Merkezi") with slug + listing URL; `limit` 1..50 |
| `secretcv_list_cities` | Turkish cities/regions with listings (81 provinces; İstanbul split into Anadolu/Avrupa) with slug + listing URL; `limit` 1..50 |

Example output (`secretcv_search_jobs` / "barista"):

```json
{"query": "barista", "total": 220, "count": 2, "jobs": [
  {"title": "Barista / Tuzla - Sabancı Üniversitesi",
   "company": "Coffy", "city": "İstanbul Anadolu",
   "posted_relative": "1 gün önce",
   "url": "https://www.secretcv.com/coffy-11372/barista-tuzla-sabanci-universitesi-is-ilanlari-1884564"}, …]}
```

Example output (`secretcv_get_job` / the Coffy barista posting):

```json
{"title": "Barista / Tuzla - Sabancı Üniversitesi", "company": "Coffy",
 "city": "İstanbul Anadolu", "date_posted": "2026-11-06T19:18:10+03:00",
 "employment_type": "Tam Zamanlı",
 "description": "Coffy hizmet deneyimiyle harmanlayarak misafirlerimize …"}
```

## How it works

secretcv.com serves its listings fully server-rendered — no login, no API key, no session cookies. Keyword search is path-based (`/is-ilanlari/<keyword>-is-ilanlari`, e.g. barista → 220 jobs); city listings use `/is-ilanlari/<city>-is-ilanlari` (istanbul → 2,397 jobs); city + keyword uses `/is-ilanlari/<city>/<keyword>-is-ilanlari`. (The `?q=` query form is dead — HTTP 410.) Listing pages carry 20 job cards each (title, company, city + district, relative post date) and a total count ("18.225 İş İlanı Listelendi"). Job detail pages carry a schema.org JobPosting JSON-LD block (title, description with "Genel Yetkinlikler" + "İŞ TANIMI", qualifications, datePosted, employmentType, hiringOrganization, jobLocation, baseSalary — "-" when undisclosed). The sectors index (`/sektore-gore-is-ilanlari`) mixes sectors with city/district links, so sector/city parsing filters on the 81-province slug set. City names are slugified (İstanbul → istanbul). Transport uses Chrome TLS impersonation (`curl-cffi`, `chrome120`); requests are spaced ~0.8s apart; everything is read-only.

## Install

```bash
uvx secretcv-mcp        # run directly (needs uv)
# or
pip install secretcv-mcp
secretcv-mcp    # starts the MCP server on stdio
```

## Tests

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Offline tests run on recorded fixtures (real pages fetched 2026-11-07); live tests hit secretcv.com. 25/25 green at build time (16 offline + 9 live) plus an MCP stdio smoke test.

## Roadmap

- Second-page listings (the site has no server-side pagination links; a "load more" API would be needed)
- Company pages (`/firma/<slug>-is-ilanlari`: all jobs from one employer)
- Salary statistics per keyword/city (most postings do not disclose a salary)

## License

MIT — see [LICENSE](LICENSE).
