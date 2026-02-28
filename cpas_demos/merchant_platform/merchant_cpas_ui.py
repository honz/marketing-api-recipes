"""
Merchant Platform UI

A Streamlit-based web interface for merchants to manage CPAS brand partnerships,
create catalog segments, and share them with brand partners.

Uses SQLite cache layer to minimize Graph API calls.
First load fetches from API; subsequent loads serve from cache until TTL expires.

To run:
$ cd cpas_demos
$ streamlit run merchant_platform/merchant_cpas_ui.py
"""

import sys
from pathlib import Path

# Add this directory first so `import config` finds merchant_platform/config.py,
# then parent directory for shared module imports.
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(1, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st

from merchant_cpas_backend import (
    validate_merchant_setup,
    get_dashboard_stats,
    get_pending_requests,
    get_all_partnerships,
    get_active_partners,
    get_catalog_segments,
    get_full_catalogs,
    share_catalog_with_brand,
    refresh_all_data,
    get_merchant_name,
    get_brand_values,
    create_catalog_segment,
)
from cache import init_cache, force_refresh_all, invalidate_catalog_list, invalidate_all_partnerships, has_cached_partnerships, cached_get_all_segment_partnerships

# Import config for default values
try:
    import config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    config = None


def get_cache_db():
    """Initialize SQLite cache. Uses module-level singleton in cache.py."""
    return init_cache()


def warm_cache(access_token, merchant_bm_id):
    """
    Populate catalog cache on startup.
    Only loads the catalog list — partnerships are loaded on-demand
    when the user navigates to a tab that needs them.
    """
    from cache import cached_get_owned_product_catalogs

    cached_get_owned_product_catalogs(access_token, merchant_bm_id)

    if "merchant_name" not in st.session_state:
        st.session_state.merchant_name = get_merchant_name(access_token, merchant_bm_id)


def init_session_state():
    """Initialize session state variables."""
    if "merchant_validated" not in st.session_state:
        st.session_state.merchant_validated = False
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Dashboard"


def main():
    st.set_page_config(
        page_title="Merchant CPAS Platform",
        page_icon="",
        layout="wide",
    )

    # Initialize cache singleton (module-level, persists within process)
    get_cache_db()

    # Pre-populate cache on startup if config has credentials
    default_token = getattr(config, 'ACCESS_TOKEN', None) if CONFIG_AVAILABLE else None
    default_merchant_bm = getattr(config, 'MERCHANT_BUSINESS_ID', None) if CONFIG_AVAILABLE else None

    init_session_state()

    # Only warm cache once per session — skip on subsequent reruns
    cache_ready = st.session_state.get("cache_ready", False)
    if not cache_ready and default_token and default_merchant_bm:
        warm_cache(default_token, default_merchant_bm)
        st.session_state.cache_ready = True

    st.title("Merchant CPAS Platform")
    st.markdown("Manage brand partnerships and enable self-service CPAS onboarding")

    # Sidebar for authentication
    with st.sidebar:
        st.header("Configuration")

        # Get defaults from config if available
        default_token = getattr(config, 'ACCESS_TOKEN', None) if CONFIG_AVAILABLE else None
        default_merchant_bm = getattr(config, 'MERCHANT_BUSINESS_ID', None) if CONFIG_AVAILABLE else None

        # Show config status
        if CONFIG_AVAILABLE and default_token:
            st.success("Config loaded")
        else:
            st.info("Enter credentials below or update config.py")

        # Only show input fields if config values are not set
        if default_token:
            access_token = default_token
            st.text("Access Token: [Loaded from config]")
        else:
            access_token = st.text_input(
                "Access Token",
                type="password",
                help="Facebook/Meta access token with business_management permission",
            )

        if default_merchant_bm:
            merchant_bm_id = default_merchant_bm
            st.caption(f"BM ID: {merchant_bm_id}")
        else:
            merchant_bm_id = st.text_input(
                "Merchant Business Manager ID",
                help="Your merchant's Business Manager ID",
            )

        # Show merchant name if available (derived from BM ID)
        merchant_name = st.session_state.get("merchant_name", "")
        if merchant_name:
            st.text(f"Merchant: {merchant_name}")

        # Validate button
        if st.button("Validate Setup", type="primary"):
            if not all([access_token, merchant_bm_id]):
                st.error("Please fill in all required fields")
            else:
                with st.spinner("Validating credentials..."):
                    result, error = validate_merchant_setup(access_token, merchant_bm_id)
                    if error:
                        st.error(f"Validation failed: {error}")
                        st.session_state.merchant_validated = False
                    else:
                        st.success("Setup validated!")
                        st.session_state.merchant_validated = True
                        st.session_state.merchant_name = result["merchant_info"].get("name", merchant_bm_id)
                        with st.spinner("Loading data into cache..."):
                            warm_cache(access_token, merchant_bm_id)
                        st.session_state.cache_ready = True
                        st.rerun()

    # Gate the UI: require validation + cache warmup before showing tabs
    if not st.session_state.cache_ready:
        st.info("👈 Please enter your credentials and click **Validate Setup** in the sidebar to get started.")
        st.stop()

    # Main navigation
    # Apply pending navigation request (set before the widget renders)
    if "_nav_to" in st.session_state:
        st.session_state.active_tab = st.session_state._nav_to
        del st.session_state._nav_to

    TAB_OPTIONS = ["Dashboard", "Pending Requests", "Active Partners", "Catalog Segments", "Create & Share"]
    active_tab = st.radio(
        "Navigation",
        options=TAB_OPTIONS,
        key="active_tab",
        horizontal=True,
        label_visibility="collapsed",
    )

    # Tab 1: Dashboard
    if active_tab == "Dashboard":
        st.header("Merchant Dashboard")

        if not access_token or not merchant_bm_id:
            st.info("👈 Please configure your credentials in the sidebar to get started")
        else:
            col_title, col_refresh = st.columns([4, 1])
            with col_title:
                display_name = st.session_state.get("merchant_name", merchant_bm_id)
                st.markdown(f"**Merchant:** {display_name}")
            with col_refresh:
                if st.button("🔄 Refresh All", key="refresh_dashboard"):
                    force_refresh_all()
                    # Re-fetch partnership data so the dashboard doesn't
                    # fall back to the "not loaded" placeholder state.
                    progress_bar = st.progress(0, text="Refreshing partnerships…")
                    def _refresh_progress(done, total):
                        progress_bar.progress(done / total, text=f"Checking segment {done}/{total}…")
                    cached_get_all_segment_partnerships(
                        access_token, merchant_bm_id,
                        force_refresh=True, progress_callback=_refresh_progress,
                    )
                    progress_bar.empty()
                    st.rerun()

            # Catalog stats (cheap — cached)
            segments, _ = get_catalog_segments(access_token, merchant_bm_id)
            segment_count = len(segments) if segments else 0

            # Partnership stats (expensive — only show if cached)
            partnerships_cached = has_cached_partnerships()
            if partnerships_cached:
                stats = get_dashboard_stats(access_token, merchant_bm_id)
            else:
                stats = {"pending_requests": "—", "accepted_partners": "—", "total_partnerships": "—"}

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Pending Requests",
                    stats.get("pending_requests", 0),
                    help="Brands with shared segments awaiting acceptance",
                )

            with col2:
                st.metric(
                    "Accepted Partners",
                    stats.get("accepted_partners", 0),
                    help="Brands that have accepted catalog segment sharing",
                )

            with col3:
                st.metric(
                    "Catalog Segments",
                    segment_count,
                    help="Your catalog segments available for sharing",
                )

            with col4:
                st.metric(
                    "Total Partnerships",
                    stats.get("total_partnerships", 0),
                    help="Total brand partnerships across all segments",
                )

            if not partnerships_cached:
                st.info("Partnership stats not loaded yet. Click **Load Partnership Data** to fetch from API.")
                if st.button("Load Partnership Data", type="primary", key="load_partnerships"):
                    progress_bar = st.progress(0, text="Loading partnerships across all segments...")
                    def _update_progress(done, total):
                        progress_bar.progress(done / total, text=f"Checking segment {done}/{total}...")
                    cached_get_all_segment_partnerships(
                        access_token, merchant_bm_id,
                        force_refresh=True, progress_callback=_update_progress,
                    )
                    progress_bar.empty()
                    st.rerun()

            st.divider()

            st.subheader("Quick Actions")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("Review Pending Requests"):
                    st.session_state._nav_to = "Pending Requests"
                    st.rerun()

            with col2:
                if st.button("Manage Partners"):
                    st.session_state._nav_to = "Active Partners"
                    st.rerun()

            with col3:
                if st.button("Create & Share Segment"):
                    st.session_state._nav_to = "Create & Share"
                    st.rerun()

    # Tab 2: Pending Requests
    if active_tab == "Pending Requests":
        st.header("Pending Partnership Requests")
        st.markdown("Brands that have been shared a catalog segment but have not yet accepted.")

        if not access_token or not merchant_bm_id:
            st.warning("Please configure credentials in the sidebar first")
        else:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                status_filter = st.selectbox(
                    "Filter by Status",
                    options=["PENDING", "ACCEPTED", "All"],
                )
            with col2:
                if st.button("🔄 Refresh", key="refresh_requests"):
                    invalidate_all_partnerships()
                    progress_bar = st.progress(0, text="Refreshing partnerships…")
                    def _refresh_progress_tab2(done, total):
                        progress_bar.progress(done / total, text=f"Checking segment {done}/{total}…")
                    cached_get_all_segment_partnerships(
                        access_token, merchant_bm_id,
                        force_refresh=True, progress_callback=_refresh_progress_tab2,
                    )
                    progress_bar.empty()
                    st.rerun()

            if not has_cached_partnerships():
                st.info("Partnership data not loaded yet.")
                if st.button("Load Partnership Data", type="primary", key="load_partnerships_tab2"):
                    progress_bar = st.progress(0, text="Loading partnerships across all segments...")
                    def _update_progress(done, total):
                        progress_bar.progress(done / total, text=f"Checking segment {done}/{total}...")
                    cached_get_all_segment_partnerships(
                        access_token, merchant_bm_id,
                        force_refresh=True, progress_callback=_update_progress,
                    )
                    progress_bar.empty()
                    st.rerun()
            else:
                filter_val = None if status_filter == "All" else status_filter
                partnerships, error = get_all_partnerships(
                    access_token, merchant_bm_id, filter_val,
                )

                if error:
                    st.error(f"Failed to load partnerships: {error}")
                elif not partnerships:
                    if status_filter == "PENDING":
                        st.info("No pending requests found. All shared segments have been accepted.")
                    else:
                        st.info("No partnerships found across catalog segments.")
                else:
                    st.markdown(f"**Found {len(partnerships)} partnership(s)**")

                    for i, p in enumerate(partnerships):
                        with st.container():
                            col1, col2, col3 = st.columns([3, 2, 2])

                            with col1:
                                st.markdown(f"**{p.get('business_name', 'Unknown Brand')}**")
                                st.caption(f"Business ID: {p.get('business_id', 'N/A')}")

                            with col2:
                                status = p.get("status", "Unknown")
                                if status == "PENDING":
                                    st.warning(f"⏳ {status}")
                                elif status == "ACCEPTED":
                                    st.success(f"✅ {status}")

                            with col3:
                                st.caption(f"Segment: {p.get('catalog_name', 'N/A')}")
                                tasks = p.get("permitted_tasks", [])
                                if tasks:
                                    st.caption(f"Permissions: {', '.join(tasks)}")

                            st.divider()

    # Tab 3: Active Partners
    if active_tab == "Active Partners":
        st.header("Active Brand Partners")
        st.markdown("Brands that have accepted catalog segment sharing and can run CPAS campaigns.")

        if not access_token or not merchant_bm_id:
            st.warning("Please configure credentials in the sidebar first")
        else:
            col_title, col_refresh = st.columns([4, 1])
            with col_refresh:
                if st.button("🔄 Refresh", key="refresh_partners"):
                    invalidate_all_partnerships()
                    progress_bar = st.progress(0, text="Refreshing partnerships…")
                    def _refresh_progress_tab3(done, total):
                        progress_bar.progress(done / total, text=f"Checking segment {done}/{total}…")
                    cached_get_all_segment_partnerships(
                        access_token, merchant_bm_id,
                        force_refresh=True, progress_callback=_refresh_progress_tab3,
                    )
                    progress_bar.empty()
                    st.rerun()

            if not has_cached_partnerships():
                st.info("Partnership data not loaded yet.")
                if st.button("Load Partnership Data", type="primary", key="load_partnerships_tab3"):
                    progress_bar = st.progress(0, text="Loading partnerships across all segments...")
                    def _update_progress(done, total):
                        progress_bar.progress(done / total, text=f"Checking segment {done}/{total}...")
                    cached_get_all_segment_partnerships(
                        access_token, merchant_bm_id,
                        force_refresh=True, progress_callback=_update_progress,
                    )
                    progress_bar.empty()
                    st.rerun()
            else:
                partners, error = get_active_partners(
                    access_token, merchant_bm_id,
                )

                if error:
                    st.error(f"Failed to load partners: {error}")
                elif not partners:
                    st.info("No active partners found. Share catalog segments with brands to get started.")
                else:
                    # Dedupe by brand and show all their segments
                    brands = {}
                    for p in partners:
                        biz_id = p.get("business_id")
                        if biz_id not in brands:
                            brands[biz_id] = {
                                "business_name": p.get("business_name", "Unknown"),
                                "business_id": biz_id,
                                "segments": [],
                            }
                        brands[biz_id]["segments"].append({
                            "catalog_name": p.get("catalog_name"),
                            "catalog_id": p.get("catalog_id"),
                            "permitted_tasks": p.get("permitted_tasks", []),
                        })

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Unique Brands", len(brands))
                    with col2:
                        st.metric("Total Partnerships", len(partners), help="Brand-segment pairs")

                    search = st.text_input("Search partners", placeholder="Enter brand name...")

                    for biz_id, brand in brands.items():
                        brand_name = brand["business_name"]

                        if search and search.lower() not in brand_name.lower():
                            continue

                        with st.expander(f"🏢 {brand_name} ({len(brand['segments'])} segment(s))"):
                            st.markdown(f"**Business ID:** {biz_id}")

                            seg_data = []
                            for s in brand["segments"]:
                                seg_data.append({
                                    "Segment Name": s["catalog_name"],
                                    "Segment ID": s["catalog_id"],
                                    "Permissions": ", ".join(s["permitted_tasks"]),
                                })

                            seg_df = pd.DataFrame(seg_data)
                            seg_df.index = range(1, len(seg_df) + 1)
                            st.dataframe(seg_df, use_container_width=True)

                    # Export
                    if partners:
                        df_data = []
                        for p in partners:
                            df_data.append({
                                "Brand Name": p.get("business_name", "Unknown"),
                                "Business ID": p.get("business_id", "N/A"),
                                "Segment Name": p.get("catalog_name", "N/A"),
                                "Segment ID": p.get("catalog_id", "N/A"),
                                "Status": p.get("status", "N/A"),
                                "Permissions": ", ".join(p.get("permitted_tasks", [])),
                            })

                        df = pd.DataFrame(df_data)
                        csv_data = df.to_csv(index=False)

                        st.download_button(
                            label="Download Partners CSV",
                            data=csv_data,
                            file_name="active_partners.csv",
                            mime="text/csv",
                        )

    # Tab 4: Catalog Segments
    if active_tab == "Catalog Segments":
        st.header("Catalog Segment Management")

        if not access_token or not merchant_bm_id:
            st.warning("Please configure credentials in the sidebar first")
        else:
            col_title, col_refresh = st.columns([4, 1])
            with col_title:
                st.subheader("Your Catalog Segments")
            with col_refresh:
                if st.button("🔄 Refresh", key="refresh_catalogs"):
                    invalidate_catalog_list()
                    st.rerun()

            with st.spinner("Loading catalog segments..."):
                segments, seg_error = get_catalog_segments(
                    access_token, merchant_bm_id,
                )
                catalogs, cat_error = get_full_catalogs(
                    access_token, merchant_bm_id,
                )

            if seg_error:
                st.error(f"Failed to load catalog segments: {seg_error}")
            elif not segments:
                st.info("No catalog segments found. Segments are subsets of your catalogs created for sharing with brand partners.")
            else:
                # Summary metrics
                total_products = sum(seg.get("product_count", 0) or 0 for seg in segments)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Catalog Segments", len(segments))
                with col2:
                    st.metric("Full Catalogs", len(catalogs) if catalogs else 0)
                with col3:
                    st.metric("Total Products (Segments)", f"{total_products:,}")

                st.divider()

                df_data = []
                for seg in segments:
                    df_data.append({
                        "ID": seg.get("id", "N/A"),
                        "Name": seg.get("name", "Unknown"),
                        "Products": seg.get("product_count", "N/A"),
                        "Vertical": seg.get("vertical", "N/A"),
                    })

                df = pd.DataFrame(df_data)
                df.index = range(1, len(df) + 1)
                st.dataframe(df, use_container_width=True)

            st.divider()

            # Show full catalogs for reference
            if not cat_error and catalogs:
                with st.expander(f"Full Catalogs ({len(catalogs)}) - for reference"):
                    cat_data = []
                    for cat in catalogs:
                        cat_data.append({
                            "ID": cat.get("id", "N/A"),
                            "Name": cat.get("name", "Unknown"),
                            "Products": cat.get("product_count", "N/A"),
                            "Vertical": cat.get("vertical", "N/A"),
                        })
                    cat_df = pd.DataFrame(cat_data)
                    cat_df.index = range(1, len(cat_df) + 1)
                    st.dataframe(cat_df, use_container_width=True)

    # Tab 5: Create & Share
    if active_tab == "Create & Share":
        st.header("Create & Share Segments")

        if not access_token or not merchant_bm_id:
            st.warning("Please configure credentials in the sidebar first")
        else:
            # Show persistent creation result from a previous run
            if "segment_created" in st.session_state:
                result = st.session_state.segment_created
                if result.get("success"):
                    st.success(f"Segment created! ID: **{result['id']}** — Name: {result['name']}")
                else:
                    st.error(f"Segment creation failed: {result['error']}")
                if st.button("Dismiss", key="dismiss_segment_result"):
                    del st.session_state.segment_created
                    st.rerun()
                st.divider()

            # Section A: Create New Segment
            st.subheader("Create New Segment")
            st.markdown("Create a catalog segment by filtering a parent catalog by brand.")

            with st.spinner("Loading catalogs..."):
                catalogs, cat_error = get_full_catalogs(
                    access_token, merchant_bm_id,
                )

            if cat_error:
                st.error(f"Failed to load catalogs: {cat_error}")
            elif not catalogs:
                st.info("No parent catalogs found.")
            else:
                catalog_options = {
                    f"{cat.get('name', 'Unknown')} ({cat.get('product_count', '?')} products)": cat.get("id")
                    for cat in catalogs if cat.get("id")
                }

                selected_catalog_label = st.selectbox(
                    "Select Parent Catalog",
                    options=list(catalog_options.keys()),
                    key="create_segment_catalog",
                )
                selected_catalog_id = catalog_options[selected_catalog_label]

                # Fetch brand values from selected catalog
                with st.spinner("Loading brand values..."):
                    brands, brand_error = get_brand_values(access_token, selected_catalog_id)

                if brand_error:
                    st.error(f"Failed to load brands: {brand_error}")
                elif not brands:
                    st.warning("No brand values found in this catalog's products.")
                else:
                    st.caption(f"{len(brands)} brand(s) available")

                    selected_brands = st.multiselect(
                        "Select Brand(s) to Filter",
                        options=brands,
                        help="Select one or more brands to include in the segment",
                    )

                    # Auto-suggest segment name
                    if selected_brands:
                        suggested_name = ", ".join(selected_brands[:3])
                        if len(selected_brands) > 3:
                            suggested_name += f" +{len(selected_brands) - 3} more"
                        catalog_name = next(
                            (c.get("name", "") for c in catalogs if c.get("id") == selected_catalog_id), ""
                        )
                        default_name = f"{suggested_name} - {catalog_name}"
                    else:
                        default_name = ""

                    segment_name = st.text_input(
                        "Segment Name",
                        value=default_name,
                        help="Name for the new catalog segment",
                    )

                    if st.button("Create Segment", type="primary", disabled=not selected_brands or not segment_name):
                        try:
                            with st.spinner("Creating catalog segment..."):
                                segment_id, err = create_catalog_segment(
                                    access_token, merchant_bm_id, selected_catalog_id, segment_name, selected_brands,
                                )

                            if err:
                                st.error(f"Failed to create segment: {err}")
                                st.session_state.segment_created = {"success": False, "error": err}
                            else:
                                st.success(f"Segment created! ID: **{segment_id}** — Name: {segment_name}")
                                st.info("Click Refresh on the Catalog Segments tab to see it in the list.")
                                st.session_state.segment_created = {
                                    "success": True,
                                    "id": segment_id,
                                    "name": segment_name,
                                }
                                st.session_state.last_created_segment_id = segment_id
                        except Exception as e:
                            st.error(f"Error creating segment: {e}")
                            st.session_state.segment_created = {"success": False, "error": str(e)}

            st.divider()

            # Section B: Share Segment
            st.subheader("Share Segment with Brand")
            st.markdown("Share an existing catalog segment with a brand partner.")

            # Show persistent share result from a previous run
            if "segment_shared" in st.session_state:
                share_result = st.session_state.segment_shared
                if share_result.get("success"):
                    st.success(f"Segment **{share_result['segment_id']}** shared with **{share_result['brand_bm_id']}**")
                else:
                    st.error(f"Failed to share segment: {share_result['error']}")
                col_dismiss, col_nav, _ = st.columns([1, 2, 3])
                with col_dismiss:
                    if st.button("Dismiss", key="dismiss_share_result"):
                        del st.session_state.segment_shared
                        st.rerun()
                with col_nav:
                    if share_result.get("success"):
                        if st.button("View Pending Requests", key="goto_pending"):
                            del st.session_state.segment_shared
                            st.session_state._nav_to = "Pending Requests"
                            st.rerun()
                st.divider()

            with st.spinner("Loading segments..."):
                segments, seg_error = get_catalog_segments(
                    access_token, merchant_bm_id,
                )

            if seg_error:
                st.error(f"Failed to load segments: {seg_error}")
            elif not segments:
                st.info("No catalog segments available to share.")
            else:
                # Inject newly created segment if it's not yet in the cached list
                last_created = st.session_state.get("last_created_segment_id")
                last_created_name = st.session_state.get("segment_created", {}).get("name", "")
                if last_created and not any(s.get("id") == last_created for s in segments):
                    segments.insert(0, {"id": last_created, "name": last_created_name, "product_count": "New"})

                with st.form("share_segment_form"):
                    segment_ids = [seg.get("id") for seg in segments if seg.get("id")]

                    # Pre-select the recently created segment
                    default_idx = 0
                    if last_created and last_created in segment_ids:
                        default_idx = segment_ids.index(last_created)

                    selected_segment = st.selectbox(
                        "Select Segment to Share",
                        options=segment_ids,
                        index=default_idx,
                        format_func=lambda x: next(
                            (seg.get("name", x) for seg in segments if seg.get("id") == x), x
                        ),
                    )

                    brand_bm_id = st.text_input(
                        "Brand Business Manager ID",
                        help="The Business Manager ID of the brand to share with",
                    )

                    st.markdown("**UTM Parameters**")
                    utm_source = st.text_input("UTM Source", placeholder="e.g., facebook")
                    utm_medium = st.text_input("UTM Medium", placeholder="e.g., cpas")
                    utm_campaign = st.text_input("UTM Campaign", placeholder="e.g., nike_summer_2025")

                    share_submit = st.form_submit_button("Share Segment", type="primary")

                    if share_submit:
                        if not brand_bm_id:
                            st.error("Please enter the brand's Business Manager ID")
                        else:
                            # Resolve segment name for cache storage
                            segment_name = next(
                                (seg.get("name", "") for seg in segments if seg.get("id") == selected_segment), ""
                            )
                            with st.spinner("Sharing catalog segment..."):
                                success, err = share_catalog_with_brand(
                                    access_token, selected_segment, brand_bm_id,
                                    catalog_name=segment_name,
                                    utm_source=utm_source,
                                    utm_medium=utm_medium,
                                    utm_campaign=utm_campaign,
                                )

                                if success:
                                    st.session_state.segment_shared = {
                                        "success": True,
                                        "segment_id": selected_segment,
                                        "brand_bm_id": brand_bm_id,
                                    }
                                    st.rerun()
                                else:
                                    st.session_state.segment_shared = {
                                        "success": False,
                                        "error": err,
                                    }
                                    st.rerun()

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "### Quick Help\n\n"
        "**Dashboard:** View partnership stats\n\n"
        "**Pending Requests:** Shared segments awaiting brand acceptance\n\n"
        "**Active Partners:** Brands with accepted partnerships\n\n"
        "**Catalog Segments:** View your segments\n\n"
        "**Create & Share:** Create segments and share with brands\n\n"
        "Use Refresh to fetch latest data from API. "
        "Data is cached locally to minimize API calls."
    )


if __name__ == "__main__":
    main()
