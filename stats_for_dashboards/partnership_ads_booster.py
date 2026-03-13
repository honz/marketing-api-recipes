"""
Partnership Ads Booster

This solution creates a boosting engine to automate the creation of partnership ads.

This script provides two main functionalities:
1. Fetch all advertisable medias with eligibility and permission for partnership ads
2. Create partnership ads from a CSV input file

Instructions to run:
$python3 -m venv venv
$source venv/bin/activate
$pip install requests
$python3 partnership_ads_booster.py --mode fetch --access-token YOUR_TOKEN --ig-account-id YOUR_IG_ID --creator-username CREATOR_USERNAME
$python3 partnership_ads_booster.py --mode create --access-token YOUR_TOKEN --input-csv input.csv --ig-account-id YOUR_IG_ID --ad-account-id YOUR_AD_ID --facebook-page-id YOUR_PAGE_ID

Optional flags:
--no-ssl-verify    Disable SSL certificate verification (use for testing/development only)

For Streamlit UI, set environment variable before running:
SSL_VERIFY=false streamlit run partnership_ads_ui.py
"""

import argparse
import csv
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

import requests


def get_ssl_verify_from_env() -> bool:
    """
    Get SSL verification setting from environment variable.

    Returns:
        True if SSL should be verified (default), False otherwise
    """
    env_value = os.environ.get("SSL_VERIFY", "true").lower()
    return env_value not in ("false", "0", "no", "off")


def extract_instagram_shortcode(permalink: str) -> str:
    """
    Extract Instagram shortcode from permalink.

    Handles two formats:
    1. Full URL: https://www.instagram.com/reel/aBc123XyZ/ -> aBc123XyZ
       Also supports /reels/ URLs: https://www.instagram.com/reels/aBc123XyZ/
    2. Shortcode only: aBc123XyZ -> aBc123XyZ

    Args:
        permalink: Instagram permalink (URL or shortcode)

    Returns:
        Instagram shortcode

    Raises:
        ValueError: If the permalink is a stories URL (not supported)
    """
    if not permalink:
        return permalink

    # Check if it's a stories URL
    if "/stories/" in permalink:
        raise ValueError("Stories boosting is not supported by this script")

    # Check if it's a URL
    url_pattern = (
        r"(?:https?://)?(?:www\.)?instagram\.com/(?:p|reels?|tv)/([A-Za-z0-9_-]+)"
    )
    match = re.search(url_pattern, permalink)

    if match:
        return match.group(1)

    # If not a URL, assume it's already a shortcode
    return permalink.strip("/")


