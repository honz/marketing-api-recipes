import sys
import time

sys.path.append(
    "/opt/homebrew/lib/python2.7/site-packages"
)  # Replace this with the place you installed facebookads using pip
sys.path.append(
    "/opt/homebrew/lib/python2.7/site-packages/facebook_business-3.0.0-py2.7.egg-info"
)  # same as above
sys.path.append("..")  # Add parent directory to path for imports

from utils.constants import (
    AD_ACCOUNT_ID as ad_account_id,
    APP_ID as app_id,
    APP_SECRET as app_secret,
    PAGE_ID as page_id,
)
from utils.demo_utils import print_and_log
from facebook_business.adobjects.adset import AdSet
from facebook_business.api import FacebookAdsApi
from facebook_business.exceptions import FacebookRequestError
from utils.test_creds import LL_ACCESS_TOKEN as access_token

# Initialize the Facebook API
sdk = FacebookAdsApi.init(app_id, app_secret, access_token)
RUN_ID = str(abs(hash(time.time())))[:8]

print_and_log(RUN_ID, "Interpreter beginning.")


def load_adset_ids_from_input():
    user_input = input("Enter ad set IDs as a CSV of integers: ").strip()
    try:
        adset_ids = [int(id_str) for id_str in user_input.split(",")]
    except ValueError:
        print_and_log(RUN_ID, "Invalid input. Please enter a CSV of integers.")
        return []
    return adset_ids


def interpreter_loop(adset_ids):
    while True:
        command = input(
            "Enter command (b <number> for budget, s <active/inactive> for status, q to quit): "
        ).strip()

        if command.lower() == "q":
            print_and_log(RUN_ID, "Exiting...")
            break

        parts = command.split()
        if len(parts) != 2:
            print_and_log(RUN_ID, "Invalid command format. Please try again.")
            continue

        action, value = parts
        if action == "b":
            try:
                # ----------------
                # DEMO MEAT START
                # ----------------
                new_budget = int(value)
                for adset_id in adset_ids:
                    try:
                        adset = AdSet(adset_id).api_update(
                            params={AdSet.Field.daily_budget: new_budget}
                        )
                        print_and_log(
                            RUN_ID,
                            f"Ad set {adset_id} daily budget updated to {new_budget}",
                        )
                    except FacebookRequestError as e:
                        print_and_log(
                            RUN_ID,
                            f"Failed to update ad set {adset_id} daily budget: {e.api_error_message()}",
                        )
            # ----------------
            # DEMO MEAT END
            # ----------------
            except ValueError:
                print_and_log(RUN_ID, "Invalid budget value. Please enter a number.")
        elif action == "s":
            if value.lower() in ["active", "inactive"]:
                # ----------------
                # DEMO MEAT START
                # ----------------
                for adset_id in adset_ids:
                    try:
                        adset = AdSet(adset_id).api_update(
                            params={
                                AdSet.Field.status: value.upper()  # 'ACTIVE' or 'INACTIVE'
                            }
                        )
                        print_and_log(
                            RUN_ID, f"Ad set {adset_id} status updated to {value}"
                        )
                    except FacebookRequestError as e:
                        print_and_log(
                            RUN_ID,
                            f"Failed to update ad set {adset_id} status: {e.api_error_message()}",
                        )
            # ----------------
            # DEMO MEAT END
            # ----------------
            else:
                print_and_log(
                    RUN_ID, "Invalid status. Please enter 'active' or 'inactive'."
                )
        else:
            print_and_log(RUN_ID, "Unknown command. Please try again.")


# Example usage
adset_ids = load_adset_ids_from_input()
if adset_ids:
    interpreter_loop(adset_ids)
