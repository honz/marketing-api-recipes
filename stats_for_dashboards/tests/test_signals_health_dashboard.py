import pytest
from unittest.mock import patch, ANY
from stats_for_dashboards import signals_health_dashboard
from datetime import datetime

@pytest.fixture
def mock_dependencies():
    with patch('stats_for_dashboards.signals_health_dashboard.FacebookAdsApi.init') as mock_facebook_api_init, \
         patch('stats_for_dashboards.signals_health_dashboard.get_pixels_for_business_id') as mock_get_pixels, \
         patch('stats_for_dashboards.signals_health_dashboard.get_spend_for_pixels') as mock_get_spend, \
         patch('stats_for_dashboards.signals_health_dashboard.get_stats_and_settings_for_pixels') as mock_get_stats, \
         patch('stats_for_dashboards.signals_health_dashboard.print_and_log') as mock_print_and_log:

        # Mock the return values
        mock_get_pixels.return_value = [{'id': '789'}, {'id': '012'}]
        mock_get_spend.return_value = {'789': 100, '012': 200}
        mock_get_stats.return_value = {
            '789': {'stats': 'stat3', 'match_rate': 0.9, 'event_stats': 'event3', 'automatic_matching_fields': 'fields3', 'checks': 'check3'},
            '012': {'stats': 'stat4', 'match_rate': 0.8, 'event_stats': 'event4', 'automatic_matching_fields': 'fields4', 'checks': 'check4'}
        }

        yield mock_facebook_api_init, mock_get_pixels, mock_get_spend, mock_get_stats, mock_print_and_log

def test_main(mock_dependencies):
    mock_facebook_api_init, mock_get_pixels, mock_get_spend, mock_get_stats, mock_print_and_log = mock_dependencies
    today = datetime.now().date().strftime('%Y-%m-%d')

    # Run the main function
    signals_health_dashboard.main()

    # Check if the Facebook API was initialized
    mock_facebook_api_init.assert_called_once_with(
        signals_health_dashboard.app_id,
        signals_health_dashboard.app_secret,
        signals_health_dashboard.access_token
    )

    # Check if pixels were retrieved
    mock_get_pixels.assert_called_once_with(
        signals_health_dashboard.business_id,
        ANY,  # RUN_ID is dynamically generated
        True
    )

    # Check if spend was retrieved
    mock_get_spend.assert_called_once_with(
        mock_get_pixels.return_value,
        signals_health_dashboard.business_id,
        ANY,  # since date
        today,  # until date
        ANY,  # RUN_ID is dynamically generated
        True
    )

    # Check if stats were retrieved
    mock_get_stats.assert_called_once_with(
        mock_get_pixels.return_value,
        ANY,  # RUN_ID is dynamically generated
        True
    )

    # Check if print_and_log was called
    assert mock_print_and_log.called

    # Check if the CSV file was written correctly
    with open("signals_health_dashboard.csv", "r") as f:
        lines = f.readlines()
        assert lines[0] == "pixel_id,date,spend,stats,match_rate,event_stats,automatic_matching_fields,checks\n"
        assert f"789,{today},100,stat3,0.9,event3,fields3,check3\n" in lines
        assert f"012,{today},200,stat4,0.8,event4,fields4,check4\n" in lines
