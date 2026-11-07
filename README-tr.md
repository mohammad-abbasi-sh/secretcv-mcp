# secretcv-mcp 🇹🇷

mcp-name: io.github.mohammad-abbasi-sh/secretcv-mcp

secretcv.com için resmi olmayan **salt okunur** MCP sunucusu — Türkiye'nin iş ilanı sitesi: anahtar kelime/şehir ile iş arama (~18.000 aktif ilan), schema.org JobPosting verisinden tam ilan detayı (unvan, firma, şehir, ilan tarihi, çalışma şekli, açıklanmışsa maaş, açıklama + nitelikler), sektör listesi ve şehir listesi.

> Mohammad Abbasi tarafından "Turkey MCP factory" (Sepehr tarzı hat) kapsamında geliştirildi. secretcv.com ile bağlantısı yoktur.

## Yapay zekâ ajanları için

MCP istemci yapılandırmanıza ekleyin (stdio):

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

Veya yerelde çalıştırın: `python -m secretcv_mcp.server` (`mcp<2`, `curl-cffi` gerekir).

## Araçlar

| Araç | Açıklama |
|------|-------------|
| `secretcv_search_jobs` | Anahtar kelime ve/veya şehir ile iş arar — `query` ("barista", "garson", "şoför"), `city` ("İstanbul", "Ankara", "İzmir"; "İstanbul Anadolu" / "İstanbul Avrupa" ayrı bölgelerdir); eşleşen ilan sayısı + ilanlar (unvan, firma, şehir, ilçe, göreli ilan tarihi, ilan URL'si). Yalnızca ilk sonuç sayfası (20 ilan) |
| `secretcv_latest_jobs` | secretcv.com'daki en yeni ilanlar (`limit` 1..20); toplam aktif ilan sayısı + ilanlar |
| `secretcv_get_job` | Tek bir ilanın tam detayı — `job_url` (arama/en yeni araçlarının döndürdüğü URL); unvan, firma (+ firma sayfası URL'si), şehir/bölge, ilan tarihi, çalışma şekli, açıklanmışsa aylık maaş (TRY), tam açıklama + nitelikler |
| `secretcv_list_sectors` | İş sektörleri (örn. "Bankacılık / Finans", "Bilgisayar / BT / İnternet", "Çağrı Merkezi"); slug + liste URL'si; `limit` 1..50 |
| `secretcv_list_cities` | İlanı olan Türkiye şehirleri/bölgeleri (81 il; İstanbul Anadolu/Avrupa ayrı); slug + liste URL'si; `limit` 1..50 |

## Nasıl çalışır

secretcv.com ilanlarını tamamen sunucu taraflı gösterir — giriş, API anahtarı ve çerez gerekmez. Anahtar kelime araması yol (path) tabanlıdır (`/is-ilanlari/<kelime>-is-ilanlari`, örn. barista → 220 ilan); şehir listeleri `/is-ilanlari/<şehir>-is-ilanlari` (istanbul → 2.397 ilan); şehir + kelime `/is-ilanlari/<şehir>/<kelime>-is-ilanlari`. (`?q=` biçimi çalışmıyor — HTTP 410.) Liste sayfalarında 20 ilan kartı (unvan, firma, şehir + ilçe, göreli ilan tarihi) ve toplam sayı ("18.225 İş İlanı Listelendi") bulunur. İlan detay sayfalarında schema.org JobPosting JSON-LD bloğu vardır (unvan, "Genel Yetkinlikler" + "İŞ TANIMI" içeren açıklama, nitelikler, ilan tarihi, çalışma şekli, firma, konum, maaş — açıklanmamışsa "-"). Sektör dizini (`/sektore-gore-is-ilanlari`) sektörleri şehir/ilçe bağlantılarıyla karıştırdığı için ayrıştırma 81 il slug kümesine göre filtreler. Şehir adları slug'laştırılır (İstanbul → istanbul). Aktarım Chrome TLS taklidi kullanır (`curl-cffi`, `chrome120`); istekler ~0,8 sn arayla; her şey salt okunurdur.

## Kurulum

```bash
uvx secretcv-mcp        # doğrudan çalıştır (uv gerekir)
# veya
pip install secretcv-mcp
secretcv-mcp    # MCP sunucusunu stdio üzerinde başlatır
```

## Testler

```bash
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

Çevrimdışı testler kaydedilmiş gerçek sayfalarla çalışır (2026-11-07'de çekildi); canlı testler secretcv.com'a bağlanır. Derleme anında 25/25 yeşil (16 çevrimdışı + 9 canlı) + MCP stdio duman testi.

## Yol haritası

- İkinci sayfa listeleri (sitede sunucu taraflı sayfalama bağlantısı yok; "daha fazla yükle" API'si gerekir)
- Firma sayfaları (`/firma/<slug>-is-ilanlari`: bir işverenin tüm ilanları)
- Anahtar kelime/şehir başına maaş istatistikleri (ilanların çoğu maaş açıklamaz)

## Lisans

MIT — bkz. [LICENSE](LICENSE).
