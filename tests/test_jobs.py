"""Offline tests for secretcv_mcp.jobs — recorded real secretcv.com pages.

Fixtures are real pages fetched 2026-11-07 (curl-cffi chrome120):
- listing.html: /is-ilanlari (18,225 jobs, 20 cards on page 1).
- search-barista.html: /is-ilanlari/barista-is-ilanlari (220 jobs).
- search-istanbul.html: /is-ilanlari/istanbul-is-ilanlari (2,397 jobs).
- job-detail.html: Coffy Barista / Tuzla - Sabancı Üniversitesi
  (JobPosting JSON-LD, posted 2026-11-06, Tam Zamanlı).
- sectors.html: /sektore-gore-is-ilanlari (209 index links).
"""
import os
import unittest

from secretcv_mcp import jobs as J

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name: str) -> str:
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


class TestSlugify(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(J.slugify("İstanbul"), "istanbul")
        self.assertEqual(J.slugify("Ankara"), "ankara")
        self.assertEqual(J.slugify("İzmir"), "izmir")
        self.assertEqual(J.slugify("Şanlıurfa"), "sanliurfa")
        self.assertEqual(J.slugify("Çanakkale"), "canakkale")

    def test_multiword(self):
        self.assertEqual(J.slugify("Satış Danışmanı"), "satis-danismani")
        self.assertEqual(J.slugify("İstanbul Anadolu"), "istanbul-anadolu")
        self.assertEqual(J.slugify("Şoför"), "sofor")

    def test_empty(self):
        with self.assertRaises(ValueError):
            J.slugify("   ")


class TestListingParse(unittest.TestCase):
    def setUp(self):
        self.data = J.parse_listing(_read("listing.html"))

    def test_total(self):
        self.assertEqual(self.data["total"], 18225)

    def test_job_count(self):
        self.assertEqual(len(self.data["jobs"]), 20)

    def test_first_job(self):
        j = self.data["jobs"][0]
        self.assertEqual(j["title"], "Mağaza Satış Danışmanı - İzmir / Ödemiş")
        self.assertEqual(j["company"], "Özşanal Züccaciye ve Dayanıklı Tüketim Malları")
        self.assertEqual(j["city"], "İzmir")
        self.assertEqual(j["district"], "Ödemiş")
        self.assertEqual(j["posted_relative"], "1 gün önce")
        self.assertTrue(j["url"].endswith("-is-ilanlari-1884548"))

    def test_all_have_title_url_company(self):
        for j in self.data["jobs"]:
            self.assertIn("title", j)
            self.assertIn("url", j)
            self.assertIn("company", j)
            self.assertTrue(j["url"].startswith("https://www.secretcv.com/"))


class TestSearchParse(unittest.TestCase):
    def test_barista(self):
        data = J.parse_listing(_read("search-barista.html"))
        self.assertEqual(data["total"], 220)
        self.assertEqual(len(data["jobs"]), 20)
        j = data["jobs"][0]
        self.assertEqual(j["title"], "Barista / Tuzla - Sabancı Üniversitesi")
        self.assertEqual(j["company"], "Coffy")
        self.assertEqual(j["city"], "İstanbul Anadolu")

    def test_istanbul(self):
        data = J.parse_listing(_read("search-istanbul.html"))
        self.assertEqual(data["total"], 2397)
        self.assertEqual(len(data["jobs"]), 20)
        self.assertEqual(data["jobs"][0]["city"], "İstanbul Anadolu")


class TestJobDetailParse(unittest.TestCase):
    def setUp(self):
        self.job = J.parse_job_detail(_read("job-detail.html"))

    def test_core_fields(self):
        self.assertEqual(self.job["title"], "Barista / Tuzla - Sabancı Üniversitesi")
        self.assertEqual(self.job["company"], "Coffy")
        self.assertEqual(
            self.job["company_url"],
            "https://www.secretcv.com/firma/coffy-11372-is-ilanlari",
        )
        self.assertEqual(self.job["city"], "İstanbul Anadolu")
        self.assertEqual(self.job["date_posted"], "2026-11-06T19:18:10+03:00")
        self.assertEqual(self.job["employment_type"], "Tam Zamanlı")

    def test_description(self):
        self.assertIn("Coffy", self.job["description"])
        self.assertIn("İŞ TANIMI", self.job["qualifications"])

    def test_no_salary_when_undisclosed(self):
        self.assertNotIn("salary_try_monthly", self.job)

    def test_no_jobposting(self):
        with self.assertRaises(ValueError):
            J.parse_job_detail("<html><body>no data</body></html>")


class TestSectorsCitiesParse(unittest.TestCase):
    def test_sectors(self):
        rows = J.parse_sectors(_read("sectors.html"))
        self.assertGreater(len(rows), 100)
        slugs = {r["slug"] for r in rows}
        self.assertIn("bankacilik-finans", slugs)
        self.assertIn("cagri-merkezi", slugs)
        self.assertNotIn("istanbul", slugs)
        self.assertNotIn("ankara", slugs)

    def test_cities_parsed(self):
        rows = J.parse_cities(_read("sectors.html"))
        slugs = {r["slug"] for r in rows}
        self.assertIn("istanbul", slugs)
        self.assertIn("ankara", slugs)
        self.assertIn("izmir", slugs)

    def test_cities_completed(self):
        rows = J.complete_cities(J.parse_cities(_read("sectors.html")))
        self.assertEqual(len(rows), 83)  # 81 provinces + 2 İstanbul regions
        slugs = {r["slug"] for r in rows}
        self.assertIn("zonguldak", slugs)
        self.assertIn("bayburt", slugs)
        self.assertIn("istanbul-avrupa", slugs)


if __name__ == "__main__":
    unittest.main()
