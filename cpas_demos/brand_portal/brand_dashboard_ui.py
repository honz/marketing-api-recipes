"""
Brand CPAS Dashboard (Merchant-Hosted)

A Streamlit-based dashboard for brands to view their CPAS partnership status,
request partnerships, and see shared catalog segments — all hosted by the
merchant alongside their own merchant platform.

Dual-token model:
- Merchant's token (from config.py) is used on startup to display the
  merchant name and check partnership status from the merchant's side.
- Brand's token (entered in the UI sidebar) is used for brand-side API
  calls: validation, viewing shared catalogs, sending collaboration requests.

Data is loaded immediately after brand validation and cached in session state.
All tabs read from cache. Click Refresh to re-fetch from the API.

To run:
$ cd cpas_demos
$ streamlit run brand_portal/brand_dashboard_ui.py --server.port 8502
"""

import sys
from pathlib import Path

# Add this directory first so `import config` finds brand_portal/config.py,
# then parent directory for shared module imports.
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(1, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta

import extra_streamlit_components as stx
import pandas as pd
import streamlit as st

from brand_dashboard_backend import (
    get_merchant_info,
    validate_brand,
    send_collab_request,
    accept_segment_share,
)
from cache import (
    cached_get_shared_catalogs,
    cached_get_pending_shares,
    cached_check_collab_status,
    has_cached_shared_catalogs,
    invalidate_all,
    invalidate_shared_catalogs,
    invalidate_pending_shares,
    invalidate_collab_status,
    optimistic_accept_segment,
)

# Cookie keys for persisting brand credentials in the browser
_COOKIE_KEY_TOKEN = "cpas_brand_token"
_COOKIE_KEY_BM_ID = "cpas_brand_bm_id"
_COOKIE_KEY_NAME = "cpas_brand_name"
_COOKIE_EXPIRY_DAYS = 7

# Import config for merchant credentials
try:
    import config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    config = None


def init_session_state():
    """Initialize session state variables."""
    if "brand_validated" not in st.session_state:
        st.session_state.brand_validated = False
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Partnership Status"


def load_all_data(brand_token, brand_bm_id, merchant_token, merchant_bm_id):
    """
    Load all dashboard data upfront and cache it.
    Called once after validation and on explicit Refresh.
    Shows progress in the main area so the user knows what's happening.
    """
    has_merchant_config = bool(merchant_token and merchant_bm_id)

    with st.spinner("Loading shared catalogs..."):
        cached_get_shared_catalogs(
            brand_token, brand_bm_id,
            merchant_token=merchant_token, merchant_bm_id=merchant_bm_id,
            force_refresh=True,
        )

    if has_merchant_config:
        # Try loading pending shares — if the shared SQLite DB has data,
        # this returns instantly with no progress bar needed.
        with st.spinner("Loading pending shares..."):
            result, _ = cached_get_pending_shares(
                merchant_token, brand_bm_id, merchant_bm_id,
                force_refresh=True,
            )
        # If result is None, the DB had no data and the API scan ran
        # (with no progress callback — acceptable for first-time fallback).
        # On subsequent loads the session-state cache will serve it.

    with st.spinner("Checking collaboration request status..."):
        cached_check_collab_status(
            brand_token, brand_bm_id, merchant_bm_id,
            force_refresh=True,
        )


def main():
    st.set_page_config(
        page_title="Brand CPAS Dashboard",
        page_icon="",
        layout="wide",
    )

    init_session_state()

    # Cookie manager — persists brand credentials in the browser across refreshes
    cookie_manager = stx.CookieManager(key="cpas_cookies")

    # Process deferred cookie writes/deletes from previous render.
    # Cookie set/delete components must render in a cycle that is NOT
    # immediately followed by st.rerun(), so the browser has time to
    # load the component iframe and execute the JS.
    if "_pending_cookies" in st.session_state:
        pending = st.session_state.pop("_pending_cookies")
        expires = datetime.now() + timedelta(days=_COOKIE_EXPIRY_DAYS)
        cookie_manager.set(_COOKIE_KEY_TOKEN, pending["token"], expires_at=expires, key="set_token")
        cookie_manager.set(_COOKIE_KEY_BM_ID, pending["bm_id"], expires_at=expires, key="set_bm")
        cookie_manager.set(_COOKIE_KEY_NAME, pending["name"], expires_at=expires, key="set_name")
    if "_pending_cookie_deletes" in st.session_state:
        for name in st.session_state.pop("_pending_cookie_deletes"):
            try:
                cookie_manager.delete(name, key=f"del_{name}")
            except KeyError:
                pass  # cookie not in local cache yet, but JS will still delete it

    # Load merchant config
    merchant_token = getattr(config, "ACCESS_TOKEN", None) if CONFIG_AVAILABLE else None
    merchant_bm_id = getattr(config, "MERCHANT_BUSINESS_ID", None) if CONFIG_AVAILABLE else None

    # Resolve merchant name on first load
    if "merchant_name" not in st.session_state:
        if merchant_token and merchant_bm_id:
            info, err = get_merchant_info(merchant_token, merchant_bm_id)
            if info and not err:
                st.session_state.merchant_name = info.get("name", merchant_bm_id)
            else:
                st.session_state.merchant_name = None
        else:
            st.session_state.merchant_name = None

    merchant_name = st.session_state.get("merchant_name")

    # Restore brand session from browser cookies (survives page refresh)
    if not st.session_state.brand_validated and not st.session_state.get("_skip_cookie_restore"):
        saved_token = cookie_manager.get(_COOKIE_KEY_TOKEN)
        saved_bm_id = cookie_manager.get(_COOKIE_KEY_BM_ID)
        if saved_token and saved_bm_id:
            st.session_state.brand_validated = True
            st.session_state.brand_token = saved_token
            st.session_state.brand_bm_id = saved_bm_id
            st.session_state.brand_name = cookie_manager.get(_COOKIE_KEY_NAME) or saved_bm_id
            st.rerun()

    # Header
    if merchant_name:
        st.title(f"Brand CPAS Dashboard — powered by {merchant_name}")
    else:
        st.title("Brand CPAS Dashboard")
        if not merchant_token or not merchant_bm_id:
            st.warning(
                "Merchant configuration not found. "
                "The merchant admin needs to set up `brand_portal/config.py` "
                "with their access token and Business Manager ID."
            )

    # -------------------------------------------------------------------------
    # Sidebar: Brand Credentials
    # -------------------------------------------------------------------------
    with st.sidebar:
        st.header("Brand Credentials")

        if st.session_state.brand_validated:
            # Show validated state — credentials stored in session
            brand_name = st.session_state.get("brand_name", "")
            st.success(f"Brand: {brand_name}")
            st.caption(f"BM ID: {st.session_state.brand_bm_id}")

            if st.button("Log Out"):
                st.session_state.brand_validated = False
                st.session_state.pop("brand_token", None)
                st.session_state.pop("brand_bm_id", None)
                st.session_state.pop("brand_name", None)
                st.session_state._skip_cookie_restore = True
                st.session_state._pending_cookie_deletes = [
                    _COOKIE_KEY_TOKEN, _COOKIE_KEY_BM_ID, _COOKIE_KEY_NAME,
                ]
                invalidate_all()
                st.rerun()
        else:
            brand_token_input = st.text_input(
                "Access Token",
                type="password",
                help="Your brand's Facebook/Meta access token with business_management permission",
            )

            brand_bm_id_input = st.text_input(
                "Brand Business Manager ID",
                help="Your brand's Business Manager ID",
            )

            if st.button("Validate", type="primary"):
                if not brand_token_input or not brand_bm_id_input:
                    st.error("Please enter both your access token and Business Manager ID")
                else:
                    with st.spinner("Validating..."):
                        result, error = validate_brand(brand_token_input, brand_bm_id_input)
                        if error:
                            st.error(f"Validation failed: {error}")
                        else:
                            st.session_state.brand_validated = True
                            st.session_state.brand_token = brand_token_input
                            st.session_state.brand_bm_id = brand_bm_id_input
                            st.session_state.brand_name = result["brand_info"].get("name", brand_bm_id_input)
                            st.session_state._pending_cookies = {
                                "token": brand_token_input,
                                "bm_id": brand_bm_id_input,
                                "name": st.session_state.brand_name,
                            }
                            invalidate_all()
                            st.rerun()

        st.markdown("---")
        st.markdown(
            "### Quick Help\n\n"
            "**Partnership Status:** View your partnership with this merchant\n\n"
            "**Request Partnership:** Send a collaboration request\n\n"
            "**Shared Catalogs:** Browse catalog segments shared with you\n\n"
            "Data is cached locally. Click **Refresh** to fetch latest from API."
        )

    # -------------------------------------------------------------------------
    # Gate: require brand validation
    # -------------------------------------------------------------------------
    if not st.session_state.brand_validated:
        st.info("Enter your brand credentials in the sidebar and click **Validate** to get started.")
        st.stop()

    # Read credentials from session state (persists across reruns)
    brand_token = st.session_state.get("brand_token")
    brand_bm_id = st.session_state.get("brand_bm_id")

    if not brand_token or not brand_bm_id:
        st.warning("Brand credentials not found. Please re-enter in the sidebar.")
        st.session_state.brand_validated = False
        st.stop()

    brand_name = st.session_state.get("brand_name", brand_bm_id)
    merchant_display = merchant_name or "the merchant"
    has_merchant_config = bool(merchant_token and merchant_bm_id)

    # -------------------------------------------------------------------------
    # Auto-load data on first visit after validation
    # -------------------------------------------------------------------------
    if not has_cached_shared_catalogs():
        st.subheader("Loading dashboard data...")
        load_all_data(brand_token, brand_bm_id, merchant_token, merchant_bm_id)
        st.rerun()

    # -------------------------------------------------------------------------
    # Tab navigation
    # -------------------------------------------------------------------------
    if "_nav_to" in st.session_state:
        st.session_state.active_tab = st.session_state._nav_to
        del st.session_state._nav_to

    TAB_OPTIONS = ["Partnership Status", "Request Partnership", "Shared Catalogs"]
    active_tab = st.radio(
        "Navigation",
        options=TAB_OPTIONS,
        key="active_tab",
        horizontal=True,
        label_visibility="collapsed",
    )

    # =====================================================================
    # Tab 1: Partnership Status
    # =====================================================================
    if active_tab == "Partnership Status":
        st.header("Partnership Status")

        col_desc, col_refresh = st.columns([4, 1])
        with col_desc:
            st.markdown(f"Your brand's relationship with **{merchant_display}**.")
        with col_refresh:
            if st.button("Refresh", key="refresh_status"):
                invalidate_all()
                st.rerun()

        # Read from cache (no API calls)
        shared_catalogs, shared_err = cached_get_shared_catalogs(
            brand_token, brand_bm_id,
            merchant_token=merchant_token, merchant_bm_id=merchant_bm_id,
        )

        pending_shares = None
        pending_err = None
        if has_merchant_config:
            pending_shares, pending_err = cached_get_pending_shares(
                merchant_token, brand_bm_id, merchant_bm_id,
            )

        has_accepted = shared_catalogs and len(shared_catalogs) > 0
        # Filter to only PENDING segments from the scan
        pending_only = [
            s for s in (pending_shares or []) if s.get("status") == "PENDING"
        ]
        has_pending = len(pending_only) > 0

        if has_accepted or has_pending:
            # --- Accepted catalogs ---
            if has_accepted:
                st.subheader("Active Segments")
                st.caption("Segments you can use for CPAS campaigns:")

                table_data = []
                for cat in shared_catalogs:
                    table_data.append({
                        "Name": cat.get("name", "Unknown"),
                        "Segment ID": cat.get("id", "N/A"),
                        "Products": cat.get("product_count", "N/A"),
                        "Status": "Active",
                    })

                df = pd.DataFrame(table_data)
                df.index = range(1, len(df) + 1)
                st.dataframe(df, use_container_width=True)

            # --- Pending shares with Accept buttons ---
            if has_pending:
                st.subheader("Pending Segments")
                st.caption(
                    "The merchant has shared these segments with you. "
                    "Click Accept to activate them for CPAS campaigns."
                )

                for seg in pending_only:
                    seg_id = seg.get("segment_id", "")
                    seg_name = seg.get("segment_name", "Unknown")
                    product_count = seg.get("product_count", 0)

                    col_name, col_products, col_btn = st.columns([3, 1, 1])
                    with col_name:
                        st.markdown(f"**{seg_name}**")
                        st.caption(f"ID: {seg_id}")
                    with col_products:
                        st.metric("Products", product_count)
                    with col_btn:
                        if st.button("Accept", key=f"accept_{seg_id}"):
                            with st.spinner(f"Accepting {seg_name}..."):
                                success, err = accept_segment_share(
                                    merchant_token, seg_id, brand_bm_id,
                                )
                            if success:
                                st.success(f"Accepted **{seg_name}**!")
                                optimistic_accept_segment(seg_id, seg_name, product_count)
                                st.rerun()
                            else:
                                st.error(f"Failed to accept: {err}")
        else:
            # No segments found — check collab request status (cached)
            st.info("No shared catalog segments found.")

            if has_merchant_config:
                collab_status = cached_check_collab_status(
                    brand_token, brand_bm_id, merchant_bm_id,
                )

                request_status = collab_status.get("status")

                if request_status == "PENDING":
                    st.warning(
                        f"Your partnership request is being reviewed by **{merchant_display}**. "
                        "Check back later for updates."
                    )
                elif request_status == "APPROVED":
                    st.success(
                        f"Partnership approved! **{merchant_display}** will share a catalog "
                        "segment with you shortly."
                    )
                elif request_status == "REJECTED":
                    st.error(
                        f"Your partnership request was rejected by **{merchant_display}**."
                    )
                elif request_status == "not_found":
                    st.markdown(
                        "No existing partnership or request found. "
                        "Go to the **Request Partnership** tab to send a collaboration request."
                    )
                    if st.button("Go to Request Partnership"):
                        st.session_state._nav_to = "Request Partnership"
                        st.rerun()
                elif request_status == "error":
                    st.error(f"Error checking request status: {collab_status.get('message', 'Unknown error')}")
            else:
                st.markdown(
                    "No catalog segments have been shared with your brand yet. "
                    "Go to the **Request Partnership** tab to send a collaboration request."
                )
                if st.button("Go to Request Partnership"):
                    st.session_state._nav_to = "Request Partnership"
                    st.rerun()

        if shared_err:
            st.error(f"Error loading shared catalogs: {shared_err}")
        if pending_err:
            st.error(f"Error scanning pending shares: {pending_err}")

    # =====================================================================
    # Tab 2: Request Partnership
    # =====================================================================
    if active_tab == "Request Partnership":
        st.header("Request Partnership")

        if not merchant_bm_id:
            st.error(
                "Merchant Business Manager ID is not configured. "
                "The merchant admin needs to set up `brand_portal/config.py`."
            )
        else:
            show_form = True

            # Use cached data to check existing status (no API calls)
            if has_merchant_config:
                shared_catalogs, _ = cached_get_shared_catalogs(
                    brand_token, brand_bm_id,
                    merchant_token=merchant_token, merchant_bm_id=merchant_bm_id,
                )

                pending_shares, _ = cached_get_pending_shares(
                    merchant_token, brand_bm_id, merchant_bm_id,
                )
                has_any_shares = (
                    (shared_catalogs and len(shared_catalogs) > 0)
                    or (pending_shares and len(pending_shares) > 0)
                )

                if has_any_shares:
                    total_active = len(shared_catalogs) if shared_catalogs else 0
                    total_pending = len([
                        s for s in (pending_shares or [])
                        if s.get("status") == "PENDING"
                    ])
                    parts = []
                    if total_active:
                        parts.append(f"{total_active} active segment(s)")
                    if total_pending:
                        parts.append(f"{total_pending} pending segment(s)")
                    st.success(
                        f"You already have a partnership with **{merchant_display}** "
                        f"with {' and '.join(parts)}."
                    )
                    if st.button("View Partnership Status"):
                        st.session_state._nav_to = "Partnership Status"
                        st.rerun()
                    show_form = False
                else:
                    collab_status = cached_check_collab_status(
                        brand_token, brand_bm_id, merchant_bm_id,
                    )
                    request_status = collab_status.get("status")

                    if request_status == "PENDING":
                        st.warning(
                            f"You already have a pending request with **{merchant_display}**. "
                            "It is being reviewed."
                        )
                        show_form = False
                    elif request_status == "APPROVED":
                        st.success(
                            f"Your request has been approved by **{merchant_display}**! "
                            "A catalog segment will be shared with you shortly."
                        )
                        show_form = False

            if show_form:
                st.markdown(
                    f"Submit a collaboration request to **{merchant_display}** to start "
                    "a CPAS partnership."
                )

                with st.form("collab_request_form"):
                    contact_email = st.text_input(
                        "Contact Email",
                        help="Email address for the merchant to reach you",
                    )
                    contact_name = st.text_input(
                        "Contact Name",
                        help="Your name or your team's contact name",
                    )

                    submit = st.form_submit_button("Submit Request", type="primary")

                    if submit:
                        if not contact_email or not contact_name:
                            st.error("Please fill in both email and name")
                        else:
                            with st.spinner("Submitting collaboration request..."):
                                request_id, err = send_collab_request(
                                    brand_token,
                                    brand_bm_id,
                                    merchant_bm_id,
                                    contact_email,
                                    contact_name,
                                )

                                if err:
                                    st.error(f"Failed to submit request: {err}")
                                else:
                                    st.success(
                                        f"Request sent to **{merchant_display}**! "
                                        "They'll share a catalog segment once approved."
                                    )
                                    st.caption(f"Request ID: {request_id}")
                                    # Invalidate so next check picks up the new request
                                    invalidate_collab_status()

    # =====================================================================
    # Tab 3: Shared Catalogs
    # =====================================================================
    if active_tab == "Shared Catalogs":
        st.header("Shared Catalogs")

        col_desc, col_refresh = st.columns([4, 1])
        with col_desc:
            st.markdown("Catalog segments shared with your brand for CPAS campaigns.")
        with col_refresh:
            if st.button("Refresh", key="refresh_catalogs"):
                invalidate_all()
                st.rerun()

        # Read from cache (no API calls)
        # Accepted segments from brand's client_product_catalogs
        catalogs, cat_error = cached_get_shared_catalogs(
            brand_token, brand_bm_id,
            merchant_token=merchant_token, merchant_bm_id=merchant_bm_id,
        )

        # Pending segments from merchant-side batch scan
        pending_shares = None
        if has_merchant_config:
            pending_shares, _ = cached_get_pending_shares(
                merchant_token, brand_bm_id, merchant_bm_id,
            )

        # Build unified table from both sources
        table_data = []
        accepted_ids = set()

        # Add accepted catalogs
        for cat in (catalogs or []):
            cat_id = cat.get("id", "N/A")
            accepted_ids.add(cat_id)
            table_data.append({
                "Name": cat.get("name", "Unknown"),
                "Segment ID": cat_id,
                "Products": cat.get("product_count", "N/A"),
                "Status": "Active",
            })

        # Add pending segments (avoid duplicates with accepted)
        for seg in (pending_shares or []):
            seg_id = seg.get("segment_id", "")
            if seg_id in accepted_ids:
                continue
            status = seg.get("status", "PENDING")
            table_data.append({
                "Name": seg.get("segment_name", "Unknown"),
                "Segment ID": seg_id,
                "Products": seg.get("product_count", "N/A"),
                "Status": "Active" if status == "ACCEPTED" else "Pending",
            })

        if table_data:
            # Metrics
            total_products = sum(
                (row["Products"] if isinstance(row["Products"], int) else 0)
                for row in table_data
            )
            active_count = sum(1 for r in table_data if r["Status"] == "Active")
            pending_count = sum(1 for r in table_data if r["Status"] == "Pending")

            cols = st.columns(3)
            with cols[0]:
                st.metric("Total Segments", len(table_data))
            with cols[1]:
                st.metric("Active", active_count)
            with cols[2]:
                st.metric("Pending", pending_count)

            st.divider()

            df = pd.DataFrame(table_data)
            df.index = range(1, len(df) + 1)
            st.dataframe(df, use_container_width=True)

            st.caption("Use the Segment ID when setting up CPAS campaigns in Ads Manager.")

            csv_data = df.to_csv(index=False)
            st.download_button(
                label="Export to CSV",
                data=csv_data,
                file_name="shared_catalogs.csv",
                mime="text/csv",
            )
        else:
            if cat_error:
                st.error(f"Failed to load catalogs: {cat_error}")
            else:
                st.info(
                    "No catalog segments have been shared with your brand yet. "
                    "Once the merchant shares a segment, it will appear here."
                )


if __name__ == "__main__":
    main()
