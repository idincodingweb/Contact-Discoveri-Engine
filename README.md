# Contact Discovery Engine

Pure-Python automation tool to find decision-maker contacts from companies / niches / domains and export them to CSV/JSON/XLSX.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# optional JS rendering:
python -m playwright install chromium
```

## Usage

```bash
# By niche keyword
python main.py --keyword "Dental Marketing Agency" --country US --max-results 20

# By domain
python main.py --domain nike.com

# Full URL
python main.py --website https://www.acme.com

# Batch from file (one keyword/domain per line)
python main.py --input-file targets.txt

# Resume an interrupted job
python main.py --keyword "Apparel Store Indonesia" --resume

# With Playwright (SPA-heavy sites)
python main.py --domain example-spa.com --render-js
```

## Outputs

* `outputs/results.csv`
* `outputs/results.json`
* `outputs/results.xlsx`
* `outputs/contacts.db` (SQLite — full data including discoveries & crawl_logs)

## GitHub Actions

Trigger manually via the **Contact Discovery** workflow with custom inputs, or wait for the nightly schedule. Results are uploaded as a workflow artifact.

## Architecture

`main.py` → `engines/pipeline.py` → `crawlers/*` + `extractors/*` → `database/repo.py` → `exporters/exporter.py`.
