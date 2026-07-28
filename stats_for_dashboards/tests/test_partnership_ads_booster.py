import csv
import json
import sys
from io import StringIO
from unittest.mock import call, MagicMock, mock_open, patch

import pytest
from stats_for_dashboards import partnership_ads_booster


class TestExtractInstagramShortcode:
    """Tests for extract_instagram_shortcode function"""

    def test_extract_from_reel_url(self):
        url = "https://www.instagram.com/reel/aBc123XyZ/"
        result = partnership_ads_booster.extract_instagram_shortcode(url)
        assert result == "aBc123XyZ"

    def test_extract_from_post_url(self):
        url = "https://www.instagram.com/p/dEf456GhI/"
        result = partnership_ads_booster.extract_instagram_shortcode(url)
        assert result == "dEf456GhI"

    def test_extract_from_tv_url(self):
        url = "https://www.instagram.com/tv/jKl789MnO/"
        result = partnership_ads_booster.extract_instagram_shortcode(url)
        assert result == "jKl789MnO"

    def test_extract_from_reels_url(self):
        url = "https://www.instagram.com/reels/DVd0eJEESn9/"
        result = partnership_ads_booster.extract_instagram_shortcode(url)
        assert result == "DVd0eJEESn9"

    def test_extract_from_url_without_https(self):
        url = "instagram.com/reel/pQr012StU/"
        result = partnership_ads_booster.extract_instagram_shortcode(url)
        assert result == "pQr012StU"

    def test_extract_from_url_with_www(self):
        url = "https://www.instagram.com/reel/vWx345YzA/"
        result = partnership_ads_booster.extract_instagram_shortcode(url)
        assert result == "vWx345YzA"

    def test_shortcode_only(self):
        shortcode = "bCd678EfG"
        result = partnership_ads_booster.extract_instagram_shortcode(shortcode)
        assert result == "bCd678EfG"

    def test_shortcode_with_trailing_slash(self):
        shortcode = "hIj901KlM/"
        result = partnership_ads_booster.extract_instagram_shortcode(shortcode)
        assert result == "hIj901KlM"

    def test_empty_string(self):
        result = partnership_ads_booster.extract_instagram_shortcode("")
        assert result == ""

    def test_stories_url_raises_error(self):
        url = "https://www.instagram.com/stories/username/123456789/"
        with pytest.raises(ValueError, match="Stories boosting is not supported"):
            partnership_ads_booster.extract_instagram_shortcode(url)

    def test_stories_in_shortcode_raises_error(self):
        # Test that a shortcode with "/stories/" in it also raises an error
        shortcode = "/stories/12345"
        with pytest.raises(ValueError, match="Stories boosting is not supported"):
            partnership_ads_booster.extract_instagram_shortcode(shortcode)


@pytest.fixture
def mock_creator_username():
    return "test_creator"


@pytest.fixture
def mock_access_token():
    return "test_access_token"


@pytest.fixture
def mock_ig_account_id():
    return "17841400875057971"


@pytest.fixture
def mock_business_id():
    return "123456789012345"


@pytest.fixture
def mock_ad_account_id():
    return "1549883851784009"


@pytest.fixture
def mock_facebook_page_id():
    return "102988293558"


@pytest.fixture
def sample_media_response():
    return {
        "data": [
            {
                "id": "media_123",
                "permalink": "https://instagram.com/p/abc123",
                "owner_id": "owner_123",
                "has_permission_for_partnership_ad": True,
                "eligibility_errors": [],
            },
            {
                "id": "media_456",
                "permalink": "https://instagram.com/p/def456",
                "owner_id": "owner_456",
                "has_permission_for_partnership_ad": False,
                "eligibility_errors": ["ERROR_1"],
            },
        ],
        "paging": {},
    }


@pytest.fixture
def sample_csv_rows():
    return [
        {
            "media_id": "media_123",
            "permalink": "https://instagram.com/p/abc123",
            "owner_id": "owner_123",
            "has_permission_for_partnership_ad": "True",
            "eligibility_errors": "[]",
            "ad_set_id": "adset_123",
            "cta_type": "INSTALL_MOBILE_APP",
            "link": "https://app.link/install",
            "app_link": "myapp://landing",
            "ad_name": "Test Ad 1",
            "ad_code": "",
            "product_set_id": "",
        }
    ]


class TestFetchMediaInsights:
    """Tests for fetch_media_insights function"""

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_media_insights_success(self, mock_get, mock_access_token):
        """Test successful fetch of likes and comments"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "like_count": 150,
            "comments_count": 25,
        }
        mock_get.return_value = mock_response

        result = partnership_ads_booster.fetch_media_insights(
            mock_access_token, "media_123"
        )

        assert result["likes"] == 150
        assert result["comments"] == 25

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_media_insights_api_error(self, mock_get, mock_access_token):
        """Test that API errors return None values gracefully"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_get.return_value = mock_response

        result = partnership_ads_booster.fetch_media_insights(
            mock_access_token, "media_123"
        )

        assert result["likes"] is None
        assert result["comments"] is None

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_media_insights_partial_data(self, mock_get, mock_access_token):
        """Test handling of partial data from API"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "like_count": 100,
            # comments_count missing
        }
        mock_get.return_value = mock_response

        result = partnership_ads_booster.fetch_media_insights(
            mock_access_token, "media_123"
        )

        assert result["likes"] == 100
        assert result["comments"] is None


class TestFetchPageOfAdvertisableMedias:
    """Tests for fetch_page_of_advertisable_medias function (pagination support)"""

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_first_page_success(
        self,
        mock_get,
        mock_access_token,
        mock_ig_account_id,
        sample_media_response,
    ):
        """Test fetching the first page without cursor"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            **sample_media_response,
            "paging": {"next": "https://graph.facebook.com/v22.0/next_page"}
        }
        mock_get.return_value = mock_response

        medias, next_cursor = partnership_ads_booster.fetch_page_of_advertisable_medias(
            mock_access_token,
            mock_ig_account_id,
        )

        assert len(medias) == 2
        assert medias[0]["id"] == "media_123"
        assert next_cursor == "https://graph.facebook.com/v22.0/next_page"

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_with_cursor(
        self,
        mock_get,
        mock_access_token,
        mock_ig_account_id,
    ):
        """Test fetching subsequent page with cursor"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "media_789",
                    "permalink": "https://instagram.com/p/789",
                    "owner_id": "owner_789",
                    "has_permission_for_partnership_ad": True,
                    "eligibility_errors": [],
                }
            ],
            "paging": {}
        }
        mock_get.return_value = mock_response

        cursor_url = "https://graph.facebook.com/v22.0/next_page?cursor=abc123"
        medias, next_cursor = partnership_ads_booster.fetch_page_of_advertisable_medias(
            mock_access_token,
            mock_ig_account_id,
            cursor=cursor_url,
        )

        assert len(medias) == 1
        assert medias[0]["id"] == "media_789"
        assert next_cursor is None  # No more pages
        # Verify cursor URL was used directly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == cursor_url

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_last_page_no_next_cursor(
        self,
        mock_get,
        mock_access_token,
        mock_ig_account_id,
        sample_media_response,
    ):
        """Test that last page returns None for next_cursor"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_media_response  # No paging.next
        mock_get.return_value = mock_response

        medias, next_cursor = partnership_ads_booster.fetch_page_of_advertisable_medias(
            mock_access_token,
            mock_ig_account_id,
        )

        assert len(medias) == 2
        assert next_cursor is None

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_with_creator_username(
        self,
        mock_get,
        mock_access_token,
        mock_ig_account_id,
        mock_creator_username,
        sample_media_response,
    ):
        """Test that creator_username is passed as parameter"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_media_response
        mock_get.return_value = mock_response

        partnership_ads_booster.fetch_page_of_advertisable_medias(
            mock_access_token,
            mock_ig_account_id,
            creator_username=mock_creator_username,
        )

        call_args = mock_get.call_args
        assert call_args[1]["params"]["creator_username"] == mock_creator_username

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_with_permission_filter(
        self,
        mock_get,
        mock_access_token,
        mock_ig_account_id,
    ):
        """Test that only_with_permission filters results"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "media_1",
                    "permalink": "https://instagram.com/p/1",
                    "owner_id": "owner_1",
                    "has_permission_for_partnership_ad": True,
                    "eligibility_errors": [],
                },
                {
                    "id": "media_2",
                    "permalink": "https://instagram.com/p/2",
                    "owner_id": "owner_2",
                    "has_permission_for_partnership_ad": False,
                    "eligibility_errors": [],
                },
            ],
            "paging": {}
        }
        mock_get.return_value = mock_response

        medias, _ = partnership_ads_booster.fetch_page_of_advertisable_medias(
            mock_access_token,
            mock_ig_account_id,
            only_with_permission=True,
        )

        assert len(medias) == 1
        assert medias[0]["id"] == "media_1"

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_api_error_returns_empty(
        self,
        mock_get,
        mock_access_token,
        mock_ig_account_id,
    ):
        """Test that API errors return empty list and None cursor"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_get.return_value = mock_response

        medias, next_cursor = partnership_ads_booster.fetch_page_of_advertisable_medias(
            mock_access_token,
            mock_ig_account_id,
        )

        assert medias == []
        assert next_cursor is None

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_request_exception_returns_empty(
        self,
        mock_get,
        mock_access_token,
        mock_ig_account_id,
    ):
        """Test that request exceptions return empty list and None cursor"""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        medias, next_cursor = partnership_ads_booster.fetch_page_of_advertisable_medias(
            mock_access_token,
            mock_ig_account_id,
        )

        assert medias == []
        assert next_cursor is None

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_empty_data_returns_empty_list(
        self,
        mock_get,
        mock_access_token,
        mock_ig_account_id,
    ):
        """Test that empty data response returns empty list"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [], "paging": {}}
        mock_get.return_value = mock_response

        medias, next_cursor = partnership_ads_booster.fetch_page_of_advertisable_medias(
            mock_access_token,
            mock_ig_account_id,
        )

        assert medias == []
        assert next_cursor is None


