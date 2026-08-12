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

# Maps CSV identities values to API ad_format integers
# 1 = both identities (default), 2 = first identity only, 3 = dynamic optimization
IDENTITIES_MAP = {"both": 1, "first": 2, "dynamic": 3}


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
    business_id: str,
    ig_user_id: str,
    creator_username: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = 25,
    only_with_permission: bool = False,
    post_types: Optional[List[str]] = None,
    ad_eligibilities: Optional[List[str]] = None,
    ad_usages: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search_key: Optional[str] = None,
    include_engagement_metrics: bool = False,
) -> Tuple[List[Dict], Optional[str]]:
    """
    Fetch a single page of advertisable medias for pagination support.
    Uses the Content Discovery API (partnership-ads-advertisable-content).

    Args:
        access_token: Facebook/Instagram access token
        business_id: Business ID (required for Content Discovery API)
        ig_user_id: Instagram User ID (required)
        creator_username: Instagram creator username (optional, legacy filter)
        cursor: Pagination cursor from previous request (None for first page)
        limit: Number of items per page (default 25, max 50)
        only_with_permission: If True, only include medias with partnership ad permission
        post_types: Filter by post types (e.g., ["FEED", "STORY", "REEL"])
        ad_eligibilities: Filter by ad eligibility (e.g., ["AD_READY", "INELIGIBLE"])
        ad_usages: Filter by ad usage (e.g., ["NEVER_USED", "ACTIVE", "PREVIOUSLY_USED"])
        start_date: Start date for content creation (YYYY-MM-DD format)
        end_date: End date for content creation (YYYY-MM-DD format)
        search_key: Keyword search across caption text
        include_engagement_metrics: If True, include organic insights (likes, comments, etc.)

    Returns:
        Tuple of (list of media dicts, next_cursor or None if no more pages)
        Media dicts are mapped to legacy format for backward compatibility.

    Raises:
        APIError: If the API returns a 5xx error (should be retried)
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    # Build the URL for Content Discovery API
    url = f"https://graph.facebook.com/v25.0/{business_id}/partnership-ads-advertisable-content"
    
    # Build base fields (always requested) - FULL FIELD SET
    fields = (
        "content_id,platform,media_type,post_type,caption,permalink,creation_time,"
        "author{display_name,ig_user_id,fb_page_id,profile_picture_url},"
        "is_recommended,ad_usage,"
        "partnership_info{ad_eligibility,tagged_partner{display_name,ig_user_id,fb_page_id},"
        "permission_status,permission_type,ad_code,content_types}"
    )
    
    # Add organic insights only if requested
    if include_engagement_metrics:
        fields += ",organic_insights{likes,comments,views,reach,shares,interaction,saves}"
    
    # Build parameters - use limit 25 for better performance
    params = {
        "ig_user_id": ig_user_id,
        "limit": min(limit, 25),
        "fields": fields,
    }
    
    # Add pagination cursor if provided
    if cursor:
        params["after"] = cursor
    
    # Add optional filters
    # API enum values are lowercase (e.g. "ad_ready"), so normalize filter values.
    if post_types:
        params["post_types"] = json.dumps([t.lower() for t in post_types])
    if ad_eligibilities:
        params["ad_eligibilities"] = json.dumps([e.lower() for e in ad_eligibilities])
    if ad_usages:
        params["ad_usages"] = json.dumps([u.lower() for u in ad_usages])
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if search_key:
        params["search_key"] = search_key
    # Note: creator_username is not a direct filter in new API; use ad_partner_ig_user_ids instead

    # Debug logging
    print(f"DEBUG: Calling Content Discovery API")
    print(f"DEBUG: URL: {url}")
    print(f"DEBUG: Params: {json.dumps(params, indent=2)}")

    try:
        response = requests.get(url, headers=headers, params=params, verify=get_ssl_verify_from_env())
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return [], None

    # Raise exception for server errors (5xx) so caller can retry
    if response.status_code >= 500:
        # Log the error details for debugging
        print(f"Content Discovery API returned {response.status_code}. This API may not be enabled for your business yet (GK: pa_content_discovery_api).")
        print(f"Error details: {response.text}")
        print(f"Request URL: {response.url}")
        raise APIError(response.status_code, response.text)

    # For client errors (4xx), return empty to signal end
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        print(f"Request URL: {response.url}")
        # If it's a 400 error about invalid parameters, the API might not support those filters yet
        if response.status_code == 400:
            print("Note: Some filter parameters may not be supported by the Content Discovery API yet.")
        return [], None

    response_data = response.json()
    content_items = response_data.get("data", [])

    # Map new API response format to legacy format for backward compatibility
    medias = []
    for item in content_items:
        # Extract partnership info (first entry if multiple partners)
        partnership_info = item.get("partnership_info", [])
        first_partnership = partnership_info[0] if partnership_info else {}
        
        # Extract organic insights
        organic_insights = item.get("organic_insights", {})
        
        # Extract author info
        author = item.get("author", {})
        
        # Map to legacy format
        media = {
            "id": item.get("content_id", ""),
            "permalink": item.get("permalink", ""),
            "owner_id": author.get("ig_user_id", "") or author.get("fb_page_id", ""),
            # Check if any partnership has AUTHORIZED permission status
            "has_permission_for_partnership_ad": any(
                (p.get("permission_status") or "").upper() == "AUTHORIZED"
                for p in partnership_info
            ),
            # Map ad_eligibility to eligibility_errors format
            "eligibility_errors": [],
            # New fields from Content Discovery API
            "platform": item.get("platform", ""),
            "media_type": item.get("media_type", ""),
            "post_type": item.get("post_type", ""),
            "caption": item.get("caption", ""),
            "creation_time": item.get("creation_time", ""),
            "author_display_name": author.get("display_name", ""),
            "author_profile_picture_url": author.get("profile_picture_url", ""),
            "is_recommended": item.get("is_recommended", False),
            "ad_usage": item.get("ad_usage", ""),
            "ad_eligibility": first_partnership.get("ad_eligibility", ""),
            "permission_status": first_partnership.get("permission_status", ""),
            "ad_code": first_partnership.get("ad_code", ""),
            "content_types": first_partnership.get("content_types", []),
            # Organic insights
            "likes": organic_insights.get("likes"),
            "comments": organic_insights.get("comments"),
            "views": organic_insights.get("views"),
            "reach": organic_insights.get("reach"),
            "shares": organic_insights.get("shares"),
            "interaction": organic_insights.get("interaction"),
            "saves": organic_insights.get("saves"),
        }
        
        # Map ad_eligibility to eligibility_errors for backward compatibility
        ad_eligibility = first_partnership.get("ad_eligibility", "")
        if ad_eligibility and ad_eligibility.upper() != "AD_READY":
            media["eligibility_errors"] = [f"Ad eligibility: {ad_eligibility}"]
        
        medias.append(media)

    # Apply permission filter if requested (for backward compatibility)
    if only_with_permission:
        medias = [
            m for m in medias
            if m.get("has_permission_for_partnership_ad", False)
        ]

    # Get next cursor from paging
    next_cursor = None
    if "paging" in response_data and "cursors" in response_data["paging"]:
        next_cursor = response_data["paging"]["cursors"].get("after")

    return medias, next_cursor


def fetch_all_advertisable_medias(
    access_token: str,
    business_id: str,
    ig_user_id: str,
    creator_username: Optional[str] = None,
    output_csv: str = "advertisable_medias.csv",
    limit: Optional[int] = None,
    only_with_permission: bool = False,
    include_engagement_metrics: bool = False,
    post_types: Optional[List[str]] = None,
    ad_eligibilities: Optional[List[str]] = None,
    ad_usages: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search_key: Optional[str] = None,
) -> None:
    """
    Fetch all advertisable medias for the given Instagram account and save to CSV.
    Uses the Content Discovery API.

    Args:
        access_token: Facebook/Instagram access token
        business_id: Business ID (required for Content Discovery API)
        ig_user_id: Instagram User ID
        creator_username: Instagram creator username (optional but recommended to avoid fetching too much data)
        output_csv: Output CSV file path
        limit: Maximum number of medias to fetch (optional, fetches all if not specified)
        only_with_permission: If True, only include medias with partnership ad permission
        include_engagement_metrics: If True, fetch engagement metrics (likes, comments, reach, impressions, saves)
        post_types: Filter by post types
        ad_eligibilities: Filter by ad eligibility
        ad_usages: Filter by ad usage
        start_date: Start date for content creation (YYYY-MM-DD)
        end_date: End date for content creation (YYYY-MM-DD)
        search_key: Keyword search across caption text
    """
    creator_info = f" (creator: {creator_username})" if creator_username else ""
    print(
        f"Fetching advertisable medias for IG user {ig_user_id}{creator_info}..."
    )

    all_medias = []
    cursor = None
    total_fetched = 0

    while True:
        medias, next_cursor = fetch_page_of_advertisable_medias(
            access_token=access_token,
            business_id=business_id,
            ig_user_id=ig_user_id,
            creator_username=creator_username,
            cursor=cursor,
            limit=50,  # Use new max limit
            only_with_permission=only_with_permission,
            post_types=post_types,
            ad_eligibilities=ad_eligibilities,
            ad_usages=ad_usages,
            start_date=start_date,
            end_date=end_date,
            search_key=search_key,
            include_engagement_metrics=include_engagement_metrics,
        )

        if not medias:
            break

        all_medias.extend(medias)
        total_fetched += len(medias)
        print(f"Fetched {total_fetched} medias so far...")

        # Check if we've reached the limit
        if limit and total_fetched >= limit:
            all_medias = all_medias[:limit]
            break

        # Check if there are more pages
        if not next_cursor:
            break

        cursor = next_cursor

    print(f"Total medias fetched: {len(all_medias)}")

    # Write to CSV with new fields from Content Discovery API
    if all_medias:
        # Define CSV columns (backward compatible + new fields)
        fieldnames = [
            "media_id",
            "permalink",
            "owner_id",
            "has_permission_for_partnership_ad",
            "eligibility_errors",
            # New fields from Content Discovery API
            "platform",
            "media_type",
            "post_type",
            "caption",
            "creation_time",
            "author_display_name",
            "author_profile_picture_url",
            "is_recommended",
            "ad_usage",
            "ad_eligibility",
            "permission_status",
            "ad_code",
            "content_types",
            # Organic insights (now included by default)
            "likes",
            "comments",
            "views",
            "reach",
            "shares",
            "interaction",
            "saves",
        ]

        with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for media in all_medias:
                # Map media dict to CSV row
                row = {
                    "media_id": media.get("id", ""),
                    "permalink": media.get("permalink", ""),
                    "owner_id": media.get("owner_id", ""),
                    "has_permission_for_partnership_ad": media.get(
                        "has_permission_for_partnership_ad", False
                    ),
                    "eligibility_errors": json.dumps(media.get("eligibility_errors", [])),
                    "platform": media.get("platform", ""),
                    "media_type": media.get("media_type", ""),
                    "post_type": media.get("post_type", ""),
                    "caption": media.get("caption", ""),
                    "creation_time": media.get("creation_time", ""),
                    "author_display_name": media.get("author_display_name", ""),
                    "author_profile_picture_url": media.get("author_profile_picture_url", ""),
                    "is_recommended": media.get("is_recommended", False),
                    "ad_usage": media.get("ad_usage", ""),
                    "ad_eligibility": media.get("ad_eligibility", ""),
                    "permission_status": media.get("permission_status", ""),
                    "ad_code": media.get("ad_code", ""),
                    "content_types": json.dumps(media.get("content_types", [])),
                    "likes": media.get("likes", ""),
                    "comments": media.get("comments", ""),
                    "views": media.get("views", ""),
                    "reach": media.get("reach", ""),
                    "shares": media.get("shares", ""),
                    "interaction": media.get("interaction", ""),
                    "saves": media.get("saves", ""),
                }
                writer.writerow(row)

        print(f"Results saved to {output_csv}")
    else:
        print("No medias found.")


def fetch_branded_content_advertisable_medias(
    access_token: str,
    business_id: str,
    ig_user_id: str,
    ad_code: Optional[str] = None,
    permalinks: Optional[List[str]] = None,
    content_ids: Optional[List[str]] = None,
) -> Optional[Dict]:
    """
    Fetch eligibility information for a specific media using Content Discovery API.
    Uses direct lookup mode.

    Args:
        access_token: Facebook/Instagram access token
        business_id: Business ID (required for Content Discovery API)
        ig_user_id: Instagram User ID
        ad_code: Ad code for the media
        permalinks: List of permalinks (max 50)
        content_ids: List of content IDs (max 50)

    Returns:
        Dict containing eligibility information or None
        Mapped to legacy format for backward compatibility.
    """
    url = f"https://graph.facebook.com/v23.0/{business_id}/partnership-ads-advertisable-content"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    params = {
        "ig_user_id": ig_user_id,
        "fields": (
            "content_id,permalink,partnership_info{ad_eligibility,permission_status,ad_code},"
            "author{ig_user_id,fb_page_id}"
        ),
    }

    if ad_code:
        params["ad_codes"] = json.dumps([ad_code])
    elif permalinks:
        params["permalinks"] = json.dumps(permalinks)
    elif content_ids:
        params["content_ids"] = json.dumps(content_ids)
    else:
        raise ValueError("ad_code, permalinks, or content_ids must be passed")

    response = requests.get(url, headers=headers, params=params, verify=get_ssl_verify_from_env())
    if response.status_code == 200:
        response_data = response.json()
        if "data" in response_data and len(response_data["data"]) > 0:
            item = response_data["data"][0]
            # Map to legacy format
            partnership_info = item.get("partnership_info", [])
            first_partnership = partnership_info[0] if partnership_info else {}
            author = item.get("author", {})
            
            legacy_format = {
                "id": item.get("content_id", ""),
                "permalink": item.get("permalink", ""),
                "owner_id": author.get("ig_user_id", "") or author.get("fb_page_id", ""),
                "has_permission_for_partnership_ad": (first_partnership.get("permission_status") or "").upper() == "AUTHORIZED",
                "eligibility_errors": [],
            }
            
            # Map ad_eligibility to eligibility_errors
            ad_eligibility = first_partnership.get("ad_eligibility", "")
            if ad_eligibility and ad_eligibility.upper() != "AD_READY":
                legacy_format["eligibility_errors"] = [f"Ad eligibility: {ad_eligibility}"]
            
            print(f"Eligibility: {legacy_format}")
            return legacy_format
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
    identities: Optional[str] = None,
    multi_advertiser_ads: Optional[str] = None,
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
        identities: Controls which identities to display in the ad (optional).
            Values (case insensitive): BOTH (default), FIRST, DYNAMIC.
            Maps to ad_format in branded_content: BOTH=1, FIRST=2, DYNAMIC=3.
        multi_advertiser_ads: Controls multi-advertiser ads enrollment (optional).
            Values (case insensitive): OPT_OUT (to disable multi-advertiser ads),
            OPT_IN (to enable, default behavior).

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
    if identities:
        ad_format = IDENTITIES_MAP.get(identities.strip().lower())
        if ad_format is not None:
            branded_content["ad_format"] = ad_format
        else:
            print(f"Warning: Unknown identities value '{identities}', ignoring. Valid values: BOTH, FIRST, DYNAMIC")

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

    # Add contextual_multi_ads parameter to control multi-advertiser ads
    if multi_advertiser_ads:
        enroll_status = multi_advertiser_ads.strip().upper()
        if enroll_status in ("OPT_OUT", "OPT_IN"):
            params["contextual_multi_ads"] = json.dumps({"enroll_status": enroll_status})
        else:
            print(f"Warning: Unknown multi_advertiser_ads value '{multi_advertiser_ads}', ignoring. Valid values: OPT_OUT, OPT_IN")

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


def copy_ad_set(
    access_token: str,
    source_ad_set_id: str,
    new_name: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Create a copy of an existing ad set via POST /{ad-set-id}/copies.

    The copy is created under the same campaign (no campaign_id override).
    If new_name is provided the copied ad set is renamed to that value
    via a follow-up update call (POST /{copied_id} with name).

    API Reference: POST /{ad_set_id}/copies
        https://developers.facebook.com/documentation/ads-commerce/marketing-api/reference/ad-campaign/copies

    Args:
        access_token: Facebook/Instagram access token
        source_ad_set_id: Source ad set ID to copy (numeric string)
        new_name: Optional exact name for the copied ad set (ad_set_rename)

    Returns:
        Tuple of (copied_ad_set_id or None, error message or None)
    """
    url = f"https://graph.facebook.com/v25.0/{source_ad_set_id}/copies"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    # Keep the copy under the same campaign, paused by default.
    # deep_copy=false (default) keeps behaviour minimal - only the ad set,
    # not its child ads.
    params = {
        "status_option": "PAUSED",
        "deep_copy": False,
    }

    try:
        response = requests.post(url, headers=headers, params=params, verify=get_ssl_verify_from_env())
        response_data = response.json() if response.content else {}
        if response.status_code == 200:
            # Successful copy returns { copied_adset_id: "...", ad_object_ids: [...] }
            copied_id = (
                response_data.get("copied_adset_id")
                or response_data.get("copied_ad_set_id")
                or response_data.get("id")
            )
            if not copied_id:
                # Some versions wrap under `data`
                data = response_data.get("data", {})
                if isinstance(data, dict):
                    copied_id = data.get("copied_adset_id") or data.get("id")
            if not copied_id:
                error = f"Copy succeeded but no copied_adset_id in response: {response.text}"
                print(f"Error: {error}")
                return None, error
            print(f"Ad set {source_ad_set_id} copied to {copied_id}")

            # Rename the copy if a new name was requested
            if new_name:
                # Rename is a field update on the AdSet node -> POST with `name` param
                rename_url = f"https://graph.facebook.com/v25.0/{copied_id}"
                try:
                    rename_resp = requests.post(
                        rename_url,
                        headers=headers,
                        params={"name": new_name},
                        verify=get_ssl_verify_from_env(),
                    )
                    if rename_resp.status_code == 200:
                        print(f"Renamed copied ad set {copied_id} to '{new_name}'")
                    else:
                        # Rename failure is non-fatal - keep the copied ID but surface warning
                        print(
                            f"Warning: Failed to rename copied ad set {copied_id} to '{new_name}': "
                            f"{rename_resp.status_code} - {rename_resp.text}"
                        )
                except requests.exceptions.RequestException as e:
                    print(f"Warning: Rename request error for {copied_id}: {e}")

            return copied_id, None
        else:
            error = f"Ad set copy failed for {source_ad_set_id}: {response.status_code} - {response.text}"
            print(f"Error: {error}")
            return None, error
    except requests.exceptions.RequestException as e:
        error = f"Ad set copy request error for {source_ad_set_id}: {e}"
        print(error)
        return None, error
    except Exception as e:
        error = f"Ad set copy unknown error for {source_ad_set_id}: {e}"
        print(error)
        return None, error


