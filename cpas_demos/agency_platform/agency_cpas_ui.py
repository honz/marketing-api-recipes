"""
Agency Platform UI

A Streamlit-based web interface for agencies to onboard brand partners with CPAS merchants.

To run:
$ cd cpas_demos
$ streamlit run agency_platform/agency_cpas_ui.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st

from agency_cpas_backend import (
    validate_setup,
    get_available_merchants,
    initiate_partnership,
    get_sent_requests,
    get_partnership_status,
    get_available_catalog_segments,
    setup_collab_ad_account,
    get_brand_ad_accounts,
    create_cpas_campaign,
    get_full_onboarding_status,
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
    if "selected_merchant" not in st.session_state:
        st.session_state.selected_merchant = None
    if "setup_validated" not in st.session_state:
        st.session_state.setup_validated = False
    if "created_ad_account_id" not in st.session_state:
        st.session_state.created_ad_account_id = None
    if "selected_catalog_id" not in st.session_state:
        st.session_state.selected_catalog_id = None


def main():
    st.set_page_config(
        page_title="Agency CPAS Platform",
        page_icon="🤝",
        layout="wide",
    )

    init_session_state()

    st.title("🤝 Agency CPAS Onboarding Platform")
    st.markdown("Help your brand partners launch Collaborative Ads with top merchants")

    # Sidebar for authentication and setup
    with st.sidebar:
        st.header("Configuration")

        # Get defaults from config if available
        default_token = getattr(config, 'ACCESS_TOKEN', None) if CONFIG_AVAILABLE else None
        default_agency_bm = getattr(config, 'AGENCY_BUSINESS_ID', None) if CONFIG_AVAILABLE else None
        default_brand_bm = getattr(config, 'DEFAULT_BRAND_BUSINESS_ID', None) if CONFIG_AVAILABLE else None
        default_brand_name = getattr(config, 'DEFAULT_BRAND_NAME', None) if CONFIG_AVAILABLE else None
        default_email = getattr(config, 'DEFAULT_CONTACT_EMAIL', None) if CONFIG_AVAILABLE else None
        default_contact = getattr(config, 'DEFAULT_CONTACT_NAME', None) if CONFIG_AVAILABLE else None

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

        st.subheader("Agency Details")
        if default_agency_bm:
            agency_bm_id = default_agency_bm
            st.text(f"Agency BM ID: {agency_bm_id[:8]}...")
        else:
            agency_bm_id = st.text_input(
                "Agency Business Manager ID",
                help="Your agency's Business Manager ID",
            )

        st.subheader("Brand Details")
        if default_brand_bm:
            brand_bm_id = default_brand_bm
            st.text(f"Brand BM ID: {brand_bm_id[:8]}...")
        else:
            brand_bm_id = st.text_input(
                "Brand Business Manager ID",
                help="Your client brand's Business Manager ID",
            )

        brand_name = st.text_input(
            "Brand Name",
            value=default_brand_name or "",
            help="Name of the brand (for display purposes)",
        )
        contact_email = st.text_input(
            "Contact Email",
            value=default_email or "",
            help="Contact email for collaboration requests",
        )
        contact_name = st.text_input(
            "Contact Name",
            value=default_contact or "",
            help="Contact name for collaboration requests",
        )

        # Validate button
        if st.button("Validate Setup", type="primary"):
            if not all([access_token, agency_bm_id, brand_bm_id]):
                st.error("Please fill in all required fields")
            else:
                with st.spinner("Validating..."):
                    result, error = validate_setup(access_token, agency_bm_id, brand_bm_id)
                    if error:
                        st.error(f"Validation failed: {error}")
                        st.session_state.setup_validated = False
                    else:
                        st.success("Setup validated successfully!")
                        st.session_state.setup_validated = True
                        st.session_state.validation_result = result

    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview",
        "🔍 Partner Discovery",
        "📨 Connection Requests",
        "💼 Ad Account Setup",
        "🚀 Campaign Launch",
    ])

    # Tab 1: Overview
    with tab1:
        st.header("Onboarding Overview")

        if not access_token or not brand_bm_id:
            st.info("👈 Please configure your credentials in the sidebar to get started")
        else:
            st.markdown(f"**Brand:** {brand_name or brand_bm_id}")

            if st.session_state.selected_merchant:
                merchant = st.session_state.selected_merchant
                st.markdown(f"**Selected Merchant:** {merchant.get('logo_emoji', '')} {merchant.get('name', 'Unknown')}")

                # Show onboarding progress
                st.subheader("Onboarding Progress")

                with st.spinner("Checking status..."):
                    status = get_full_onboarding_status(
                        access_token, brand_bm_id, merchant.get("key")
                    )

                col1, col2, col3, col4, col5 = st.columns(5)

                with col1:
                    if status["connection_request"]:
                        st.success("Step 1: Request Sent")
                    else:
                        st.warning("Step 1: Send Request")

                with col2:
                    if status["request_approved"]:
                        st.success("Step 2: Approved")
                    else:
                        st.warning("Step 2: Pending")

                with col3:
                    if status["catalog_available"]:
                        st.success("Step 3: Catalog Ready")
                    else:
                        st.warning("Step 3: Await Catalog")

                with col4:
                    if status["ad_account_ready"]:
                        st.success("Step 4: Account Ready")
                    else:
                        st.warning("Step 4: Create Account")

                with col5:
                    if status["campaign_created"]:
                        st.success("Step 5: Campaign Live")
                    else:
                        st.warning("Step 5: Launch Campaign")

            else:
                st.info("Select a merchant in the 'Partner Discovery' tab to see onboarding progress")

    # Tab 2: Partner Discovery
    with tab2:
        st.header("Select CPAS Merchant")
        st.markdown("Choose a merchant platform to collaborate with")

        merchants = get_available_merchants()

        # Display merchants as cards
        cols = st.columns(3)
        for i, merchant in enumerate(merchants[:6]):  # Show first 6
            with cols[i % 3]:
                with st.container():
                    st.markdown(f"### {merchant.get('logo_emoji', '')} {merchant.get('name', 'Unknown')}")
                    st.markdown(f"**Category:** {merchant.get('category', 'N/A')}")
                    st.markdown(f"{merchant.get('description', '')}")
                    st.markdown(f"**Verticals:** {', '.join(merchant.get('verticals', []))}")

                    if st.button(f"Select {merchant.get('name')}", key=f"select_{merchant.get('key')}"):
                        st.session_state.selected_merchant = merchant
                        st.success(f"Selected {merchant.get('name')}")
                        st.rerun()

        if st.session_state.selected_merchant:
            st.divider()
            st.success(f"**Currently Selected:** {st.session_state.selected_merchant.get('logo_emoji', '')} {st.session_state.selected_merchant.get('name')}")

    # Tab 3: Connection Requests
    with tab3:
        st.header("Collaboration Requests")

        if not access_token or not brand_bm_id:
            st.warning("Please configure credentials in the sidebar first")
        elif not st.session_state.selected_merchant:
            st.warning("Please select a merchant in the 'Partner Discovery' tab first")
        else:
            merchant = st.session_state.selected_merchant

            st.subheader(f"Send Request to {merchant.get('logo_emoji', '')} {merchant.get('name')}")

            with st.form("send_request_form"):
                st.markdown(f"**Merchant:** {merchant.get('name')}")
                st.markdown(f"**Brand:** {brand_name or brand_bm_id}")

                req_email = st.text_input("Contact Email", value=contact_email or "")
                req_name = st.text_input("Contact Name", value=contact_name or "")
                is_agency = st.checkbox("Sending as Agency", value=True)

                submit = st.form_submit_button("Send Collaboration Request", type="primary")

                if submit:
                    if not req_email or not req_name:
                        st.error("Please provide contact email and name")
                    else:
                        with st.spinner("Sending request..."):
                            request_id, error = initiate_partnership(
                                access_token,
                                brand_bm_id,
                                merchant.get("key"),
                                req_email,
                                req_name,
                                is_agency,
                            )

                            if error:
                                st.error(f"Failed to send request: {error}")
                            else:
                                st.success(f"Request sent successfully! Request ID: {request_id}")

            st.divider()

            # Show sent requests
            st.subheader("Sent Requests")
            if st.button("Refresh Requests"):
                st.rerun()

            with st.spinner("Loading requests..."):
                requests, error = get_sent_requests(access_token, brand_bm_id)

                if error:
                    st.error(f"Failed to load requests: {error}")
                elif not requests:
                    st.info("No collaboration requests found")
                else:
                    # Convert to dataframe for display
                    df_data = []
                    for req in requests:
                        df_data.append({
                            "Request ID": req.get("id", "N/A"),
                            "Merchant": req.get("receiver_business", {}).get("name", "Unknown"),
                            "Status": req.get("request_status", "Unknown"),
                            "Created": req.get("created_time", "N/A"),
                        })

                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True)

    # Tab 4: Ad Account Setup
    with tab4:
        st.header("Ad Account Setup")

        if not access_token or not brand_bm_id:
            st.warning("Please configure credentials in the sidebar first")
        elif not st.session_state.selected_merchant:
            st.warning("Please select a merchant in the 'Partner Discovery' tab first")
        else:
            merchant = st.session_state.selected_merchant

            # Prerequisites check
            st.subheader("Prerequisites")
            with st.spinner("Checking prerequisites..."):
                status = get_full_onboarding_status(access_token, brand_bm_id, merchant.get("key"))

            col1, col2 = st.columns(2)
            with col1:
                if status["request_approved"]:
                    st.success("Collaboration approved")
                else:
                    st.warning("Collaboration not yet approved")

            with col2:
                if status["catalog_available"]:
                    st.success(f"Catalog segments available ({status['details'].get('catalog_count', 0)})")
                else:
                    st.warning("No catalog segments available yet")

            st.divider()

            # Create ad account
            st.subheader("Create Collaborative Ad Account")

            with st.form("create_account_form"):
                account_name = st.text_input(
                    "Account Name Suffix",
                    value=merchant.get("name", ""),
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
                    with st.spinner("Creating ad account..."):
                        ad_account_id, error = setup_collab_ad_account(
                            access_token,
                            brand_bm_id,
                            account_name,
                            timezone_options[timezone],
                            currency,
                        )

                        if error:
                            st.error(f"Failed to create ad account: {error}")
                        else:
                            st.success(f"Ad account created! ID: {ad_account_id}")
                            st.session_state.created_ad_account_id = ad_account_id

            st.divider()

            # Show existing ad accounts
            st.subheader("Existing Ad Accounts")

            with st.spinner("Loading ad accounts..."):
                accounts, error = get_brand_ad_accounts(access_token, brand_bm_id)

                if error:
                    st.error(f"Failed to load ad accounts: {error}")
                elif not accounts:
                    st.info("No ad accounts found")
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

                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True)

            st.divider()

            # Attach catalog segment
            st.subheader("Available Catalog Segments")

            with st.spinner("Loading catalog segments..."):
                catalogs, error = get_available_catalog_segments(access_token, brand_bm_id)

                if error:
                    st.error(f"Failed to load catalog segments: {error}")
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

                    df = pd.DataFrame(df_data)
                    st.dataframe(df, use_container_width=True)

                    # Select catalog for campaign
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

    # Tab 5: Campaign Launch
    with tab5:
        st.header("Launch CPAS Campaign")

        if not access_token or not brand_bm_id:
            st.warning("Please configure credentials in the sidebar first")
        elif not st.session_state.selected_merchant:
            st.warning("Please select a merchant in the 'Partner Discovery' tab first")
        else:
            merchant = st.session_state.selected_merchant

            # Get accounts and catalogs for dropdowns
            accounts, _ = get_brand_ad_accounts(access_token, brand_bm_id)
            catalogs, _ = get_available_catalog_segments(access_token, brand_bm_id)

            if not accounts:
                st.warning("No ad accounts available. Please create one in the 'Ad Account Setup' tab.")
            elif not catalogs:
                st.warning("No catalog segments available. The merchant needs to share a catalog segment.")
            else:
                st.subheader(f"Create Campaign with {merchant.get('logo_emoji', '')} {merchant.get('name')}")

                with st.form("create_campaign_form"):
                    campaign_name = st.text_input(
                        "Campaign Name",
                        value=f"{brand_name or 'Brand'} x {merchant.get('name')} - CPAS",
                    )

                    # Ad account selection
                    account_options = {acc.get("name", acc.get("id")): acc.get("id") for acc in accounts}
                    selected_account_name = st.selectbox("Ad Account", options=list(account_options.keys()))
                    selected_account_id = account_options[selected_account_name]

                    # Catalog selection
                    catalog_options = {cat.get("name", cat.get("id")): cat.get("id") for cat in catalogs}
                    selected_catalog_name = st.selectbox("Catalog Segment", options=list(catalog_options.keys()))
                    selected_catalog_id = catalog_options[selected_catalog_name]

                    # Budget
                    daily_budget_inr = st.number_input(
                        "Daily Budget (INR)",
                        min_value=100,
                        max_value=1000000,
                        value=1000,
                        step=100,
                    )
                    daily_budget_paisa = daily_budget_inr * 100  # Convert to paisa

                    # Targeting
                    st.markdown("**Targeting**")
                    target_countries = st.multiselect(
                        "Countries",
                        options=["IN", "US", "GB", "AE", "SG"],
                        default=["IN"],
                    )

                    create_campaign_submit = st.form_submit_button("Create Campaign (PAUSED)", type="primary")

                    if create_campaign_submit:
                        with st.spinner("Creating campaign..."):
                            result, error = create_cpas_campaign(
                                access_token,
                                selected_account_id,
                                selected_catalog_id,
                                campaign_name,
                                daily_budget_paisa,
                                target_countries,
                            )

                            if error:
                                st.error(f"Failed to create campaign: {error}")
                            else:
                                st.success("Campaign created successfully!")
                                st.json(result)

                                # Create summary for download
                                summary_data = {
                                    "campaign_id": [result.get("campaign_id")],
                                    "ad_set_id": [result.get("ad_set_id")],
                                    "ad_account_id": [selected_account_id],
                                    "catalog_segment_id": [selected_catalog_id],
                                    "campaign_name": [campaign_name],
                                    "daily_budget_inr": [daily_budget_inr],
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

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### Quick Help

    **Step 1:** Configure credentials
    **Step 2:** Select a merchant
    **Step 3:** Send collaboration request
    **Step 4:** Wait for merchant approval
    **Step 5:** Create ad account
    **Step 6:** Launch campaign

    All campaigns are created in PAUSED status.
    """)


if __name__ == "__main__":
    main()
