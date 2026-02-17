# Merchant CPAS Platform

A web dashboard for merchants to manage Collaborative Ads (CPAS) partnerships with brands. Merchants can review partnership requests, monitor active partners, create catalog segments, and share them with brand partners — all from a single interface.

## Prerequisites

- Python 3.8 or higher

## Install

```bash
cd cpas_demos
./install.sh
```

This creates a Python virtual environment, installs dependencies (`streamlit`, `pandas`, `requests`), and copies the config template.

## Configure

Edit `merchant_platform/config.py` with your credentials:

```python
ACCESS_TOKEN = "your_graph_api_token"
MERCHANT_BUSINESS_ID = "your_merchant_business_manager_id"
```

### Getting an Access Token

1. Go to the [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app
3. Add the `business_management` permission
4. Click **Generate Access Token**
5. Copy the token into `config.py`

The token needs admin access to your merchant's Business Manager.

## Run

```bash
./run.sh
```

The dashboard opens in your browser at `http://localhost:8501`.

## Features

### Dashboard

Overview of your CPAS partnership stats: pending requests, accepted partners, catalog segment count, and total partnerships. Partnership data is loaded on-demand to avoid slow startups.

### Pending Requests

View brands that have been shared a catalog segment but haven't accepted yet. Filter by status (Pending / Accepted / All) and refresh to check for updates.

### Active Partners

Browse brands that have accepted catalog segment sharing. Search by brand name, see which segments each brand has access to, and export the full list as CSV.

### Catalog Segments

View all your catalog segments and full catalogs with product counts. Segments are subsets of your catalogs created for sharing with specific brand partners.

### Create & Share

**Create a segment** — Select a parent catalog, pick one or more brands to filter by, and create a new catalog segment. The segment name is auto-suggested from the selected brands.

**Share a segment** — Select an existing segment, enter the brand's Business Manager ID, optionally set UTM parameters for tracking, and share. The brand will see the segment as a pending request on their side.

## Troubleshooting

**"Invalid access token"** — Your token may have expired. Generate a new one from the Graph API Explorer.

**"Invalid merchant Business Manager"** — Double-check the `MERCHANT_BUSINESS_ID` in your config. It should be the numeric Business Manager ID (not a page ID or ad account ID).

**No catalog segments found** — Your Business Manager may not own any product catalogs, or the catalogs may not have segments yet. Use the Create & Share tab to create one.

**Partnership data loading is slow** — The platform checks each catalog segment for partnerships via two API calls per segment. This is done in parallel but can be slow with many segments. Data is cached locally after the first load.

**Port 8501 already in use** — Another Streamlit app is running. Stop it or run with a different port: `streamlit run merchant_platform/merchant_cpas_ui.py --server.port 8502`
