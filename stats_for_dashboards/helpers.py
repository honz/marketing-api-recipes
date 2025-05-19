import sys
import os
from collections import defaultdict
from facebook_business.adobjects.business import Business
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.dataset import Dataset
import matplotlib.pyplot as plt

def print_and_log(run_id: str, message: str):
    # Print the message to the console
    print(message)

    # Get root directory path
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_path = os.path.join(root_dir, "demo_out.log")

    # Log the message to demo_out.log with run_id
    with open(log_path, "a") as log_file:
        log_file.write(f"{run_id}: {message}\n")
        
def get_catalogs_for_business_id(business_id, run_id, should_log=False):
    """
    Fetches all owned and client catalogs for a given business
    """
    business = Business(business_id)
    owned_catalogues = business.get_owned_product_catalogs()
    client_catalogues = business.get_client_product_catalogs()

    if should_log:
        print_and_log(
            run_id,
            f"Found {len(owned_catalogues)} owned catalogs and {len(client_catalogues)} client catalogs for business {business_id}\n",
        )
    return list(owned_catalogues) + list(client_catalogues)


def get_ad_accounts_for_business_id(business_id, run_id, should_log=False):
    """
    Fetches all owned and client ad accounts for a given business
    """
    business = Business(business_id)
    owned_ad_accounts = business.get_owned_ad_accounts()
    client_ad_accounts = business.get_client_ad_accounts()

    if should_log:
        print_and_log(
            run_id,
            f"Found {len(owned_ad_accounts)} owned ad accounts and {len(client_ad_accounts)} client ad accounts for business {business_id}\n",
        )
    return list(owned_ad_accounts) + list(client_ad_accounts)


def get_pixels_for_business_id(business_id, run_id, should_log=False):
    """
    Fetches all ads pixels for a given business
    """
    business = Business(business_id)
    pixels = business.get_ads_pixels()

    if should_log:
        print_and_log(run_id, f"Found {len(pixels)} pixels for business {business_id}\n")
    return pixels

def get_spend_for_pixels(pixels, business_id, run_id, start_time, end_time, should_log=False):
    """
    Fetches spend for all provided pixels
    Agency Starter Pack: Pixel Spend
    """
    pixel_spend = defaultdict(float)

    # Extracting ad accounts for each pixel, filtered by business ID
    pixel_to_ad_accounts = {pixel["id"]: pixel.get_ad_accounts(params={
        'business_id': str(business_id)
    }) for pixel in pixels}

    # Extracting ad sets for each ad account
    ad_account_to_ad_sets = {
        ad_account["id"]: list(map(lambda ad_set: ad_set, ad_account.get_ad_sets()))
        for _, ad_accounts in pixel_to_ad_accounts.items()
        for ad_account in ad_accounts
    }
        
    # Getting spend for each pixel by retrieving insights for each ad set
    for _, ad_sets in ad_account_to_ad_sets.items():
        for ad_set in ad_sets:
            adset_id = ad_set["id"]
            pixel_id = AdSet(adset_id).api_get(fields=['promoted_object'])
            insights = ad_set.get_insights(params={
                'date_preset': 'lifetime',
                'time_range': {'since': start_time, 'until': end_time},
                'fields': [
                    'spend',
                    'adset_id',
                ],
            })  # Assuming this method exists
            if not insights:
                continue
            insight = insights[0]
            spend = float(insight.get('spend', 0))
            pixel_spend[pixel_id] += spend

    if should_log:
        print_and_log(run_id, f"Found {len(pixel_spend)} pixels with spend\n")
        for pixel_id, spend in pixel_spend.items():
            print_and_log(run_id, f"Pixel {pixel_id} has spent {spend} USD\n")
    return pixel_spend

def get_stats_and_settings_for_pixels(pixels, run_id, should_log=False):
    """
    Fetches stats for all provided pixels
    """
    pixel_stats = defaultdict(dict)
    
    for pixel in pixels:
        pixel_id = pixel["id"]
        stats = pixel.api_get(fields=['match_rate_approx', 'event_stats', 'automatic_matching_fields'])
        pixel_stats[pixel_id]["stats"] = pixel.get_stats()
        pixel_stats[pixel_id]["match_rate"] = stats.get('match_rate_approx', 0)
        pixel_stats[pixel_id]["event_stats"] = stats.get('event_stats', {})
        pixel_stats[pixel_id]["automatic_matching_fields"] = stats.get('automatic_matching_fields', [])
        checks = pixel.get_da_checks()
        pixel_stats[pixel_id]["checks"] = checks
    
    # TODO: Integration Quality API
    
    if should_log:
        print_and_log(run_id, f"Found {len(pixel_stats)} pixels with stats\n")
        for pixel_id, stats in pixel_stats.items():
            print_and_log(run_id, f"Pixel {pixel_id} has stats {stats}\n")
    return pixel_stats

def get_integration_quality_for_datasets(datasets, run_id, should_log=False):
    """
    Fetches integration quality for a given dataset
    """
    dataset_integration_quality = defaultdict(dict)
    for dataset in datasets:
        dataset_id = dataset["id"]
        dataset_integration_quality[dataset_id] = dataset.get_integration_quality(params={
            'fields': [
                'event_match_quality',
                'event_coverage'
                'event_name'
            ]
        })
    if should_log:
        print_and_log(run_id, f"Found {len(dataset_integration_quality)} datasets with integration quality\n")
        for dataset_id, quality in dataset_integration_quality.items():
            print_and_log(run_id, f"Dataset {dataset_id} has integration quality {quality}\n")
    return dataset_integration_quality

def get_stats_for_catalogs(catalogs, run_id, should_log=False) -> dict:
    """
    Fetches stats for all provided catalogs
    """
    catalog_stats = defaultdict(dict)
    
    for catalog in catalogs:
        catalog_id = catalog["id"]
        stats = catalog.api_get(fields=['product_count'])
        catalog_stats[str(catalog_id)]["stats"] = catalog.get_stats()
        catalog_stats[str(catalog_id)]["diagnostics"] = catalog.get_diagnostics()
        catalog_stats[str(catalog_id)]["product_count"] = stats.get('product_count', 0)
    
    if should_log:
        print_and_log(run_id, f"Found {len(catalog_stats)} catalogs with stats\n")
        for catalog_id, stats in catalog_stats.items():
            print_and_log(run_id, f"Catalog {catalog_id} has stats {stats}\n")
    return catalog_stats

def calculate_moving_average(data, window_size):
    """
    Calculates the moving average of a list of data points
    """
    moving_average = []
    for i in range(len(data)):
        if i < window_size:
            moving_average.append(sum(data[:i + 1]) / (i + 1))
        else:
            moving_average.append(sum(data[i - window_size + 1 : i + 1]) / window_size)
    return moving_average

def plot_moving_average(data, window_size, title, x_label, y_label):
    """
    Plots the moving average of a list of data points
    """
    moving_average = calculate_moving_average(data, window_size)
    plt.plot(moving_average, label="Moving Average")
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.legend()
    plt.show()