def fetch_account_level_permissions(
    access_token: str,
    ig_account_id: str,
    output_csv: Optional[str] = None,
) -> List[Dict]:
    """
    Fetch all existing account-level permissions for partnership ads.

    Uses the Account-Level Permissioning API to get the list of creator accounts
    that have granted permission to the brand/advertiser account.

    API Reference: GET /{brand-ig-id}/branded_content_ad_permissions

    Args:
        access_token: Facebook/Instagram access token
        ig_account_id: Instagram account ID (brand's account)
        output_csv: Optional output CSV file path

    Returns:
        List of permission records with creator account info
    """
    print(f"Fetching account-level permissions for IG account {ig_account_id}...")

    url = f"https://graph.facebook.com/v24.0/{ig_account_id}/branded_content_ad_permissions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    params = {
        "fields": "creator_ig_id,creator_username,permission_status",
    }

    all_permissions = []

    try:
        while True:
            response = requests.get(url, headers=headers, params=params, verify=get_ssl_verify_from_env())

            if response.status_code != 200:
                print(f"Error: {response.status_code} - {response.text}")
                return []

            response_data = response.json()

            if "data" in response_data:
                permissions = response_data["data"]
                all_permissions.extend(permissions)
                print(
                    f"Fetched {len(permissions)} permissions (Total: {len(all_permissions)})"
                )

            if "paging" in response_data and "next" in response_data["paging"]:
                url = response_data["paging"]["next"]
                params = {}
            else:
                break

        if output_csv and all_permissions:
            fieldnames = ["creator_ig_id", "creator_username", "permission_status"]
            with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for permission in all_permissions:
                    writer.writerow(
                        {
                            "creator_ig_id": permission.get("creator_ig_id", ""),
                            "creator_username": permission.get("creator_username", ""),
                            "permission_status": permission.get(
                                "permission_status", ""
                            ),
                        }
                    )
            print(
                f"\nSuccessfully saved {len(all_permissions)} permissions to {output_csv}"
            )

        return all_permissions

    except requests.exceptions.RequestException as e:
        print(f"Request error occurred: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def request_account_level_permission(
    access_token: str,
    ig_account_id: str,
    creator_instagram_account: Optional[str] = None,
    creator_instagram_username: Optional[str] = None,
) -> Dict:
    """
    Request account-level permission from a creator for partnership ads.

    Uses the Account-Level Permissioning API to request permission from
    a creator to run partnership ads using their content.

    API Reference: POST /{brand-ig-id}/branded_content_ad_permissions

    Args:
        access_token: Facebook/Instagram access token
        ig_account_id: Instagram account ID (brand's account)
        creator_instagram_account: Creator's Instagram account ID (either this or creator_instagram_username is required)
        creator_instagram_username: Creator's Instagram username (either this or creator_instagram_account is required)

    Returns:
        Dict with success status and any error message
    """
    if not creator_instagram_account and not creator_instagram_username:
        return {
            "success": False,
            "error": "Either creator_instagram_account or creator_instagram_username is required",
        }

    url = f"https://graph.facebook.com/v24.0/{ig_account_id}/branded_content_ad_permissions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    data = {}
    if creator_instagram_account:
        data["creator_instagram_account"] = creator_instagram_account
    elif creator_instagram_username:
        data["creator_instagram_username"] = creator_instagram_username

    try:
        response = requests.post(url, headers=headers, json=data, verify=get_ssl_verify_from_env())
        if response.status_code == 200:
            result = response.json()
            return {"success": result.get("success", True), "error": None}
        else:
            error_message = response.text
            return {"success": False, "error": error_message}

    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def bulk_request_account_level_permissions(
    access_token: str,
    ig_account_id: str,
    input_csv: str,
    output_csv: str = "permission_request_results.csv",
    max_rows: int = 100,
) -> None:
    """
    Bulk request account-level permissions from creators using a CSV file.

    The input CSV must have either 'creator_instagram_account' or 'creator_instagram_username' column
    (or both). At least one identifier is required per row.

    Args:
        access_token: Facebook/Instagram access token
        ig_account_id: Instagram account ID (brand's account)
        input_csv: Input CSV file path with creator IDs or usernames
        output_csv: Output CSV file path for results
        max_rows: Maximum number of rows to process (default: 100)
    """
    print(f"Processing bulk permission requests from {input_csv}...")

    try:
        with open(input_csv, "r", newline="", encoding="utf-8-sig") as csvfile:
            reader = csv.DictReader(csvfile)
            rows = list(reader)

        if not rows:
            print("No data found in input CSV")
            return

        if len(rows) > max_rows:
            print(f"Error: Input CSV has {len(rows)} rows, which exceeds the limit of {max_rows}")
            print(f"Please reduce the number of rows to {max_rows} or less")
            return

        results = []
        total = len(rows)
        for idx, row in enumerate(rows, 1):
            creator_account = row.get("creator_instagram_account", "").strip()
            creator_username = row.get("creator_instagram_username", "").strip()

            if not creator_account and not creator_username:
                results.append(
                    {
                        "creator_instagram_account": creator_account,
                        "creator_instagram_username": creator_username,
                        "status": "failed",
                        "error": "Either creator_instagram_account or creator_instagram_username is required",
                    }
                )
                continue

            identifier = creator_username or creator_account
            print(f"[{idx}/{total}] Requesting permission from {identifier}...")

            result = request_account_level_permission(
                access_token,
                ig_account_id,
                creator_instagram_account=creator_account if creator_account else None,
                creator_instagram_username=(
                    creator_username if creator_username else None
                ),
            )

            results.append(
                {
                    "creator_instagram_account": creator_account,
                    "creator_instagram_username": creator_username,
                    "status": "success" if result["success"] else "failed",
                    "error": result.get("error", ""),
                }
            )

        fieldnames = [
            "creator_instagram_account",
            "creator_instagram_username",
            "status",
            "error",
        ]
        with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        successful = sum(1 for r in results if r["status"] == "success")
        failed = sum(1 for r in results if r["status"] == "failed")
        print(f"\nBulk permission request completed!")
        print(f"Successful: {successful}, Failed: {failed}")
        print(f"Results saved to {output_csv}")

    except FileNotFoundError:
        print(f"Error: Input file '{input_csv}' not found")
    except Exception as e:
        print(f"An error occurred: {e}")


