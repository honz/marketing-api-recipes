"""
Partnership Ads Booster - Web UI

A Streamlit-based web interface for the partnership ads automation tool.

To run:
Instructions to run:
$python3 -m venv venv
$source venv/bin/activate
$pip install requests
$pip install streamlit pandas
$streamlit run partnership_ads_ui.py

For bulk export, use the CLI script:
$python export_medias.py --access-token YOUR_TOKEN --ig-account-id YOUR_ID --include-metrics
"""

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from partnership_ads_booster import (
    fetch_page_of_advertisable_medias,
    create_partnership_ads_from_csv,
    fetch_account_level_permissions,
    bulk_request_account_level_permissions,
)


def main():
    st.set_page_config(
        page_title="Partnership Ads Booster",
        page_icon="🚀",
        layout="wide",
    )

    st.title("🚀 Partnership Ads Booster")
    st.markdown("Automate fetching and creating Instagram partnership ads")

    # Helper function to sanitize input (remove invisible Unicode characters)
    def sanitize_input(text: str) -> str:
        if not text:
            return text
        # Remove zero-width spaces and other invisible characters
        invisible_chars = [
            '\u200b',  # Zero-width space
            '\u200c',  # Zero-width non-joiner
            '\u200d',  # Zero-width joiner
            '\ufeff',  # BOM
            '\u00a0',  # Non-breaking space
            '\u2060',  # Word joiner
        ]
        result = text
        for char in invisible_chars:
            result = result.replace(char, '')
        return result.strip()

