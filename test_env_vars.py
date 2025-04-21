#!/usr/bin/env python
"""
Simple script to test that environment variables are being loaded correctly.
Run this script to verify that your environment variables are set up properly.
"""

from utils.constants import APP_ID, APP_SECRET, AD_ACCOUNT_ID, PAGE_ID, CATALOG_ID
from utils.test_creds import LL_ACCESS_TOKEN

print("\nMeta API Credentials Check:")
print("===========================")
print(f"APP_ID: {APP_ID}")
print(f"APP_SECRET: {APP_SECRET[:3]}{'*' * (len(APP_SECRET) - 3) if len(APP_SECRET) > 3 else ''}")
print(f"AD_ACCOUNT_ID: {AD_ACCOUNT_ID}")
print(f"PAGE_ID: {PAGE_ID}")
print(f"CATALOG_ID: {CATALOG_ID}")
print(f"ACCESS_TOKEN: {LL_ACCESS_TOKEN[:10]}...{LL_ACCESS_TOKEN[-4:] if len(LL_ACCESS_TOKEN) > 14 else ''}")
print("\nTo configure these values, see utils/README.md for instructions.")
print("Set environment variables before running any scripts.")