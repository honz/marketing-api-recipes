#!/bin/bash
# Script to set up Meta API environment variables for marketing-api-recipes demos
# Run with: source ~/marketing-api-recipes/utils/setup_meta_env.sh

# Default values (replace with your actual values)
META_APP_ID=${META_APP_ID:-"your_app_id_here"}
META_APP_SECRET=${META_APP_SECRET:-"your_app_secret_here"}
META_AD_ACCOUNT_ID=${META_AD_ACCOUNT_ID:-"act_your_ad_account_id_here"}
META_PAGE_ID=${META_PAGE_ID:-"your_page_id_here"}
META_CATALOG_ID=${META_CATALOG_ID:-"your_catalog_id_here"}
META_ACCESS_TOKEN=${META_ACCESS_TOKEN:-"your_access_token_here"}
META_BUSINESS_ID=${META_BUSINESS_ID:-"your_business_id_here"}

# Export environment variables
export META_APP_ID
export META_APP_SECRET
export META_AD_ACCOUNT_ID
export META_PAGE_ID
export META_CATALOG_ID
export META_ACCESS_TOKEN
export META_BUSINESS_ID
# Print confirmation message
echo "Meta API environment variables set:"
echo "-----------------------------------"
echo "META_APP_ID: $META_APP_ID"
echo "META_APP_SECRET: ${META_APP_SECRET:0:3}${'*' * ${#META_APP_SECRET[@]} > 3 ? ${#META_APP_SECRET[@]} - 3 : 0}"
echo "META_AD_ACCOUNT_ID: $META_AD_ACCOUNT_ID"
echo "META_PAGE_ID: $META_PAGE_ID"
echo "META_CATALOG_ID: $META_CATALOG_ID"
echo "META_ACCESS_TOKEN: ${META_ACCESS_TOKEN:0:10}...${META_ACCESS_TOKEN: -4}"
echo "META_BUSINESS_ID: $META_BUSINESS_ID"
echo ""
echo "Note: Edit this file to add your actual API credentials"
echo "To update your access token with a long-lived token, run:"
echo "cd ~/marketing-api-recipes && ./get_long_lived_token.py"
echo ""
echo "Remember to run this script with 'source' to set variables in your current shell:"
echo "source ~/marketing-api-recipes/utils/setup_meta_env.sh"
