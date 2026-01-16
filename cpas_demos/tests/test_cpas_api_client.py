"""
Tests for CPAS API Client

Unit tests for the shared CPAS API client functions.
Follows patterns from test_partnership_ads_booster.py.
"""

import unittest
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.cpas_api_client import (
    make_api_request,
    send_collaboration_request,
    get_collaboration_requests,
    accept_collaboration_request,
    reject_collaboration_request,
    get_suggested_partners,
    get_owned_catalog_segments,
    get_shared_catalog_segments,
    share_catalog_segment,
    create_ad_account,
    get_ad_accounts,
    create_campaign,
    create_ad_set,
    get_business_info,
    validate_access_token,
    create_cpas_campaign_with_ad_set,
)
from shared.constants import CollabRequestStatus, CampaignObjective


class TestMakeApiRequest(unittest.TestCase):
    """Tests for the generic API request wrapper."""

    @patch("shared.cpas_api_client.requests.get")
    def test_get_request_success(self, mock_get):
        """Test successful GET request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "123"}]}
        mock_get.return_value = mock_response

        result, error = make_api_request("test_token", "123/test_endpoint")

        self.assertIsNone(error)
        self.assertIsNotNone(result)
        self.assertEqual(result["data"][0]["id"], "123")

    @patch("shared.cpas_api_client.requests.post")
    def test_post_request_success(self, mock_post):
        """Test successful POST request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "new_123"}
        mock_post.return_value = mock_response

        result, error = make_api_request(
            "test_token", "123/test_endpoint", method="POST", params={"name": "test"}
        )

        self.assertIsNone(error)
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "new_123")

    @patch("shared.cpas_api_client.requests.get")
    def test_api_error_handling(self, mock_get):
        """Test API error response handling."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "code": 100,
                "message": "Invalid parameter",
            }
        }
        mock_response.text = "Error text"
        mock_get.return_value = mock_response

        result, error = make_api_request("test_token", "123/test_endpoint")

        self.assertIsNone(result)
        self.assertIsNotNone(error)
        self.assertIn("100", error)
        self.assertIn("Invalid parameter", error)

    @patch("shared.cpas_api_client.requests.get")
    def test_request_exception_handling(self, mock_get):
        """Test handling of request exceptions."""
        mock_get.side_effect = Exception("Connection error")

        result, error = make_api_request("test_token", "123/test_endpoint")

        self.assertIsNone(result)
        self.assertIsNotNone(error)
        self.assertIn("Connection error", error)


class TestCollaborationRequests(unittest.TestCase):
    """Tests for collaboration request functions."""

    @patch("shared.cpas_api_client.make_api_request")
    def test_send_collaboration_request_success(self, mock_api):
        """Test sending collaboration request successfully."""
        mock_api.return_value = ({"id": "request_123"}, None)

        request_id, error = send_collaboration_request(
            "test_token",
            "brand_bm_123",
            "merchant_bm_456",
            "test@example.com",
            "Test User",
        )

        self.assertIsNone(error)
        self.assertEqual(request_id, "request_123")

        # Verify API was called with correct parameters
        mock_api.assert_called_once()
        call_args = mock_api.call_args
        self.assertEqual(call_args[0][1], "brand_bm_123/collaborative_ads_collaboration_requests")

    @patch("shared.cpas_api_client.make_api_request")
    def test_send_collaboration_request_failure(self, mock_api):
        """Test handling of failed collaboration request."""
        mock_api.return_value = (None, "API Error: Invalid business ID")

        request_id, error = send_collaboration_request(
            "test_token",
            "invalid_bm",
            "merchant_bm_456",
            "test@example.com",
            "Test User",
        )

        self.assertIsNone(request_id)
        self.assertIn("Invalid business ID", error)

    @patch("shared.cpas_api_client.make_api_request")
    def test_get_collaboration_requests_success(self, mock_api):
        """Test getting collaboration requests."""
        mock_api.return_value = (
            {
                "data": [
                    {"id": "req_1", "request_status": "PENDING"},
                    {"id": "req_2", "request_status": "APPROVED"},
                ]
            },
            None,
        )

        requests, error = get_collaboration_requests("test_token", "bm_123")

        self.assertIsNone(error)
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0]["id"], "req_1")

    @patch("shared.cpas_api_client.make_api_request")
    def test_get_collaboration_requests_with_status_filter(self, mock_api):
        """Test getting requests with status filter."""
        mock_api.return_value = ({"data": [{"id": "req_1", "request_status": "PENDING"}]}, None)

        requests, error = get_collaboration_requests(
            "test_token", "bm_123", status=CollabRequestStatus.PENDING
        )

        self.assertIsNone(error)
        self.assertEqual(len(requests), 1)

        # Verify status was passed to API
        call_args = mock_api.call_args
        self.assertIn("status", call_args[1]["params"])

    @patch("shared.cpas_api_client.make_api_request")
    def test_accept_collaboration_request_success(self, mock_api):
        """Test accepting a collaboration request."""
        mock_api.return_value = ({"success": True}, None)

        success, error = accept_collaboration_request("test_token", "req_123")

        self.assertTrue(success)
        self.assertIsNone(error)

    @patch("shared.cpas_api_client.make_api_request")
    def test_reject_collaboration_request_success(self, mock_api):
        """Test rejecting a collaboration request."""
        mock_api.return_value = ({"success": True}, None)

        success, error = reject_collaboration_request("test_token", "req_123")

        self.assertTrue(success)
        self.assertIsNone(error)


class TestCatalogSegments(unittest.TestCase):
    """Tests for catalog segment functions."""

    @patch("shared.cpas_api_client.make_api_request")
    def test_get_owned_catalog_segments_success(self, mock_api):
        """Test getting owned catalog segments."""
        mock_api.return_value = (
            {
                "data": [
                    {"id": "cat_1", "name": "Electronics", "product_count": 1000},
                    {"id": "cat_2", "name": "Fashion", "product_count": 2000},
                ]
            },
            None,
        )

        catalogs, error = get_owned_catalog_segments("test_token", "bm_123")

        self.assertIsNone(error)
        self.assertEqual(len(catalogs), 2)
        self.assertEqual(catalogs[0]["name"], "Electronics")

    @patch("shared.cpas_api_client.make_api_request")
    def test_get_shared_catalog_segments_success(self, mock_api):
        """Test getting shared catalog segments."""
        mock_api.return_value = (
            {"data": [{"id": "cat_shared_1", "name": "Brand Products"}]},
            None,
        )

        catalogs, error = get_shared_catalog_segments("test_token", "bm_123")

        self.assertIsNone(error)
        self.assertEqual(len(catalogs), 1)

    @patch("shared.cpas_api_client.make_api_request")
    def test_share_catalog_segment_success(self, mock_api):
        """Test sharing a catalog segment."""
        mock_api.return_value = ({"success": True}, None)

        success, error = share_catalog_segment("test_token", "cat_123", "brand_bm_456")

        self.assertTrue(success)
        self.assertIsNone(error)


class TestAdAccountOperations(unittest.TestCase):
    """Tests for ad account functions."""

    @patch("shared.cpas_api_client.make_api_request")
    def test_create_ad_account_success(self, mock_api):
        """Test creating an ad account."""
        mock_api.return_value = ({"id": "act_123456"}, None)

        account_id, error = create_ad_account(
            "test_token",
            "bm_123",
            "CPAS - Test Campaign",
        )

        self.assertIsNone(error)
        self.assertEqual(account_id, "act_123456")

    @patch("shared.cpas_api_client.make_api_request")
    def test_create_ad_account_with_custom_settings(self, mock_api):
        """Test creating ad account with custom timezone and currency."""
        mock_api.return_value = ({"id": "act_789"}, None)

        account_id, error = create_ad_account(
            "test_token",
            "bm_123",
            "Test Account",
            timezone_id=1,  # Pacific
            currency="USD",
        )

        self.assertIsNone(error)
        self.assertEqual(account_id, "act_789")

        # Verify custom settings were passed
        call_args = mock_api.call_args
        params = call_args[1]["params"]
        self.assertEqual(params["timezone_id"], 1)
        self.assertEqual(params["currency"], "USD")

    @patch("shared.cpas_api_client.make_api_request")
    def test_get_ad_accounts_success(self, mock_api):
        """Test getting ad accounts."""
        mock_api.return_value = (
            {
                "data": [
                    {"id": "act_111", "name": "Account 1"},
                    {"id": "act_222", "name": "Account 2"},
                ]
            },
            None,
        )

        accounts, error = get_ad_accounts("test_token", "bm_123")

        self.assertIsNone(error)
        self.assertEqual(len(accounts), 2)


class TestCampaignOperations(unittest.TestCase):
    """Tests for campaign functions."""

    @patch("shared.cpas_api_client.make_api_request")
    def test_create_campaign_success(self, mock_api):
        """Test creating a campaign."""
        mock_api.return_value = ({"id": "camp_123"}, None)

        campaign_id, error = create_campaign(
            "test_token",
            "act_123",
            "Test Campaign",
        )

        self.assertIsNone(error)
        self.assertEqual(campaign_id, "camp_123")

    @patch("shared.cpas_api_client.make_api_request")
    def test_create_campaign_adds_act_prefix(self, mock_api):
        """Test that act_ prefix is added if missing."""
        mock_api.return_value = ({"id": "camp_123"}, None)

        create_campaign("test_token", "123456", "Test Campaign")

        call_args = mock_api.call_args
        self.assertTrue(call_args[0][1].startswith("act_"))

    @patch("shared.cpas_api_client.make_api_request")
    def test_create_ad_set_success(self, mock_api):
        """Test creating an ad set."""
        mock_api.return_value = ({"id": "adset_123"}, None)

        ad_set_id, error = create_ad_set(
            "test_token",
            "act_123",
            "camp_456",
            "Test Ad Set",
            "cat_segment_789",
        )

        self.assertIsNone(error)
        self.assertEqual(ad_set_id, "adset_123")

    @patch("shared.cpas_api_client.make_api_request")
    def test_create_ad_set_with_targeting(self, mock_api):
        """Test creating ad set with custom targeting."""
        mock_api.return_value = ({"id": "adset_123"}, None)

        targeting = {"geo_locations": {"countries": ["US", "GB"]}}

        ad_set_id, error = create_ad_set(
            "test_token",
            "act_123",
            "camp_456",
            "Test Ad Set",
            "cat_segment_789",
            targeting=targeting,
        )

        self.assertIsNone(error)

        # Verify targeting was passed
        call_args = mock_api.call_args
        params = call_args[1]["params"]
        self.assertEqual(params["targeting"]["geo_locations"]["countries"], ["US", "GB"])


class TestFullFlowHelpers(unittest.TestCase):
    """Tests for full flow helper functions."""

    @patch("shared.cpas_api_client.create_ad_set")
    @patch("shared.cpas_api_client.create_campaign")
    def test_create_cpas_campaign_with_ad_set_success(self, mock_campaign, mock_adset):
        """Test creating complete CPAS campaign with ad set."""
        mock_campaign.return_value = ("camp_123", None)
        mock_adset.return_value = ("adset_456", None)

        result, error = create_cpas_campaign_with_ad_set(
            "test_token",
            "act_123",
            "cat_789",
            "Test Campaign",
            "Test Ad Set",
        )

        self.assertIsNone(error)
        self.assertIsNotNone(result)
        self.assertEqual(result["campaign_id"], "camp_123")
        self.assertEqual(result["ad_set_id"], "adset_456")

    @patch("shared.cpas_api_client.create_ad_set")
    @patch("shared.cpas_api_client.create_campaign")
    def test_create_cpas_campaign_campaign_fails(self, mock_campaign, mock_adset):
        """Test handling when campaign creation fails."""
        mock_campaign.return_value = (None, "Failed to create campaign")

        result, error = create_cpas_campaign_with_ad_set(
            "test_token",
            "act_123",
            "cat_789",
            "Test Campaign",
            "Test Ad Set",
        )

        self.assertIsNone(result)
        self.assertIn("Failed to create campaign", error)
        mock_adset.assert_not_called()

    @patch("shared.cpas_api_client.create_ad_set")
    @patch("shared.cpas_api_client.create_campaign")
    def test_create_cpas_campaign_adset_fails(self, mock_campaign, mock_adset):
        """Test handling when ad set creation fails after campaign success."""
        mock_campaign.return_value = ("camp_123", None)
        mock_adset.return_value = (None, "Failed to create ad set")

        result, error = create_cpas_campaign_with_ad_set(
            "test_token",
            "act_123",
            "cat_789",
            "Test Campaign",
            "Test Ad Set",
        )

        self.assertIsNone(result)
        self.assertIn("camp_123", error)
        self.assertIn("Failed to create ad set", error)


class TestBusinessInfo(unittest.TestCase):
    """Tests for business info functions."""

    @patch("shared.cpas_api_client.make_api_request")
    def test_get_business_info_success(self, mock_api):
        """Test getting business info."""
        mock_api.return_value = (
            {"id": "bm_123", "name": "Test Business"},
            None,
        )

        info, error = get_business_info("test_token", "bm_123")

        self.assertIsNone(error)
        self.assertEqual(info["name"], "Test Business")

    @patch("shared.cpas_api_client.make_api_request")
    def test_validate_access_token_success(self, mock_api):
        """Test validating access token."""
        mock_api.return_value = (
            {"id": "user_123", "name": "Test User"},
            None,
        )

        info, error = validate_access_token("test_token")

        self.assertIsNone(error)
        self.assertEqual(info["name"], "Test User")


if __name__ == "__main__":
    unittest.main()
