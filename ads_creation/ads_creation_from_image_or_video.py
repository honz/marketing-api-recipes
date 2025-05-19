import json
import logging
import os

import requests
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adimage import AdImage
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.adspixel import AdsPixel
from facebook_business.adobjects.advideo import AdVideo
from facebook_business.adobjects.business import Business
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.targeting import Targeting
from facebook_business.adobjects.user import User as AdUser
from facebook_business.api import FacebookAdsApi
from facebook_business.exceptions import FacebookRequestError

logging.basicConfig(level=logging.INFO)


class AdsManager:
    def __init__(self, access_token):
        self.access_token = access_token
        FacebookAdsApi.init(access_token=self.access_token)

    def _format_account_id(self, account_id):
        """Formats account ID to add 'act_' prefix."""
        return f"act_{account_id}"

    def _get_campaign_by_name(self, ad_account_id, campaign_name):
        """Retrieve a campaign by its name."""
        ad_account = AdAccount(fbid=self._format_account_id(ad_account_id))
        campaigns = ad_account.get_campaigns(fields=[Campaign.Field.name])
        for campaign in campaigns:
            if campaign[Campaign.Field.name] == campaign_name:
                return campaign
        return None

    def create_image_hash(self, ad_account_id, photo_path):
        """Create an image hash for a given photo path.
        Args:
            ad_account_id (str): The ID of the ad account.
            photo_path (str): The path to the photo file.

        Returns:
            str: The image hash.
        """
        ad_account = AdAccount(fbid=self._format_account_id(ad_account_id))
        # image = AdImage(parent_id=self._format_account_id(ad_account_id))
        ad_account.create_image(params={filename: photo_path})
        image[AdImage.Field.filename] = photo_path
        image.remote_create()
        return image[AdImage.Field.hash]

    def create_campaign_if_not_exists(
        self, ad_account_id, campaign_name, promotion_type=""
    ):
        """Create a campaign if it does not already exist.

        Args:
            ad_account_id (str): The ID of the ad account.
            campaign_name (str): The name of the campaign.
            promotion_type (str, optional): The type of promotion for the campaign. Defaults to "".

        Returns:
            Campaign: The created or existing campaign.
        """
        campaign = self._get_campaign_by_name(ad_account_id, campaign_name)
        if campaign:
            print("Campaign already exists with the name: ", campaign_name)
            return campaign

        # Create new campaign
        ad_account = AdAccount(fbid=self._format_account_id(ad_account_id))
        params = {
            "name": campaign_name,
            "objective": "OUTCOME_SALES",
            "status": "PAUSED",
            "special_ad_categories": [],
            "buying_type": "AUCTION",
            "campaign_group_creation_source": "click_quick_create",
            "can_use_spend_cap": True,
            "billing_event": "IMPRESSIONS",
        }

        if promotion_type:
            params["smart_promotion_type"] = promotion_type

        try:
            campaign = ad_account.create_campaign(fields=[], params=params)
            print("Campaign created with ID: ", campaign["id"])
            return campaign
        except FacebookRequestError as e:
            print("Failed to create campaign: ", e)
            return None

    def delete_campaign(self, ad_account_id, campaign_name):
        """Delete a campaign by its name.

        Args:
            ad_account_id (str): The ID of the ad account.
            campaign_name (str): The name of the campaign.

        Returns:
            bool: True if the campaign was deleted successfully, False otherwise.
        """
        campaign = self._get_campaign_by_name(ad_account_id, campaign_name)
        if not campaign:
            print(f"No campaign found with name {campaign_name}.")
            return False

        try:
            campaign.api_delete()
            print(f"Campaign with name {campaign_name} deleted successfully.")
            return True
        except FacebookRequestError as e:
            print("Failed to delete campaign: ", e)
            return False

    def create_ad_set_if_not_exists(
        self,
        ad_account_id,
        campaign,
        adset_name,
        target=None,
        budget_setting=None,
        promoted_object={},
    ):
        """Create an AdSet if it does not already exist.

        Args:
            ad_account_id (str): The ID of the ad account.
            campaign (Campaign): The Campaign object for the AdSet.
            adset_name (str): The name of the AdSet.
            target (dict, optional): The targeting spec for the AdSet. Defaults to {}.
            budget_setting (dict, optional): The budget setting for the AdSet. Defaults to None.
            promoted_object (dict, optional): The promoted object for the AdSet. Defaults to {}.

        Returns:
            AdSet: The created or existing AdSet.
        """
        # default setting
        adset_setting = {
            AdSet.Field.name: adset_name,
            AdSet.Field.campaign_id: campaign.get_id(),
            AdSet.Field.billing_event: AdSet.BillingEvent.impressions,
            AdSet.Field.optimization_goal: AdSet.OptimizationGoal.offsite_conversions,
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            AdSet.Field.targeting: target,
        }

        # Define the Campaign
        campaign = Campaign(fbid=campaign.get_id())

        # Search for existing AdSets
        adsets = campaign.get_ad_sets(fields=[AdSet.Field.name])

        # Check if AdSet already exists
        for adset in adsets:
            if adset[AdSet.Field.name] == adset_name:
                print("AdSet already exists with the name: ", adset_name)
                return adset

        if not target:  # default values can change
            target = {
                Targeting.Field.geo_locations: {
                    "countries": ["US", "AU", "CA", "GB"],
                },
                "genders": [2],
                "age_max": 65,
                "age_min": 23,
            }

        if promoted_object:
            promoted_object = {AdSet.Field.promoted_object: promoted_object}
            adset_setting = adset_setting | promoted_object
        if budget_setting:
            adset_setting = adset_setting | budget_setting

        # If AdSet does not exist, create a new one
        try:
            ad_account = AdAccount(fbid=self._format_account_id(ad_account_id))
            adset_setting = adset_setting | {"status": AdSet.Status.paused}

            adset = ad_account.create_ad_set(params=adset_setting)
            print("AdSet created with ID: ", adset.get_id())
            return adset

        except FacebookRequestError as e:
            print("Failed to create ad set: ", e)
            return None

    def delete_ad_set(self, ad_account_id, campaign_name, adset_name):
        """Delete an AdSet.

        Args:
            ad_account_id (str): The ID of the ad account.
            campaign_name (str): The name of the campaign.
            adset_name (str): The name of the AdSet.

        Returns:
            bool: True if the AdSet was deleted successfully, False otherwise.
        """
        # Define the Ad Account
        ad_account = AdAccount(fbid="act_{}".format(ad_account_id))

        # Search for existing campaigns
        campaigns = ad_account.get_campaigns(fields=[Campaign.Field.name])

        # Iterate over campaigns to find the right one
        for campaign in campaigns:
            if campaign[Campaign.Field.name] == campaign_name:
                # Found the campaign, now look for AdSet
                adsets = campaign.get_ad_sets(fields=[AdSet.Field.name])

                # Check if AdSet with provided name exists
                for adset in adsets:
                    if adset[AdSet.Field.name] == adset_name:
                        try:
                            adset.api_delete()
                            print(f"AdSet with name {adset_name} deleted successfully.")
                            return True
                        except FacebookRequestError as e:
                            print("Failed to delete AdSet: ", e)
                            return False

        print(f"No AdSet found with name {adset_name} under campaign {campaign_name}.")
        return False

    def _get_matching_ads(self, adset, ad_name):
        """Retrieve existing Ads with the given name."""
        existing_ads = AdSet(fbid=adset.get_id()).get_ads(fields=[Ad.Field.name])
        return [ad for ad in existing_ads if ad[Ad.Field.name] == ad_name]

    def _create_ad(self, ad_account_id, adset, ad_name, ad_creative):
        """Create and return a new Ad instance.

        Args:
            ad_account_id (str): The ID of the ad account.
            adset (AdSet): The AdSet object for the Ad.
            ad_name (str): The name of the Ad.
            ad_creative (dict): The creative spec for the Ad.

        Returns:
            Ad: The created Ad.
        """

        ad_fields = {
            Ad.Field.name: ad_name,
            Ad.Field.adset_id: adset.get_id(),
            Ad.Field.creative: ad_creative,
            Ad.Field.status: "PAUSED",
        }

        ad_account = AdAccount(fbid=self._format_account_id(ad_account_id))
        ad = ad_account.create_ad(params=ad_fields)
        # ad.update(ad_fields)
        # ad.remote_create()
        return ad

    def create_ad_if_not_exists(
        self,
        ad_account_id,
        adset,
        ad_name,
        page_id,
        ad_creative_object={},
        image_path=None,
        video_path=None,
    ):
        """Create an ad if it does not already exist.

        Args:
            ad_account_id (str): The ID of the ad account.
            adset (AdSet): The AdSet object for the ad.
            ad_name (str): The name of the ad.
            page_id (int): The ID of the Facebook page.
            ad_creative_object (dict, optional): The creative object for the ad. Defaults to {}.
            image_path (str, optional): The path to the image file. Defaults to None.
            video_path (str, optional): The path to the video file. Defaults to None.

        Returns:
            Ad: The created or existing ad.
        """
        matching_ads = self._get_matching_ads(adset, ad_name)
        if matching_ads:
            print(f"Ad already exists with the name: {ad_name}")
            return matching_ads[0]

        # Create AdCreative
        # ad_creative = AdCreative(parent_id='act_{}'.format(ad_account_id))

        object_story_spec = self._build_object_story_spec(
            ad_account_id, page_id, ad_creative_object, image_path, video_path
        )
        ad_creative_fields = self._get_ad_creative_fields(ad_name, object_story_spec)

        ad_account = AdAccount(fbid=self._format_account_id(ad_account_id))
        # ad_creative.update(ad_creative_fields)
        # ad_creative.remote_create()
        # print("ad_creative_fields is {}".format(ad_creative_fields))
        # ad_creative = ad_account.create_ad_creative(params=ad_creative_fields)
        # print("ad creative successfully created {}".format(ad_creative))
        # Create the Ad
        ad = self._create_ad(ad_account_id, adset, ad_name, ad_creative_fields)
        print(f"Ad created with ID: {ad.get_id()}")
        return ad

    def _get_ad_creative_fields(self, ad_name, object_story_spec):
        """Return fields required for AdCreative.

        Args:
            ad_name (str): The name of the ad.
            object_story_spec (dict): The object story spec for the ad.

        Returns:
            dict: The fields required for AdCreative.
        """
        fields = {
            AdCreative.Field.name: ad_name,
            AdCreative.Field.object_story_spec: object_story_spec,
            "degrees_of_freedom_spec": {
                "creative_features_spec": {
                    "standard_enhancements": {"enroll_status": "OPT_IN"}
                }
            },
        }
        return fields

    def _upload_image(self, ad_account_id, image_path):
        """Upload an image and return its hash.

        Args:
            ad_account_id (str): The ID of the ad account.
            image_path (str): The path to the image file.

        Returns:
            str: The hash of the uploaded image.
        """
        ad_account = AdAccount(fbid=self._format_account_id(ad_account_id))
        # image = AdImage(parent_id='act_{}'.format(ad_account_id))
        image = ad_account.create_ad_image(params={"filename": image_path})
        # image[AdImage.Field.filename] = image_path
        # image.remote_create()
        return image["hash"]

    def _upload_video(self, ad_account_id, video_path):
        """Create a video and return its ID.

        Args:
            ad_account_id (str): The ID of the ad account.
            video_path (str): The path to the video file.

        Returns:
            int: The ID of the created video.
        """
        ad_account = AdAccount(fbid=self._format_account_id(ad_account_id))
        video = ad_account.create_ad_video(
            params={"names": os.path.basename(video_path), "source": video_path}
        )

        # video = AdVideo(parent_id='act_{}'.format(ad_account_id))
        # video[AdVideo.Field.name] = os.path.basename(video_path)
        # video[AdVideo.Field.filepath] = video_path
        # video.remote_create()
        video_id = video.get_id()
        print("video successfully created {}".format(video_id))
        return video_id

    def _build_object_story_spec(
        self, ad_account_id, page_id, ad_creative_object, image_path="", video_path=""
    ):
        """Build the object_story_spec dictionary.

        Args:
            ad_account_id (str): The ID of the ad account.
            page_id (str): The ID of the Facebook page.
            ad_creative_object (dict): The creative object for the ad.
            image_path (str, optional): The path to the image file. Defaults to "".
            video_path (str, optional): The path to the video file. Defaults to "".

        Returns:
            dict: The object_story_spec dictionary.
        """
        spec = {
            "page_id": page_id,
            "link_data": {
                "link": ad_creative_object.get("url", ""),
                "message": ad_creative_object.get("message", ""),
                "name": ad_creative_object.get("title", ""),
                "call_to_action": {
                    "type": "SHOP_NOW",
                    "value": {"link": ad_creative_object.get("url", "")},
                },
            },
        }

        if image_path and video_path:
            spec = {
                "page_id": page_id,
                "video_data": {
                    "message": ad_creative_object.get("message", ""),
                    "call_to_action": {
                        "type": "SHOP_NOW",
                        "value": {"link": ad_creative_object.get("url", "")},
                    },
                    "image_hash": self._upload_image(ad_account_id, image_path),
                    "video_id": self._upload_video(ad_account_id, video_path),
                },
            }
        elif image_path:
            spec["link_data"]["image_hash"] = self._upload_image(
                ad_account_id, image_path
            )

        return spec


