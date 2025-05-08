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
from utils.constants import (
    AD_ACCOUNT_ID as ad_account_id,
    APP_ID as app_id,
    APP_SECRET as app_secret,
    BUSINESS_ID as business_id,
    PAGE_ID as page_id,
)
from utils.demo_utils import print_and_log
from utils.test_creds import LL_ACCESS_TOKEN as access_token


def get_business_catalogues(business_id, run_id):
    """
    Fetches all owned and client catalogues for a given business
    """
    business = Business(business_id)
    owned_catalogues = business.get_owned_product_catalogs()
    client_catalogues = business.get_client_product_catalogs()

    print_and_log(
        run_id,
        f"Found {len(owned_catalogues)} owned catalogues and {len(client_catalogues)} client catalogues for business {business_id}\n",
    )

    return list(owned_catalogues) + list(client_catalogues)


def get_ad_accounts(business_id, run_id):
    """
    Fetches all owned and client ad accounts for a given business
    """
    business = Business(business_id)

    owned_ad_accounts = business.get_owned_ad_accounts()
    client_ad_accounts = business.get_client_ad_accounts()

    print_and_log(
        run_id,
        f"Found {len(owned_ad_accounts)} owned ad accounts and {len(client_ad_accounts)} client ad accounts for business {business_id}\n",
    )

    return list(owned_ad_accounts) + list(client_ad_accounts)


def get_pixels(business_id, run_id):
    """
    Fetches all ads pixels for a given business
    """
    business = Business(business_id)
    pixels = business.get_ads_pixels()

    print_and_log(run_id, f"Found {len(pixels)} pixels for business {business_id}\n")
    return pixels
