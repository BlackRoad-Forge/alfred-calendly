#!/usr/bin/python
# encoding: utf-8

import unittest

from mock import Mock, patch

from stripe_client import StripeClient, StripeClientException


class StripeClientTest(unittest.TestCase):
    def setUp(self):
        self.client = StripeClient("sk_test_fake_key_123")

    @patch("workflow.web.post")
    def test_create_product_success(self, mock_post):
        response_mock = Mock()
        response_mock.status_code = 200
        response_mock.json.return_value = {
            "id": "prod_abc123",
            "name": "Calendly: Consultation",
        }
        mock_post.return_value = response_mock

        result = self.client.create_product("Calendly: Consultation")

        self.assertEqual(result["id"], "prod_abc123")
        mock_post.assert_called_once()

    @patch("workflow.web.post")
    def test_create_product_failure_raises(self, mock_post):
        response_mock = Mock()
        response_mock.status_code = 400
        response_mock.json.return_value = {"error": {"message": "bad request"}}
        mock_post.return_value = response_mock

        with self.assertRaises(StripeClientException):
            self.client.create_product("Test")

    @patch("workflow.web.post")
    def test_create_price_success(self, mock_post):
        response_mock = Mock()
        response_mock.status_code = 200
        response_mock.json.return_value = {
            "id": "price_abc123",
            "unit_amount": 5000,
            "currency": "usd",
        }
        mock_post.return_value = response_mock

        result = self.client.create_price("prod_abc123", 5000, "usd")

        self.assertEqual(result["id"], "price_abc123")
        self.assertEqual(result["unit_amount"], 5000)

    @patch("workflow.web.post")
    def test_create_price_failure_raises(self, mock_post):
        response_mock = Mock()
        response_mock.status_code = 400
        response_mock.json.return_value = {"error": {"message": "invalid"}}
        mock_post.return_value = response_mock

        with self.assertRaises(StripeClientException):
            self.client.create_price("prod_bad", 5000)

    @patch("workflow.web.post")
    def test_create_payment_link_success(self, mock_post):
        response_mock = Mock()
        response_mock.status_code = 200
        response_mock.json.return_value = {
            "id": "plink_abc123",
            "url": "https://buy.stripe.com/test_abc",
        }
        mock_post.return_value = response_mock

        result = self.client.create_payment_link("price_abc123")

        self.assertEqual(result["id"], "plink_abc123")
        self.assertEqual(result["url"], "https://buy.stripe.com/test_abc")

    @patch("workflow.web.post")
    def test_create_payment_link_with_metadata(self, mock_post):
        response_mock = Mock()
        response_mock.status_code = 200
        response_mock.json.return_value = {
            "id": "plink_abc123",
            "url": "https://buy.stripe.com/test_abc",
        }
        mock_post.return_value = response_mock

        metadata = {"calendly_link": "https://calendly.com/d/abc", "event_type": "u1"}
        result = self.client.create_payment_link("price_abc123", metadata=metadata)

        call_kwargs = mock_post.call_args
        data = call_kwargs[1]["data"] if "data" in call_kwargs[1] else call_kwargs[0][0]
        self.assertIn("metadata[calendly_link]", data)

    @patch("workflow.web.post")
    def test_create_payment_link_failure_raises(self, mock_post):
        response_mock = Mock()
        response_mock.status_code = 500
        response_mock.json.return_value = {"error": {"message": "server error"}}
        mock_post.return_value = response_mock

        with self.assertRaises(StripeClientException):
            self.client.create_payment_link("price_bad")

    @patch("workflow.web.post")
    def test_create_checkout_session_success(self, mock_post):
        response_mock = Mock()
        response_mock.status_code = 200
        response_mock.json.return_value = {
            "id": "cs_abc123",
            "url": "https://checkout.stripe.com/c/pay/cs_abc123",
        }
        mock_post.return_value = response_mock

        result = self.client.create_checkout_session(
            "price_abc123", success_url="https://example.com/success"
        )

        self.assertEqual(result["id"], "cs_abc123")

    @patch("workflow.web.get")
    def test_list_prices_success(self, mock_get):
        response_mock = Mock()
        response_mock.status_code = 200
        response_mock.json.return_value = {
            "data": [
                {"id": "price_1", "unit_amount": 5000},
                {"id": "price_2", "unit_amount": 10000},
            ]
        }
        mock_get.return_value = response_mock

        result = self.client.list_prices()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "price_1")

    @patch("workflow.web.get")
    def test_list_prices_failure_raises(self, mock_get):
        response_mock = Mock()
        response_mock.status_code = 401
        mock_get.return_value = response_mock

        with self.assertRaises(StripeClientException):
            self.client.list_prices()

    def test_auth_header_format(self):
        client = StripeClient("sk_test_key")
        self.assertIn("Basic", client.auth_header)


if __name__ == "__main__":
    unittest.main()
