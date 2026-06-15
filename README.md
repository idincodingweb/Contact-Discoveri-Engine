Contact Discovery Engine 🔍
Halo bro! Saya Idin Code, dan ini proyek yang asik banget — pure Python automation tool, no UI bullshit, no AI gimmick. Langsung saya breakdown arsitekturnya dulu sebelum gelontorin kode.

🏗️ Arsitektur & Design Decisions
Why this approach?

Saya pakai layered architecture dengan separation of concerns yang jelas:

┌─────────────────────────────────────────────────┐
│  CLI Entry (main.py) — argparse + orchestrator  │
└────────────────────┬────────────────────────────┘
                     │
        ┌────────────▼────────────┐
        │   Discovery Pipeline    │
        │  (engines/pipeline.py)  │
        └────┬───────────┬────────┘
             │           │
   ┌─────────▼──┐   ┌────▼─────────┐
   │  Crawlers  │   │  Extractors  │
   │  (async)   │   │  (regex/bs4) │
   └─────────┬──┘   └────┬─────────┘
             │           │
        ┌────▼───────────▼────┐
        │  SQLite Repository  │
        │  (database/repo.py) │
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │  Exporters          │
        │  CSV / JSON / XLSX  │
        └─────────────────────┘

        
Trade-offs yang saya pilih:

Decision	Reason
httpx async sebagai primary HTTP	Lebih modern dari aiohttp, HTTP/2 support, sintaks lebih clean
aiohttp untuk fallback Bing/DuckDuckGo SERP	Kadang DDG lebih cooperative dgn aiohttp connector
BeautifulSoup4 + lxml parser	lxml = parser tercepat, bs4 = API paling ergonomis
Playwright opt-in via flag --render-js	Heavy dependency, jangan paksa load kalau gak butuh
SQLite with WAL mode	Concurrency-friendly, zero-config, perfect untuk single-machine job
Bing + DuckDuckGo HTML endpoint untuk search	Google butuh API key, Bing/DDG bisa di-scrape dari HTML SERP
Resume via crawl_logs table	Setiap URL yang sudah di-fetch dicatat → restart skip URL yg done


📁 Project Structure

contact_discovery_engine/
├── main.py
├── requirements.txt
├── README.md
├── .github/
│   └── workflows/
│       └── discover.yml
├── engines/
│   ├── __init__.py
│   ├── pipeline.py
│   ├── search_engine.py
│   └── url_resolver.py
├── crawlers/
│   ├── __init__.py
│   ├── async_crawler.py
│   ├── sitemap_crawler.py
│   └── playwright_crawler.py
├── extractors/
│   ├── __init__.py
│   ├── email_extractor.py
│   ├── phone_extractor.py
│   ├── social_extractor.py
│   ├── person_extractor.py
│   └── role_classifier.py
├── database/
│   ├── __init__.py
│   ├── schema.sql
│   └── repo.py
├── exporters/
│   ├── __init__.py
│   └── exporter.py
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   ├── http.py
│   ├── url.py
│   ├── cache.py
│   └── ratelimit.py
├── outputs/
│   └── .gitkeep
└── tests/
    ├── __init__.py
    ├── test_extractors.py
    └── test_url.py

    
