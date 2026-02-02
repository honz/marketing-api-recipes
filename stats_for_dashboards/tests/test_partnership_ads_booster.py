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
        self, mock_get, mock_access_token, mock_ig_account_id
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
            mock_access_token, mock_ig_account_id, ad_code="test_ad_code"
        )

        assert result is not None
        assert result["id"] == "media_123"
        assert result["has_permission_for_partnership_ad"] == True

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_with_permalinks_success(
        self, mock_get, mock_access_token, mock_ig_account_id
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"id": "media_123", "permalink": "https://instagram.com/p/abc123"}]
        }
        mock_get.return_value = mock_response

        result = partnership_ads_booster.fetch_branded_content_advertisable_medias(
            mock_access_token,
            mock_ig_account_id,
            permalinks=["https://instagram.com/p/abc123"],
        )

        assert result is not None
        assert result["id"] == "media_123"

    def test_fetch_without_ad_code_or_permalinks(
        self, mock_access_token, mock_ig_account_id
    ):
        with pytest.raises(ValueError, match="ad_code or permalinks must be passed"):
            partnership_ads_booster.fetch_branded_content_advertisable_medias(
                mock_access_token, mock_ig_account_id
            )

    @patch("stats_for_dashboards.partnership_ads_booster.requests.get")
    def test_fetch_api_error(self, mock_get, mock_access_token, mock_ig_account_id):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_get.return_value = mock_response

        result = partnership_ads_booster.fetch_branded_content_advertisable_medias(
            mock_access_token, mock_ig_account_id, ad_code="test_ad_code"
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
        """Test that all optional parameters (product_set_id, utm_parameters, testimonial) work together"""
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

        # Check product_set_id
        assert "degrees_of_freedom_spec" in params
        assert "creative_sourcing_spec" in params

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
        assert "Bad Request" in error


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
        mock_ig_account_id,
        mock_ad_account_id,
        mock_facebook_page_id,
    ):
        csv_content = "media_id,permalink,ad_set_id,cta_type,ad_name\n"
        csv_content += "media_123,https://instagram.com/p/abc123,,,Test Ad 1\n"

        mock_file.return_value.__enter__.return_value = StringIO(csv_content)

        partnership_ads_booster.create_partnership_ads_from_csv(
            mock_access_token,
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
        mock_ig_account_id,
        mock_ad_account_id,
        mock_facebook_page_id,
    ):
        with pytest.raises(SystemExit) as exc_info:
            partnership_ads_booster.create_partnership_ads_from_csv(
                mock_access_token,
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
        mock_ig_account_id,
        mock_ad_account_id,
        mock_facebook_page_id,
    ):
        csv_content = "permalink,cta_type,link,app_link,ad_name,ad_set_id,ad_code,product_set_id\n"
        csv_content += "https://www.instagram.com/stories/username/123456/,INSTALL_MOBILE_APP,https://app.link,myapp://landing,Test Ad,adset_123,,,\n"

        mock_file.return_value.__enter__.return_value = StringIO(csv_content)

        partnership_ads_booster.create_partnership_ads_from_csv(
            mock_access_token,
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
