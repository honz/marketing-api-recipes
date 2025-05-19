"""
This script retrieves catalog health details for a given business portfolio.
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

from facebook_business.api import FacebookAdsApi
from stats_for_dashboards.helpers import get_catalogs_for_business_id, get_stats_for_catalogs
from utils.constants import (
    APP_ID as app_id,
    APP_SECRET as app_secret,
    BUSINESS_ID as business_id,
)
from utils.demo_utils import print_and_log
from utils.test_creds import LL_ACCESS_TOKEN as access_token

def main():
    RUN_ID = str(abs(hash(time.time())))[:8]
    print_and_log(RUN_ID, "Catalog health dashboard beginning.")
    
    FacebookAdsApi.init(app_id, app_secret, access_token)
    catalogs = get_catalogs_for_business_id(business_id, RUN_ID, True)
    stats = get_stats_for_catalogs(catalogs, RUN_ID, True)
    
    # Save catalog and stats
    with open("catalog_health_dashboard.csv", "w") as f:
        f.write("catalog_id,stats,diagnostics,product_count\n")
        for catalog in catalogs:
            catalog_id = catalog["id"]
            f.write(f"{catalog_id},{stats[catalog_id]['stats']},{stats[catalog_id]['diagnostics']},{stats[catalog_id]['product_count']}\n")
    
    print_and_log(RUN_ID, "Catalog health dashboard complete")

if __name__ == "__main__":
    main()
