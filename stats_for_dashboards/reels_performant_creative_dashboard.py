"""
This script retrieves reels performant details for a given business portfolio.
These statistics can be saved in a data warehouse to build a reels performant creative dashboard.
"""

import sys
import time

sys.path.append(
    "/opt/homebrew/lib/python2.7/site-packages"
)  # Replace this with the place you installed facebookads using pip
sys.path.append(
    "/opt/homebrew/lib/python2.7/site-packages/facebook_business-3.0.0-py2.7.egg-info"
)  # same as above
sys.path.append("..")  # Add parent directory to path for imports


from facebook_business.adobjects.business import Business
from facebook_business.api import FacebookAdsApi
from helpers import get_ad_accounts
from utils.constants import (
    AD_ACCOUNT_ID as ad_account_id,
    APP_ID as app_id,
    APP_SECRET as app_secret,
    BUSINESS_ID as business_id,
    PAGE_ID as page_id,
)
from utils.demo_utils import print_and_log
from utils.test_creds import LL_ACCESS_TOKEN as access_token


# Initialize the Facebook API
FacebookAdsApi.init(app_id, app_secret, access_token)

RUN_ID = str(abs(hash(time.time())))[:8]
print_and_log(RUN_ID, "Reels Performant Creative dashboard beginning.")


# Extract the ad account IDs for a given business portfolio: …/<BUSINESS_ID>/<owned/client>_ad_accounts.
ad_accounts = get_ad_accounts(business_id, RUN_ID)

# For each ad account ID, extract various insights:
for ad_account in ad_accounts:
    ad_account_id = ad_account["id"]

    insights = ad_account.get_insights()
    print_and_log(
        RUN_ID,
        f"Ad Account ID: {ad_account_id}\n\tInsights: {insights}",
    )

print_and_log(RUN_ID, "Reels Performant Creative dashboard complete")