# Initialize session state for credentials
    if 'access_token' not in st.session_state:
        st.session_state.access_token = ''
    if 'business_id' not in st.session_state:
        st.session_state.business_id = ''
    if 'ig_user_id' not in st.session_state:
        st.session_state.ig_user_id = ''
    if 'ad_account_id' not in st.session_state:
        st.session_state.ad_account_id = ''
    if 'fb_page_id' not in st.session_state:
        st.session_state.fb_page_id = ''

    # Callback functions to update session state
    def save_access_token():
        value = sanitize_input(st.session_state.access_token_input)
        st.session_state.access_token = value

    def save_business_id():
        value = sanitize_input(st.session_state.business_id_input)
        st.session_state.business_id = value

    def save_ig_user_id():
        value = sanitize_input(st.session_state.ig_user_id_input)
        st.session_state.ig_user_id = value

    # Sidebar for common inputs
    st.sidebar.header("Authentication")
    st.sidebar.text_input(
        "Access Token",
        type="password",
        help="Your Facebook/Instagram access token",
        key="access_token_input",
        value=st.session_state.access_token,
        on_change=save_access_token
    )
    st.sidebar.text_input(
        "Business ID",
        help="Your Business ID (required for Content Discovery API)",
        key="business_id_input",
        value=st.session_state.business_id,
        on_change=save_business_id
    )
    st.sidebar.text_input(
        "Instagram User ID",
        help="Your Instagram User ID",
        key="ig_user_id_input",
        value=st.session_state.ig_user_id,
        on_change=save_ig_user_id
    )

    # Get sanitized values from session state
    access_token = st.session_state.access_token
    business_id = st.session_state.business_id
    ig_user_id = st.session_state.ig_user_id

    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📥 Fetch Medias", "🔐 Bulk Request Permission", "🎯 Create Ads"])

    # Tab 1: Fetch Advertisable Medias (Paginated)
    with tab1:
        st.header("Fetch Advertisable Medias")
        st.markdown(
            "Download advertisable medias with eligibility and permission information"
        )

        # Initialize session state for pagination
        if 'fetch_medias_state' not in st.session_state:
            st.session_state.fetch_medias_state = {
                'medias': [],
                'next_cursor': None,
                'has_more': True,
                'is_initialized': False,
                'include_metrics': False,
                'is_fetching': False,
            }

        state = st.session_state.fetch_medias_state

        # Basic Filters - in a clean, organized layout
        st.subheader("🔍 Basic Filters")
        
        include_metrics = st.checkbox(
            "📊 Include engagement metrics",
            value=False,
            help="Fetch likes, comments, views, and other engagement metrics",
            key="fetch_include_metrics"
        )

        # Advanced Filters - collapsible section
        with st.expander("⚙️ Advanced Filters", expanded=False):
            st.markdown("Refine your search with additional filters")
            
            # Search keywords
            search_key = st.text_input(
                "🔎 Search Keywords",
                help="Search by keyword across caption text",
                key="fetch_search_key",
                placeholder="e.g., summer collection"
            )
            
            st.markdown("---")
            
            # Filter columns
            col1, col2 = st.columns(2)
            with col1:
                post_types = st.multiselect(
                    "📱 Post Types",
                    options=["FEED", "STORIES", "REELS"],
                    help="Filter by post type",
                    key="fetch_post_types"
                )
                
            ad_eligibilities = st.multiselect(
                    "✓ Ad Eligibility",
                    options=["AD_READY", "INELIGIBLE", "NEEDS_ATTENTION", "EXCLUDED"],
                    help="Filter by ad eligibility status",
                    key="fetch_ad_eligibilities"
                )
            
            with col2:
                ad_usages = st.multiselect(
                    "📈 Ad Usage",
                    options=["NEVER_USED", "ACTIVE", "PREVIOUSLY_USED"],
                    help="Filter by ad usage status",
                    key="fetch_ad_usages"
                )
            
            st.markdown("---")
            
            # Date range filter with shortcuts
            st.markdown("**📅 Date Range**")
            
            # Date shortcut buttons
            st.markdown("Quick selects:")
            shortcut_col1, shortcut_col2, shortcut_col3, shortcut_col4, shortcut_col5 = st.columns(5)
            with shortcut_col1:
                if st.button("7 days ago", key="date_7d", help="Set start date to 7 days ago"):
                    st.session_state.fetch_start_date = datetime.now().date() - timedelta(days=7)
                    st.rerun()
            with shortcut_col2:
                if st.button("1 month ago", key="date_1m", help="Set start date to 1 month ago"):
                    st.session_state.fetch_start_date = datetime.now().date() - timedelta(days=30)
                    st.rerun()
            with shortcut_col3:
                if st.button("1 year ago", key="date_1y", help="Set start date to 1 year ago"):
                    st.session_state.fetch_start_date = datetime.now().date() - timedelta(days=365)
                    st.rerun()
            with shortcut_col4:
                if st.button("Today", key="date_today", help="Set end date to today (API uses yesterday as max)"):
                    # API doesn't allow future dates, use yesterday as max
                    st.session_state.fetch_end_date = datetime.now().date() - timedelta(days=1)
                    st.rerun()
            with shortcut_col5:
                if st.button("Clear dates", key="date_clear", help="Clear both dates"):
                    st.session_state.fetch_start_date = None
                    st.session_state.fetch_end_date = None
                    st.rerun()
            
            col3, col4 = st.columns(2)
            with col3:
                start_date = st.date_input(
                    "Start Date",
                    value=None,
                    help="Filter by content creation date (from) - leave blank for no start date filter",
                    key="fetch_start_date"
                )
            with col4:
                end_date = st.date_input(
                    "End Date",
                    value=None,
                    help="Filter by content creation date (to) - leave blank for no end date filter",
                    key="fetch_end_date"
                )

        # Action buttons row
        col1, col2, col3 = st.columns([2, 2, 2])

        with col1:
            fetch_clicked = st.button(
                "🔄 Fetch Next 25" if state['is_initialized'] else "🔍 Fetch Medias",
                type="primary",
                use_container_width=True
            )

        with col2:
            if state['medias']:
                # Convert to DataFrame for CSV export
                export_data = []
                for m in state['medias']:
                    row = {
                        'media_id': m.get('id', ''),
                        'permalink': m.get('permalink', ''),
                        'owner_id': m.get('owner_id', ''),
                        'has_permission_for_partnership_ad': m.get('has_permission_for_partnership_ad', False),
                        'eligibility_errors': str(m.get('eligibility_errors', [])),
                    }
                    # Include metrics columns if they exist
                    if 'likes' in m:
                        row['likes'] = m.get('likes')
                    if 'comments' in m:
                        row['comments'] = m.get('comments')
                    export_data.append(row)

                df_export = pd.DataFrame(export_data)
                csv_data = df_export.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv_data,
                    file_name="advertisable_medias.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.button("⬇️ Download CSV", disabled=True, use_container_width=True)

        with col3:
            if st.button("🗑️ Clear All", use_container_width=True, disabled=not state['medias']):
                state['medias'] = []
                state['next_cursor'] = None
                state['has_more'] = True
                state['is_initialized'] = False
                st.rerun()

        # Handle fetch action
        if fetch_clicked:
            if not access_token or not business_id or not ig_user_id:
                st.error("❌ Please provide Access Token, Business ID, and Instagram User ID")
            else:
                # Check if filters changed - reset if so
                if (state['is_initialized'] and
                    state['include_metrics'] != include_metrics):
                    state['medias'] = []
                    state['next_cursor'] = None
                    state['has_more'] = True

                # Update filter state
                state['include_metrics'] = include_metrics

                with st.spinner("Fetching medias..." + (" (including metrics)" if include_metrics else "")):
                    try:
                        # Prepare date strings
                        start_date_str = start_date.strftime("%Y-%m-%d") if start_date else None
                        end_date_str = end_date.strftime("%Y-%m-%d") if end_date else None
                        
                        # Show debug info in UI
                        st.info(f"🔍 Debug: Calling API with business_id={business_id}, ig_user_id={ig_user_id}")
                        
                        batch, next_cursor = fetch_page_of_advertisable_medias(
                            access_token=access_token,
                            business_id=business_id,
                            ig_user_id=ig_user_id,
                            cursor=state['next_cursor'],
                            limit=50,
                            post_types=post_types if post_types else None,
                            ad_eligibilities=ad_eligibilities if ad_eligibilities else None,
                            ad_usages=ad_usages if ad_usages else None,
                            start_date=start_date_str,
                            end_date=end_date_str,
                            search_key=search_key if search_key else None,
                            include_engagement_metrics=state['include_metrics'],
                        )

                        state['medias'].extend(batch)
                        state['next_cursor'] = next_cursor
                        state['has_more'] = next_cursor is not None
                        state['is_initialized'] = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

        # Display data
        if state['medias']:
            st.success(f"✅ Loaded {len(state['medias'])} medias")

            # Convert to display DataFrame - NEW TABLE DESIGN with rich Content Discovery API fields
            display_data = []
            for m in state['medias']:
                # Get partnership info for eligibility and permission details
                ad_eligibility = m.get('ad_eligibility', '')
                permission_status = m.get('permission_status', '')
                ad_usage = m.get('ad_usage', '')
                # API returns lowercase enums (e.g. "ad_ready"); normalize for matching
                ad_eligibility_key = (ad_eligibility or '').upper()
                permission_status_key = (permission_status or '').upper()
                ad_usage_key = (ad_usage or '').upper()
                
                # Create eligibility badge with color coding
                if ad_eligibility_key == 'AD_READY':
                    eligibility_badge = '✅ Ready'
                elif ad_eligibility_key == 'NEEDS_ATTENTION':
                    eligibility_badge = '⚠️ Needs Attention'
                elif ad_eligibility_key == 'INELIGIBLE':
                    eligibility_badge = '❌ Ineligible'
                elif ad_eligibility_key == 'EXCLUDED':
                    eligibility_badge = '🚫 Excluded'
                else:
                    eligibility_badge = ad_eligibility or 'Unknown'
                
                # Create permission badge (green check = authorized, red cross = not)
                if permission_status_key == 'AUTHORIZED':
                    permission_badge = '✅'
                elif permission_status_key == 'UNAUTHORIZED':
                    permission_badge = '❌'
                else:
                    permission_badge = permission_status or 'Unknown'
                
                # Create usage badge
                if ad_usage_key == 'NEVER_USED':
                    usage_badge = '🆕 New'
                elif ad_usage_key == 'ACTIVE':
                    usage_badge = '🟢 Active'
                elif ad_usage_key == 'PREVIOUSLY_USED':
                    usage_badge = '📊 Used'
                else:
                    usage_badge = ad_usage or 'Unknown'
                
                # Safely handle caption
                caption = m.get('caption') or ''
                caption_display = (caption[:50] + '...') if len(caption) > 50 else caption
                
                row = {
                    'content_id': m.get('id', ''),
                    'platform': m.get('platform', ''),
                    'media_type': m.get('media_type', ''),
                    'post_type': m.get('post_type', ''),
                    'permalink': m.get('permalink', ''),
                    'caption': caption_display,
                    'author': m.get('author_display_name', ''),
                    'eligibility': eligibility_badge,
                    'permission': permission_badge,
                    'usage': usage_badge,
                    'is_recommended': 'yes' if m.get('is_recommended', False) else 'no',
                }
                # Include metrics columns if they exist
                if m.get('likes') is not None:
                    row['likes'] = m.get('likes')
                if m.get('comments') is not None:
                    row['comments'] = m.get('comments')
                if m.get('views') is not None:
                    row['views'] = m.get('views')
                if m.get('reach') is not None:
                    row['reach'] = m.get('reach')
                if m.get('shares') is not None:
                    row['shares'] = m.get('shares')
                if m.get('interaction') is not None:
                    row['interaction'] = m.get('interaction')
                if m.get('saves') is not None:
                    row['saves'] = m.get('saves')
                display_data.append(row)

            df_display = pd.DataFrame(display_data)

            # Build column config dynamically - NEW TABLE DESIGN
            column_config = {
                "content_id": st.column_config.TextColumn("Content ID", width="medium"),
                "platform": st.column_config.TextColumn("Platform", width="small"),
                "media_type": st.column_config.TextColumn("Media", width="small"),
                "post_type": st.column_config.TextColumn("Post Type", width="small"),
                "permalink": st.column_config.LinkColumn("Link", width="medium"),
                "caption": st.column_config.TextColumn("Caption", width="large"),
                "author": st.column_config.TextColumn("Creator", width="medium"),
                "eligibility": st.column_config.TextColumn("Eligibility", width="small"),
                "permission": st.column_config.TextColumn("Permission", width="small"),
                "usage": st.column_config.TextColumn("Usage", width="small"),
                "is_recommended": st.column_config.TextColumn("Recommended", width="small", help="Recommended by AI"),
            }
            if 'likes' in df_display.columns:
                column_config["likes"] = st.column_config.NumberColumn("Likes", width="small")
            if 'comments' in df_display.columns:
                column_config["comments"] = st.column_config.NumberColumn("Comments", width="small")
            if 'views' in df_display.columns:
                column_config["views"] = st.column_config.NumberColumn("Views", width="small")
            if 'reach' in df_display.columns:
                column_config["reach"] = st.column_config.NumberColumn("Reach", width="small")
            if 'shares' in df_display.columns:
                column_config["shares"] = st.column_config.NumberColumn("Shares", width="small")
            if 'interaction' in df_display.columns:
                column_config["interaction"] = st.column_config.NumberColumn("Interaction", width="small")
            if 'saves' in df_display.columns:
                column_config["saves"] = st.column_config.NumberColumn("Saves", width="small")

            st.dataframe(
                df_display,
                height=400,
                width='stretch',
                column_config=column_config
            )

            # Status message
            if state['has_more']:
                st.info("📊 Click 'Fetch Next 25' to load more medias.")
            else:
                st.success("✅ All medias loaded!")
        elif state['is_initialized']:
            st.warning("No medias found matching your criteria.")

        # CLI Export hint
        st.divider()
        st.info("""
        **💡 Need to export all medias?** Use the CLI script for bulk exports:
        ```
        python export_medias.py --access-token YOUR_TOKEN --ig-account-id YOUR_ID --include-metrics
        ```
        Run `python export_medias.py --help` for all options.
        """)

    # Tab 3: Create Partnership Ads
    with tab3:
        st.header("Create Partnership Ads")
        st.markdown("Bulk create partnership ads from a CSV file")

        # Show required CSV format
        with st.expander("📋 Required CSV Format"):
            st.markdown(
                """
            Your input CSV must have the following columns:

            **Required:**
            - `cta_type`: Call to action type (e.g., "INSTALL_MOBILE_APP", "LEARN_MORE")
            - `link`: CTA link (mandatory)
            - `ad_name`: Name for the ad
            - `ad_set_id`: Ad set ID (must be text, not number) — **optional if `copy_ad_set_id` is provided**
            - **Either** `permalink` OR `ad_code` (at least one is required)

            **Optional:**
            - `app_link`: CTA app link
            - `app_id`: App ID for app events tracking
            - `product_set_id`: Product set ID
            - `utm_parameters`: UTM parameters in query string format (e.g., `utm_source=instagram&utm_medium=paid`)
            - `testimonial`: Testimonial text for the ad
            - `source_url`: Source URL for the creative
            - `identities`: Controls which identities to display in the ad. Values (case insensitive): `BOTH` (default, both identities), `FIRST` (first identity only), `DYNAMIC` (system optimizes)
            - `multi_advertiser_ads`: Controls multi-advertiser ads enrollment. Values (case insensitive): `OPT_OUT` (to disable multi-advertiser ads), `OPT_IN` (to enable, default behavior)
            - `copy_ad_set_id`: Source ad set ID to duplicate via `POST /{ad_set_id}/copies`. When set, a copy is created **in the same campaign** and its ID is used as `ad_set_id` for ad creation, so `ad_set_id` becomes optional.
            - `ad_set_rename`: Exact name for the newly copied ad set. Only used when `copy_ad_set_id` is provided; the copy is renamed to this value.

            **Note:** Stories URLs are not supported and will be rejected.
            """
            )

        # Show hint if sidebar credentials not provided
        if not access_token or not business_id or not ig_user_id:
            st.info("👈 Enter your Access Token and Instagram Account ID in the sidebar first.")

        with st.form("create_form"):
            col1, col2 = st.columns(2)

            with col1:
                ad_account_id = st.text_input(
                    "Ad Account ID",
                    help="Your Facebook ad account ID",
                    key="ad_account_id_input",
                    value=st.session_state.ad_account_id,
                )

            with col2:
                facebook_page_id = st.text_input(
                    "Facebook Page ID",
                    help="Your Facebook page ID",
                    key="fb_page_id_input",
                    value=st.session_state.fb_page_id,
                )

            uploaded_file = st.file_uploader(
                "Upload CSV File",
                type=["csv"],
                help="Upload the CSV file with ad information",
            )

            output_filename_create = st.text_input(
                "Output Filename",
                value="created_ads_output.csv",
                help="Name for the output CSV file with results",
            )

            submit_create = st.form_submit_button("🎯 Create Ads", type="primary")

        if submit_create:
            # Save ad account and page IDs in session state
            st.session_state.ad_account_id = sanitize_input(ad_account_id)
            st.session_state.fb_page_id = sanitize_input(facebook_page_id)

            ad_account_id = st.session_state.ad_account_id
            facebook_page_id = st.session_state.fb_page_id

            if not access_token or not business_id or not ig_user_id:
                st.error("❌ Please provide Access Token and Instagram Account ID")
            elif not ad_account_id or not facebook_page_id:
                st.error("❌ Please provide Ad Account ID and Facebook Page ID")
            elif not uploaded_file:
                st.error("❌ Please upload a CSV file")
            else:
                with st.spinner("Creating partnership ads..."):
                    try:
                        # Save uploaded file to current directory
                        temp_input = f"input_{uploaded_file.name}"
                        temp_output_create = output_filename_create

                        with open(temp_input, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                        # Show input preview - read with string dtypes for ID columns
                        input_df = pd.read_csv(
                            temp_input,
                            dtype={
                                'ad_set_id': str,
                                'media_id': str,
                                'owner_id': str,
                            }
                        )
                        st.subheader("Input CSV Preview")
                        st.dataframe(input_df.head(10), width='stretch')
                        st.info(f"📊 Total rows to process: {len(input_df)}")

                        # Create ads
                        create_partnership_ads_from_csv(
                            access_token,
                            business_id,
                            ig_user_id,
                            ad_account_id,
                            facebook_page_id,
                            temp_input,
                            temp_output_create,
                        )

                        # Read results with string dtypes for ID columns
                        results_df = pd.read_csv(
                            temp_output_create,
                            dtype={
                                'ad_set_id': str,
                                'video_id': str,
                                'creative_id': str,
                                'published_ad_id': str,
                                'media_id': str,
                                'owner_id': str,
                            }
                        )

                        # Calculate statistics
                        successful = len(
                            results_df[results_df["status"] == "success"]
                        )
                        failed = len(results_df[results_df["status"] == "failed"])

                        # Display results
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Processed", len(results_df))
                        with col2:
                            st.metric("✅ Successful", successful)
                        with col3:
                            st.metric("❌ Failed", failed)

                        # Show results table
                        st.subheader("Results")
                        st.dataframe(results_df, width='stretch')

                        # Show errors if any
                        if failed > 0:
                            st.subheader("❌ Failed Ads")
                            failed_df = results_df[results_df["status"] == "failed"][
                                ["ad_name", "ad_set_id", "error"]
                            ]
                            st.dataframe(failed_df, width='stretch')

                        # Download button
                        with open(temp_output_create, "rb") as f:
                            st.download_button(
                                label="⬇️ Download Results CSV",
                                data=f.read(),
                                file_name=output_filename_create,
                                mime="text/csv",
                            )

                        if successful > 0:
                            st.success(
                                f"✅ Successfully created {successful} ads out of {len(results_df)} total!"
                            )
                        else:
                            st.warning("⚠️ No ads were created successfully.")

                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

    # Tab 2: Bulk Request Permission
    with tab2:
        st.header("Bulk Request Permission")
        st.markdown(
            "View existing partnership ad permissions and request new permissions in bulk"
        )

        # Sub-tabs for View and Request
        permission_tab1, permission_tab2 = st.tabs(
            ["📋 View Existing Permissions", "📤 Bulk Request Permissions"]
        )

        # Sub-tab 1: View Existing Permissions
        with permission_tab1:
            st.subheader("Existing Account Level Permissions")
            st.markdown(
                "View all creator accounts that have granted permission to run partnership ads"
            )

            with st.form("view_permissions_form"):
                output_filename_permissions = st.text_input(
                    "Output Filename",
                    value="existing_permissions.csv",
                    help="Name for the output CSV file",
                )

                submit_view_permissions = st.form_submit_button(
                    "🔍 Fetch Existing Permissions", type="primary"
                )

            if submit_view_permissions:
                if not access_token or not business_id or not ig_user_id:
                    st.error("❌ Please provide Access Token and Instagram Account ID in the sidebar")
                else:
                    with st.spinner("Fetching existing permissions..."):
                        try:
                            permissions = fetch_account_level_permissions(
                                access_token,
                                ig_user_id,
                                output_filename_permissions,
                            )

                            if permissions:
                                df = pd.DataFrame(permissions)
                                # Only keep the required columns
                                display_columns = ["creator_ig_id", "creator_username", "permission_status"]
                                df = df[[col for col in display_columns if col in df.columns]]
                                st.success(f"✅ Found {len(permissions)} existing permissions!")

                                # Display preview
                                st.subheader("Permissions List")

                                # Show metrics
                                st.metric("Total Permissions", len(permissions))

                                # Display table
                                st.dataframe(df, width='stretch')

                                # Download button
                                with open(output_filename_permissions, "rb") as f:
                                    st.download_button(
                                        label="⬇️ Download Permissions CSV",
                                        data=f.read(),
                                        file_name=output_filename_permissions,
                                        mime="text/csv",
                                    )
                            else:
                                st.info("ℹ️ No existing permissions found for this account.")

                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")

        # Sub-tab 2: Bulk Request Permissions
        with permission_tab2:
            st.subheader("Request Permissions from Creators")
            st.markdown(
                "Upload a CSV file with creator IDs to request partnership ad permissions in bulk (max 100 rows)"
            )

            # Show required CSV format
            with st.expander("📋 Required CSV Format"):
                st.markdown(
                    """
                Your input CSV must have at least one of the following columns:

                - `creator_instagram_account`: The Instagram account ID of the creator
                - `creator_instagram_username`: The creator's Instagram username

                **Note:** Either field is sufficient. You can provide one or both.

                **⚠️ Limit: Maximum 100 rows per request**

                **Example with account IDs:**
                ```csv
                creator_instagram_account
                17841401234567890
                17841409876543210
                ```

                **Example with usernames:**
                ```csv
                creator_instagram_username
                creator_handle_1
                creator_handle_2
                ```

                **Example with both:**
                ```csv
                creator_instagram_account,creator_instagram_username
                17841401234567890,creator_handle_1
                17841409876543210,creator_handle_2
                ```

                **Note:** Permission requests are sent to creators. They must accept
                the permission request before you can create partnership ads with their content.
                """
                )

            with st.form("bulk_request_form"):
                uploaded_permission_file = st.file_uploader(
                    "Upload CSV File with Creator IDs (max 100 rows)",
                    type=["csv"],
                    help="Upload a CSV file containing creator_instagram_account or creator_instagram_username column",
                )

                output_filename_request = st.text_input(
                    "Output Filename",
                    value="permission_request_results.csv",
                    help="Name for the output CSV file with request results",
                )

                submit_bulk_request = st.form_submit_button(
                    "📤 Send Permission Requests", type="primary"
                )

            if submit_bulk_request:
                if not access_token or not business_id or not ig_user_id:
                    st.error("❌ Please provide Access Token and Instagram Account ID in the sidebar")
                elif not uploaded_permission_file:
                    st.error("❌ Please upload a CSV file with creator IDs")
                else:
                    with st.spinner("Sending permission requests..."):
                        try:
                            # Save uploaded file
                            temp_input_permission = f"input_{uploaded_permission_file.name}"

                            with open(temp_input_permission, "wb") as f:
                                f.write(uploaded_permission_file.getbuffer())

                            # Show input preview
                            input_df = pd.read_csv(
                                temp_input_permission,
                                dtype={"creator_instagram_account": str},
                                encoding="utf-8-sig",
                            )
                            st.subheader("Input CSV Preview")
                            st.dataframe(input_df.head(10), width='stretch')

                            # Check row limit
                            if len(input_df) > 100:
                                st.error(f"❌ CSV has {len(input_df)} rows, which exceeds the limit of 100. Please reduce the number of rows.")
                            else:
                                st.info(f"📊 Total creators to request: {len(input_df)}")

                                # Send bulk requests
                                bulk_request_account_level_permissions(
                                    access_token,
                                    ig_user_id,
                                    temp_input_permission,
                                    output_filename_request,
                                )

                                # Read results
                                results_df = pd.read_csv(
                                    output_filename_request,
                                    dtype={"creator_instagram_account": str}
                                )

                                # Calculate statistics
                                successful = len(results_df[results_df["status"] == "success"])
                                failed = len(results_df[results_df["status"] == "failed"])

                                # Display results
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Total Processed", len(results_df))
                                with col2:
                                    st.metric("✅ Successful", successful)
                                with col3:
                                    st.metric("❌ Failed", failed)

                                # Show results table
                                st.subheader("Results")
                                st.dataframe(results_df, width='stretch')

                                # Show errors if any
                                if failed > 0:
                                    st.subheader("❌ Failed Requests")
                                    failed_df = results_df[results_df["status"] == "failed"][
                                        ["creator_instagram_account", "creator_instagram_username", "error"]
                                    ]
                                    st.dataframe(failed_df, width='stretch')

                                # Download button
                                with open(output_filename_request, "rb") as f:
                                    st.download_button(
                                        label="⬇️ Download Results CSV",
                                        data=f.read(),
                                        file_name=output_filename_request,
                                        mime="text/csv",
                                    )

                                if successful > 0:
                                    st.success(
                                        f"✅ Successfully sent {successful} permission requests out of {len(results_df)} total!"
                                    )
                                else:
                                    st.warning("⚠️ No permission requests were sent successfully.")

                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
    ### 📚 Quick Help

    **Fetch Mode:**
    1. Enter your credentials
    2. Optionally filter by creator
    3. Click Fetch Medias
    4. Download the CSV

    **Create Mode:**
    1. Enter all required IDs
    2. Upload your CSV file
    3. Click Create Ads
    4. Download the results

    **Note:** All ads are created in PAUSED status.
    """
    )


if __name__ == "__main__":
    main()
