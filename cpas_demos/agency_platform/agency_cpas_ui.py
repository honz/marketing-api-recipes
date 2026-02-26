"""
Agency Platform UI — Multi-Brand Dashboard

A Streamlit-based dashboard for agencies to manage multiple brand partners,
discover brands via the API, handle inbound + outbound collaboration requests,
and create ad accounts and campaigns scoped to each brand.

To run:
$ cd cpas_demos
$ streamlit run agency_platform/agency_cpas_ui.py
"""

import sys
from pathlib import Path

# Add this directory first so `import config` finds agency_platform/config.py,
# then parent directory for shared module imports.
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(1, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st

from agency_cpas_backend import (
    validate_agency_setup,
    discover_brands,
    get_brand_onboarding_summary,
    get_available_merchants,
    initiate_partnership,
    get_outbound_requests,
    get_inbound_requests,
    accept_inbound_request,
    reject_inbound_request,
    get_available_catalog_segments,
    setup_collab_ad_account,
    get_brand_ad_accounts,
    create_cpas_campaign,
)
from shared.constants import (
    DEFAULT_TIMEZONE_ID,
    DEFAULT_CURRENCY,
    DEFAULT_DAILY_BUDGET,
    CollabRequestStatus,
)

# Import config for default values
try:
    import config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    config = None


def init_session_state():
    """Initialize session state variables."""
    defaults = {
        "setup_validated": False,
        "brands": [],
        "brand_summaries": {},
        "selected_brand_id": None,
        "selected_brand_name": None,
        "created_ad_account_id": None,
        "selected_catalog_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_selected_brand():
    """Get the currently selected brand dict from session state."""
    brand_id = st.session_state.selected_brand_id
    if not brand_id:
        return None
    for brand in st.session_state.brands:
        if brand.get("id") == brand_id:
            return brand
    return None


def main():
    st.set_page_config(
        page_title="Agency CPAS Dashboard",
        page_icon="🤝",
        layout="wide",
    )

    init_session_state()

    st.title("🤝 Agency CPAS Dashboard")
    st.markdown("Multi-brand collaborative ads management platform")

    # =========================================================================
    # Sidebar — Agency configuration only
    # =========================================================================
    with st.sidebar:
        st.header("Agency Configuration")

        default_token = getattr(config, "ACCESS_TOKEN", None) if CONFIG_AVAILABLE else None
        default_agency_bm = getattr(config, "AGENCY_BUSINESS_ID", None) if CONFIG_AVAILABLE else None

        if CONFIG_AVAILABLE and default_token:
            st.success("Config loaded")
        else:
            st.info("Enter credentials below or update config.py")

        # Access token
        if default_token:
            access_token = default_token
            st.text("Access Token: [Loaded from config]")
        else:
            access_token = st.text_input(
                "Access Token",
                type="password",
                help="System User token with business_management, ads_management, catalog_management",
            )

        # Agency BM ID
        if default_agency_bm:
            agency_bm_id = default_agency_bm
            st.text(f"Agency BM ID: {agency_bm_id}")
        else:
            agency_bm_id = st.text_input(
                "Agency Business Manager ID",
                help="Your agency's Business Manager ID",
            )

        # Validate & discover
        if st.button("Validate Setup", type="primary"):
            if not all([access_token, agency_bm_id]):
                st.error("Please provide access token and agency BM ID")
            else:
                with st.spinner("Validating..."):
                    result, error = validate_agency_setup(access_token, agency_bm_id)
                    if error:
                        st.error(f"Validation failed: {error}")
                        st.session_state.setup_validated = False
                    else:
                        st.success("Agency validated!")
                        st.session_state.setup_validated = True

                        # Discover brands
                        brands, brand_error = discover_brands(access_token, agency_bm_id)
                        if brand_error:
                            st.warning(f"Could not discover brands: {brand_error}")
                            st.session_state.brands = []
                        else:
                            st.session_state.brands = brands or []
                            st.success(f"Found {len(st.session_state.brands)} brand(s)")

                        # Reset summaries on re-validate
                        st.session_state.brand_summaries = {}

        # Show brand count
        if st.session_state.brands:
            st.divider()
            st.metric("Brands Discovered", len(st.session_state.brands))

        # Quick help
        st.sidebar.markdown("---")
        st.sidebar.markdown("""
        ### Permissions Needed

        **On the Agency System User token:**
        - `business_management`
        - `ads_management`
        - `catalog_management`

        **Brands must (one-time):**
        - Add agency BM as Partner
        - Grant: manage ad accounts, manage campaigns, advertise on catalogs
        """)

    # =========================================================================
    # Main content — 5 tabs
    # =========================================================================
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard",
        "🏢 Brand Details",
        "🤝 Partnerships",
        "💼 Ad Accounts",
        "🚀 Campaigns",
    ])

    # =====================================================================
    # Tab 1: Dashboard — multi-brand overview
    # =====================================================================
    with tab1:
        st.header("Brand Overview")

        if not access_token or not agency_bm_id:
            st.info("Configure your agency credentials in the sidebar to get started.")
        elif not st.session_state.brands:
            if st.session_state.setup_validated:
                st.warning(
                    "No brands discovered. Brands must add your agency BM as a Partner "
                    "in their Business Settings before they appear here."
                )
            else:
                st.info("Click 'Validate Setup' in the sidebar to discover brands.")
        else:
            brands = st.session_state.brands

            # Load summaries progressively
            col_refresh, _ = st.columns([1, 5])
            with col_refresh:
                refresh = st.button("Refresh Summaries")

            if refresh or not st.session_state.brand_summaries:
                progress = st.progress(0, text="Loading brand summaries...")
                for i, brand in enumerate(brands):
                    bid = brand["id"]
                    st.session_state.brand_summaries[bid] = get_brand_onboarding_summary(
                        access_token, bid
                    )
                    progress.progress(
                        (i + 1) / len(brands),
                        text=f"Loading {brand.get('name', bid)}...",
                    )
                progress.empty()

            summaries = st.session_state.brand_summaries

            # Metrics row
            total = len(brands)
            with_partnerships = sum(
                1 for b in brands
                if summaries.get(b["id"], {}).get("outbound_requests", 0) > 0
                or summaries.get(b["id"], {}).get("inbound_requests", 0) > 0
            )
            with_catalogs = sum(
                1 for b in brands
                if summaries.get(b["id"], {}).get("catalog_segments", 0) > 0
            )
            with_accounts = sum(
                1 for b in brands
                if summaries.get(b["id"], {}).get("ad_accounts", 0) > 0
            )

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Brands", total)
            m2.metric("With Partnerships", with_partnerships)
            m3.metric("With Catalogs", with_catalogs)
            m4.metric("With Ad Accounts", with_accounts)

            st.divider()

            # Brand overview table
            table_data = []
            for brand in brands:
                bid = brand["id"]
                s = summaries.get(bid, {})
                table_data.append({
                    "Brand Name": brand.get("name", "Unknown"),
                    "BM ID": bid,
                    "Verification": brand.get("verification_status", "N/A"),
                    "Outbound Reqs": s.get("outbound_requests", 0),
                    "Inbound Reqs": s.get("inbound_requests", 0),
                    "Catalogs": s.get("catalog_segments", 0),
                    "Ad Accounts": s.get("ad_accounts", 0),
                })

            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.divider()

            # Brand selector
            brand_options = {
                f"{b.get('name', 'Unknown')} ({b['id']})": b["id"]
                for b in brands
            }
            selected_label = st.selectbox(
                "Select a brand to manage",
                options=list(brand_options.keys()),
            )

            if st.button("View Details", type="primary"):
                selected_id = brand_options[selected_label]
                st.session_state.selected_brand_id = selected_id
                selected_brand = next(
                    (b for b in brands if b["id"] == selected_id), None
                )
                if selected_brand:
                    st.session_state.selected_brand_name = selected_brand.get("name", selected_id)
                st.rerun()

    # =====================================================================
    # Tab 2: Brand Details — drill-down
    # =====================================================================
    with tab2:
        st.header("Brand Details")

        brand = get_selected_brand()
        if not brand:
            st.info("Select a brand from the Dashboard tab to view details.")
        else:
            bid = brand["id"]
            st.subheader(brand.get("name", "Unknown"))

            col1, col2, col3 = st.columns(3)
            col1.metric("BM ID", bid)
            col2.metric("Verification", brand.get("verification_status", "N/A"))

            summary = st.session_state.brand_summaries.get(bid, {})
            col3.metric("Errors", len(summary.get("errors", [])))

            st.divider()

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Outbound Requests", summary.get("outbound_requests", 0))
            c2.metric("Inbound Requests", summary.get("inbound_requests", 0))
            c3.metric("Catalog Segments", summary.get("catalog_segments", 0))
            c4.metric("Ad Accounts", summary.get("ad_accounts", 0))

            if summary.get("errors"):
                st.divider()
                st.warning("Some API calls encountered errors:")
                for err in summary["errors"]:
                    st.text(f"  - {err}")

            st.divider()
            st.markdown("Use the **Partnerships**, **Ad Accounts**, and **Campaigns** tabs to manage this brand.")

    # =====================================================================
    # Tab 3: Partnerships — inbound + outbound
    # =====================================================================
    with tab3:
        st.header("Partnerships")

        brand = get_selected_brand()
        if not brand:
            st.info("Select a brand from the Dashboard tab first.")
        elif not access_token:
            st.warning("Please configure credentials in the sidebar.")
        else:
            bid = brand["id"]
            brand_name = brand.get("name", bid)

            st.subheader(f"Managing partnerships for: {brand_name}")

            # Section A: Send Outbound Request
            st.markdown("### Send Outbound Request")
            merchants = get_available_merchants()

            with st.form("send_request_form"):
                merchant_options = {
                    f"{m.get('logo_emoji', '')} {m.get('name', 'Unknown')}": m.get("key")
                    for m in merchants
                }
                selected_merchant_label = st.selectbox(
                    "Merchant",
                    options=list(merchant_options.keys()),
                )
                req_email = st.text_input("Contact Email")
                req_name = st.text_input("Contact Name")

                submit = st.form_submit_button("Send Collaboration Request", type="primary")

                if submit:
                    if not req_email or not req_name:
                        st.error("Please provide contact email and name.")
                    else:
                        merchant_key = merchant_options[selected_merchant_label]
                        with st.spinner("Sending request..."):
                            request_id, error = initiate_partnership(
                                access_token, bid, merchant_key, req_email, req_name
                            )
                            if error:
                                st.error(f"Failed: {error}")
                            else:
                                st.success(f"Request sent! ID: {request_id}")

            st.divider()

            # Section B: Outbound Requests Table
            st.markdown("### Outbound Requests")
            if st.button("Refresh Outbound", key="refresh_outbound"):
                st.rerun()

            with st.spinner("Loading outbound requests..."):
                outbound, error = get_outbound_requests(access_token, bid)
                if error:
                    st.error(f"Failed to load: {error}")
                elif not outbound:
                    st.info("No outbound collaboration requests found.")
                else:
                    df_data = []
                    for req in outbound:
                        df_data.append({
                            "Request ID": req.get("id", "N/A"),
                            "Merchant": req.get("receiver_business", {}).get("name", "Unknown"),
                            "Status": req.get("request_status", "Unknown"),
                            "Created": req.get("created_time", "N/A"),
                        })
                    st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)

            st.divider()

            # Section C: Inbound Requests
            st.markdown("### Inbound Requests")
            if st.button("Refresh Inbound", key="refresh_inbound"):
                st.rerun()

            with st.spinner("Loading inbound requests..."):
                inbound, error = get_inbound_requests(access_token, bid)
                if error:
                    st.error(f"Failed to load: {error}")
                elif not inbound:
                    st.info("No inbound collaboration requests found.")
                else:
                    for req in inbound:
                        req_id = req.get("id", "N/A")
                        sender = req.get("sender_business", {}).get("name", "Unknown")
                        status = req.get("request_status", "Unknown")
                        created = req.get("created_time", "N/A")

                        cols = st.columns([2, 2, 1, 2, 1, 1])
                        cols[0].text(f"ID: {req_id}")
                        cols[1].text(f"From: {sender}")
                        cols[2].text(status)
                        cols[3].text(created)

                        if status == CollabRequestStatus.PENDING:
                            if cols[4].button("Accept", key=f"accept_{req_id}"):
                                success, err = accept_inbound_request(access_token, req_id)
                                if err:
                                    st.error(f"Accept failed: {err}")
                                else:
                                    st.success(f"Accepted {req_id}")
                                    st.rerun()

                            if cols[5].button("Reject", key=f"reject_{req_id}"):
                                success, err = reject_inbound_request(access_token, req_id)
                                if err:
                                    st.error(f"Reject failed: {err}")
                                else:
                                    st.success(f"Rejected {req_id}")
                                    st.rerun()

            st.divider()

            # Section D: Inbound Catalog Shares
            st.markdown("### Inbound Catalog Shares")

            with st.spinner("Loading catalog segments..."):
                catalogs, error = get_available_catalog_segments(access_token, bid)
                if error:
                    st.error(f"Failed to load: {error}")
                elif not catalogs:
                    st.info("No catalog segments shared with this brand yet.")
                else:
                    df_data = []
                    for cat in catalogs:
                        df_data.append({
                            "Catalog ID": cat.get("id", "N/A"),
                            "Name": cat.get("name", "Unknown"),
                            "Products": cat.get("product_count", "N/A"),
                            "Vertical": cat.get("vertical", "N/A"),
                        })
                    st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)

    # =====================================================================
    # Tab 4: Ad Accounts — create/view scoped to selected brand
    # =====================================================================
    with tab4:
        st.header("Ad Accounts")

        brand = get_selected_brand()
        if not brand:
            st.info("Select a brand from the Dashboard tab first.")
        elif not access_token:
            st.warning("Please configure credentials in the sidebar.")
        else:
            bid = brand["id"]
            brand_name = brand.get("name", bid)

            st.subheader(f"Ad accounts for: {brand_name}")

            # Create ad account
            st.markdown("### Create Collaborative Ad Account")

            with st.form("create_account_form"):
                account_name = st.text_input(
                    "Account Name Suffix",
                    help="The ad account will be named 'CPAS - [suffix]'",
                )

                timezone_options = {
                    "Asia/Kolkata (India)": 50,
                    "America/Los_Angeles (Pacific)": 1,
                    "America/New_York (Eastern)": 26,
                    "Europe/London (UK)": 58,
                }
                timezone = st.selectbox("Timezone", options=list(timezone_options.keys()))
                currency = st.selectbox("Currency", options=["INR", "USD", "EUR", "GBP"])

                create_submit = st.form_submit_button("Create Ad Account", type="primary")

                if create_submit:
                    if not account_name:
                        st.error("Please provide an account name suffix.")
                    else:
                        with st.spinner("Creating ad account..."):
                            ad_account_id, error = setup_collab_ad_account(
                                access_token, bid, account_name,
                                timezone_options[timezone], currency,
                            )
                            if error:
                                st.error(f"Failed: {error}")
                            else:
                                st.success(f"Ad account created! ID: {ad_account_id}")
                                st.session_state.created_ad_account_id = ad_account_id

            st.divider()

            # Existing ad accounts
            st.markdown("### Existing Ad Accounts")

            with st.spinner("Loading ad accounts..."):
                accounts, error = get_brand_ad_accounts(access_token, bid)
                if error:
                    st.error(f"Failed to load: {error}")
                elif not accounts:
                    st.info("No ad accounts found for this brand.")
                else:
                    df_data = []
                    for acc in accounts:
                        df_data.append({
                            "Account ID": acc.get("id", "N/A"),
                            "Name": acc.get("name", "Unknown"),
                            "Currency": acc.get("currency", "N/A"),
                            "Timezone": acc.get("timezone_name", "N/A"),
                            "Status": acc.get("account_status", "N/A"),
                        })
                    st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)

            st.divider()

            # Available catalog segments
            st.markdown("### Available Catalog Segments")

            with st.spinner("Loading catalog segments..."):
                catalogs, error = get_available_catalog_segments(access_token, bid)
                if error:
                    st.error(f"Failed to load: {error}")
                elif not catalogs:
                    st.info("No catalog segments available. The merchant needs to share a catalog segment with the brand.")
                else:
                    df_data = []
                    for cat in catalogs:
                        df_data.append({
                            "Catalog ID": cat.get("id", "N/A"),
                            "Name": cat.get("name", "Unknown"),
                            "Products": cat.get("product_count", "N/A"),
                            "Vertical": cat.get("vertical", "N/A"),
                        })
                    st.dataframe(pd.DataFrame(df_data), use_container_width=True, hide_index=True)

                    catalog_ids = [cat.get("id") for cat in catalogs if cat.get("id")]
                    if catalog_ids:
                        selected_catalog = st.selectbox(
                            "Select Catalog for Campaign",
                            options=catalog_ids,
                            format_func=lambda x: next(
                                (cat.get("name", x) for cat in catalogs if cat.get("id") == x), x
                            ),
                        )
                        st.session_state.selected_catalog_id = selected_catalog

    # =====================================================================
    # Tab 5: Campaigns — create/view scoped to selected brand
    # =====================================================================
    with tab5:
        st.header("Launch CPAS Campaign")

        brand = get_selected_brand()
        if not brand:
            st.info("Select a brand from the Dashboard tab first.")
        elif not access_token:
            st.warning("Please configure credentials in the sidebar.")
        else:
            bid = brand["id"]
            brand_name = brand.get("name", bid)

            st.subheader(f"Campaigns for: {brand_name}")

            accounts, _ = get_brand_ad_accounts(access_token, bid)
            catalogs, _ = get_available_catalog_segments(access_token, bid)

            if not accounts:
                st.warning("No ad accounts available. Create one in the 'Ad Accounts' tab.")
            elif not catalogs:
                st.warning("No catalog segments available. The merchant needs to share a catalog segment.")
            else:
                with st.form("create_campaign_form"):
                    campaign_name = st.text_input(
                        "Campaign Name",
                        value=f"{brand_name} - CPAS",
                    )

                    account_options = {
                        acc.get("name", acc.get("id")): acc.get("id") for acc in accounts
                    }
                    selected_account_name = st.selectbox("Ad Account", options=list(account_options.keys()))
                    selected_account_id = account_options[selected_account_name]

                    catalog_options = {
                        cat.get("name", cat.get("id")): cat.get("id") for cat in catalogs
                    }
                    selected_catalog_name = st.selectbox("Catalog Segment", options=list(catalog_options.keys()))
                    selected_catalog_id = catalog_options[selected_catalog_name]

                    daily_budget_inr = st.number_input(
                        "Daily Budget (INR)",
                        min_value=100,
                        max_value=1000000,
                        value=1000,
                        step=100,
                    )
                    daily_budget_paisa = daily_budget_inr * 100

                    st.markdown("**Targeting**")
                    target_countries = st.multiselect(
                        "Countries",
                        options=["IN", "US", "GB", "AE", "SG"],
                        default=["IN"],
                    )

                    create_campaign_submit = st.form_submit_button(
                        "Create Campaign (PAUSED)", type="primary"
                    )

                    if create_campaign_submit:
                        with st.spinner("Creating campaign..."):
                            result, error = create_cpas_campaign(
                                access_token, selected_account_id,
                                selected_catalog_id, campaign_name,
                                daily_budget_paisa, target_countries,
                            )
                            if error:
                                st.error(f"Failed: {error}")
                            else:
                                st.success("Campaign created successfully!")
                                st.json(result)

                                summary_data = {
                                    "campaign_id": [result.get("campaign_id")],
                                    "ad_set_id": [result.get("ad_set_id")],
                                    "ad_account_id": [selected_account_id],
                                    "catalog_segment_id": [selected_catalog_id],
                                    "campaign_name": [campaign_name],
                                    "daily_budget_inr": [daily_budget_inr],
                                    "brand_bm_id": [bid],
                                    "status": ["PAUSED"],
                                }
                                summary_df = pd.DataFrame(summary_data)

                                csv_data = summary_df.to_csv(index=False)
                                st.download_button(
                                    label="Download Campaign Summary CSV",
                                    data=csv_data,
                                    file_name="cpas_campaign_summary.csv",
                                    mime="text/csv",
                                )


if __name__ == "__main__":
    main()
