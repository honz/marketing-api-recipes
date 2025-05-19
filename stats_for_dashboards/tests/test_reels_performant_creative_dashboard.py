import pytest
from unittest.mock import patch, ANY
from stats_for_dashboards import reels_performant_creative_dashboard

@pytest.fixture
def mock_dependencies():
    with patch('stats_for_dashboards.reels_performant_creative_dashboard.FacebookAdsApi.init') as mock_facebook_api_init, \
         patch('stats_for_dashboards.reels_performant_creative_dashboard.get_ad_accounts_for_business_id') as mock_get_ad_accounts, \
         patch('stats_for_dashboards.reels_performant_creative_dashboard.AdAccount.get_insights') as mock_get_insights, \
         patch('stats_for_dashboards.reels_performant_creative_dashboard.AdCreative.remote_create') as mock_creative_create, \
         patch('stats_for_dashboards.reels_performant_creative_dashboard.Ad.remote_create') as mock_ad_create, \
         patch('stats_for_dashboards.reels_performant_creative_dashboard.print_and_log') as mock_print_and_log:

        # Mock the return values
        mock_get_ad_accounts.return_value = [{'id': '123'}, {'id': '456'}]
        mock_get_insights.return_value = [{'impressions': 1000, 'ad_id': 'ad_123'}]

        yield mock_facebook_api_init, mock_get_ad_accounts, mock_get_insights, mock_creative_create, mock_ad_create, mock_print_and_log

def test_main(mock_dependencies):
    mock_facebook_api_init, mock_get_ad_accounts, mock_get_insights, mock_creative_create, mock_ad_create, mock_print_and_log = mock_dependencies

    # Run the main function
    reels_performant_creative_dashboard.main()

    # Check if the Facebook API was initialized
    mock_facebook_api_init.assert_called_once_with(
        reels_performant_creative_dashboard.app_id,
        reels_performant_creative_dashboard.app_secret,
        reels_performant_creative_dashboard.access_token
    )

    # Check if ad accounts were retrieved
    mock_get_ad_accounts.assert_called_once_with(
        reels_performant_creative_dashboard.business_id,
        ANY  # RUN_ID is dynamically generated
    )

    # Check if insights were retrieved for each ad account
    assert mock_get_insights.call_count == len(mock_get_ad_accounts.return_value)

    # Check if creatives were created
    assert mock_creative_create.call_count == len(mock_get_ad_accounts.return_value)

    # Check if ads were created
    assert mock_ad_create.call_count == len(mock_get_ad_accounts.return_value)

    # Check if print_and_log was called
    assert mock_print_and_log.called
