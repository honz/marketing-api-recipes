# CPAS Demo Applications

Streamlit-based demo applications for [Collaborative Ads (CPAS)](https://www.facebook.com/business/help/2726187407374421) — Meta's framework that lets brands run ads on a merchant's product catalog.

## Platforms

| Platform | Description | Status |
|----------|-------------|--------|
| [Merchant Platform](merchant_platform/) | Merchants manage brand partnerships, create catalog segments, and share them with brands | Available |
| Agency Platform | Agencies onboard brand partners with CPAS merchants | Coming soon |
| Brand Portal | Brands discover merchants and request catalog access | Coming soon |

## Prerequisites

- Python 3.8+
- A Meta [Graph API access token](https://developers.facebook.com/tools/explorer/) with `business_management` permission

## Quick Start

```bash
cd cpas_demos
./install.sh          # creates venv, installs dependencies
# edit merchant_platform/config.py with your credentials
./run.sh              # launches the Merchant Platform
```

See each platform's README for detailed setup instructions.

## File Structure

```
cpas_demos/
├── install.sh                         # Setup script (venv + deps)
├── run.sh                             # Launch script
├── config.example.py                  # Shared config template
├── merchant_platform/
│   ├── config.example.py              # Merchant-specific config template
│   ├── merchant_cpas_ui.py            # Streamlit UI
│   ├── merchant_cpas_backend.py       # Backend logic
│   ├── cache.py                       # SQLite cache layer
│   └── README.md                      # Merchant platform docs
├── shared/
│   ├── cpas_api_client.py             # Graph API wrapper
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
