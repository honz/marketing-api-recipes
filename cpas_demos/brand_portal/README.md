# Brand CPAS Dashboard (Merchant-Hosted)

A web dashboard for brands to view their CPAS (Collaborative Ads) partnership status with a merchant, request new partnerships, and browse shared catalog segments. This dashboard is hosted by the merchant alongside their own merchant platform.

## Dual-Token Model

This dashboard uses two separate tokens:

- **Merchant's token** (in `config.py`) — Set by the merchant admin. Used to display the merchant name and check partnership status from the merchant's perspective. Brand reps never see or edit this file.
- **Brand's token** (entered in the UI) — Entered by the brand rep at runtime. Used for brand-side API calls: validating credentials, viewing shared catalogs, and sending collaboration requests.

The Graph API enforces access control: `client_product_catalogs` only returns catalogs shared with the calling business. A brand cannot discover or access other brands' segments.

## Prerequisites

- Python 3.8 or higher

## Install

```bash
cd cpas_demos
./install.sh
```

This creates a Python virtual environment, installs dependencies (`streamlit`, `pandas`, `requests`), and copies config templates for both merchant and brand portals.

## Configure

The merchant admin edits `brand_portal/config.py` with the merchant's credentials:

```python
ACCESS_TOKEN = "your_merchant_graph_api_token"
MERCHANT_BUSINESS_ID = "your_merchant_business_manager_id"
```

### Getting an Access Token

1. Go to the [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app
3. Add the `business_management` permission
4. Click **Generate Access Token**
5. Copy the token into `config.py`

The token needs admin access to the merchant's Business Manager.

## Run

```bash
./run_brand.sh
```

The dashboard opens in your browser at `http://localhost:8502`.

## Brand User Guide

### 1. Validate Your Credentials

Enter your brand's access token and Business Manager ID in the sidebar, then click **Validate**. Your brand name will appear once validated.

### 2. Partnership Status (Tab 1)

View your brand's relationship with the hosting merchant:

- **Active segments** — Segments you can run CPAS ads on
- **Pending segments** — Segments shared with you but awaiting acceptance (with product counts). Click **Accept** to activate a segment for CPAS campaigns.
- **No segments** — Checks for an existing collaboration request and shows its status

Pending shares are read directly from the shared SQLite database (populated by the merchant platform), so refreshing is instant with zero API calls. The brand portal only falls back to a full API sync if the database is empty (first-time bootstrap).

### 3. Request Partnership (Tab 2)

If you don't have an existing partnership, submit a collaboration request:

- Enter your contact email and name
- Click **Submit Request**
- The merchant will review and share a catalog segment once approved

### 4. Shared Catalogs (Tab 3)

Browse catalog segments shared with your brand:

- View segment name, ID, product count, and vertical
- Use the catalog ID for campaign setup in Ads Manager
- Export the list as CSV

## Troubleshooting

**"Merchant configuration not found"** — The merchant admin hasn't set up `brand_portal/config.py` yet. Copy `config.example.py` to `config.py` and fill in the merchant's credentials.

**"Invalid access token"** — Your brand's token may have expired. Generate a new one from the Graph API Explorer.

**"Invalid Brand Business Manager"** — Double-check your Business Manager ID. It should be the numeric Business Manager ID (not a page ID or ad account ID).

**No shared catalogs found** — The merchant hasn't shared any catalog segments with your brand yet. Use the Request Partnership tab to send a collaboration request.

**Port 8502 already in use** — Another app is running on that port. Stop it or run with a different port: `streamlit run brand_portal/brand_dashboard_ui.py --server.port 8503`
