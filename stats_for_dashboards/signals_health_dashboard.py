"""
This script retrieves signals health details for a given business portfolio.
These statistics can be saved in a data warehouse to build a health dashboard.
"""

import sys
import time

from helpers import get_pixels

sys.path.append(
    "/opt/homebrew/lib/python2.7/site-packages"
)  # Replace this with the place you installed facebookads using pip
sys.path.append(
    "/opt/homebrew/lib/python2.7/site-packages/facebook_business-3.0.0-py2.7.egg-info"
)  # same as above
sys.path.append("..")  # Add parent directory to path for imports


from facebook_business.adobjects.business import Business
from facebook_business.api import FacebookAdsApi
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
print_and_log(RUN_ID, "Signals health dashboard beginning.")

# Extract the pixel IDs for a given business portfolio: …/<BUSINESS_ID>/adspixels
pixels = get_pixels(business_id, RUN_ID)

# For each pixel ID, extract various metadata:
#   Event statistics: …/<PIXEL_ID>/stats.
#   Event match quality: …/<PIXEL_ID>/integration_quality?fields=event_match_quality,event_name.
#   Pixel settings: …/<PIXEL_ID>?fields=automatic_matching_fields,checks.
for pixel in pixels:
    pixel_id = pixel["id"]
    stats = pixel.get_stats()
    print_and_log(
        RUN_ID,
        f"Pixel ID: {pixel_id}\n\tStats: {stats}",
    )

print()  # for empty new line

print_and_log(RUN_ID, "Signals health dashboard complete")
