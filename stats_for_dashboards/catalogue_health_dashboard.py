"""
This script retrieves catalogue health details for a given business portfolio.
These statistics can be saved in a data warehouse to build a health dashboard.
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
from helpers import get_business_catalogues
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
print_and_log(RUN_ID, "Catalogue health dashboard beginning.")


# Extract the catalogue IDs for a given business portfolio: …/<BUSINESS_ID>/<owned/client>_product_catalogues
catalogues = get_business_catalogues(business_id, RUN_ID)

# For each catalogue ID, extract various metadata:
#   Event statistics: …<CATALOG_ID>/event_stats.
#   Warnings/diagnostics: …<CATALOG_ID>/diagnostics?types=[‘EVENT_SOURCE_ISSUES’].
#   Key product metadata: …<CATALOG_ID>/products?fields=retailer ID,brand,description,name, custom_label_0,short description,color,material,pattern, size,custom_data,video_fetch_status
for catalogue in catalogues:
    catalogue_id = catalogue["id"]

    stats = catalogue.get_event_stats()
    diagnostics = catalogue.get_diagnostics()
    products = catalogue.get_products()
    print_and_log(
        RUN_ID,
        f"Catalogue ID: {catalogue_id}\n\tStats: {stats}\n\tDiagnostics: {diagnostics}\n\tProducts: {products}",
    )

print_and_log(RUN_ID, "Catalogue health dashboard complete")
