"""
This script retrieves reels performant details for a given business portfolio.
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
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.ad import Ad
from stats_for_dashboards.helpers import get_ad_accounts_for_business_id
from utils.constants import (
    AD_ACCOUNT_ID as ad_account_id,
    APP_ID as app_id,
    APP_SECRET as app_secret,
    BUSINESS_ID as business_id,
)
from utils.demo_utils import print_and_log
from utils.test_creds import LL_ACCESS_TOKEN as access_token

def main():
    FacebookAdsApi.init(app_id, app_secret, access_token)
    RUN_ID = str(abs(hash(time.time())))[:8]
    print_and_log(RUN_ID, "Reels Performant Creative dashboard beginning.")

    # Extract the ad account IDs for a given business portfolio
    ad_accounts = get_ad_accounts_for_business_id(business_id, RUN_ID)

    for ad_account in ad_accounts:
        ad_account_id = ad_account["id"]
        ad_account_obj = AdAccount(f'act_{ad_account_id}')

        # Extract reels insights
        insights = ad_account_obj.get_insights(
            params={
                'level': 'ad',
                'fields': ['impressions', 'ad_id'],
                'breakdowns': ['publisher_platform', 'platform_position'],
                'filtering': [
                    {"field": "publisher_platform", "operator": "ANY", "value": ["instagram"]},
                    {"field": "platform_position", "operator": "ANY", "value": ["reels"]}
                ]
            }
        )
        print_and_log(RUN_ID, f"Ad Account ID: {ad_account_id}\n\tInsights: {insights}")

        # Apply Advantage+ Creative features
        creative = AdCreative(parent_id=ad_account_id)
        creative[AdCreative.Field.degrees_of_freedom_spec] = {
            'creative_features_spec': {
                'video_auto_crop': {
                    'enroll_status': 'OPT_IN'
                },
                'adapt_to_placement': {
                    'enroll_status': 'OPT_IN'
                },
            }
        }
        creative[AdCreative.Field.asset_feed_spec] = {
            'audios': [{'url': 'audio_url'}]  # Replace 'audio_url' with actual audio asset URL
        }
        creative.remote_create()

        # Create ads from reels
        ad = Ad(parent_id=ad_account_id)
        ad[Ad.Field.name] = 'Reels Ad'
        ad[Ad.Field.creative] = {'creative_id': creative['id']}
        ad.remote_create()

    print_and_log(RUN_ID, "Reels Performant Creative dashboard complete")

if __name__ == "__main__":
    main()
