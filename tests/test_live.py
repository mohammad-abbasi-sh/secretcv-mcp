"""Live tests for secretcv_mcp — real requests to secretcv.com.

Requires network + Chrome TLS impersonation (curl-cffi). The server
is polite by design (~0.8s between requests), so this file takes
~15s. Run: python -m unittest discover -s tests -v

Totals change during the day; tests assert structure and sane ranges,
not exact totals.
"""
import json
import unittest

from secretcv_mcp import http as H
from secretcv_mcp import jobs as J


class TestLiveSearch(unittest.TestCase):
    def test_barista(self):
        html_text = H.fetch_search_html("barista")
        data = J.parse_listing(html_text)
        self.assertGreater(data["total"], 0)
        self.assertGreater(len(data["jobs"]), 0)
        self.assertIn("barista", data["jobs"][0]["title"].lower())

    def test_city_istanbul(self):
        html_text = H.fetch_city_html("istanbul")
        data = J.parse_listing(html_text)
        self.assertGreater(data["total"], 1000)
        self.assertGreater(len(data["jobs"]), 0)

    def test_small_province_pattern(self):
        # The city URL pattern must hold even where few jobs exist.
        for slug in ("bayburt", "ardahan", "tunceli"):
            html_text = H.fetch_city_html(slug)
            data = J.parse_listing(html_text)
            self.assertIsNotNone(data["total"])
            self.assertGreaterEqual(len(data["jobs"]), 0)

    def test_unknown_keyword_zero_results(self):
        # Unknown keywords return HTTP 200 with "0 İş İlanı Listelendi".
        html_text = H.fetch_search_html("xyzabcqwerty")
        data = J.parse_listing(html_text)
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["jobs"], [])


class TestLiveDetail(unittest.TestCase):
    def test_coffy_barista(self):
        html_text = H.fetch_job_html(
            "https://www.secretcv.com/coffy-11372/"
            "barista-tuzla-sabanci-universitesi-is-ilanlari-1884564"
        )
        job = J.parse_job_detail(html_text)
        self.assertEqual(job["company"], "Coffy")
        self.assertIn("Barista", job["title"])
        self.assertIn("date_posted", job)


class TestLiveServerTools(unittest.TestCase):
    """End-to-end: call the MCP tool functions and check JSON output."""

    def test_search_tool(self):
        from secretcv_mcp.server import secretcv_search_jobs

        out = json.loads(secretcv_search_jobs("barista", limit=3))
        self.assertNotIn("error", out)
        self.assertEqual(out["count"], 3)
        self.assertGreater(out["total"], 0)

    def test_search_city_tool(self):
        from secretcv_mcp.server import secretcv_search_jobs

        out = json.loads(secretcv_search_jobs(None, city="Ankara", limit=2))
        self.assertNotIn("error", out)
        self.assertEqual(out["count"], 2)

    def test_latest_tool(self):
        from secretcv_mcp.server import secretcv_latest_jobs

        out = json.loads(secretcv_latest_jobs(limit=2))
        self.assertNotIn("error", out)
        self.assertGreater(out["total"], 10000)

    def test_empty_query_error(self):
        from secretcv_mcp.server import secretcv_search_jobs

        out = json.loads(secretcv_search_jobs(None, None))
        self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main()