def fetch_media_insights(
    access_token: str,
    media_id: str,
) -> Dict[str, Optional[int]]:
    """
    Fetch engagement metrics for a specific media.

    Args:
        access_token: Facebook/Instagram access token
        media_id: Instagram media ID

    Returns:
        Dict containing: likes, comments
        Values are None if not available for this media type
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    result = {
        "likes": None,
        "comments": None,
    }

    # Fetch basic metrics (like_count, comments_count) from media object
    try:
        media_url = f"https://graph.facebook.com/v22.0/{media_id}"
        media_params = {"fields": "like_count,comments_count"}
        response = requests.get(media_url, headers=headers, params=media_params, verify=get_ssl_verify_from_env())
        if response.status_code == 200:
            data = response.json()
            result["likes"] = data.get("like_count")
            result["comments"] = data.get("comments_count")
    except Exception as e:
        print(f"Warning: Failed to fetch metrics for media {media_id}: {e}")

    return result


class APIError(Exception):
    """Exception raised for API errors that should be retried."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")


def fetch_page_of_advertisable_medias(
    access_token: str,
    ig_account_id: str,
    creator_username: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = 25,
    only_with_permission: bool = False,
) -> Tuple[List[Dict], Optional[str]]:
    """
    Fetch a single page of advertisable medias for pagination support.

    Args:
        access_token: Facebook/Instagram access token
        ig_account_id: Instagram account ID
        creator_username: Instagram creator username (optional)
        cursor: Pagination cursor from previous request (None for first page)
        limit: Number of items per page (default 25, max 25)
        only_with_permission: If True, only include medias with partnership ad permission

    Returns:
        Tuple of (list of media dicts, next_cursor or None if no more pages)

    Raises:
        APIError: If the API returns a 5xx error (should be retried)
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    # If we have a cursor, it's a full URL from the paging.next field
    if cursor:
        url = cursor
        params = {}
    else:
        url = f"https://graph.facebook.com/v22.0/{ig_account_id}/branded_content_advertisable_medias"
        params = {
            "fields": "eligibility_errors,owner_id,permalink,id,has_permission_for_partnership_ad",
            "limit": min(limit, 25),  # API max is 25
        }
        if creator_username:
            params["creator_username"] = creator_username

    response = requests.get(url, headers=headers, params=params, verify=get_ssl_verify_from_env())

    # Raise exception for server errors (5xx) so caller can retry
    if response.status_code >= 500:
        raise APIError(response.status_code, response.text)

    # For client errors (4xx), return empty to signal end
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return [], None

    response_data = response.json()
    medias = response_data.get("data", [])

    # Apply permission filter if requested
    if only_with_permission:
        medias = [
            m for m in medias
            if m.get("has_permission_for_partnership_ad", False)
        ]

    # Get next cursor
    next_cursor = None
    if "paging" in response_data and "next" in response_data["paging"]:
        next_cursor = response_data["paging"]["next"]

    return medias, next_cursor


def fetch_all_advertisable_medias(
    access_token: str,
    ig_account_id: str,
    creator_username: Optional[str] = None,
    output_csv: str = "advertisable_medias.csv",
    limit: Optional[int] = None,
    only_with_permission: bool = False,
    include_engagement_metrics: bool = False,
) -> None:
    """
    Fetch all advertisable medias for the given Instagram account and save to CSV.

    Args:
        access_token: Facebook/Instagram access token
        ig_account_id: Instagram account ID
        creator_username: Instagram creator username (optional but recommended to avoid fetching too much data)
        output_csv: Output CSV file path
        limit: Maximum number of medias to fetch (optional, fetches all if not specified)
        only_with_permission: If True, only include medias with partnership ad permission
        include_engagement_metrics: If True, fetch engagement metrics (likes, comments, reach, impressions, saves)
    """
    creator_info = f" (creator: {creator_username})" if creator_username else ""
    print(
        f"Fetching advertisable medias for IG account {ig_account_id}{creator_info}..."
    )

    url = f"https://graph.facebook.com/v22.0/{ig_account_id}/branded_content_advertisable_medias"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    params = {
        "fields": "eligibility_errors,owner_id,permalink,id,has_permission_for_partnership_ad",
        "limit": 25,
    }

    if creator_username:
        params["creator_username"] = creator_username

    all_medias = []

    try:
        while True:
            response = requests.get(url, headers=headers, params=params, verify=get_ssl_verify_from_env())

            if response.status_code != 200:
                print(f"Error: {response.status_code} - {response.text}")
                sys.exit(1)

            response_data = response.json()

            if "data" in response_data:
                medias = response_data["data"]

                # Apply permission filter if requested
                if only_with_permission:
                    medias = [
                        m
                        for m in medias
                        if m.get("has_permission_for_partnership_ad", False)
                    ]

                all_medias.extend(medias)
                print(f"Fetched {len(medias)} medias (Total: {len(all_medias)})")

                if limit and len(all_medias) >= limit:
                    all_medias = all_medias[:limit]
                    print(f"Reached limit of {limit} medias")
                    break

            if "paging" in response_data and "next" in response_data["paging"]:
                url = response_data["paging"]["next"]
                params = {}
            else:
                break

        if not all_medias:
            print("No advertisable medias found")
            return

        csv_rows = []
        total_medias = len(all_medias)
        for idx, media in enumerate(all_medias, 1):
            row = {
                "media_id": media.get("id", ""),
                "permalink": media.get("permalink", ""),
                "owner_id": media.get("owner_id", ""),
                "has_permission_for_partnership_ad": media.get(
                    "has_permission_for_partnership_ad", False
                ),
                "eligibility_errors": json.dumps(media.get("eligibility_errors", [])),
            }

            # Fetch engagement metrics if requested
            if include_engagement_metrics:
                media_id = media.get("id")
                if media_id:
                    print(f"Fetching metrics for media {idx}/{total_medias}...")
                    metrics = fetch_media_insights(access_token, media_id)
                    row["likes"] = metrics.get("likes")
                    row["comments"] = metrics.get("comments")

            csv_rows.append(row)

        fieldnames = [
            "media_id",
            "permalink",
            "owner_id",
            "has_permission_for_partnership_ad",
            "eligibility_errors",
        ]

        # Add engagement metrics columns if they were fetched
        if include_engagement_metrics:
            fieldnames.extend(["likes", "comments"])
        with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)

        print(
            f"\nSuccessfully saved {len(csv_rows)} advertisable medias to {output_csv}"
        )

    except requests.exceptions.RequestException as e:
        print(f"Request error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)


def fetch_branded_content_advertisable_medias(
    access_token: str,
    ig_account_id: str,
    ad_code: Optional[str] = None,
    permalinks: Optional[List[str]] = None,
) -> Optional[Dict]:
    """
    Fetch eligibility information for a specific media.

    Args:
        access_token: Facebook/Instagram access token
        ig_account_id: Instagram account ID
        ad_code: Ad code for the media
        permalinks: List of permalinks

    Returns:
        Dict containing eligibility information or None
    """
    url = f"https://graph.facebook.com/v22.0/{ig_account_id}/branded_content_advertisable_medias"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    params = {
        "fields": "eligibility_errors,owner_id,permalink,id,has_permission_for_partnership_ad",
    }

    if ad_code:
        params["ad_code"] = ad_code
    elif permalinks:
        params["permalinks"] = json.dumps(permalinks)
    else:
        raise ValueError("ad_code or permalinks must be passed")

    response = requests.get(url, headers=headers, params=params, verify=get_ssl_verify_from_env())
    if response.status_code == 200:
        response_data = response.json()
        if "data" in response_data and len(response_data["data"]) > 0:
            print(f"Eligibility: {response_data['data'][0]}")
            return response_data["data"][0]
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return {"error": response.text}

    return None


def upload_instagram_video(
    access_token: str,
    ad_account_id: str,
    source_instagram_media_id: str,
    ad_code: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Upload Instagram video to ad account.

    Args:
        access_token: Facebook/Instagram access token
        ad_account_id: Ad account ID
        source_instagram_media_id: Source Instagram media ID
        ad_code: Ad code for partnership ad

    Returns:
        Tuple of (Video ID or None, Error message or None)
    """
    url = f"https://graph.facebook.com/v22.0/act_{ad_account_id}/advideos"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    params = {
        "source_instagram_media_id": source_instagram_media_id,
    }

    if ad_code:
        params["partnership_ad_ad_code"] = ad_code
        params["is_partnership_ad"] = True

    response = requests.post(url, headers=headers, params=params, verify=get_ssl_verify_from_env())
    if response.status_code == 200:
        response_data = response.json()
        if "id" in response_data:
            print(f"Video uploaded successfully with ID: {response_data['id']}")
            return response_data["id"], None
        else:
            error = "Video upload: 'id' not found in response data"
            print(f"Error: {error}")
            return None, error
    else:
        error = f"Video upload failed: {response.status_code} - {response.text}"
        print(f"Error: {error}")
        return None, error


