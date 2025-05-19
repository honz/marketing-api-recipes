import pytest
from unittest.mock import patch
from unittest.mock import ANY
from stats_for_dashboards import catalog_health_dashboard

@pytest.fixture
def mock_dependencies():
    with patch('stats_for_dashboards.catalog_health_dashboard.FacebookAdsApi.init') as mock_facebook_api_init, \
         patch('stats_for_dashboards.catalog_health_dashboard.get_catalogs_for_business_id') as mock_get_catalogs, \
         patch('stats_for_dashboards.catalog_health_dashboard.get_stats_for_catalogs') as mock_get_stats, \
         patch('stats_for_dashboards.catalog_health_dashboard.print_and_log') as mock_print_and_log:

        # Mock the return values
        mock_get_catalogs.return_value = [{'id': '123'}, {'id': '456'}]
        mock_get_stats.return_value = {
            '123': {'stats': 'stat1', 'diagnostics': 'diag1', 'product_count': 10},
            '456': {'stats': 'stat2', 'diagnostics': 'diag2', 'product_count': 20}
        }

        yield mock_facebook_api_init, mock_get_catalogs, mock_get_stats, mock_print_and_log

def test_main(mock_dependencies):
    mock_facebook_api_init, mock_get_catalogs, mock_get_stats, mock_print_and_log = mock_dependencies

    # Run the main function
    catalog_health_dashboard.main()

    # Check if the Facebook API was initialized
    mock_facebook_api_init.assert_called_once_with(
        catalog_health_dashboard.app_id,
        catalog_health_dashboard.app_secret,
        catalog_health_dashboard.access_token
    )

    # Check if catalogs were retrieved
    mock_get_catalogs.assert_called_once_with(
        catalog_health_dashboard.business_id,
        ANY,  # RUN_ID is dynamically generated
        True
    )

    # Check if stats were retrieved
    mock_get_stats.assert_called_once_with(
        mock_get_catalogs.return_value,
        ANY,  # RUN_ID is dynamically generated
        True
    )

    # Check if print_and_log was called
    assert mock_print_and_log.called

    # Check if the CSV file was written correctly
    with open("catalog_health_dashboard.csv", "r") as f:
        lines = f.readlines()
        assert lines[0] == "catalog_id,stats,diagnostics,product_count\n"
        assert "123,stat1,diag1,10\n" in lines
        assert "456,stat2,diag2,20\n" in lines
