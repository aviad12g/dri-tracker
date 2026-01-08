# DRI Tracker (Dissident Resonance Index)

A research-grade OSINT monitoring dashboard that quantifies and visualizes online extremist movement activity through aggregate metrics and trend analysis.

## Overview

The DRI (Dissident Resonance Index) is a composite 0-100 index that measures:
- **V_score (Virality)**: How widely ideas are spreading across platforms
- **R_score (Radicalization)**: How deep audiences are moving into fringe platforms
- **S_score (Search Interest)**: Changes in search volume for tracked keywords
- **P_score (Political Signal)**: Political mainstreaming indicators

## Architecture

```
/backend      - Python FastAPI backend (ingest, compute, API)
/frontend     - Next.js dashboard with Tailwind CSS
/db           - PostgreSQL migrations
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+

### Setup

1. Clone and configure environment:
```bash
cp .env.sample .env
# Edit .env with your API keys and database credentials
```

2. Setup database:
```bash
cd db
psql -U postgres -c "CREATE DATABASE dri_tracker;"
psql -U postgres -d dri_tracker -f migrations/001_initial_schema.sql
```

3. Install backend dependencies:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

4. Install frontend dependencies:
```bash
cd frontend
npm install
```

5. Seed demo data:
```bash
cd backend
python -m dri.seed
```

6. Run the application:
```bash
# Terminal 1: Backend
cd backend
uvicorn dri.api:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

Visit http://localhost:3000 to view the dashboard.

## CLI Commands

```bash
# Ingest data for a specific date
python -m dri.ingest --date 2025-01-15

# Compute DRI for a specific date
python -m dri.compute --date 2025-01-15

# Run both ingest and compute for yesterday
python -m dri.daily_job
```

## API Keys Required

| Platform | Key Type | Required | Notes |
|----------|----------|----------|-------|
| YouTube | Data API v3 | Yes | Free tier usually sufficient |
| Telegram | API ID + Hash | Yes | Via my.telegram.org |
| Google Trends | - | No | Uses pytrends library |
| X/Twitter | - | No | Manual CSV upload supported |
| TikTok | - | No | Manual CSV upload supported |
| Rumble | - | No | Manual CSV upload supported |

## Manual Data Upload Format

For platforms without API access (X, TikTok, Rumble), upload CSV files with this format:

```csv
date,actor_id,platform,followers,views_total,shares_total,likes_total,comments_total
2025-01-15,fuentes_nick,x,500000,1500000,25000,75000,12000
```

## Data Quality Model

Each day's computation includes a quality assessment:
- **Verified**: Data from official APIs with full coverage
- **Partial**: Some platforms/actors missing
- **Estimated**: Significant data gaps or manual entries

The dashboard displays quality badges and the `dri_daily.data_quality_summary` field stores detailed JSON.

## Formulas

### Virality Velocity (V_vir)
```
V_vir(d) = SUM[ W_A(actor) * W_P(platform) * ((Views + 10*Shares) / 1) * ln(Followers) ]
```

### Radicalization Coefficient (R_rad)
```
R_rad(d) = (TelegramViews + RumblePeakConcurrents) / XFeederImpressions * 100
```

### Search Interest Delta (delta_S)
```
delta_S(d) = (Vol_hard(d) - mean_baseline) / std_baseline
```

### Political Signal (Pol)
```
Pol(d) = clip(SUM[score_delta for events on day], 0, 5)
P_score(d) = 20 * Pol
```

### Master Index
```
DRI(d) = 0.4*V_score + 0.3*R_score + 0.2*S_score + 0.1*P_score
```

## Configuration

Actor tier weights:
- mega: 1.0
- core: 1.5
- prop: 1.2
- control: 0.0 (excluded from DRI)

Platform weights:
- tiktok, youtube_short, reels: 1.0
- x: 1.2
- rumble, telegram, cozy: 1.5

## Assumptions & Design Decisions

1. **Daily granularity**: All metrics computed per-day, not real-time
2. **Rolling normalization**: 90-day rolling window for Z-score calculations
3. **Missing data handling**: Missing values flagged but computation continues
4. **Control actors**: Included in data but excluded from DRI calculation
5. **Keyword regions**: US and GLOBAL supported, US is default
6. **Date handling**: All dates in UTC

## Scheduling (Production)

Use cron or systemd to run the daily job:

```bash
# Run at 6 AM UTC daily
0 6 * * * cd /path/to/backend && /path/to/venv/bin/python -m dri.daily_job >> /var/log/dri/daily.log 2>&1
```

## Security Notes

- This system is for OSINT research only
- Only public data is collected
- No personal identification or doxxing capabilities
- Aggregate metrics only, no individual user tracking
- Platform ToS respected

## License

MIT License - For research and analysis purposes only.