def create_ad_creative(
    access_token: str,
    ad_account_id: str,
    facebook_page_id: str,
    ig_account_id: str,
    source_instagram_media_id: str,
    ad_code: Optional[str],
    cta_type: str,
    link: str,
    app_link: Optional[str] = None,
    product_set_id: Optional[str] = None,
    utm_parameters: Optional[str] = None,
    testimonial: Optional[str] = None,
    source_url: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Create ad creative.

    Args:
        access_token: Facebook/Instagram access token
        ad_account_id: Ad account ID
        facebook_page_id: Facebook page ID
        ig_account_id: Instagram account ID
        source_instagram_media_id: Source Instagram media ID
        ad_code: Ad code for partnership ad
        cta_type: Call to action type
        link: CTA link (mandatory)
        app_link: CTA app link (optional)
        product_set_id: Product set ID (optional)
        utm_parameters: UTM parameters in query string format (optional)
        testimonial: Testimonial text for the ad (optional)
        source_url: Source URL for the creative (optional)

    Returns:
        Tuple of (Creative ID or None, Error message or None)
    """
    url = f"https://graph.facebook.com/v23.0/act_{ad_account_id}/adcreatives"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    params = {
        "object_id": facebook_page_id,
        "facebook_branded_content": json.dumps({"sponsor_page_id": facebook_page_id}),
        "instagram_branded_content": json.dumps({"sponsor_id": ig_account_id}),
    }

    # Build CTA value object based on available parameters
    cta_value = {"link": link}
    if app_link:
        cta_value["app_link"] = app_link

    params["call_to_action"] = json.dumps(
        {
            "type": cta_type,
            "value": cta_value,
        }
    )

    branded_content = {}
    if ad_code:
        branded_content["instagram_boost_post_access_token"] = ad_code
    if testimonial:
        branded_content["testimonial"] = testimonial

    if branded_content:
        params["branded_content"] = json.dumps(branded_content)

    if ad_code:
        pass  # branded_content already set above
    elif source_instagram_media_id:
        params["source_instagram_media_id"] = source_instagram_media_id
    else:
        raise ValueError("ad_code or source_instagram_media_id must be passed")

    # Build creative_sourcing_spec if product_set_id or source_url is provided
    creative_sourcing_spec = {}
    if product_set_id:
        params["degrees_of_freedom_spec"] = json.dumps(
            {
                "creative_features_spec": {
                    "product_extensions": {"enroll_status": "OPT_IN"}
                }
            }
        )
        creative_sourcing_spec["associated_product_set_id"] = product_set_id
    if source_url:
        creative_sourcing_spec["source_url"] = source_url
    if creative_sourcing_spec:
        params["creative_sourcing_spec"] = json.dumps(creative_sourcing_spec)

    if utm_parameters:
        params["url_tags"] = utm_parameters

    try:
        response = requests.post(url, headers=headers, params=params, verify=get_ssl_verify_from_env())
        response_data = response.json()
        if response.status_code == 200:
            if "id" in response_data:
                print(f"creative_id: {response_data['id']}")
                return response_data["id"], None
            else:
                error = "Creative creation: 'id' not found in response data"
                print(f"Error: {error}")
                return None, error
        else:
            error = (
                f"Creative creation failed: {response.status_code} - {response.text}"
            )
            print(f"Error: {error}")
            return None, error
    except requests.exceptions.RequestException as e:
        error = f"Creative creation request error: {e}"
        print(error)
        return None, error
    except Exception as e:
        error = f"Creative creation unknown error: {e}"
        print(error)
        return None, error


def create_ad(
    access_token: str,
    ad_account_id: str,
    ad_name: str,
    ad_set_id: str,
    creative_id: str,
    app_id: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Create ad.

    Args:
        access_token: Facebook/Instagram access token
        ad_account_id: Ad account ID
        ad_name: Ad name
        ad_set_id: Ad set ID
        creative_id: Creative ID
        app_id: App ID for app events tracking (optional)

    Returns:
        Tuple of (Ad ID or None, Error message or None)
    """
    url = f"https://graph.facebook.com/v22.0/act_{ad_account_id}/ads"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    params = {
        "status": "PAUSED",
        "name": ad_name,
        "adset_id": ad_set_id,
        "creative": json.dumps({"creative_id": creative_id}),
    }

    # Add tracking_specs for app events if app_id is provided
    if app_id:
        params["tracking_specs"] = json.dumps([
            {
                "action.type": "app_custom_event",
                "application": app_id
            }
        ])
    try:
        response = requests.post(url, headers=headers, params=params, verify=get_ssl_verify_from_env())
        response_data = response.json()
        if response.status_code == 200:
            if "id" in response_data:
                published_ad_id = response_data["id"]
                print(f"Published ad id: {published_ad_id}")
                return published_ad_id, None
            else:
                error = f"Ad creation: 'id' not found in response data for ad name '{ad_name}' (ad_set_id: {ad_set_id})"
                print(f"Error: {error}")
                return None, error
        else:
            error = f"Ad creation failed for ad '{ad_name}' (ad_set_id: {ad_set_id}): {response.status_code} - {response.text}"
            print(f"Error: {error}")
            return None, error
    except requests.exceptions.RequestException as e:
        error = f"Ad creation request error for ad '{ad_name}' (ad_set_id: {ad_set_id}): {e}"
        print(error)
        return None, error

    return (
        None,
        f"Ad creation failed for ad '{ad_name}' (ad_set_id: {ad_set_id}): Unknown error",
    )


def create_partnership_ads_from_csv(
    access_token: str,
    ig_account_id: str,
    ad_account_id: str,
    facebook_page_id: str,
    input_csv: str,
    output_csv: str = "created_ads_output.csv",
) -> None:
    """
    Create partnership ads from input CSV file.

    The input CSV should have the following columns:
    - permalink: Media permalink or shortcode (either permalink or ad_code is required)
    - ad_code: Ad code if available (either permalink or ad_code is required)
    - ad_set_id: Ad set ID to create ad under (must be entered as text, not number)
    - cta_type: Call to action type (e.g., "INSTALL_MOBILE_APP", "LEARN_MORE")
    - link: CTA link (mandatory)
    - app_link: CTA app link (optional)
    - app_id: App ID for app events tracking (optional)
    - ad_name: Name for the ad
    - product_set_id (optional): Product set ID
    - utm_parameters (optional): UTM parameters in query string format (e.g., 'utm_source=instagram&utm_medium=paid')
    - testimonial (optional): Testimonial text for the ad
    - source_url (optional): Source URL for the creative

    Args:
        access_token: Facebook/Instagram access token
        ig_account_id: Instagram account ID
        ad_account_id: Ad account ID
        facebook_page_id: Facebook page ID
        input_csv: Input CSV file path
        output_csv: Output CSV file path
    """
    print(f"Reading input CSV: {input_csv}")

    try:
        rows = []
        with open(input_csv, mode="r", encoding="utf-8") as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                rows.append(row)

        if not rows:
            print("No rows found in input CSV")
            return

        print(f"Processing {len(rows)} rows...")

        output_rows = []
        for idx, row in enumerate(rows, 1):
            print(f"\n[{idx}/{len(rows)}] Processing: {row.get('ad_name', 'Unknown')}")

            output_row = row.copy()

            permalink = row.get("permalink", "")
            ad_code = row.get("ad_code", "")
            cta_type = row.get("cta_type")
            link = row.get("link")
            app_link = row.get("app_link", "")
            app_id = row.get("app_id", "")
            ad_name = row.get("ad_name")
            ad_set_id = row.get("ad_set_id")
            product_set_id = row.get("product_set_id", "")
            utm_parameters = row.get("utm_parameters", "")
            testimonial = row.get("testimonial", "")
            source_url = row.get("source_url", "")

            required_fields = {
                "cta_type": cta_type,
                "link": link,
                "ad_name": ad_name,
                "ad_set_id": ad_set_id,
            }

            missing_fields = [k for k, v in required_fields.items() if not v]
            if missing_fields:
                error_msg = f"Missing required fields: {', '.join(missing_fields)}"
                print(f"Error: {error_msg}")
                output_row["status"] = "failed"
                output_row["error"] = error_msg
                output_row["video_id"] = ""
                output_row["creative_id"] = ""
                output_row["published_ad_id"] = ""
                output_rows.append(output_row)
                continue

            if not permalink and not ad_code:
                error_msg = "Either permalink or ad_code must be provided"
                print(f"Error: {error_msg}")
                output_row["status"] = "failed"
                output_row["error"] = error_msg
                output_row["video_id"] = ""
                output_row["creative_id"] = ""
                output_row["published_ad_id"] = ""
                output_rows.append(output_row)
                continue

            video_id = None
            video_error = None
            creative_id = None
            creative_error = None
            published_ad_id = None
            ad_error = None
            eligibility_error = None

            try:
                if ad_code:
                    # When ad_code is provided, it already has permission
                    eligibility = fetch_branded_content_advertisable_medias(
                        access_token, ig_account_id, ad_code=ad_code
                    )
                elif permalink:
                    # Extract shortcode from permalink if it's a URL
                    # This will raise ValueError if it's a stories URL
                    try:
                        shortcode = extract_instagram_shortcode(permalink)
                    except ValueError as e:
                        # Stories URLs are not supported
                        eligibility_error = str(e)
                        print(f"Eligibility check failed: {eligibility_error}")
                        output_row["status"] = "failed"
                        output_row["error"] = eligibility_error
                        output_row["video_id"] = ""
                        output_row["creative_id"] = ""
                        output_row["published_ad_id"] = ""
                        output_rows.append(output_row)
                        continue

                    eligibility = fetch_branded_content_advertisable_medias(
                        access_token, ig_account_id, permalinks=[shortcode]
                    )
                else:
                    eligibility = None

                if not eligibility:
                    eligibility_error = "Failed to fetch media eligibility"
                elif eligibility.get("error"):
                    eligibility_error = f"API Error: {eligibility.get('error')}"
                elif not ad_code and not eligibility.get(
                    "has_permission_for_partnership_ad"
                ):
                    # Only check permission if using permalink (ad_code already has permission)
                    eligibility_error = (
                        "Media does not have permission for partnership ads"
                    )
                elif (
                    eligibility.get("eligibility_errors")
                    and len(eligibility.get("eligibility_errors", [])) > 0
                ):
                    errors = eligibility.get("eligibility_errors", [])
                    eligibility_error = f"Eligibility errors: {', '.join(errors)}"

                if eligibility_error:
                    print(f"Eligibility check failed: {eligibility_error}")
                    output_row["status"] = "failed"
                    output_row["error"] = eligibility_error
                    output_row["video_id"] = ""
                    output_row["creative_id"] = ""
                    output_row["published_ad_id"] = ""
                    output_rows.append(output_row)
                    continue

                source_instagram_media_id = eligibility.get("id")
                if not source_instagram_media_id:
                    error_msg = "Media ID not found in eligibility response"
                    print(f"Error: {error_msg}")
                    output_row["status"] = "failed"
                    output_row["error"] = error_msg
                    output_row["video_id"] = ""
                    output_row["creative_id"] = ""
                    output_row["published_ad_id"] = ""
                    output_rows.append(output_row)
                    continue

                video_id, video_error = upload_instagram_video(
                    access_token,
                    ad_account_id,
                    source_instagram_media_id,
                    ad_code if ad_code else None,
                )

                if not video_id:
                    print(f"Video upload failed: {video_error}")
                    output_row["status"] = "failed"
                    output_row["error"] = video_error or "Video upload failed"
                    output_row["video_id"] = ""
                    output_row["creative_id"] = ""
                    output_row["published_ad_id"] = ""
                    output_rows.append(output_row)
                    continue

                creative_id, creative_error = create_ad_creative(
                    access_token,
                    ad_account_id,
                    facebook_page_id,
                    ig_account_id,
                    source_instagram_media_id,
                    ad_code if ad_code else None,
                    cta_type,
                    link,
                    app_link if app_link else None,
                    product_set_id if product_set_id else None,
                    utm_parameters if utm_parameters else None,
                    testimonial if testimonial else None,
                    source_url if source_url else None,
                )

                if not creative_id:
                    print(f"Creative creation failed: {creative_error}")
                    output_row["status"] = "failed"
                    output_row["error"] = creative_error or "Creative creation failed"
                    output_row["video_id"] = video_id or ""
                    output_row["creative_id"] = ""
                    output_row["published_ad_id"] = ""
                    output_rows.append(output_row)
                    continue

                published_ad_id, ad_error = create_ad(
                    access_token, ad_account_id, ad_name, ad_set_id, creative_id,
                    app_id if app_id else None,
                )

                if not published_ad_id:
                    print(f"Ad creation failed: {ad_error}")
                    output_row["status"] = "failed"
                    output_row["error"] = ad_error or "Ad creation failed"
                    output_row["video_id"] = video_id or ""
                    output_row["creative_id"] = creative_id or ""
                    output_row["published_ad_id"] = ""
                    output_rows.append(output_row)
                    continue

                output_row["status"] = "success"
                output_row["error"] = ""
                output_row["video_id"] = video_id or ""
                output_row["creative_id"] = creative_id or ""
                output_row["published_ad_id"] = published_ad_id or ""
                output_rows.append(output_row)

            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                print(f"Error: {error_msg}")
                output_row["status"] = "failed"
                output_row["error"] = error_msg
                output_row["video_id"] = video_id or ""
                output_row["creative_id"] = creative_id or ""
                output_row["published_ad_id"] = published_ad_id or ""
                output_rows.append(output_row)

        fieldnames = list(output_rows[0].keys()) if output_rows else []
        with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)

        successful = len([r for r in output_rows if r.get("status") == "success"])
        print(f"\n\nSummary:")
        print(f"Total rows processed: {len(output_rows)}")
        print(f"Successful: {successful}")
        print(f"Failed: {len(output_rows) - successful}")
        print(f"Results saved to: {output_csv}")

    except FileNotFoundError:
        print(f"Error: The file {input_csv} was not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Partnership Ads Booster - Fetch and create partnership ads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Fetch all advertisable medias:
    python partnership_ads_booster.py --mode fetch --access-token YOUR_TOKEN --ig-account-id 17841400875057971 --creator-username CREATOR_USERNAME

  Create partnership ads from CSV:
    python partnership_ads_booster.py --mode create --access-token YOUR_TOKEN \\
      --ig-account-id 17841400875057971 --ad-account-id 1549883851784009 \\
      --facebook-page-id 102988293558 --input-csv input.csv
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["fetch", "create"],
        required=True,
        help='Mode: "fetch" to download advertisable medias or "create" to create partnership ads',
    )
    parser.add_argument(
        "--access-token", required=True, help="Facebook/Instagram access token"
    )
    parser.add_argument("--ig-account-id", required=True, help="Instagram account ID")
    parser.add_argument(
        "--creator-username",
        help="Instagram creator username (optional but recommended to avoid fetching too much data)",
    )
    parser.add_argument(
        "--ad-account-id", help="Ad account ID (required for create mode)"
    )
    parser.add_argument(
        "--facebook-page-id", help="Facebook page ID (required for create mode)"
    )
    parser.add_argument(
        "--input-csv", help="Input CSV file path (required for create mode)"
    )
    parser.add_argument(
        "--output-csv",
        help="Output CSV file path (default: advertisable_medias.csv for fetch, created_ads_output.csv for create)",
    )
    parser.add_argument(
        "--only-with-permission",
        action="store_true",
        help="Only fetch medias with partnership ad permission (fetch mode only)",
    )
    parser.add_argument(
        "--include-metrics",
        action="store_true",
        help="Include engagement metrics (likes, comments) - slower (fetch mode only)",
    )
    parser.add_argument(
        "--no-ssl-verify",
        action="store_true",
        help="Disable SSL certificate verification (use for testing/development only)",
    )

    args = parser.parse_args()

    # Set SSL verification based on command line argument
    if args.no_ssl_verify:
        os.environ["SSL_VERIFY"] = "false"
        print("Warning: SSL certificate verification is disabled")

    if args.mode == "fetch":
        output_csv = args.output_csv or "advertisable_medias.csv"
        fetch_all_advertisable_medias(
            args.access_token,
            args.ig_account_id,
            args.creator_username,
            output_csv,
            only_with_permission=args.only_with_permission,
            include_engagement_metrics=args.include_metrics,
        )

    elif args.mode == "create":
        if not args.ad_account_id:
            print("Error: --ad-account-id is required for create mode")
            sys.exit(1)
        if not args.facebook_page_id:
            print("Error: --facebook-page-id is required for create mode")
            sys.exit(1)
        if not args.input_csv:
            print("Error: --input-csv is required for create mode")
            sys.exit(1)

        output_csv = args.output_csv or "created_ads_output.csv"
        create_partnership_ads_from_csv(
            args.access_token,
            args.ig_account_id,
            args.ad_account_id,
            args.facebook_page_id,
            args.input_csv,
            output_csv,
        )


if __name__ == "__main__":
    main()
