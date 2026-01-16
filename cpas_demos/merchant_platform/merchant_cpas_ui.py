"""
Merchant Platform UI

A Streamlit-based web interface for merchants to manage CPAS brand partnerships
and enable brand self-service onboarding.

To run:
$ cd cpas_demos
$ streamlit run merchant_platform/merchant_cpas_ui.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st

from merchant_cpas_backend import (
    validate_merchant_setup,
    get_dashboard_stats,
    get_pending_requests,
    get_all_requests,
    approve_request,
    reject_request,
    bulk_approve_requests,
    bulk_reject_requests,
    get_active_partners,
    get_catalog_segments,
    share_catalog_with_brand,
    brand_submit_request,
    brand_check_request_status,
    brand_get_shared_catalogs,
    brand_create_ad_account,
    brand_create_campaign,
)
from shared.constants import CollabRequestStatus, DEFAULT_DAILY_BUDGET

# Import config for default values
try:
    import config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    config = None


def init_session_state():
    """Initialize session state variables."""
    if "merchant_validated" not in st.session_state:
        st.session_state.merchant_validated = False
    if "selected_requests" not in st.session_state:
        st.session_state.selected_requests = []
    if "brand_onboarding_step" not in st.session_state:
        st.session_state.brand_onboarding_step = 1


def main():
    st.set_page_config(
        page_title="Merchant CPAS Platform",
        page_icon="🏪",
        layout="wide",
    )

    init_session_state()

    st.title("🏪 Merchant CPAS Platform")
    st.markdown("Manage brand partnerships and enable self-service CPAS onboarding")

    # Sidebar for authentication
    with st.sidebar:
        st.header("Configuration")

        # Get defaults from config if available
        default_token = getattr(config, 'ACCESS_TOKEN', None) if CONFIG_AVAILABLE else None
        default_merchant_bm = getattr(config, 'MERCHANT_BUSINESS_ID', None) if CONFIG_AVAILABLE else None
        default_merchant_name = getattr(config, 'MERCHANT_NAME', None) if CONFIG_AVAILABLE else None

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
            st.text(f"Merchant BM ID: {merchant_bm_id[:8]}...")
        else:
            merchant_bm_id = st.text_input(
                "Merchant Business Manager ID",
                help="Your merchant's Business Manager ID",
            )

        merchant_name = st.text_input(
            "Merchant Name",
            value=default_merchant_name or "",
            help="Your merchant name (for display)",
        )

        # Validate button
        if st.button("Validate Setup", type="primary"):
            if not all([access_token, merchant_bm_id]):
                st.error("Please fill in all required fields")
            else:
                with st.spinner("Validating..."):
                    result, error = validate_merchant_setup(access_token, merchant_bm_id)
                    if error:
                        st.error(f"Validation failed: {error}")
                        st.session_state.merchant_validated = False
                    else:
                        st.success("Setup validated successfully!")
                        st.session_state.merchant_validated = True

    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard",
        "📨 Pending Requests",
        "🤝 Active Partners",
        "📦 Catalog Segments",
        "🚀 Brand Self-Service",
    ])

    # Tab 1: Dashboard
    with tab1:
        st.header("Merchant Dashboard")

        if not access_token or not merchant_bm_id:
            st.info("👈 Please configure your credentials in the sidebar to get started")
        else:
            st.markdown(f"**Merchant:** {merchant_name or merchant_bm_id}")

            # Dashboard metrics
            with st.spinner("Loading dashboard..."):
                stats = get_dashboard_stats(access_token, merchant_bm_id)

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Pending Requests",
                    stats.get("pending_requests", 0),
                    help="Brand requests awaiting your approval",
                )

            with col2:
                st.metric(
                    "Active Partners",
                    stats.get("active_partners", 0),
                    help="Brands with approved collaborations",
                )

            with col3:
                st.metric(
                    "Catalog Segments",
                    stats.get("catalog_segments", 0),
                    help="Your catalog segments available for sharing",
                )

            with col4:
                st.metric(
                    "Total Requests",
                    stats.get("pending_requests", 0) + stats.get("approved_requests", 0),
                    help="Total collaboration requests received",
                )

            st.divider()

            # Quick actions
            st.subheader("Quick Actions")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("Review Pending Requests"):
                    st.info("Navigate to the 'Pending Requests' tab")

            with col2:
                if st.button("Manage Partners"):
                    st.info("Navigate to the 'Active Partners' tab")

            with col3:
                if st.button("Share Catalog"):
                    st.info("Navigate to the 'Catalog Segments' tab")

    # Tab 2: Pending Requests
    with tab2:
        st.header("Pending Collaboration Requests")

        if not access_token or not merchant_bm_id:
            st.warning("Please configure credentials in the sidebar first")
        else:
            # Filters
            col1, col2 = st.columns([2, 1])
            with col1:
                status_filter = st.selectbox(
                    "Filter by Status",
                    options=["All", "PENDING", "APPROVED", "REJECTED"],
                )
            with col2:
                if st.button("Refresh"):
                    st.rerun()

            # Get requests
            filter_status = None if status_filter == "All" else status_filter
            with st.spinner("Loading requests..."):
                requests, error = get_all_requests(access_token, merchant_bm_id, filter_status)

            if error:
                st.error(f"Failed to load requests: {error}")
            elif not requests:
                st.info("No collaboration requests found")
            else:
                # Display as table with actions
                st.markdown(f"**Found {len(requests)} request(s)**")

                for i, req in enumerate(requests):
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

                        with col1:
                            brand_name = req.get("sender_business", {}).get("name", "Unknown Brand")
                            st.markdown(f"**{brand_name}**")
                            st.caption(f"Contact: {req.get('contact_name', 'N/A')} ({req.get('contact_email', 'N/A')})")

                        with col2:
                            request_status = req.get("request_status", "Unknown")
                            if request_status == "PENDING":
                                st.warning(request_status)
                            elif request_status == "APPROVED":
                                st.success(request_status)
                            else:
                                st.error(request_status)

                        with col3:
                            st.caption(f"Received: {req.get('created_time', 'N/A')[:10] if req.get('created_time') else 'N/A'}")

                        with col4:
                            if req.get("request_status") == "PENDING":
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    if st.button("Approve", key=f"approve_{i}"):
                                        with st.spinner("Approving..."):
                                            success, err = approve_request(access_token, req.get("id"))
                                            if success:
                                                st.success("Approved!")
                                                st.rerun()
                                            else:
                                                st.error(f"Failed: {err}")

                                with col_b:
                                    if st.button("Reject", key=f"reject_{i}"):
                                        with st.spinner("Rejecting..."):
                                            success, err = reject_request(access_token, req.get("id"))
                                            if success:
                                                st.info("Rejected")
                                                st.rerun()
                                            else:
                                                st.error(f"Failed: {err}")

                        st.divider()

                # Bulk actions
                st.subheader("Bulk Actions")
                pending_requests = [r for r in requests if r.get("request_status") == "PENDING"]

                if pending_requests:
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        if st.button("Approve All Pending", type="primary"):
                            request_ids = [r.get("id") for r in pending_requests]
                            with st.spinner(f"Approving {len(request_ids)} requests..."):
                                results = bulk_approve_requests(access_token, request_ids)
                                st.success(f"Approved: {results['successful']}, Failed: {results['failed']}")
                                st.rerun()

                    with col2:
                        if st.button("Reject All Pending"):
                            request_ids = [r.get("id") for r in pending_requests]
                            with st.spinner(f"Rejecting {len(request_ids)} requests..."):
                                results = bulk_reject_requests(access_token, request_ids)
                                st.info(f"Rejected: {results['successful']}, Failed: {results['failed']}")
                                st.rerun()
                else:
                    st.info("No pending requests for bulk actions")

    # Tab 3: Active Partners
    with tab3:
        st.header("Active Brand Partners")

        if not access_token or not merchant_bm_id:
            st.warning("Please configure credentials in the sidebar first")
        else:
            with st.spinner("Loading partners..."):
                partners, error = get_active_partners(access_token, merchant_bm_id)

            if error:
                st.error(f"Failed to load partners: {error}")
            elif not partners:
                st.info("No active partners found. Approve pending requests to add partners.")
            else:
                st.markdown(f"**{len(partners)} Active Partner(s)**")

                # Search filter
                search = st.text_input("Search partners", placeholder="Enter brand name...")

                # Display partners
                for partner in partners:
                    brand_name = partner.get("sender_business", {}).get("name", "Unknown")

                    if search and search.lower() not in brand_name.lower():
                        continue

                    with st.expander(f"🏢 {brand_name}"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown(f"**Business ID:** {partner.get('sender_business', {}).get('id', 'N/A')}")
                            st.markdown(f"**Contact:** {partner.get('contact_name', 'N/A')}")
                            st.markdown(f"**Email:** {partner.get('contact_email', 'N/A')}")

                        with col2:
                            st.markdown(f"**Partnership Since:** {partner.get('created_time', 'N/A')[:10] if partner.get('created_time') else 'N/A'}")
                            st.markdown(f"**Status:** {partner.get('request_status', 'N/A')}")

                # Export
                if partners:
                    df_data = []
                    for p in partners:
                        df_data.append({
                            "Brand Name": p.get("sender_business", {}).get("name", "Unknown"),
                            "Business ID": p.get("sender_business", {}).get("id", "N/A"),
                            "Contact Name": p.get("contact_name", "N/A"),
                            "Contact Email": p.get("contact_email", "N/A"),
                            "Partnership Date": p.get("created_time", "N/A"),
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
    with tab4:
        st.header("Catalog Segment Management")

        if not access_token or not merchant_bm_id:
            st.warning("Please configure credentials in the sidebar first")
        else:
            # Show existing segments
            st.subheader("Your Catalog Segments")

            with st.spinner("Loading catalog segments..."):
                catalogs, error = get_catalog_segments(access_token, merchant_bm_id)

            if error:
                st.error(f"Failed to load catalogs: {error}")
            elif not catalogs:
                st.info("No catalog segments found")
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

                st.divider()

                # Share segment form
                st.subheader("Share Catalog Segment")

                with st.form("share_catalog_form"):
                    catalog_ids = [cat.get("id") for cat in catalogs if cat.get("id")]
                    selected_catalog = st.selectbox(
                        "Select Catalog",
                        options=catalog_ids,
                        format_func=lambda x: next(
                            (cat.get("name", x) for cat in catalogs if cat.get("id") == x), x
                        ),
                    )

                    brand_bm_id = st.text_input(
                        "Brand Business Manager ID",
                        help="The Business Manager ID of the brand to share with",
                    )

                    share_submit = st.form_submit_button("Share Catalog", type="primary")

                    if share_submit:
                        if not brand_bm_id:
                            st.error("Please enter the brand's Business Manager ID")
                        else:
                            with st.spinner("Sharing catalog..."):
                                success, err = share_catalog_with_brand(
                                    access_token, selected_catalog, brand_bm_id
                                )

                                if success:
                                    st.success(f"Catalog shared with {brand_bm_id}")
                                else:
                                    st.error(f"Failed to share: {err}")

    # Tab 5: Brand Self-Service
    with tab5:
        st.header("Brand Self-Service Portal")
        st.markdown(f"Welcome to **{merchant_name or 'Merchant'}**'s CPAS onboarding portal")

        # This tab simulates the brand's perspective
        st.info("This tab demonstrates the brand self-service experience. Brands would access this portal to onboard themselves.")

        st.divider()

        # Step-by-step wizard
        step = st.session_state.brand_onboarding_step

        # Progress bar
        progress = (step - 1) / 4
        st.progress(progress, text=f"Step {step} of 5")

        st.subheader(f"Step {step}: ", divider=True)

        # Step 1: Enter brand details
        if step == 1:
            st.markdown("**Enter Your Brand Details**")

            with st.form("brand_details_form"):
                brand_bm_id = st.text_input("Your Brand Business Manager ID")
                brand_name_input = st.text_input("Brand Name")
                brand_email = st.text_input("Contact Email")
                brand_contact = st.text_input("Contact Name")
                brand_token = st.text_input("Access Token", type="password")

                submit = st.form_submit_button("Submit Request", type="primary")

                if submit:
                    if not all([brand_bm_id, brand_name_input, brand_email, brand_contact, brand_token]):
                        st.error("Please fill in all fields")
                    elif not merchant_bm_id:
                        st.error("Merchant configuration is missing. Please configure in sidebar.")
                    else:
                        with st.spinner("Submitting request..."):
                            request_id, err = brand_submit_request(
                                brand_token,
                                merchant_bm_id,
                                brand_bm_id,
                                brand_name_input,
                                brand_email,
                                brand_contact,
                            )

                            if err:
                                st.error(f"Failed to submit: {err}")
                            else:
                                st.success(f"Request submitted! ID: {request_id}")
                                st.session_state.brand_onboarding_step = 2
                                st.session_state.brand_request_id = request_id
                                st.session_state.brand_token = brand_token
                                st.session_state.brand_bm_id = brand_bm_id
                                st.rerun()

        # Step 2: Wait for approval
        elif step == 2:
            st.markdown("**Waiting for Merchant Approval**")

            st.info("Your request has been submitted. Please wait for the merchant to review and approve your request.")

            brand_token = st.session_state.get("brand_token")
            brand_bm_id = st.session_state.get("brand_bm_id")

            if brand_token and brand_bm_id and merchant_bm_id:
                if st.button("Check Status"):
                    with st.spinner("Checking..."):
                        status = brand_check_request_status(brand_token, brand_bm_id, merchant_bm_id)

                        if status.get("status") == "APPROVED":
                            st.success("Your request has been approved!")
                            st.session_state.brand_onboarding_step = 3
                            st.rerun()
                        elif status.get("status") == "PENDING":
                            st.warning("Your request is still pending approval")
                        elif status.get("status") == "REJECTED":
                            st.error("Your request was rejected")
                        else:
                            st.info(f"Status: {status}")

            if st.button("Skip to Next Step (Demo)"):
                st.session_state.brand_onboarding_step = 3
                st.rerun()

        # Step 3: Create ad account
        elif step == 3:
            st.markdown("**Create Your Collaborative Ad Account**")

            brand_token = st.session_state.get("brand_token")
            brand_bm_id = st.session_state.get("brand_bm_id")

            if brand_token and brand_bm_id:
                with st.form("create_account_form"):
                    st.info("A new ad account will be created for your CPAS campaigns")

                    create_submit = st.form_submit_button("Create Ad Account", type="primary")

                    if create_submit:
                        with st.spinner("Creating ad account..."):
                            ad_account_id, err = brand_create_ad_account(
                                brand_token,
                                brand_bm_id,
                                merchant_name or "Merchant",
                            )

                            if err:
                                st.error(f"Failed to create: {err}")
                            else:
                                st.success(f"Ad account created! ID: {ad_account_id}")
                                st.session_state.brand_ad_account_id = ad_account_id
                                st.session_state.brand_onboarding_step = 4
                                st.rerun()
            else:
                st.warning("Missing brand credentials. Please restart onboarding.")

            if st.button("Skip to Next Step (Demo)"):
                st.session_state.brand_onboarding_step = 4
                st.rerun()

        # Step 4: Select catalog segment
        elif step == 4:
            st.markdown("**Select Catalog Segment**")

            brand_token = st.session_state.get("brand_token")
            brand_bm_id = st.session_state.get("brand_bm_id")

            if brand_token and brand_bm_id:
                with st.spinner("Loading available catalogs..."):
                    catalogs, err = brand_get_shared_catalogs(brand_token, brand_bm_id)

                if err:
                    st.error(f"Failed to load catalogs: {err}")
                elif not catalogs:
                    st.warning("No catalog segments available yet. The merchant needs to share a catalog with you.")
                else:
                    st.success(f"Found {len(catalogs)} catalog segment(s)")

                    catalog_options = {cat.get("name", cat.get("id")): cat.get("id") for cat in catalogs}
                    selected_catalog_name = st.selectbox("Select Catalog", options=list(catalog_options.keys()))
                    selected_catalog_id = catalog_options[selected_catalog_name]

                    if st.button("Use This Catalog", type="primary"):
                        st.session_state.brand_catalog_id = selected_catalog_id
                        st.session_state.brand_onboarding_step = 5
                        st.rerun()
            else:
                st.warning("Missing brand credentials. Please restart onboarding.")

            if st.button("Skip to Next Step (Demo)"):
                st.session_state.brand_onboarding_step = 5
                st.rerun()

        # Step 5: Create campaign
        elif step == 5:
            st.markdown("**Launch Your CPAS Campaign**")

            brand_token = st.session_state.get("brand_token")
            brand_bm_id = st.session_state.get("brand_bm_id")
            ad_account_id = st.session_state.get("brand_ad_account_id")
            catalog_id = st.session_state.get("brand_catalog_id")

            with st.form("create_campaign_form"):
                campaign_name = st.text_input(
                    "Campaign Name",
                    value=f"CPAS Campaign with {merchant_name or 'Merchant'}",
                )

                daily_budget_inr = st.number_input(
                    "Daily Budget (INR)",
                    min_value=100,
                    max_value=1000000,
                    value=1000,
                )

                if ad_account_id:
                    st.info(f"Ad Account: {ad_account_id}")
                else:
                    ad_account_id = st.text_input("Ad Account ID (enter manually)")

                if catalog_id:
                    st.info(f"Catalog: {catalog_id}")
                else:
                    catalog_id = st.text_input("Catalog Segment ID (enter manually)")

                create_submit = st.form_submit_button("Create Campaign (PAUSED)", type="primary")

                if create_submit:
                    if not brand_token:
                        brand_token = st.text_input("Enter Access Token")

                    if brand_token and ad_account_id and catalog_id:
                        with st.spinner("Creating campaign..."):
                            result, err = brand_create_campaign(
                                brand_token,
                                ad_account_id,
                                catalog_id,
                                campaign_name,
                                daily_budget_inr * 100,  # Convert to paisa
                            )

                            if err:
                                st.error(f"Failed to create campaign: {err}")
                            else:
                                st.success("Campaign created successfully!")
                                st.balloons()
                                st.json(result)

                                # Summary download
                                summary = {
                                    "campaign_id": [result.get("campaign_id")],
                                    "ad_set_id": [result.get("ad_set_id")],
                                    "merchant": [merchant_name or merchant_bm_id],
                                    "status": ["PAUSED"],
                                }
                                summary_df = pd.DataFrame(summary)
                                csv_data = summary_df.to_csv(index=False)

                                st.download_button(
                                    label="Download Summary",
                                    data=csv_data,
                                    file_name="cpas_campaign_summary.csv",
                                    mime="text/csv",
                                )
                    else:
                        st.error("Missing required information")

            # Reset button
            if st.button("Start Over"):
                st.session_state.brand_onboarding_step = 1
                for key in ["brand_token", "brand_bm_id", "brand_request_id", "brand_ad_account_id", "brand_catalog_id"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    ### Quick Help

    **Dashboard:** View partnership stats
    **Pending Requests:** Review brand requests
    **Active Partners:** Manage partnerships
    **Catalog Segments:** Share catalogs
    **Brand Self-Service:** Brand onboarding wizard

    Need help? Contact your Meta representative.
    """)


if __name__ == "__main__":
    main()
