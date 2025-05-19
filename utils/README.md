# Utility Functions

This directory contains utility functions and constants used throughout the Marketing API recipes.

## Files
- `constants.py` - Common constants like API keys and account IDs
- `demo_utils.py` - Utility functions for demos, including logging
- `test_creds.py` - Test credentials for API access
- `setup_meta_env.sh` - Setup script for environment variables

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
| META_BUSINESS_ID | Meta Business ID | 123 |

## Setup Scripts

### Quick Setup

The easiest way to set up environment variables is to use the provided setup script:

1. Edit `setup_meta_env.sh` with your API credentials
2. Run the script using source:
   ```bash
   source utils/setup_meta_env.sh
   ```

### Long-Lived Access Token Generation

For better security and convenience, use the long-lived token generation script:

```bash
cd /path/to/marketing-api-recipes
./get_long_lived_token.py [short_lived_token]
```

This script:
- Exchanges a short-lived token for a long-lived token (60-day validity)
- Updates your shell configuration file
- Sets the META_ACCESS_TOKEN environment variable

### Manual Setup

You can also set these variables manually in your shell before running any script:

```bash
export META_APP_ID=your_app_id
export META_APP_SECRET=your_app_secret
export META_AD_ACCOUNT_ID=act_your_ad_account_id
export META_PAGE_ID=your_page_id
export META_CATALOG_ID=your_catalog_id
export META_ACCESS_TOKEN=your_access_token
```

When the scripts run, they will output which values they're using (either from environment variables or defaults).