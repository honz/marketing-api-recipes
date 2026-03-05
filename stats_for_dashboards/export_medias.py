#!/usr/bin/env python3
"""
Export Advertisable Medias - CLI Script

A standalone script to export all advertisable medias from an Instagram account.
Can be run in the background and handles rate limiting automatically.

Usage:
    python export_medias.py --access-token YOUR_TOKEN --ig-account-id YOUR_ID

    # With filters
    python export_medias.py --access-token YOUR_TOKEN --ig-account-id YOUR_ID \
        --creator-username someuser --only-with-permission --include-metrics

    # Run in background
    nohup python export_medias.py --access-token YOUR_TOKEN --ig-account-id YOUR_ID \
        --output medias.csv > export.log 2>&1 &

    # Disable SSL verification (for corporate proxies)
    SSL_VERIFY=false python export_medias.py --access-token YOUR_TOKEN --ig-account-id YOUR_ID
"""

import argparse
import csv
import sys
import time
from datetime import datetime
from typing import Optional

from partnership_ads_booster import (
    fetch_page_of_advertisable_medias,
    fetch_media_insights,
    APIError,
)


def export_all_medias(
    access_token: str,
    ig_account_id: str,
    output_file: str,
    creator_username: Optional[str] = None,
    only_with_permission: bool = False,
    include_metrics: bool = False,
    delay_seconds: float = 30.0,
    max_retries: int = 6,
    page_size: int = 25,
) -> None:
    """
    Export all advertisable medias to a CSV file.

    Args:
        access_token: Facebook/Instagram access token
        ig_account_id: Instagram account ID
        output_file: Output CSV file path
        creator_username: Optional filter by creator username
        only_with_permission: Only include medias with permission granted
        include_metrics: Include engagement metrics (likes, comments)
        delay_seconds: Delay between API calls for rate limiting (default: 30s)
        max_retries: Maximum retries for failed API calls (uses exponential backoff: 30s, 60s, 120s, 240s, 480s, 960s)
        page_size: Number of items per page (default 25, try 10 if API is flaky)
    """
    all_medias = []
    cursor = None
    page_count = 0
    consecutive_empty = 0
    max_consecutive_empty = 3

    print(f"Starting export at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Instagram Account ID: {ig_account_id}")
    print(f"Output file: {output_file}")
    print(f"Page size: {page_size}")
    if creator_username:
        print(f"Filtering by creator: {creator_username}")
    if only_with_permission:
        print("Only including medias with permission granted")
    if include_metrics:
        print("Including engagement metrics (likes, comments)")
    print(f"Rate limit delay: {delay_seconds}s between API calls")
    print("-" * 50)

    while True:
        page_count += 1
        retry_count = 0
        batch = []
        next_cursor = None
        recovered_from_error = False

        # Debug: print the cursor URL being used
        if cursor:
            print(f"  [DEBUG] Next URL: {cursor}")

        # Retry logic for API calls with exponential backoff
        while retry_count < max_retries:
            try:
                batch, next_cursor = fetch_page_of_advertisable_medias(
                    access_token=access_token,
                    ig_account_id=ig_account_id,
                    creator_username=creator_username,
                    cursor=cursor,
                    limit=page_size,
                    only_with_permission=only_with_permission,
                )
                if retry_count > 0:
                    recovered_from_error = True
                break
            except APIError as e:
                retry_count += 1
                # Exponential backoff: 30, 60, 120, 240, 480, 960 seconds
                wait_time = 30 * (2 ** (retry_count - 1))
                print(f"  API Error on page {page_count}: {e.status_code}")
                print(f"  [DEBUG] Full cursor: {cursor}")
                if retry_count < max_retries:
                    print(f"  Exponential backoff: waiting {wait_time}s (retry {retry_count}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    print(f"  Failed after {max_retries} retries. Saving partial results...")
                    break
            except Exception as e:
                retry_count += 1
                # Exponential backoff: 4, 8, 16, 32, 64 seconds
                wait_time = delay_seconds * (2 ** retry_count)
                print(f"  Error on page {page_count}: {e}")
                if retry_count < max_retries:
                    print(f"  Exponential backoff: waiting {wait_time}s (retry {retry_count}/{max_retries})...")
                    time.sleep(wait_time)
                else:
                    print(f"  Failed after {max_retries} retries: {e}")
                    raise

        # If we exhausted retries on APIError, save and exit
        if retry_count >= max_retries:
            print(f"  Stopping due to persistent API errors after {len(all_medias)} medias")
            break

        # Handle empty batches (legitimate end of data)
        if not batch:
            if next_cursor is None and cursor is not None:
                consecutive_empty += 1
                if consecutive_empty >= max_consecutive_empty:
                    print(f"  {consecutive_empty} consecutive empty batches - export complete")
                    break
                print(f"  Empty batch {consecutive_empty}/{max_consecutive_empty}, retrying...")
                time.sleep(delay_seconds * 2)
                continue
            elif cursor is None:
                print("  No medias found")
                break
            else:
                # Normal end - next_cursor is None
                break

        consecutive_empty = 0

        all_medias.extend(batch)
        print(f"Page {page_count}: fetched {len(batch)} medias (total: {len(all_medias)})")

        # Check if we've reached the end
        if next_cursor is None:
            print("Reached end of medias")
            break

        cursor = next_cursor

        # Cooldown: wait longer after recovering from an error
        if recovered_from_error:
            cooldown = 30
            print(f"  [Cooldown] Recovered from error, waiting {cooldown}s before next request...")
            time.sleep(cooldown)
        else:
            # Normal rate limiting
            time.sleep(delay_seconds)

    # Fetch engagement metrics if requested
    if include_metrics and all_medias:
        print("-" * 50)
        print("Fetching engagement metrics...")
        total = len(all_medias)
        for idx, media in enumerate(all_medias, 1):
            media_id = media.get("id")
            if media_id:
                if idx % 10 == 0 or idx == total:
                    print(f"  Fetching metrics: {idx}/{total}")
                metrics = fetch_media_insights(access_token, media_id)
                media["likes"] = metrics.get("likes")
                media["comments"] = metrics.get("comments")
                time.sleep(0.5)  # Rate limit for metrics API

    # Write to CSV
    if all_medias:
        # Collect ALL unique fieldnames from all medias (not just first one)
        all_fieldnames = set()
        for media in all_medias:
            all_fieldnames.update(media.keys())

        # Convert to sorted list for consistent column order
        fieldnames = sorted(list(all_fieldnames))

        # Ensure metrics columns are at the end if included
        if include_metrics:
            for col in ["likes", "comments"]:
                if col in fieldnames:
                    fieldnames.remove(col)
                fieldnames.append(col)

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_medias)

        print("-" * 50)
        print(f"Export complete!")
        print(f"Total medias: {len(all_medias)}")
        print(f"Total pages: {page_count}")
        print(f"Output file: {output_file}")
        print(f"Finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("No medias to export")


def main():
    parser = argparse.ArgumentParser(
        description="Export all advertisable medias from an Instagram account",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic export
    python export_medias.py --access-token YOUR_TOKEN --ig-account-id YOUR_ID

    # With filters and metrics
    python export_medias.py --access-token YOUR_TOKEN --ig-account-id YOUR_ID \\
        --creator-username someuser --only-with-permission --include-metrics

    # Run in background
    nohup python export_medias.py --access-token YOUR_TOKEN --ig-account-id YOUR_ID \\
        --output medias.csv > export.log 2>&1 &

    # Disable SSL verification
    SSL_VERIFY=false python export_medias.py --access-token YOUR_TOKEN --ig-account-id YOUR_ID
        """,
    )

    parser.add_argument(
        "--access-token",
        required=True,
        help="Facebook/Instagram access token",
    )
    parser.add_argument(
        "--ig-account-id",
        required=True,
        help="Instagram account ID",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output CSV file path (default: medias_YYYYMMDD_HHMMSS.csv)",
    )
    parser.add_argument(
        "--creator-username",
        default=None,
        help="Filter by creator username",
    )
    parser.add_argument(
        "--only-with-permission",
        action="store_true",
        help="Only include medias with permission granted",
    )
    parser.add_argument(
        "--include-metrics",
        action="store_true",
        help="Include engagement metrics (likes, comments)",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=25,
        help="Items per page (default: 25, try 10 if API is flaky)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=30.0,
        help="Delay in seconds between API calls (default: 30.0)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=6,
        help="Maximum retries for failed API calls (default: 6). Uses exponential backoff: 30s, 60s, 120s, 240s, 480s, 960s (~30min total)",
    )

    args = parser.parse_args()

    # Generate default output filename if not provided
    output_file = args.output
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"medias_{timestamp}.csv"

    try:
        export_all_medias(
            access_token=args.access_token,
            ig_account_id=args.ig_account_id,
            output_file=output_file,
            creator_username=args.creator_username,
            only_with_permission=args.only_with_permission,
            include_metrics=args.include_metrics,
            delay_seconds=args.delay,
            max_retries=args.max_retries,
            page_size=args.page_size,
        )
    except KeyboardInterrupt:
        print("\nExport cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nExport failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