def create_partnership_ads_from_csv(
    access_token: str,
    business_id: str,
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
    - ad_set_id: Ad set ID to create ad under (must be entered as text, not number).
                 Optional if copy_ad_set_id is provided - a copy will be created
                 and used as the effective ad_set_id.
    - copy_ad_set_id (optional): Source ad set ID to duplicate via POST /{ad_set_id}/copies.
                 When provided a new ad set is created under the same campaign and
                 its ID is used as ad_set_id for ad creation. This makes ad_set_id optional.
    - ad_set_rename (optional): Exact name for the copied ad set. Only used when
                 copy_ad_set_id is provided. The copy is renamed to this value.
    - cta_type: Call to action type (e.g., "INSTALL_MOBILE_APP", "LEARN_MORE")
    - link: CTA link (mandatory)
    - app_link: CTA app link (optional)
    - app_id: App ID for app events tracking (optional)
    - ad_name: Name for the ad
    - product_set_id (optional): Product set ID
    - utm_parameters (optional): UTM parameters in query string format (e.g., 'utm_source=instagram&utm_medium=paid')
    - testimonial (optional): Testimonial text for the ad
    - source_url (optional): Source URL for the creative
    - identities (optional): Controls which identities to display in the ad.
      Values (case insensitive): BOTH (default, both identities), FIRST (first identity only), DYNAMIC (system optimizes)
    - multi_advertiser_ads (optional): Controls multi-advertiser ads enrollment.
      Values (case insensitive): OPT_OUT (to disable multi-advertiser ads), OPT_IN (to enable, default behavior)

    Args:
        access_token: Facebook/Instagram access token
        business_id: Business ID (required for Content Discovery API)
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

            permalink = (row.get("permalink", "") or "").strip()
            ad_code = (row.get("ad_code", "") or "").strip()
            cta_type = (row.get("cta_type", "") or "").strip() or row.get("cta_type")
            link = (row.get("link", "") or "").strip() or row.get("link")
            app_link = (row.get("app_link", "") or "").strip()
            app_id = (row.get("app_id", "") or "").strip()
            ad_name = (row.get("ad_name", "") or "").strip() or row.get("ad_name")
            ad_set_id = (row.get("ad_set_id", "") or "").strip()
            product_set_id = (row.get("product_set_id", "") or "").strip()
            utm_parameters = (row.get("utm_parameters", "") or "").strip()
            testimonial = (row.get("testimonial", "") or "").strip()
            source_url = (row.get("source_url", "") or "").strip()
            identities = (row.get("identities", "") or "").strip()
            multi_advertiser_ads = (row.get("multi_advertiser_ads", "") or "").strip()
            copy_ad_set_id = (row.get("copy_ad_set_id", "") or "").strip()
            ad_set_rename = (row.get("ad_set_rename", "") or "").strip()

            # If copy_ad_set_id is provided, duplicate that ad set under the same
            # campaign (POST /{ad-set-id}/copies) and use the new ID as effective
            # ad_set_id.  When ad_set_rename is also provided the copy is renamed
            # to that exact value.  This makes ad_set_id optional when copying.
            effective_ad_set_id = ad_set_id
            if copy_ad_set_id:
                print(f"Copying ad set {copy_ad_set_id} (rename='{ad_set_rename}')...")
                copied_id, copy_error = copy_ad_set(
                    access_token,
                    copy_ad_set_id,
                    new_name=ad_set_rename if ad_set_rename else None,
                )
                if not copied_id:
                    error_msg = copy_error or f"Failed to copy ad set {copy_ad_set_id}"
                    print(f"Error: {error_msg}")
                    output_row["status"] = "failed"
                    output_row["error"] = error_msg
                    output_row["video_id"] = ""
                    output_row["creative_id"] = ""
                    output_row["published_ad_id"] = ""
                    # Persist copy columns for debugging even on failure
                    output_row["effective_ad_set_id"] = ""
                    output_rows.append(output_row)
                    continue
                effective_ad_set_id = copied_id
                # Persist for output visibility; do not clobber the user's original
                # ad_set_id column - keep both so the CSV is auditable.
                output_row["effective_ad_set_id"] = effective_ad_set_id
                output_row["ad_set_id"] = effective_ad_set_id
                print(f"Using copied ad set {effective_ad_set_id} for ad '{ad_name}'")
            else:
                # Ensure effective column is present for uniform output schema
                if "effective_ad_set_id" not in output_row:
                    output_row["effective_ad_set_id"] = effective_ad_set_id or ""

            # ad_set_rename without copy_ad_set_id is ignored (no-op) but not an error.
            if ad_set_rename and not copy_ad_set_id:
                print(f"Warning: ad_set_rename='{ad_set_rename}' ignored because copy_ad_set_id is empty for ad '{ad_name}'")

            # ad_set_id is required unless copy_ad_set_id supplied a replacement
            required_fields = {
                "cta_type": cta_type,
                "link": link,
                "ad_name": ad_name,
                "ad_set_id": effective_ad_set_id,
            }

            missing_fields = [k for k, v in required_fields.items() if not v]
            if missing_fields:
                # Provide a helpful hint when ad_set_id is the missing field
                if "ad_set_id" in missing_fields and not copy_ad_set_id:
                    error_msg = "Missing required fields: ad_set_id (or provide copy_ad_set_id to auto-copy an ad set)"
                else:
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

            # From here on use the resolved ad set ID
            ad_set_id = effective_ad_set_id

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
                        access_token, business_id, ig_account_id, ad_code=ad_code
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
                        access_token, business_id, ig_account_id, permalinks=[shortcode]
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
                    identities if identities else None,
                    multi_advertiser_ads if multi_advertiser_ads else None,
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
    python partnership_ads_booster.py --mode fetch --access-token YOUR_TOKEN --business-id 123456789 --ig-account-id 17841400875057971 --creator-username CREATOR_USERNAME

  Create partnership ads from CSV:
    python partnership_ads_booster.py --mode create --access-token YOUR_TOKEN \\
      --business-id 123456789 --ig-account-id 17841400875057971 --ad-account-id 1549883851784009 \\
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
        "--business-id",
        required=True,
        help="Business ID (required for Content Discovery API)",
    )
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
            args.business_id,
            args.ig_account_id,
            creator_username=args.creator_username,
            output_csv=output_csv,
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
            args.business_id,
            args.ig_account_id,
            args.ad_account_id,
            args.facebook_page_id,
            args.input_csv,
            output_csv,
        )


if __name__ == "__main__":
    main()