# Please add the following credentials to test
ACCESS_TOKEN = ""
AD_ACCOUNT = ""
PAGE_ID = ""
PIXEL_ID = ""


if __name__ == "__main__":
    ads_manager = AdsManager(ACCESS_TOKEN)

    # how to create a manual sales campaign with age, gender, country and budget setting
    campaign_name = "Manual Sales Campaign 3"
    adset_name = "uk, us, 18-20, life time budget for next week 2"
    campaign = ads_manager.create_campaign_if_not_exists(AD_ACCOUNT, campaign_name)
    target = {
        Targeting.Field.geo_locations: {
            "countries": ["US", "AU", "CA", "GB"],
        },
        "genders": [2],
        "age_max": 65,
        "age_min": 23,
    }

    promoted_object = {"pixel_id": PIXEL_ID, "custom_event_type": "PURCHASE"}

    budget_setting = {
        "lifetime_budget": 25200,
        "start_time": "2023-11-11T23:56:24-0800",
        "end_time": "2023-12-13T23:56:24-0800",
    }  # if using daily bucet, just change lifetime_budget to daily_budget, and remove start_time and end_time

    adset = ads_manager.create_ad_set_if_not_exists(
        AD_ACCOUNT, campaign, adset_name, target, budget_setting, promoted_object
    )

    # how to create a single image ad
    ad_name = "first ad6"
    creative_object = {
        "title": "test title",
        "message": "test message",
        "url": "https://www.google.com",
    }
    image_path = "./test_image.jpg"
    ad = ads_manager.create_ad_if_not_exists(
        AD_ACCOUNT, adset, ad_name, PAGE_ID, creative_object, image_path
    )

    # how to create video ad
    ad_name = "first video ad4"
    creative_object = {
        "title": "test title",
        "message": "test message",
        "url": "https://www.baidu.com",
    }
    thumb_nail_image = "./test_image.jpg"
    video_path = "./test_video.mov"
    ad = ads_manager.create_ad_if_not_exists(
        AD_ACCOUNT,
        adset,
        ad_name,
        PAGE_ID,
        creative_object,
        thumb_nail_image,
        video_path,
    )
