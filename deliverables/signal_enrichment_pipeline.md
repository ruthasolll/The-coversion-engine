# Signal Enrichment Pipeline (Rubric Evidence)

This document is fixture-based evidence for the Signal Enrichment Pipeline rubric.
It documents coverage, compliance, and structured output for the five required signals.

## 1) Coverage

Implemented source modules:
- Crunchbase loader: `enrichment/tenacious/crunchbase.py`
- Job-post loader (Playwright): `enrichment/tenacious/jobs.py`
- Layoffs loader: `enrichment/tenacious/layoffs.py`
- Leadership-change loader: `enrichment/tenacious/leadership.py`
- AI maturity scoring: `enrichment/tenacious/ai_maturity.py`

Merged artifact schema and fixture sample:
- Schema: `knowledge_base/tenacious_sales_data/schemas/hiring_signal_brief.schema.json`
- Fixture sample: `knowledge_base/tenacious_sales_data/schemas/sample_hiring_signal_brief.json`

## 2) Compliance (Playwright)

Job-post scraping uses Playwright on public pages only.
No login logic, cookie/session bypass, or captcha-bypass code is implemented in `enrichment/tenacious/jobs.py`.

## 3) Output Contract (Structured Artifact)

The required output is the `hiring_signal_brief` structured artifact.
Below are the five rubric signals with exact field names and fixture sample values.

### Signal A: Crunchbase firmographics
- `crunchbase_firmographics.industry_tags`: `["fintech", "payments", "b2b"]`
- `crunchbase_firmographics.employee_band`: `"51-200"`
- `crunchbase_firmographics.hq`: `"Nairobi, Kenya"`
- `crunchbase_firmographics.last_funding_stage`: `"series_b"`
- `crunchbase_firmographics.total_funding_usd`: `26000000`
- `crunchbase_firmographics.signal_confidence`: `0.88`

### Signal B: Job-post velocity (Playwright)
- `hiring_velocity.open_roles_today`: `11`
- `hiring_velocity.open_roles_60_days_ago`: `4`
- `hiring_velocity.velocity_label`: `"doubled"`
- `hiring_velocity.sources`: `["builtin", "wellfound", "company_careers_page"]`
- `hiring_velocity.signal_confidence`: `0.85`

### Signal C: Layoffs.fyi
- `buying_window_signals.layoff_event.detected`: `false`
- `buying_window_signals.layoff_event.source_url`: `"https://layoffs.fyi/company/orrin-labs"`
- `buying_window_signals.layoff_event.signal_confidence`: `0.66`

### Signal D: Leadership-change detection
- `buying_window_signals.leadership_change.detected`: `false`
- `buying_window_signals.leadership_change.source_url`: `"https://www.linkedin.com/company/orrin-labs/people/"`
- `buying_window_signals.leadership_change.signal_confidence`: `0.74`

### Signal E: AI maturity scoring
- `ai_maturity.score`: `2`
- `ai_maturity.confidence`: `0.7`
- `ai_maturity.justifications[0].signal`: `"ai_adjacent_open_roles"`
- `ai_maturity.justifications[0].weight`: `"high"`
- `ai_maturity.justifications[0].confidence`: `"high"`

## 4) Per-Signal Confidence Summary

All five rubric signals include explicit confidence fields in the schema/sample:
- Crunchbase: `crunchbase_firmographics.signal_confidence`
- Job-post velocity: `hiring_velocity.signal_confidence`
- Layoffs.fyi: `buying_window_signals.layoff_event.signal_confidence`
- Leadership change: `buying_window_signals.leadership_change.signal_confidence`
- AI maturity: `ai_maturity.confidence`