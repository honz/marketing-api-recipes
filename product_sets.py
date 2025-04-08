"""
Keys
    $apparelTypes = vec[
      'TEE', // T-shirt
      'JKT', // Jacket
      'PNT', // Pants
      'SHT', // Shirt
      'SKT', // Skirt
      'DRS', // Dress
      'SWR', // Sweater
      'HAT', // Hat
      'CAP', // Cap
      'VST', // Vest
      'BLZ', // Blazer
      'COT', // Coat
      'SCK', // Socks
      'TIE', // Tie
      'BRC', // Bracelet
      'BRF', // Briefs
      'BRA', // Bra
      'BLT', // Belt
      'BTS', // Boots
      'BAG', // Bag
    ];
    $sizes = vec[
      'XS', // Extra Small
      'SM', // Small
      'MD', // Medium
      'LG', // Large
      'XL', // Extra Large
    ];
    $colors = vec[
      'BLK', // Black
      'WHT', // White
      'RED', // Red
      'BLU', // Blue
      'GRN', // Green
      'YLW', // Yellow
      'PNK', // Pink
      'GRY', // Gray
      'BRN', // Brown
      'ORG', // Orange
    ];
    $regions = vec[
      'NA', // North America
      'EU', // Europe
      'AP', // Asia Pacific
      'LAT', // Latin America
    ];
"""

import sys
import time

sys.path.append(
    "/opt/homebrew/lib/python2.7/site-packages"
)  # Replace this with the place you installed facebookads using pip
sys.path.append(
    "/opt/homebrew/lib/python2.7/site-packages/facebook_business-3.0.0-py2.7.egg-info"
)  # same as above

from constants import (
    APP_ID as app_id,
    APP_SECRET as app_secret,
    CATALOG_ID as catalog_id,
)
from demo_utils import print_and_log
from facebook_business.adobjects.productcatalog import ProductCatalog
from facebook_business.adobjects.productset import ProductSet
from facebook_business.api import FacebookAdsApi
from test_creds import LL_ACCESS_TOKEN as access_token


# Initialize the Facebook API
FacebookAdsApi.init(app_id, app_secret, access_token)

RUN_ID = str(abs(hash(time.time())))[:8]

print_and_log(RUN_ID, "Product set creation beginning.")


def create_product_set(catalog_id, product_set_name, skus):
    catalog = ProductCatalog(catalog_id)
    filter_criteria = {"retailer_id": {"is_any": skus}}
    params = {"name": product_set_name, "filter": filter_criteria}
    product_set = catalog.create_product_set(fields=[], params=params)
    print_and_log(
        RUN_ID, f"Product Set '{product_set_name}' created with ID: {product_set['id']}"
    )


# Example usage
skus_list = [
    "DRS-MD-BLU-NA",
    "HAT-XL-PNK-NA",
    "BAG-XS-BRN-NA",
]
create_product_set(catalog_id, "My Product Set", skus_list)

print_and_log(RUN_ID, "Product set creation end.")
