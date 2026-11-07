"""Stdlib parsing for secretcv.com server-rendered job pages.

Verified live 2026-11-07 against real pages (fixtures in tests/):
- Listing /is-ilanlari: 18,225 jobs, 20 job cards per page
  (<div class="cv-job-box job-list job-search-cv-box job-content-box">)
  each with a title anchor (class "title lh-title", job URL + title),
  a company anchor (class "company"), a city span (city + district)
  and "İlan Tarihi: <relative>" text. Total count in the
  "total-job-text" div ("18.225 İş İlanı Listelendi").
- Keyword search /is-ilanlari/<keyword>-is-ilanlari (e.g. barista ->
  220 jobs); city listing /is-ilanlari/<city>-is-ilanlari (istanbul ->
  2,397 jobs); city + keyword /is-ilanlari/<city>/<keyword>-is-ilanlari.
  The ?q= query form is dead (HTTP 410) — path form only.
- Job detail: schema.org JobPosting JSON-LD (title, description with
  "Genel Yetkinlikler" + "İŞ TANIMI" sections, qualifications,
  datePosted, employmentType, hiringOrganization name + URL,
  jobLocation address, baseSalary — "-" when undisclosed).
- Sectors index /sektore-gore-is-ilanlari: one <ul> of ~209 links
  (sectors + cities + districts + popular positions, alphabetical);
  sectors are the links whose slug is not a Turkish province and
  contains no "/" (district paths are "<city>/<district>-is-ilanlari").
"""
from __future__ import annotations

import html
import json
import re

# The 81 Turkish provinces (URL slugs as secretcv uses them).
PROVINCES = {
    "adana", "adiyaman", "afyonkarahisar", "agri", "aksaray", "amasya",
    "ankara", "antalya", "ardahan", "artvin", "aydin", "balikesir",
    "bartin", "batman", "bayburt", "bilecik", "bingol", "bitlis", "bolu",
    "burdur", "bursa", "canakkale", "cankiri", "corum", "denizli",
    "diyarbakir", "duzce", "edirne", "elazig", "erzincan", "erzurum",
    "eskisehir", "gaziantep", "giresun", "gumushane", "hakkari", "hatay",
    "igdir", "isparta", "istanbul", "izmir", "kahramanmaras", "karabuk",
    "karaman", "kars", "kastamonu", "kayseri", "kirikkale", "kirklareli",
    "kirsehir", "kilis", "kocaeli", "konya", "kutahya", "malatya",
    "manisa", "mardin", "mersin", "mugla", "mus", "nevsehir", "nigde",
    "ordu", "osmaniye", "rize", "sakarya", "samsun", "siirt", "sinop",
    "sivas", "sanliurfa", "sirnak", "tekirdag", "tokat", "trabzon",
    "tunceli", "usak", "van", "yalova", "yozgat", "zonguldak",
}
# City regions secretcv lists separately from the province itself.
CITY_REGIONS = {"istanbul-anadolu", "istanbul-avrupa"}

_TR_UPPER_TO_LOWER = str.maketrans({
    "İ": "i", "I": "ı", "Ş": "ş", "Ğ": "ğ",
    "Ü": "ü", "Ö": "ö", "Ç": "ç",
})
_TR_LOWER_TO_ASCII = str.maketrans({
    "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c", "ı": "i",
})


def _tr_lower(s: str) -> str:
    """Turkish-aware lowercase (str.lower() mangles İ -> i + dot)."""
    return s.translate(_TR_UPPER_TO_LOWER).lower()


def slugify(text: str) -> str:
    """Turkish word/city -> secretcv URL slug ("İstanbul" -> "istanbul",
    "Satış Danışmanı" -> "satis-danismani")."""
    s = _tr_lower((text or "").strip()).translate(_TR_LOWER_TO_ASCII)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if not s:
        raise ValueError(f"cannot slugify {text!r}")
    return s