class TestFetchAllAdvertisableMedias:
    """Tests for fetch_all_advertisable_medias function"""

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_fetch_all_advertisable_medias_success(
        self,
        mock_file,
        mock_get,
        mock_access_token,
        mock_ig_account_id,
        mock_creator_username,
        sample_media_response,
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_media_response
        mock_get.return_value = mock_response

        partnership_ads_booster.fetch_all_advertisable_medias(
            mock_access_token,
            mock_ig_account_id,
            mock_creator_username,
            "test_output.csv",
        )

        mock_get.assert_called_once()
        mock_file.assert_called_once_with(
            "test_output.csv", "w", newline="", encoding="utf-8"
        )

        handle = mock_file()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        assert "media_id" in written_content
        assert "media_123" in written_content
        assert "media_456" in written_content

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_fetch_all_advertisable_medias_with_pagination(
        self,
        mock_file,
        mock_get,
        mock_access_token,
        mock_ig_account_id,
        mock_creator_username,
    ):
        first_response = {
            "data": [
                {
                    "id": "media_1",
                    "permalink": "https://instagram.com/p/1",
                    "owner_id": "owner_1",
                    "has_permission_for_partnership_ad": True,
                    "eligibility_errors": [],
                }
            ],
            "paging": {"next": "https://graph.facebook.com/v22.0/next_page"},
        }

        second_response = {
            "data": [
                {
                    "id": "media_2",
                    "permalink": "https://instagram.com/p/2",
                    "owner_id": "owner_2",
                    "has_permission_for_partnership_ad": True,
                    "eligibility_errors": [],
                }
            ],
            "paging": {},
        }

        mock_response_1 = MagicMock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = first_response

        mock_response_2 = MagicMock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = second_response

        mock_get.side_effect = [mock_response_1, mock_response_2]

        partnership_ads_booster.fetch_all_advertisable_medias(
            mock_access_token,
            mock_ig_account_id,
            mock_creator_username,
            "test_output.csv",
        )

        assert mock_get.call_count == 2

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_all_advertisable_medias_api_error(
        self, mock_get, mock_access_token, mock_ig_account_id, mock_creator_username
    ):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_get.return_value = mock_response

        with pytest.raises(SystemExit) as exc_info:
            partnership_ads_booster.fetch_all_advertisable_medias(
                mock_access_token,
                mock_ig_account_id,
                mock_creator_username,
                "test_output.csv",
            )
        assert exc_info.value.code == 1

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_fetch_all_advertisable_medias_no_data(
        self,
        mock_file,
        mock_get,
        mock_access_token,
        mock_ig_account_id,
        mock_creator_username,
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [], "paging": {}}
        mock_get.return_value = mock_response

        partnership_ads_booster.fetch_all_advertisable_medias(
            mock_access_token,
            mock_ig_account_id,
            mock_creator_username,
            "test_output.csv",
        )

        mock_file.assert_not_called()

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_fetch_all_advertisable_medias_without_creator_username(
        self,
        mock_file,
        mock_get,
        mock_access_token,
        mock_ig_account_id,
        sample_media_response,
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_media_response
        mock_get.return_value = mock_response

        partnership_ads_booster.fetch_all_advertisable_medias(
            mock_access_token, mock_ig_account_id, None, "test_output.csv"
        )

        mock_get.assert_called_once()
        # Verify creator_username is not in params when None
        call_args = mock_get.call_args
        assert "creator_username" not in call_args[1]["params"]

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_fetch_all_advertisable_medias_with_limit(
        self,
        mock_file,
        mock_get,
        mock_access_token,
        mock_ig_account_id,
        mock_creator_username,
    ):
        """Test that limit parameter correctly limits the number of fetched medias"""
        # Create response with 5 medias across 2 pages
        first_response = {
            "data": [
                {
                    "id": f"media_{i}",
                    "permalink": f"https://instagram.com/p/{i}",
                    "owner_id": f"owner_{i}",
                    "has_permission_for_partnership_ad": True,
                    "eligibility_errors": [],
                }
                for i in range(3)
            ],
            "paging": {"next": "https://graph.facebook.com/v22.0/next_page"},
        }

        second_response = {
            "data": [
                {
                    "id": f"media_{i}",
                    "permalink": f"https://instagram.com/p/{i}",
                    "owner_id": f"owner_{i}",
                    "has_permission_for_partnership_ad": True,
                    "eligibility_errors": [],
                }
                for i in range(3, 6)
            ],
            "paging": {},
        }

        mock_response_1 = MagicMock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = first_response

        mock_response_2 = MagicMock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = second_response

        mock_get.side_effect = [mock_response_1, mock_response_2]

        # Set limit to 2, should only get 2 medias
        partnership_ads_booster.fetch_all_advertisable_medias(
            mock_access_token,
            mock_ig_account_id,
            mock_creator_username,
            "test_output.csv",
            limit=2,
        )

        # Should only make 1 API call since limit is reached after first response
        assert mock_get.call_count == 1

        # Verify output file was written with limited results
        handle = mock_file()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        # Should contain media_0 and media_1 but not media_2
        assert "media_0" in written_content
        assert "media_1" in written_content
        assert "media_2" not in written_content

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_fetch_all_advertisable_medias_limit_none(
        self,
        mock_file,
        mock_get,
        mock_access_token,
        mock_ig_account_id,
        mock_creator_username,
    ):
        """Test that when limit is None, all medias are fetched"""
        first_response = {
            "data": [
                {
                    "id": "media_1",
                    "permalink": "https://instagram.com/p/1",
                    "owner_id": "owner_1",
                    "has_permission_for_partnership_ad": True,
                    "eligibility_errors": [],
                }
            ],
            "paging": {"next": "https://graph.facebook.com/v22.0/next_page"},
        }

        second_response = {
            "data": [
                {
                    "id": "media_2",
                    "permalink": "https://instagram.com/p/2",
                    "owner_id": "owner_2",
                    "has_permission_for_partnership_ad": True,
                    "eligibility_errors": [],
                }
            ],
            "paging": {},
        }

        mock_response_1 = MagicMock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = first_response

        mock_response_2 = MagicMock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = second_response

        mock_get.side_effect = [mock_response_1, mock_response_2]

        # No limit - should fetch all pages
        partnership_ads_booster.fetch_all_advertisable_medias(
            mock_access_token,
            mock_ig_account_id,
            mock_creator_username,
            "test_output.csv",
            limit=None,
        )

        # Should make 2 API calls to get all pages
        assert mock_get.call_count == 2

        # Verify both medias are in output
        handle = mock_file()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        assert "media_1" in written_content
        assert "media_2" in written_content

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_fetch_all_advertisable_medias_only_with_permission(
        self,
        mock_file,
        mock_get,
        mock_access_token,
        mock_ig_account_id,
        mock_creator_username,
        sample_media_response,
    ):
        """Test that only_with_permission filter excludes medias without permission"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_media_response
        mock_get.return_value = mock_response

        partnership_ads_booster.fetch_all_advertisable_medias(
            mock_access_token,
            mock_ig_account_id,
            mock_creator_username,
            "test_output.csv",
            only_with_permission=True,
        )

        handle = mock_file()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        # media_123 has permission, media_456 does not
        assert "media_123" in written_content
        assert "media_456" not in written_content

    @patch("stats_for_dashboards.partnership_ads_booster.fetch_media_insights")
    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_fetch_all_advertisable_medias_with_engagement_metrics(
        self,
        mock_file,
        mock_get,
        mock_fetch_insights,
        mock_access_token,
        mock_ig_account_id,
        mock_creator_username,
        sample_media_response,
    ):
        """Test that include_engagement_metrics fetches and includes metrics"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_media_response
        mock_get.return_value = mock_response

        # Mock fetch_media_insights to return metrics
        mock_fetch_insights.return_value = {"likes": 100, "comments": 10}

        partnership_ads_booster.fetch_all_advertisable_medias(
            mock_access_token,
            mock_ig_account_id,
            mock_creator_username,
            "test_output.csv",
            include_engagement_metrics=True,
        )

        # Verify fetch_media_insights was called for each media
        assert mock_fetch_insights.call_count == 2

        handle = mock_file()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        # Verify metrics columns are in output
        assert "likes" in written_content
        assert "comments" in written_content

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_fetch_all_advertisable_medias_without_engagement_metrics(
        self,
        mock_file,
        mock_get,
        mock_access_token,
        mock_ig_account_id,
        mock_creator_username,
        sample_media_response,
    ):
        """Test that metrics columns are not included when include_engagement_metrics is False"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_media_response
        mock_get.return_value = mock_response

        partnership_ads_booster.fetch_all_advertisable_medias(
            mock_access_token,
            mock_ig_account_id,
            mock_creator_username,
            "test_output.csv",
            include_engagement_metrics=False,
        )

        handle = mock_file()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)
        # Verify the header row doesn't include likes/comments columns
        lines = written_content.split('\n')
        header = lines[0] if lines else ""
        assert "likes" not in header.split(',')
        assert "comments" not in header.split(',')


class TestFetchBrandedContentAdvertisableMedias:
    """Tests for fetch_branded_content_advertisable_medias function"""

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_with_ad_code_success(
        self, mock_get, mock_access_token, mock_business_id, mock_ig_account_id
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "media_123",
                    "has_permission_for_partnership_ad": True,
                    "eligibility_errors": [],
                }
            ]
        }
        mock_get.return_value = mock_response

        result = partnership_ads_booster.fetch_branded_content_advertisable_medias(
            mock_access_token, mock_business_id, mock_ig_account_id, ad_code="test_ad_code"
        )

        assert result is not None
        assert result["id"] == "media_123"
        assert result["has_permission_for_partnership_ad"] == True

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_with_permalinks_success(
        self, mock_get, mock_access_token, mock_business_id, mock_ig_account_id
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "media_123", "permalink": "https://instagram.com/p/abc123"}]
        }
        mock_get.return_value = mock_response

        result = partnership_ads_booster.fetch_branded_content_advertisable_medias(
            mock_access_token,
            mock_business_id,
            mock_ig_account_id,
            permalinks=["https://instagram.com/p/abc123"],
        )

        assert result is not None
        assert result["id"] == "media_123"

    def test_fetch_without_ad_code_or_permalinks(
        self, mock_access_token, mock_business_id, mock_ig_account_id
    ):
        with pytest.raises(ValueError, match="ad_code, permalinks, or content_ids must be passed"):
            partnership_ads_booster.fetch_branded_content_advertisable_medias(
                mock_access_token, mock_business_id, mock_ig_account_id
            )

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_api_error(self, mock_get, mock_access_token, mock_business_id, mock_ig_account_id):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_get.return_value = mock_response

        result = partnership_ads_booster.fetch_branded_content_advertisable_medias(
            mock_access_token, mock_business_id, mock_ig_account_id, ad_code="test_ad_code"
        )

        assert result == {"error": "Bad Request"}


class TestUploadInstagramVideo:
    """Tests for upload_instagram_video function"""

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_upload_video_success(
        self, mock_post, mock_access_token, mock_ad_account_id
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "video_123"}
        mock_post.return_value = mock_response

        video_id, error = partnership_ads_booster.upload_instagram_video(
            mock_access_token, mock_ad_account_id, "media_123"
        )

        assert video_id == "video_123"
        assert error is None

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_upload_video_with_ad_code(
        self, mock_post, mock_access_token, mock_ad_account_id
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "video_123"}
        mock_post.return_value = mock_response

        video_id, error = partnership_ads_booster.upload_instagram_video(
            mock_access_token, mock_ad_account_id, "media_123", ad_code="test_ad_code"
        )

        assert video_id == "video_123"
        assert error is None
        call_args = mock_post.call_args
        assert call_args[1]["params"]["partnership_ad_ad_code"] == "test_ad_code"
        assert call_args[1]["params"]["is_partnership_ad"] == True

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_upload_video_api_error(
        self, mock_post, mock_access_token, mock_ad_account_id
    ):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        video_id, error = partnership_ads_booster.upload_instagram_video(
            mock_access_token, mock_ad_account_id, "media_123"
        )

        assert video_id is None
        assert "Bad Request" in error


class TestCreateAdCreative:
    """Tests for create_ad_creative function"""

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_success(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            None,
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            "myapp://landing",
        )

        assert creative_id == "creative_123"
        assert error is None

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_product_set(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            None,
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            "myapp://landing",
            product_set_id="product_set_123",
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        assert "degrees_of_freedom_spec" in call_args[1]["params"]

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_api_error(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.json.return_value = {"error": "Bad Request"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            None,
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            "myapp://landing",
        )

        assert creative_id is None
        assert "Bad Request" in error

    def test_create_creative_without_media_or_ad_code(
        self,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        with pytest.raises(
            ValueError, match="ad_code or source_instagram_media_id must be passed"
        ):
            partnership_ads_booster.create_ad_creative(
                mock_access_token,
                mock_ad_account_id,
                mock_facebook_page_id,
                mock_ig_account_id,
                None,
                None,
                "INSTALL_MOBILE_APP",
                "https://app.link/install",
                "myapp://landing",
            )

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_utm_parameters(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that utm_parameters is passed as url_tags"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            None,
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            "myapp://landing",
            None,  # product_set_id
            "utm_source=instagram&utm_medium=paid",  # utm_parameters
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        assert "url_tags" in call_args[1]["params"]
        assert call_args[1]["params"]["url_tags"] == "utm_source=instagram&utm_medium=paid"

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_testimonial_and_ad_code(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that testimonial is included in branded_content when ad_code is provided"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            "test_ad_code",  # ad_code
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            "myapp://landing",
            None,  # product_set_id
            None,  # utm_parameters
            "This product is amazing!",  # testimonial
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        assert "branded_content" in call_args[1]["params"]
        branded_content = json.loads(call_args[1]["params"]["branded_content"])
        assert branded_content["instagram_boost_post_access_token"] == "test_ad_code"
        assert branded_content["testimonial"] == "This product is amazing!"

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_testimonial_without_ad_code(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that testimonial is included in branded_content when only source_instagram_media_id is provided"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            None,  # ad_code
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            "myapp://landing",
            None,  # product_set_id
            None,  # utm_parameters
            "Great experience with this product!",  # testimonial
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        assert "branded_content" in call_args[1]["params"]
        branded_content = json.loads(call_args[1]["params"]["branded_content"])
        assert "instagram_boost_post_access_token" not in branded_content
        assert branded_content["testimonial"] == "Great experience with this product!"

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_all_optional_params(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that all optional parameters (product_set_id, utm_parameters, testimonial, source_url) work together"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            "test_ad_code",
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            "myapp://landing",
            "product_set_123",  # product_set_id
            "utm_source=instagram&utm_medium=paid&utm_campaign=summer",  # utm_parameters
            "Highly recommend this!",  # testimonial
            "https://example.com/source",  # source_url
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        params = call_args[1]["params"]

        # Check utm_parameters
        assert params["url_tags"] == "utm_source=instagram&utm_medium=paid&utm_campaign=summer"

        # Check testimonial in branded_content
        branded_content = json.loads(params["branded_content"])
        assert branded_content["testimonial"] == "Highly recommend this!"
        assert branded_content["instagram_boost_post_access_token"] == "test_ad_code"

        # Check product_set_id and source_url in creative_sourcing_spec
        assert "degrees_of_freedom_spec" in params
        assert "creative_sourcing_spec" in params
        creative_sourcing_spec = json.loads(params["creative_sourcing_spec"])
        assert creative_sourcing_spec["associated_product_set_id"] == "product_set_123"
        assert creative_sourcing_spec["source_url"] == "https://example.com/source"

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_without_optional_params(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that branded_content is not set when no ad_code or testimonial is provided"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            None,  # ad_code
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            "myapp://landing",
            None,  # product_set_id
            None,  # utm_parameters
            None,  # testimonial
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        params = call_args[1]["params"]

        # branded_content should not be set when no ad_code or testimonial
        assert "branded_content" not in params
        assert "url_tags" not in params

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_source_url(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that source_url is included in creative_sourcing_spec"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            None,  # ad_code
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            "myapp://landing",
            None,  # product_set_id
            None,  # utm_parameters
            None,  # testimonial
            "https://example.com/source",  # source_url
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        params = call_args[1]["params"]

        assert "creative_sourcing_spec" in params
        creative_sourcing_spec = json.loads(params["creative_sourcing_spec"])
        assert creative_sourcing_spec["source_url"] == "https://example.com/source"
        assert "associated_product_set_id" not in creative_sourcing_spec

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_source_url_and_product_set(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that source_url and product_set_id are both included in creative_sourcing_spec"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            None,  # ad_code
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            "myapp://landing",
            "product_set_123",  # product_set_id
            None,  # utm_parameters
            None,  # testimonial
            "https://example.com/source",  # source_url
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        params = call_args[1]["params"]

        assert "creative_sourcing_spec" in params
        creative_sourcing_spec = json.loads(params["creative_sourcing_spec"])
        assert creative_sourcing_spec["source_url"] == "https://example.com/source"
        assert creative_sourcing_spec["associated_product_set_id"] == "product_set_123"
        assert "degrees_of_freedom_spec" in params

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_identities_both(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that identities=BOTH sets ad_format=1 in branded_content"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            "test_ad_code",
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            identities="BOTH",
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        params = call_args[1]["params"]
        assert "branded_content" in params
        branded_content = json.loads(params["branded_content"])
        assert branded_content["ad_format"] == 1

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_identities_first(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that identities=FIRST sets ad_format=2 in branded_content"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            "test_ad_code",
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            identities="FIRST",
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        params = call_args[1]["params"]
        assert "branded_content" in params
        branded_content = json.loads(params["branded_content"])
        assert branded_content["ad_format"] == 2

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_identities_dynamic(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that identities=DYNAMIC sets ad_format=3 in branded_content"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            "test_ad_code",
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            identities="DYNAMIC",
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        params = call_args[1]["params"]
        assert "branded_content" in params
        branded_content = json.loads(params["branded_content"])
        assert branded_content["ad_format"] == 3

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_identities_case_insensitive(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that identities values are case insensitive"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        for value in ["dynamic", "Dynamic", "DYNAMIC", " dynamic "]:
            creative_id, error = partnership_ads_booster.create_ad_creative(
                mock_access_token,
                mock_ad_account_id,
                mock_facebook_page_id,
                mock_ig_account_id,
                "media_123",
                "test_ad_code",
                "INSTALL_MOBILE_APP",
                "https://app.link/install",
                identities=value,
            )

            assert creative_id == "creative_123"
            call_args = mock_post.call_args
            branded_content = json.loads(call_args[1]["params"]["branded_content"])
            assert branded_content["ad_format"] == 3, f"Failed for value: '{value}'"

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_identities_and_ad_code(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that ad_format coexists with instagram_boost_post_access_token in branded_content"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            "test_ad_code",
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            testimonial="Great product!",
            identities="FIRST",
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        params = call_args[1]["params"]
        branded_content = json.loads(params["branded_content"])
        assert branded_content["instagram_boost_post_access_token"] == "test_ad_code"
        assert branded_content["testimonial"] == "Great product!"
        assert branded_content["ad_format"] == 2

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_identities_only_no_ad_code(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that branded_content is sent when only identities is provided (no ad_code, no testimonial)"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            None,  # no ad_code
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            identities="DYNAMIC",
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        params = call_args[1]["params"]
        assert "branded_content" in params
        branded_content = json.loads(params["branded_content"])
        assert branded_content["ad_format"] == 3
        assert "instagram_boost_post_access_token" not in branded_content

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_invalid_identities(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that invalid identities values are ignored and ad_format is not set"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            None,  # no ad_code
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            identities="INVALID_VALUE",
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        params = call_args[1]["params"]
        # No branded_content should be set (no ad_code, no testimonial, invalid identities)
        assert "branded_content" not in params

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_multi_advertiser_ads_opt_out(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that multi_advertiser_ads=OPT_OUT sets contextual_multi_ads with enroll_status=OPT_OUT"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            None,  # no ad_code
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            multi_advertiser_ads="OPT_OUT",
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        params = call_args[1]["params"]
        assert "contextual_multi_ads" in params
        contextual_multi_ads = json.loads(params["contextual_multi_ads"])
        assert contextual_multi_ads == {"enroll_status": "OPT_OUT"}

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_multi_advertiser_ads_opt_in(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that multi_advertiser_ads=OPT_IN sets contextual_multi_ads with enroll_status=OPT_IN"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            None,  # no ad_code
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            multi_advertiser_ads="OPT_IN",
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        params = call_args[1]["params"]
        assert "contextual_multi_ads" in params
        contextual_multi_ads = json.loads(params["contextual_multi_ads"])
        assert contextual_multi_ads == {"enroll_status": "OPT_IN"}

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_multi_advertiser_ads_case_insensitive(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that multi_advertiser_ads values are case insensitive"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        test_cases = [
            ("opt_out", "OPT_OUT"),
            ("Opt_Out", "OPT_OUT"),
            (" OPT_OUT ", "OPT_OUT"),
            ("opt_in", "OPT_IN"),
            ("Opt_In", "OPT_IN"),
            (" OPT_IN ", "OPT_IN"),
        ]

        for input_value, expected_status in test_cases:
            mock_post.reset_mock()
            creative_id, error = partnership_ads_booster.create_ad_creative(
                mock_access_token,
                mock_ad_account_id,
                mock_facebook_page_id,
                mock_ig_account_id,
                "media_123",
                None,  # no ad_code
                "INSTALL_MOBILE_APP",
                "https://app.link/install",
                multi_advertiser_ads=input_value,
            )

            assert creative_id == "creative_123"
            assert error is None
            call_args = mock_post.call_args
            params = call_args[1]["params"]
            assert "contextual_multi_ads" in params
            contextual_multi_ads = json.loads(params["contextual_multi_ads"])
            assert contextual_multi_ads == {"enroll_status": expected_status}

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_multi_advertiser_ads_and_other_params(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that multi_advertiser_ads works correctly with other parameters"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            "ad_code_123",  # ad_code
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            testimonial="Great product!",
            identities="FIRST",
            multi_advertiser_ads="OPT_OUT",
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        params = call_args[1]["params"]
        # Check contextual_multi_ads is set
        assert "contextual_multi_ads" in params
        contextual_multi_ads = json.loads(params["contextual_multi_ads"])
        assert contextual_multi_ads == {"enroll_status": "OPT_OUT"}
        # Check branded_content has ad_format from identities
        assert "branded_content" in params
        branded_content = json.loads(params["branded_content"])
        assert branded_content["ad_format"] == 2  # FIRST = 2

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_creative_with_invalid_multi_advertiser_ads(
        self,
        mock_post,
        mock_access_token,
        mock_ad_account_id,
        mock_facebook_page_id,
        mock_ig_account_id,
    ):
        """Test that invalid multi_advertiser_ads values are ignored"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "creative_123"}
        mock_post.return_value = mock_response

        creative_id, error = partnership_ads_booster.create_ad_creative(
            mock_access_token,
            mock_ad_account_id,
            mock_facebook_page_id,
            mock_ig_account_id,
            "media_123",
            None,  # no ad_code
            "INSTALL_MOBILE_APP",
            "https://app.link/install",
            multi_advertiser_ads="INVALID_VALUE",
        )

        assert creative_id == "creative_123"
        assert error is None
        call_args = mock_post.call_args
        params = call_args[1]["params"]
        # contextual_multi_ads should NOT be set for invalid value
        assert "contextual_multi_ads" not in params


class TestCreateAd:
    """Tests for create_ad function"""

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_ad_success(self, mock_post, mock_access_token, mock_ad_account_id):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "ad_123"}
        mock_post.return_value = mock_response

        ad_id, error = partnership_ads_booster.create_ad(
            mock_access_token,
            mock_ad_account_id,
            "Test Ad",
            "adset_123",
            "creative_123",
        )

        assert ad_id == "ad_123"
        assert error is None

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_ad_without_app_id_no_tracking_specs(
        self, mock_post, mock_access_token, mock_ad_account_id
    ):
        """Test that create_ad without app_id does not include tracking_specs"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "ad_123"}
        mock_post.return_value = mock_response

        ad_id, error = partnership_ads_booster.create_ad(
            mock_access_token,
            mock_ad_account_id,
            "Test Ad",
            "adset_123",
            "creative_123",
        )

        assert ad_id == "ad_123"
        assert error is None

        # Verify tracking_specs is NOT in the params
        call_args = mock_post.call_args
        params = call_args.kwargs.get("params", {})
        assert "tracking_specs" not in params

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_ad_with_app_id_includes_tracking_specs(
        self, mock_post, mock_access_token, mock_ad_account_id
    ):
        """Test that create_ad with app_id includes proper tracking_specs for app events"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "ad_123"}
        mock_post.return_value = mock_response

        ad_id, error = partnership_ads_booster.create_ad(
            mock_access_token,
            mock_ad_account_id,
            "Test Ad",
            "adset_123",
            "creative_123",
            app_id="app_456",
        )

        assert ad_id == "ad_123"
        assert error is None

        # Verify tracking_specs is in the params with correct structure
        call_args = mock_post.call_args
        params = call_args.kwargs.get("params", {})
        assert "tracking_specs" in params

        tracking_specs = json.loads(params["tracking_specs"])
        assert len(tracking_specs) == 1
        assert tracking_specs[0]["action.type"] == "app_custom_event"
        assert tracking_specs[0]["application"] == "app_456"

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_create_ad_api_error(
        self, mock_post, mock_access_token, mock_ad_account_id
    ):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.json.return_value = {"error": "Bad Request"}
        mock_post.return_value = mock_response

        ad_id, error = partnership_ads_booster.create_ad(
            mock_access_token,
            mock_ad_account_id,
            "Test Ad",
            "adset_123",
            "creative_123",
        )

        assert ad_id is None
        assert error is not None and "Bad Request" in error


class TestCreatePartnershipAdsFromCsv:
    """Tests for create_partnership_ads_from_csv function"""

    @patch("stats_for_dashboards.partnership_ads_booster.create_ad")
    @patch("stats_for_dashboards.partnership_ads_booster.create_ad_creative")
    @patch("stats_for_dashboards.partnership_ads_booster.upload_instagram_video")
    @patch(
        "stats_for_dashboards.partnership_ads_booster.fetch_branded_content_advertisable_medias"
    )
    @patch("builtins.open", new_callable=mock_open)
    def test_create_partnership_ads_success(
        self,
        mock_file,
        mock_fetch,
        mock_upload,
        mock_creative,
        mock_ad,
        mock_access_token,
        mock_business_id,
        mock_ig_account_id,
        mock_ad_account_id,
        mock_facebook_page_id,
        sample_csv_rows,
    ):
        csv_content = "media_id,permalink,owner_id,has_permission_for_partnership_ad,eligibility_errors,ad_set_id,cta_type,link,app_link,ad_name,ad_code,product_set_id\n"
        csv_content += "media_123,https://instagram.com/p/abc123,owner_123,True,[],adset_123,INSTALL_MOBILE_APP,https://app.link/install,myapp://landing,Test Ad 1,,\n"

        mock_file.return_value.__enter__.return_value = StringIO(csv_content)

        # Mock eligibility check
        mock_fetch.return_value = {
            "id": "media_123",
            "has_permission_for_partnership_ad": True,
            "eligibility_errors": [],
        }

        # Mock functions to return tuples (value, error)
        mock_upload.return_value = ("video_123", None)
        mock_creative.return_value = ("creative_123", None)
        mock_ad.return_value = ("ad_123", None)

        partnership_ads_booster.create_partnership_ads_from_csv(
            mock_access_token,
            mock_business_id,
            mock_ig_account_id,
            mock_ad_account_id,
            mock_facebook_page_id,
            "input.csv",
            "output.csv",
        )

        mock_fetch.assert_called_once()
        mock_upload.assert_called_once()
        mock_creative.assert_called_once()
        mock_ad.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    def test_create_partnership_ads_missing_fields(
        self,
        mock_file,
        mock_access_token,
        mock_business_id,
        mock_ig_account_id,
        mock_ad_account_id,
        mock_facebook_page_id,
    ):
        csv_content = "media_id,permalink,ad_set_id,cta_type,ad_name\n"
        csv_content += "media_123,https://instagram.com/p/abc123,,,Test Ad 1\n"

        mock_file.return_value.__enter__.return_value = StringIO(csv_content)

        partnership_ads_booster.create_partnership_ads_from_csv(
            mock_access_token,
            mock_business_id,
            mock_ig_account_id,
            mock_ad_account_id,
            mock_facebook_page_id,
            "input.csv",
            "output.csv",
        )

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_create_partnership_ads_file_not_found(
        self,
        mock_file,
        mock_access_token,
        mock_business_id,
        mock_ig_account_id,
        mock_ad_account_id,
        mock_facebook_page_id,
    ):
        with pytest.raises(SystemExit) as exc_info:
            partnership_ads_booster.create_partnership_ads_from_csv(
                mock_access_token,
                mock_business_id,
                mock_ig_account_id,
                mock_ad_account_id,
                mock_facebook_page_id,
                "nonexistent.csv",
                "output.csv",
            )
        assert exc_info.value.code == 1

    @patch("builtins.open", new_callable=mock_open)
    def test_create_partnership_ads_with_stories_url(
        self,
        mock_file,
        mock_access_token,
        mock_business_id,
        mock_ig_account_id,
        mock_ad_account_id,
        mock_facebook_page_id,
    ):
        csv_content = "permalink,cta_type,link,app_link,ad_name,ad_set_id,ad_code,product_set_id\n"
        csv_content += "https://www.instagram.com/stories/username/123456/,INSTALL_MOBILE_APP,https://app.link,myapp://landing,Test Ad,adset_123,,,\n"

        mock_file.return_value.__enter__.return_value = StringIO(csv_content)

        partnership_ads_booster.create_partnership_ads_from_csv(
            mock_access_token,
            mock_business_id,
            mock_ig_account_id,
            mock_ad_account_id,
            mock_facebook_page_id,
            "input.csv",
            "output.csv",
        )


class TestMain:
    """Tests for main function"""

    @patch("stats_for_dashboards.partnership_ads_booster.fetch_all_advertisable_medias")
    @patch(
        "sys.argv",
        [
            "partnership_ads_booster.py",
            "--mode",
            "fetch",
            "--access-token",
            "test_token",
            "--ig-account-id",
            "123456",
            "--business-id",
            "999999",
            "--creator-username",
            "test_creator",
        ],
    )
    def test_main_fetch_mode(self, mock_fetch):
        partnership_ads_booster.main()
        mock_fetch.assert_called_once()

    @patch(
        "stats_for_dashboards.partnership_ads_booster.create_partnership_ads_from_csv"
    )
    @patch(
        "sys.argv",
        [
            "partnership_ads_booster.py",
            "--mode",
            "create",
            "--access-token",
            "test_token",
            "--ig-account-id",
            "123456",
            "--business-id",
            "999999",
            "--ad-account-id",
            "789",
            "--facebook-page-id",
            "999",
            "--input-csv",
            "input.csv",
        ],
    )
    def test_main_create_mode(self, mock_create):
        partnership_ads_booster.main()
        mock_create.assert_called_once()

    @patch(
        "sys.argv",
        [
            "partnership_ads_booster.py",
            "--mode",
            "create",
            "--access-token",
            "test_token",
            "--ig-account-id",
            "123456",
            "--business-id",
            "999999",
        ],
    )
    def test_main_create_mode_missing_args(self):
        with pytest.raises(SystemExit) as exc_info:
            partnership_ads_booster.main()
        assert exc_info.value.code == 1

    @patch("stats_for_dashboards.partnership_ads_booster.fetch_all_advertisable_medias")
    @patch(
        "sys.argv",
        [
            "partnership_ads_booster.py",
            "--mode",
            "fetch",
            "--access-token",
            "test_token",
            "--ig-account-id",
            "123456",
            "--business-id",
            "999999",
            "--only-with-permission",
        ],
    )
    def test_main_fetch_mode_with_only_permission_flag(self, mock_fetch):
        """Test that --only-with-permission flag is passed correctly"""
        partnership_ads_booster.main()
        mock_fetch.assert_called_once()
        call_kwargs = mock_fetch.call_args[1]
        assert call_kwargs["only_with_permission"] == True

    @patch("stats_for_dashboards.partnership_ads_booster.fetch_all_advertisable_medias")
    @patch(
        "sys.argv",
        [
            "partnership_ads_booster.py",
            "--mode",
            "fetch",
            "--access-token",
            "test_token",
            "--ig-account-id",
            "123456",
            "--business-id",
            "999999",
            "--include-metrics",
        ],
    )
    def test_main_fetch_mode_with_include_metrics_flag(self, mock_fetch):
        """Test that --include-metrics flag is passed correctly"""
        partnership_ads_booster.main()
        mock_fetch.assert_called_once()
        call_kwargs = mock_fetch.call_args[1]
        assert call_kwargs["include_engagement_metrics"] == True

    @patch("stats_for_dashboards.partnership_ads_booster.fetch_all_advertisable_medias")
    @patch(
        "sys.argv",
        [
            "partnership_ads_booster.py",
            "--mode",
            "fetch",
            "--access-token",
            "test_token",
            "--ig-account-id",
            "123456",
            "--business-id",
            "999999",
            "--only-with-permission",
            "--include-metrics",
        ],
    )
    def test_main_fetch_mode_with_both_flags(self, mock_fetch):
        """Test that both flags can be used together"""
        partnership_ads_booster.main()
        mock_fetch.assert_called_once()
        call_kwargs = mock_fetch.call_args[1]
        assert call_kwargs["only_with_permission"] == True
        assert call_kwargs["include_engagement_metrics"] == True


class TestFetchAccountLevelPermissions:
    """Tests for fetch_account_level_permissions function"""

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_permissions_success(self, mock_get, mock_access_token, mock_ig_account_id):
        """Test successful fetch of account level permissions"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "123",
                    "creator_ig_id": "17841401234567890",
                    "creator_username": "creator1",
                    "permission_status": "approved",
                },
                {
                    "id": "456",
                    "creator_ig_id": "17841409876543210",
                    "creator_username": "creator2",
                    "permission_status": "pending",
                },
            ]
        }
        mock_get.return_value = mock_response

        result = partnership_ads_booster.fetch_account_level_permissions(
            mock_access_token, mock_ig_account_id
        )

        assert len(result) == 2
        assert result[0]["creator_username"] == "creator1"
        assert result[1]["permission_status"] == "pending"

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_permissions_with_pagination(self, mock_get, mock_access_token, mock_ig_account_id):
        """Test fetch permissions with pagination"""
        first_response = MagicMock()
        first_response.status_code = 200
        first_response.json.return_value = {
            "data": [
                {"id": "1", "creator_ig_id": "111", "creator_username": "user1", "permission_status": "approved"}
            ],
            "paging": {"next": "https://graph.facebook.com/next_page"}
        }

        second_response = MagicMock()
        second_response.status_code = 200
        second_response.json.return_value = {
            "data": [
                {"id": "2", "creator_ig_id": "222", "creator_username": "user2", "permission_status": "approved"}
            ]
        }

        mock_get.side_effect = [first_response, second_response]

        result = partnership_ads_booster.fetch_account_level_permissions(
            mock_access_token, mock_ig_account_id
        )

        assert len(result) == 2
        assert mock_get.call_count == 2

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_permissions_api_error(self, mock_get, mock_access_token, mock_ig_account_id):
        """Test fetch permissions with API error"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_get.return_value = mock_response

        result = partnership_ads_booster.fetch_account_level_permissions(
            mock_access_token, mock_ig_account_id
        )

        assert result == []

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_permissions_writes_csv(self, mock_get, mock_access_token, mock_ig_account_id, tmp_path):
        """Test fetch permissions writes to CSV file"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "123",
                    "creator_ig_id": "17841401234567890",
                    "creator_username": "creator1",
                    "permission_status": "approved",
                }
            ]
        }
        mock_get.return_value = mock_response

        output_file = tmp_path / "permissions.csv"
        result = partnership_ads_booster.fetch_account_level_permissions(
            mock_access_token, mock_ig_account_id, str(output_file)
        )

        assert output_file.exists()
        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["creator_username"] == "creator1"

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_permissions_empty_response(self, mock_get, mock_access_token, mock_ig_account_id):
        """Test fetch permissions with empty response"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_get.return_value = mock_response

        result = partnership_ads_booster.fetch_account_level_permissions(
            mock_access_token, mock_ig_account_id
        )

        assert result == []

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_permissions_request_exception(self, mock_get, mock_access_token, mock_ig_account_id):
        """Test fetch permissions handles request exceptions"""
        mock_get.side_effect = partnership_ads_booster.requests.exceptions.RequestException("Connection error")

        result = partnership_ads_booster.fetch_account_level_permissions(
            mock_access_token, mock_ig_account_id
        )

        assert result == []

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_permissions_csv_only_contains_required_columns(self, mock_get, mock_access_token, mock_ig_account_id, tmp_path):
        """Test that CSV output only contains the required columns, not 'id'"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "123",
                    "creator_ig_id": "17841401234567890",
                    "creator_username": "creator1",
                    "permission_status": "approved",
                    "extra_field": "should_be_ignored",
                }
            ]
        }
        mock_get.return_value = mock_response

        output_file = tmp_path / "permissions.csv"
        partnership_ads_booster.fetch_account_level_permissions(
            mock_access_token, mock_ig_account_id, str(output_file)
        )

        with open(output_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert "id" not in rows[0]
            assert "extra_field" not in rows[0]
            assert "creator_ig_id" in rows[0]
            assert "creator_username" in rows[0]
            assert "permission_status" in rows[0]


class TestRequestAccountLevelPermission:
    """Tests for request_account_level_permission function"""

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_request_permission_with_account_id_success(self, mock_post, mock_access_token, mock_ig_account_id):
        """Test successful permission request with account ID"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        result = partnership_ads_booster.request_account_level_permission(
            mock_access_token,
            mock_ig_account_id,
            creator_instagram_account="17841401234567890"
        )

        assert result["success"] == True
        assert result["error"] is None

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_request_permission_with_username_success(self, mock_post, mock_access_token, mock_ig_account_id):
        """Test successful permission request with username"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        result = partnership_ads_booster.request_account_level_permission(
            mock_access_token,
            mock_ig_account_id,
            creator_instagram_username="creator_handle"
        )

        assert result["success"] == True
        # Verify the correct field was sent
        call_kwargs = mock_post.call_args
        assert "creator_instagram_username" in call_kwargs[1]["json"]

    def test_request_permission_missing_both_identifiers(self, mock_access_token, mock_ig_account_id):
        """Test permission request fails when both identifiers are missing"""
        result = partnership_ads_booster.request_account_level_permission(
            mock_access_token,
            mock_ig_account_id
        )

        assert result["success"] == False
        assert "Either creator_instagram_account or creator_instagram_username is required" in result["error"]

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_request_permission_api_error(self, mock_post, mock_access_token, mock_ig_account_id):
        """Test permission request with API error"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"error":{"message":"Invalid creator instagram account","code":100}}'
        mock_post.return_value = mock_response

        result = partnership_ads_booster.request_account_level_permission(
            mock_access_token,
            mock_ig_account_id,
            creator_instagram_account="invalid_id"
        )

        assert result["success"] == False
        assert "Invalid creator instagram account" in result["error"]

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_request_permission_prefers_account_id_over_username(self, mock_post, mock_access_token, mock_ig_account_id):
        """Test that account ID is preferred when both are provided"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        partnership_ads_booster.request_account_level_permission(
            mock_access_token,
            mock_ig_account_id,
            creator_instagram_account="17841401234567890",
            creator_instagram_username="creator_handle"
        )

        call_kwargs = mock_post.call_args
        json_data = call_kwargs[1]["json"]
        assert "creator_instagram_account" in json_data
        assert "creator_instagram_username" not in json_data

    @patch("stats_for_dashboards.partnership_ads_booster.requests.post")
    def test_request_permission_request_exception(self, mock_post, mock_access_token, mock_ig_account_id):
        """Test request permission handles request exceptions"""
        mock_post.side_effect = partnership_ads_booster.requests.exceptions.RequestException("Connection error")

        result = partnership_ads_booster.request_account_level_permission(
            mock_access_token,
            mock_ig_account_id,
            creator_instagram_account="17841401234567890"
        )

        assert result["success"] == False
        assert "Connection error" in result["error"]


class TestBulkRequestAccountLevelPermissions:
    """Tests for bulk_request_account_level_permissions function"""

    @patch("stats_for_dashboards.partnership_ads_booster.request_account_level_permission")
    def test_bulk_request_success(self, mock_request, mock_access_token, mock_ig_account_id, tmp_path):
        """Test successful bulk permission request"""
        mock_request.return_value = {"success": True, "error": None}

        input_csv = tmp_path / "input.csv"
        output_csv = tmp_path / "output.csv"

        with open(input_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["creator_instagram_account", "creator_instagram_username"])
            writer.writerow(["17841401234567890", "creator1"])
            writer.writerow(["17841409876543210", "creator2"])

        partnership_ads_booster.bulk_request_account_level_permissions(
            mock_access_token,
            mock_ig_account_id,
            str(input_csv),
            str(output_csv)
        )

        assert output_csv.exists()
        with open(output_csv, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert all(row["status"] == "success" for row in rows)

    @patch("stats_for_dashboards.partnership_ads_booster.request_account_level_permission")
    def test_bulk_request_with_username_only(self, mock_request, mock_access_token, mock_ig_account_id, tmp_path):
        """Test bulk request with only usernames"""
        mock_request.return_value = {"success": True, "error": None}

        input_csv = tmp_path / "input.csv"
        output_csv = tmp_path / "output.csv"

        with open(input_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["creator_instagram_username"])
            writer.writerow(["creator1"])
            writer.writerow(["creator2"])

        partnership_ads_booster.bulk_request_account_level_permissions(
            mock_access_token,
            mock_ig_account_id,
            str(input_csv),
            str(output_csv)
        )

        assert mock_request.call_count == 2

    def test_bulk_request_exceeds_limit(self, mock_access_token, mock_ig_account_id, tmp_path, capsys):
        """Test bulk request fails when exceeding 100 row limit"""
        input_csv = tmp_path / "input.csv"
        output_csv = tmp_path / "output.csv"

        with open(input_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["creator_instagram_username"])
            for i in range(101):
                writer.writerow([f"creator{i}"])

        partnership_ads_booster.bulk_request_account_level_permissions(
            mock_access_token,
            mock_ig_account_id,
            str(input_csv),
            str(output_csv)
        )

        captured = capsys.readouterr()
        assert "exceeds the limit of 100" in captured.out
        assert not output_csv.exists()

    def test_bulk_request_empty_csv(self, mock_access_token, mock_ig_account_id, tmp_path, capsys):
        """Test bulk request with empty CSV"""
        input_csv = tmp_path / "input.csv"
        output_csv = tmp_path / "output.csv"

        with open(input_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["creator_instagram_username"])

        partnership_ads_booster.bulk_request_account_level_permissions(
            mock_access_token,
            mock_ig_account_id,
            str(input_csv),
            str(output_csv)
        )

        captured = capsys.readouterr()
        assert "No data found" in captured.out

    @patch("stats_for_dashboards.partnership_ads_booster.request_account_level_permission")
    def test_bulk_request_missing_identifiers(self, mock_request, mock_access_token, mock_ig_account_id, tmp_path):
        """Test bulk request skips rows with missing identifiers"""
        mock_request.return_value = {"success": True, "error": None}

        input_csv = tmp_path / "input.csv"
        output_csv = tmp_path / "output.csv"

        with open(input_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["creator_instagram_account", "creator_instagram_username"])
            writer.writerow(["", ""])  # Missing both
            writer.writerow(["17841401234567890", ""])  # Has account ID

        partnership_ads_booster.bulk_request_account_level_permissions(
            mock_access_token,
            mock_ig_account_id,
            str(input_csv),
            str(output_csv)
        )

        with open(output_csv, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 2
            assert rows[0]["status"] == "failed"
            assert "Either creator_instagram_account or creator_instagram_username is required" in rows[0]["error"]
            assert rows[1]["status"] == "success"

    @patch("stats_for_dashboards.partnership_ads_booster.request_account_level_permission")
    def test_bulk_request_handles_utf8_bom(self, mock_request, mock_access_token, mock_ig_account_id, tmp_path):
        """Test bulk request handles UTF-8 BOM in CSV files"""
        mock_request.return_value = {"success": True, "error": None}

        input_csv = tmp_path / "input.csv"
        output_csv = tmp_path / "output.csv"

        # Write with UTF-8 BOM
        with open(input_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["creator_instagram_username"])
            writer.writerow(["creator1"])

        partnership_ads_booster.bulk_request_account_level_permissions(
            mock_access_token,
            mock_ig_account_id,
            str(input_csv),
            str(output_csv)
        )

        # Verify it was called with the correct username (no BOM prefix)
        call_kwargs = mock_request.call_args
        assert call_kwargs[1].get("creator_instagram_username") == "creator1"

    @patch("stats_for_dashboards.partnership_ads_booster.request_account_level_permission")
    def test_bulk_request_partial_failures(self, mock_request, mock_access_token, mock_ig_account_id, tmp_path):
        """Test bulk request with some failures"""
        mock_request.side_effect = [
            {"success": True, "error": None},
            {"success": False, "error": "Invalid account"},
            {"success": True, "error": None},
        ]

        input_csv = tmp_path / "input.csv"
        output_csv = tmp_path / "output.csv"

        with open(input_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["creator_instagram_username"])
            writer.writerow(["creator1"])
            writer.writerow(["invalid_creator"])
            writer.writerow(["creator3"])

        partnership_ads_booster.bulk_request_account_level_permissions(
            mock_access_token,
            mock_ig_account_id,
            str(input_csv),
            str(output_csv)
        )

        with open(output_csv, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 3
            assert rows[0]["status"] == "success"
            assert rows[1]["status"] == "failed"
            assert rows[1]["error"] == "Invalid account"
            assert rows[2]["status"] == "success"

    def test_bulk_request_file_not_found(self, mock_access_token, mock_ig_account_id, capsys):
        """Test bulk request with non-existent file"""
        partnership_ads_booster.bulk_request_account_level_permissions(
            mock_access_token,
            mock_ig_account_id,
            "non_existent_file.csv",
            "output.csv"
        )

        captured = capsys.readouterr()
        assert "not found" in captured.out

    @patch("stats_for_dashboards.partnership_ads_booster.request_account_level_permission")
    def test_bulk_request_at_limit(self, mock_request, mock_access_token, mock_ig_account_id, tmp_path):
        """Test bulk request exactly at the 100 row limit"""
        mock_request.return_value = {"success": True, "error": None}

        input_csv = tmp_path / "input.csv"
        output_csv = tmp_path / "output.csv"

        with open(input_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["creator_instagram_username"])
            for i in range(100):
                writer.writerow([f"creator{i}"])

        partnership_ads_booster.bulk_request_account_level_permissions(
            mock_access_token,
            mock_ig_account_id,
            str(input_csv),
            str(output_csv)
        )

        assert output_csv.exists()
        assert mock_request.call_count == 100
