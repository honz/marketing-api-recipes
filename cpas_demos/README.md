# CPAS Demo Applications

Two Streamlit-based demo applications for Collaborative Ads (CPAS):

1. **Agency Platform** - For agencies (like WPP, GoKwik) to onboard brand partners with CPAS merchants
2. **Merchant Platform** - For merchants (like Swiggy, Zepto) to enable brand self-service onboarding

## Quick Start

### 1. Install Dependencies

```bash
pip install streamlit pandas requests
```

### 2. Configure Credentials (Optional)

Edit `config.py` to store your credentials. If configured, the UI will use these values automatically.

```python
# config.py

# Access token (get from Graph API Explorer)
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN_HERE"

# Agency Platform settings
AGENCY_BUSINESS_ID = "YOUR_AGENCY_BM_ID"
DEFAULT_BRAND_BUSINESS_ID = "YOUR_BRAND_BM_ID"
DEFAULT_BRAND_NAME = "Your Brand Name"
DEFAULT_CONTACT_EMAIL = "contact@example.com"
DEFAULT_CONTACT_NAME = "Contact Name"

# Merchant Platform settings
MERCHANT_BUSINESS_ID = "YOUR_MERCHANT_BM_ID"
MERCHANT_NAME = "Your Merchant Name"

# Merchant Business Manager IDs
MERCHANT_BM_IDS = {
    "blinkit": "BLINKIT_BM_ID",
    "swiggy": "SWIGGY_BM_ID",
    "zepto": "ZEPTO_BM_ID",
    "bigbasket": "BIGBASKET_BM_ID",
    "amazon_fresh": "AMAZON_FRESH_BM_ID",
}
```

Alternatively, set environment variables:
```bash
export CPAS_ACCESS_TOKEN="your_token"
export CPAS_AGENCY_BM_ID="your_agency_bm_id"
export CPAS_BRAND_BM_ID="your_brand_bm_id"
export CPAS_MERCHANT_BM_ID="your_merchant_bm_id"
export CPAS_SWIGGY_BM_ID="swiggy_bm_id"
# etc.
```

### 3. Run the Demos

**Agency Platform:**
```bash
cd cpas_demos
streamlit run agency_platform/agency_cpas_ui.py
```

**Merchant Platform:**
```bash
cd cpas_demos
streamlit run merchant_platform/merchant_cpas_ui.py
```

If credentials are not configured in `config.py`, you'll be prompted to enter them in the UI sidebar.

## Configuration Details

### Config File vs UI Input

| Config Value Set | UI Behavior |
|------------------|-------------|
| `ACCESS_TOKEN` set | Token loaded from config, no input shown |
| `ACCESS_TOKEN` not set | Token input field shown in sidebar |
| `AGENCY_BUSINESS_ID` set | BM ID loaded from config, no input shown |
| Other fields | Input shown with default value from config |

### Access Token Requirements

Your access token needs:
- `business_management` permission
- `ads_management` permission (for campaign creation)
- Admin access to the relevant Business Managers

Generate a token at: https://developers.facebook.com/tools/explorer/

## Features

### Agency Platform

| Tab | Description |
|-----|-------------|
| **Overview** | Onboarding progress dashboard |
| **Partner Discovery** | Browse and select CPAS merchants (Blinkit, Swiggy, Zepto, etc.) |
| **Connection Requests** | Send and track collaboration requests |
| **Ad Account Setup** | Create collab ad accounts and attach catalog segments |
| **Campaign Launch** | Create CPAS campaigns with catalog sales objective |

### Merchant Platform

| Tab | Description |
|-----|-------------|
| **Dashboard** | View partnership statistics |
| **Pending Requests** | Review and approve/reject brand requests |
| **Active Partners** | Manage active brand partnerships |
| **Catalog Segments** | Share catalog segments with brands |
| **Brand Self-Service** | Step-by-step onboarding wizard for brands |

## File Structure

```
cpas_demos/
├── __init__.py
├── README.md
├── config.py                       # Configuration file (credentials, BM IDs)
├── agency_platform/
│   ├── __init__.py
│   ├── agency_cpas_ui.py           # Streamlit UI
│   └── agency_cpas_backend.py      # Backend logic
├── merchant_platform/
│   ├── __init__.py
│   ├── merchant_cpas_ui.py         # Streamlit UI
│   └── merchant_cpas_backend.py    # Backend logic
├── shared/
│   ├── __init__.py
│   ├── cpas_api_client.py          # Graph API wrapper
│   ├── merchants.py                # Merchant configurations
│   └── constants.py                # Constants and enums
└── tests/
    ├── __init__.py
    └── test_cpas_api_client.py     # Unit tests
```

## Running Tests

```bash
cd cpas_demos
python -m pytest tests/ -v

# Or with unittest
python -m unittest tests.test_cpas_api_client -v
```

## API Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/{business_id}/collaborative_ads_collaboration_requests` | POST | Send collab request |
| `/{business_id}/collaborative_ads_collaboration_requests` | GET | List requests |
| `/{request_id}` | POST | Approve/reject request |
| `/{business_id}/owned_product_catalogs` | GET | Get owned catalogs |
| `/{business_id}/client_product_catalogs` | GET | Get shared catalogs |
| `/{business_id}/adaccount` | POST | Create ad account |
| `act_{ad_account_id}/campaigns` | POST | Create campaign |
| `act_{ad_account_id}/adsets` | POST | Create ad set |

## Security Notes

- **Do not commit `config.py` with real credentials to version control**
- Add `cpas_demos/config.py` to your `.gitignore`
- Use environment variables for production deployments

## Notes

- All campaigns are created in **PAUSED** status
- ID columns are handled as strings to prevent JavaScript integer overflow
- Default currency is INR (Indian Rupees)
- Default timezone is Asia/Kolkata
