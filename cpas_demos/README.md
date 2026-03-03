# CPAS Demo Applications

Streamlit-based demo applications for [Collaborative Ads (CPAS)](https://www.facebook.com/business/help/2726187407374421) — Meta's framework that lets brands run ads on a merchant's product catalog.

## Platforms

| Platform | Description | Status |
|----------|-------------|--------|
| [Merchant Platform](merchant_platform/) | Merchants manage brand partnerships, create catalog segments, and share them with brands | Available |
| [Agency Platform](agency_platform/) | Agencies onboard brand partners, manage collaboration requests, and create CPAS campaigns | Available |
| [Brand Portal](brand_portal/) | Brands view partnership status, request catalog access, and browse shared segments | Available |

## Prerequisites

- Python 3.8+
- A Meta [Graph API access token](https://developers.facebook.com/tools/explorer/) with `business_management` permission

## Quick Start

```bash
cd cpas_demos
./install.sh          # creates venv, installs dependencies
# edit merchant_platform/config.py with your credentials
./run.sh              # launches the Merchant Platform (port 8501)
# edit brand_portal/config.py with merchant credentials
./run_brand.sh        # launches the Brand Dashboard (port 8502)
```

See each platform's README for detailed setup instructions.

## File Structure

```
cpas_demos/
├── install.sh                         # Setup script (venv + deps)
├── run.sh                             # Launch merchant platform
├── run_brand.sh                       # Launch brand dashboard
├── merchant_platform/
│   ├── config.example.py              # Merchant-specific config template
│   ├── merchant_cpas_ui.py            # Streamlit UI
│   ├── merchant_cpas_backend.py       # Backend logic
│   ├── cache.py                       # SQLite cache layer
│   └── README.md                      # Merchant platform docs
├── brand_portal/
│   ├── config.example.py              # Brand portal config template
│   ├── brand_dashboard_ui.py          # Streamlit UI
│   ├── brand_dashboard_backend.py     # Backend logic
│   ├── cache.py                       # Session-state + SQLite cache layer
│   └── README.md                      # Brand portal docs
├── agency_platform/
│   ├── agency_cpas_ui.py              # Streamlit UI
│   └── agency_cpas_backend.py         # Backend logic
├── shared/
│   ├── __init__.py                    # Re-exports for shared modules
│   ├── cpas_api_client.py             # Graph API wrapper
│   ├── cache_db.py                    # SQLite database (shared between platforms)
│   ├── cache_manager.py               # Cached API functions with SQLite backing
│   ├── merchants.py                   # Merchant configurations
│   └── constants.py                   # Constants and enums
└── tests/
    └── test_cpas_api_client.py        # Unit tests
```

## Running Tests

```bash
cd cpas_demos
python -m pytest tests/ -v
```

## Security

- **Never commit `config.py`** — it contains access tokens. Only `config.example.py` files are tracked.
- Use environment variables for production deployments.