def _clean(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_total(html_text: str) -> int | None:
    m = re.search(r'total-job-text[^>]*>(.*?)</', html_text, re.S)
    if not m:
        return None
    num = re.sub(r"[^\d]", "", _clean(m.group(1)).split("İş")[0])
    try:
        return int(num) if num else None
    except ValueError:
        return None


# ---------------------------------------------------------------- listing

def _parse_card(block: str) -> dict:
    row: dict = {}
    m = re.search(
        r'<a href="(https://www\.secretcv\.com/[^"]+)"[^>]*class="title lh-title[^"]*"[^>]*>\s*(.*?)\s*</a>',
        block, re.S,
    )
    if m:
        row["url"] = m.group(1)
        row["title"] = _clean(m.group(2))
    m = re.search(
        r'<a href="https://www\.secretcv\.com/firma/[^"]+"[^>]*class="company[^"]*"[^>]*>\s*(.*?)\s*</a>',
        block, re.S,
    )
    if m:
        row["company"] = _clean(m.group(1))
    m = re.search(r'bi-geo-alt-fill"></i>\s*([^<]+?)\s*</span>', block)
    if m:
        row["city"] = _clean(m.group(1))
    m = re.search(r'bi-building"></i>\s*([^<]+?)\s*</span>', block)
    if m:
        row["district"] = _clean(m.group(1))
    m = re.search(r"İlan Tarihi:\s*([^<]+)", block)
    if m:
        row["posted_relative"] = _clean(m.group(1))
    return {k: v for k, v in row.items() if v not in (None, "")}


def parse_listing(html_text: str) -> dict:
    """One listing page -> {"total": int|None, "jobs": [...]} (≤20 cards)."""
    jobs = []
    parts = html_text.split(
        '<div class="cv-job-box job-list job-search-cv-box  job-content-box ">'
    )[1:]
    for block in parts:
        row = _parse_card(block)
        if row.get("title") and row.get("url"):
            jobs.append(row)
    return {"total": _parse_total(html_text), "jobs": jobs}


# ---------------------------------------------------------------- job detail

def parse_job_detail(html_text: str) -> dict:
    """Job detail page -> fields from the JobPosting JSON-LD block."""
    data: dict = {}
    for m in re.finditer(
        r'<script type="application/ld\+json">(.*?)</script>', html_text, re.S
    ):
        try:
            obj = json.loads(m.group(1))
        except (ValueError, TypeError):
            continue
        if isinstance(obj, dict) and obj.get("@type") == "JobPosting":
            data = obj
            break
    if not data:
        raise ValueError("no JobPosting data found on this job page")
    out: dict = {}
    out["title"] = _clean(data.get("title"))
    org = data.get("hiringOrganization") or {}
    out["company"] = _clean(org.get("name"))
    if org.get("url"):
        out["company_url"] = org["url"]
    loc = (data.get("jobLocation") or {}).get("address") or {}
    out["city"] = _clean(loc.get("addressLocality"))
    out["region"] = _clean(loc.get("addressRegion"))
    out["country"] = _clean(loc.get("addressCountry"))
    out["date_posted"] = data.get("datePosted")
    out["employment_type"] = _clean(data.get("employmentType"))
    salary = (data.get("baseSalary") or {}).get("value") or {}
    sal = salary.get("value")
    if sal and sal != "-":
        out["salary_try_monthly"] = sal
        out["salary_currency"] = (data.get("baseSalary") or {}).get("currency")
    desc = _clean(data.get("description"))
    if desc:
        out["description"] = desc
    quals = _clean(data.get("qualifications"))
    if quals:
        out["qualifications"] = quals
    m = re.search(
        r'<meta property="og:url" content="([^"]+)"', html_text
    ) or re.search(r'<link rel="canonical" href="([^"]+)"', html_text)
    if m:
        out["url"] = m.group(1)
    return {k: v for k, v in out.items() if v not in (None, "")}


# ---------------------------------------------------------------- index pages

_INDEX_LINK_RE = re.compile(
    r'<a href="(https://www\.secretcv\.com/is-ilanlari/[^"]+-is-ilanlari)"'
    r'[^>]*title="([^"]+)"[^>]*>\s*([^<]+?)\s*</a>',
    re.S,
)


def _index_links(html_text: str) -> list[dict]:
    seen: dict[str, dict] = {}
    for url, _title, label in _INDEX_LINK_RE.findall(html_text):
        slug = url.split("/is-ilanlari/")[1].removesuffix("-is-ilanlari")
        if slug in seen:
            continue
        seen[slug] = {
            "slug": slug,
            "name": _clean(label),
            "url": url,
        }
    return list(seen.values())


def parse_sectors(html_text: str) -> list[dict]:
    """Sectors index -> sector entries (province + district links removed;
    the page mixes a few popular positions in, labelled as-is)."""
    rows = []
    for row in _index_links(html_text):
        slug = row["slug"]
        if "/" in slug:
            continue  # district path (<city>/<district>)
        if slug in PROVINCES or slug in CITY_REGIONS:
            continue  # city entry, not a sector
        rows.append(row)
    return rows


def parse_cities(html_text: str) -> list[dict]:
    """Cities from the sectors index page (province slugs + the two
    İstanbul regions)."""
    rows = []
    for row in _index_links(html_text):
        slug = row["slug"]
        if "/" in slug:
            continue
        if slug in PROVINCES or slug in CITY_REGIONS:
            rows.append(row)
    return rows


# Display names for the 81 provinces (the site's index pages list only
# the popular cities, so the full list is completed from the canonical
# province set; every URL follows the verified
# /is-ilanlari/<slug>-is-ilanlari pattern).
PROVINCE_NAMES = {
    "adana": "Adana", "adiyaman": "Adıyaman", "afyonkarahisar": "Afyonkarahisar",
    "agri": "Ağrı", "aksaray": "Aksaray", "amasya": "Amasya",
    "ankara": "Ankara", "antalya": "Antalya", "ardahan": "Ardahan",
    "artvin": "Artvin", "aydin": "Aydın", "balikesir": "Balıkesir",
    "bartin": "Bartın", "batman": "Batman", "bayburt": "Bayburt",
    "bilecik": "Bilecik", "bingol": "Bingöl", "bitlis": "Bitlis",
    "bolu": "Bolu", "burdur": "Burdur", "bursa": "Bursa",
    "canakkale": "Çanakkale", "cankiri": "Çankırı", "corum": "Çorum",
    "denizli": "Denizli", "diyarbakir": "Diyarbakır", "duzce": "Düzce",
    "edirne": "Edirne", "elazig": "Elazığ", "erzincan": "Erzincan",
    "erzurum": "Erzurum", "eskisehir": "Eskişehir", "gaziantep": "Gaziantep",
    "giresun": "Giresun", "gumushane": "Gümüşhane", "hakkari": "Hakkari",
    "hatay": "Hatay", "igdir": "Iğdır", "isparta": "Isparta",
    "istanbul": "İstanbul", "izmir": "İzmir",
    "kahramanmaras": "Kahramanmaraş", "karabuk": "Karabük",
    "karaman": "Karaman", "kars": "Kars", "kastamonu": "Kastamonu",
    "kayseri": "Kayseri", "kirikkale": "Kırıkkale", "kirklareli": "Kırklareli",
    "kirsehir": "Kırşehir", "kilis": "Kilis", "kocaeli": "Kocaeli",
    "konya": "Konya", "kutahya": "Kütahya", "malatya": "Malatya",
    "manisa": "Manisa", "mardin": "Mardin", "mersin": "Mersin",
    "mugla": "Muğla", "mus": "Muş", "nevsehir": "Nevşehir",
    "nigde": "Niğde", "ordu": "Ordu", "osmaniye": "Osmaniye",
    "rize": "Rize", "sakarya": "Sakarya", "samsun": "Samsun",
    "siirt": "Siirt", "sinop": "Sinop", "sivas": "Sivas",
    "sanliurfa": "Şanlıurfa", "sirnak": "Şırnak", "tekirdag": "Tekirdağ",
    "tokat": "Tokat", "trabzon": "Trabzon", "tunceli": "Tunceli",
    "usak": "Uşak", "van": "Van", "yalova": "Yalova", "yozgat": "Yozgat",
    "zonguldak": "Zonguldak",
}


def complete_cities(parsed: list[dict]) -> list[dict]:
    """Full city list: site-parsed cities first, then any province the
    index pages omit, completed from the canonical province set (plus
    the two İstanbul regions)."""
    by_slug = {r["slug"]: r for r in parsed}
    for slug in sorted(PROVINCES):
        if slug not in by_slug:
            by_slug[slug] = {
                "slug": slug,
                "name": PROVINCE_NAMES[slug],
                "url": f"https://www.secretcv.com/is-ilanlari/{slug}-is-ilanlari",
            }
    for slug, name in (("istanbul-anadolu", "İstanbul Anadolu"),
                       ("istanbul-avrupa", "İstanbul Avrupa")):
        if slug not in by_slug:
            by_slug[slug] = {
                "slug": slug,
                "name": name,
                "url": f"https://www.secretcv.com/is-ilanlari/{slug}-is-ilanlari",
            }
    return list(by_slug.values())
