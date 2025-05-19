"""
This script retrieves signals health details for a given business portfolio.
"""

import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from facebook_business.api import FacebookAdsApi
from utils.constants import (
    APP_ID as app_id,
    APP_SECRET as app_secret,
    BUSINESS_ID as business_id,
)
from utils.test_creds import LL_ACCESS_TOKEN as access_token
from stats_for_dashboards.helpers import get_integration_quality_for_datasets, get_pixels_for_business_id, get_spend_for_pixels, get_stats_and_settings_for_pixels, plot_moving_average, calculate_moving_average, print_and_log

sys.path.append(
    "/opt/homebrew/lib/python2.7/site-packages"
)  # Replace this with the place you installed facebookads using pip
sys.path.append(
    "/opt/homebrew/lib/python2.7/site-packages/facebook_business-3.0.0-py2.7.egg-info"
)  # same as above
sys.path.append("..")  # Add parent directory to path for imports

def main():
    RUN_ID = str(abs(hash(time.time())))[:8]
    print_and_log(RUN_ID, "Signals health dashboard beginning.")
    
    FacebookAdsApi.init(app_id, app_secret, access_token)
    today = datetime.now().date()
    since = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    until = today.strftime('%Y-%m-%d')
    pixels = get_pixels_for_business_id(business_id, RUN_ID, True)
    spend = get_spend_for_pixels(pixels, business_id, since, until, RUN_ID, True)
    stats = get_stats_and_settings_for_pixels(pixels, RUN_ID, True)
    
    # TODO: Integration Quality API
    # integration_quality = get_integration_quality_for_datasets(pixels, RUN_ID, True)
    
    # Save pixels, spend, and stats
    with open("signals_health_dashboard.csv", "w") as f:
        f.write("pixel_id,date,spend,stats,match_rate,event_stats,automatic_matching_fields,checks\n")
        for pixel in pixels:
            pixel_id = pixel["id"]
            f.write(f"{pixel_id},{until},{spend[pixel_id]},{stats[pixel_id]['stats']},{stats[pixel_id]['match_rate']},{stats[pixel_id]['event_stats']},{stats[pixel_id]['automatic_matching_fields']},{stats[pixel_id]['checks']}\n")
    
    print_and_log(RUN_ID, "Signals health dashboard complete")

if __name__ == "__main__":
    main()
