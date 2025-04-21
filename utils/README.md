# Utility Functions

This directory contains utility functions and constants used throughout the Marketing API recipes.

## Files
- `constants.py` - Common constants like API keys and account IDs
- `demo_utils.py` - Utility functions for demos, including logging
- `test_creds.py` - Test credentials for API access

## Environment Variables

The API credentials are read from environment variables with fallbacks to default values. Set the following environment variables for your own Meta API credentials:

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| META_APP_ID | Meta App ID | 123 |
| META_APP_SECRET | Meta App Secret | "123" |
| META_AD_ACCOUNT_ID | Ad Account ID (with "act_" prefix) | "act_123" |
| META_PAGE_ID | Meta Page ID | 123 |
| META_CATALOG_ID | Product Catalog ID | 123 |
| META_ACCESS_TOKEN | Long-lived access token | Placeholder token |

You can set these variables in your shell before running any script:

```bash
export META_APP_ID=your_app_id
export META_APP_SECRET=your_app_secret
export META_AD_ACCOUNT_ID=act_your_ad_account_id
export META_PAGE_ID=your_page_id
export META_CATALOG_ID=your_catalog_id
export META_ACCESS_TOKEN=your_access_token
```

When the scripts run, they will output which values they're using (either from environment variables or defaults).