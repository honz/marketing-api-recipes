import sys
import time

sys.path.append(
    "/opt/homebrew/lib/python2.7/site-packages"
)  # Replace this with the place you installed facebookads using pip
sys.path.append(
    "/opt/homebrew/lib/python2.7/site-packages/facebook_business-3.0.0-py2.7.egg-info"
)  # same as above

from constants import (
    AD_ACCOUNT_ID as ad_account_id,
    APP_ID as app_id,
    APP_SECRET as app_secret,
    PAGE_ID as page_id,
)
from demo_utils import print_and_log
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.api import FacebookAdsApi
from test_creds import LL_ACCESS_TOKEN as access_token

# Initialize the Facebook API
FacebookAdsApi.init(app_id, app_secret, access_token)

# Define hyperparameters
NUM_CAMPAIGNS = 1
NUM_ADSETS = 1
NUM_ADS = 3

RUN_ID = str(abs(hash(time.time())))[:8]

print_and_log(RUN_ID, "Ad setup beginning.")

# Create campaigns
for _ in range(NUM_CAMPAIGNS):
    params = {
        Campaign.Field.name: (
            f"Campaign from run {RUN_ID}"
            if NUM_CAMPAIGNS < 2
            else f"Campaign {NUM_CAMPAIGNS} from run {RUN_ID}"
        ),
        Campaign.Field.objective: Campaign.Objective.outcome_sales,
        Campaign.Field.status: "PAUSED",
        Campaign.Field.special_ad_categories: [],
    }

    campaign = AdAccount(ad_account_id).create_campaign(
        fields=[],
        params=params,
    )
    print_and_log(RUN_ID, f"Campaign {campaign.get_id()} created.")

    # Create ad sets
    for _ in range(NUM_ADSETS):
        params = {
            AdSet.Field.name: (
                f"Ad Set from run {RUN_ID}"
                if NUM_ADSETS < 2
                else f"Ad Set {NUM_ADSETS} from run {RUN_ID}"
            ),
            AdSet.Field.campaign_id: campaign.get_id(),
            AdSet.Field.daily_budget: 100,
            AdSet.Field.billing_event: AdSet.BillingEvent.impressions,
            AdSet.Field.optimization_goal: AdSet.OptimizationGoal.reach,
            AdSet.Field.bid_strategy: AdSet.BidStrategy.lowest_cost_without_cap,
            AdSet.Field.targeting: {
                "geo_locations": {
                    "countries": ["US"],
                },
            },
            AdSet.Field.status: AdSet.Status.paused,
        }
        ad_set = AdAccount(ad_account_id).create_ad_set(
            fields=[],
            params=params,
        )
        adset_id = ad_set.get_id()
        print_and_log(RUN_ID, f"Ad set {adset_id} created.")

        # Create ads
        for _ in range(NUM_ADS):
            params = {
                AdCreative.Field.name: (
                    f"Creative from run {RUN_ID}"
                    if NUM_ADS < 2
                    else f"Creative {NUM_ADS} from run {RUN_ID}"
                ),
                AdCreative.Field.object_story_spec: {
                    "page_id": page_id,
                    "link_data": {
                        "image_hash": "bf6823a7c358936b7a99e9a2efc78fc6",
                        "link": "https://scontent-sjc3-1.xx.fbcdn.net/v/t45.1600-4/474708412_120216956652780558_5968519555980627928_n.png?stp=dst-jpg_tt6&_nc_cat=101&ccb=1-7&_nc_sid=890911&_nc_ohc=_5CLqLZ2zn0Q7kNvgHHQCrj&_nc_zt=1&_nc_ht=scontent-sjc3-1.xx&_nc_gid=ABV61731dFEInDne4HOujiO&oh=00_AYBJYDTo2euGS1ahTiCuB9bFJ5KRre3TQl4JN9I9S5XZzA&oe=67973000",
                        "message": "Check out our website!",
                    },
                },
                AdCreative.Field.degrees_of_freedom_spec: {
                    "creative_features_spec": {
                        "standard_enhancements": {"enroll_status": "OPT_IN"}
                    }
                },
            }
            creative = AdAccount(ad_account_id).create_ad_creative(
                fields=[],
                params=params,
            )
            print_and_log(RUN_ID, f"Creative {creative.get_id()} created.")

            params = {
                Ad.Field.name: (
                    f"Ad from run {RUN_ID}"
                    if NUM_ADS < 2
                    else f"Ad {NUM_ADS} from run {RUN_ID}"
                ),
                Ad.Field.adset_id: ad_set.get_id(),
                Ad.Field.creative: {
                    "creative_id": creative.get_id(),
                },
                Ad.Field.status: Ad.Status.paused,
            }
            ad = AdAccount(ad_account_id).create_ad(
                fields=[],
                params=params,
            )
            print_and_log(RUN_ID, f"Ad {ad.get_id()} created.")

print_and_log(RUN_ID, "Ad setup complete")
