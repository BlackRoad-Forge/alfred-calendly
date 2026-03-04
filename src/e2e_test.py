#!/usr/bin/python
# encoding: utf-8

"""
End-to-End Tests for Calendly-Stripe-Pi Integration

Tests the full workflow:
1. Calendly event type retrieval and caching
2. Single-use link creation
3. Paid link creation (Calendly + Stripe)
4. Webhook routing to Pi endpoints
5. Full paid consultation flow
"""

import unittest
import json

from mock import Mock, patch, MagicMock, PropertyMock

import constants as c
from conftest import SettingsDict, MockPasswordNotFound as PasswordNotFound
from calendly_client import CalendlyClient
from stripe_client import StripeClient
from controller import Controller
from webhook_router import WebhookRouter


MOCK_EVENT_TYPES = [
    {
        "uri": "https://api.calendly.com/event_types/ET_001",
        "name": "30-Minute Consultation",
        "active": True,
        "scheduling_url": "https://calendly.com/testuser/30min",
    },
    {
        "uri": "https://api.calendly.com/event_types/ET_002",
        "name": "60-Minute Deep Dive",
        "active": True,
        "scheduling_url": "https://calendly.com/testuser/60min",
    },
]

MOCK_STRIPE_PRODUCT = {"id": "prod_e2e_001", "name": "Calendly: 30-Minute Consultation"}

MOCK_STRIPE_PRICE = {
    "id": "price_e2e_001",
    "unit_amount": 5000,
    "currency": "usd",
    "product": "prod_e2e_001",
}

MOCK_STRIPE_PAYMENT_LINK = {
    "id": "plink_e2e_001",
    "url": "https://buy.stripe.com/test_e2e_abc",
}

MOCK_CALENDLY_BOOKING_URL = "https://calendly.com/d/abc-123-xyz/30min"


class E2EFullPaidConsultationFlowTest(unittest.TestCase):
    """Tests the complete flow: browse events -> create paid link -> route to Pis"""

    def setUp(self):
        self.mock_wf = Mock()
        self.mock_wf.get_password.side_effect = self._get_password
        self.mock_wf.settings = SettingsDict({
            c.CONF_EVENT_STATS: {},
            c.CONF_STRIPE_PRICES: {
                "https://api.calendly.com/event_types/ET_001": 5000,
                "https://api.calendly.com/event_types/ET_002": 10000,
            },
            c.CONF_STRIPE_CURRENCY: "usd",
            c.CONF_PI_ENDPOINTS: [
                {
                    "host": "192.168.1.50",
                    "port": 8420,
                    "label": "pi-office",
                    "active": True,
                },
                {
                    "host": "192.168.1.51",
                    "port": 8420,
                    "label": "pi-studio",
                    "active": True,
                },
            ],
        })
        self.mock_wf.cached_data.return_value = MOCK_EVENT_TYPES

    def _get_password(self, key):
        passwords = {
            c.ACCESS_TOKEN: "test_calendly_token",
            c.STRIPE_API_KEY: "sk_test_e2e_key",
        }
        return passwords[key]

    @patch("workflow.web.post")
    @patch("workflow.web.get")
    def test_e2e_create_paid_link_and_route_to_pis(self, mock_get, mock_post):
        """Full E2E: Create Calendly link -> Stripe payment -> notify Pis"""
        # Mock responses in order of calls:
        # 1. Calendly create_link
        # 2. Stripe create_product
        # 3. Stripe create_price
        # 4. Stripe create_payment_link
        # 5-6. Webhook broadcast to 2 Pis

        calendly_response = Mock()
        calendly_response.status_code = 201
        calendly_response.json.return_value = {
            "resource": {"booking_url": MOCK_CALENDLY_BOOKING_URL}
        }

        stripe_product_response = Mock()
        stripe_product_response.status_code = 200
        stripe_product_response.json.return_value = MOCK_STRIPE_PRODUCT

        stripe_price_response = Mock()
        stripe_price_response.status_code = 200
        stripe_price_response.json.return_value = MOCK_STRIPE_PRICE

        stripe_plink_response = Mock()
        stripe_plink_response.status_code = 200
        stripe_plink_response.json.return_value = MOCK_STRIPE_PAYMENT_LINK

        pi_response = Mock()
        pi_response.status_code = 200

        mock_post.side_effect = [
            calendly_response,
            stripe_product_response,
            stripe_price_response,
            stripe_plink_response,
            pi_response,
            pi_response,
        ]

        controller = Controller(self.mock_wf)
        result = controller.create_paid_link(
            "https://api.calendly.com/event_types/ET_001", 5000
        )

        # Verify Calendly link was created
        self.assertEqual(result["calendly_link"], MOCK_CALENDLY_BOOKING_URL)

        # Verify Stripe payment link was created
        self.assertEqual(result["payment_url"], "https://buy.stripe.com/test_e2e_abc")
        self.assertEqual(result["payment_link_id"], "plink_e2e_001")

        # Verify webhooks were sent to both Pis (6 total POST calls)
        self.assertEqual(mock_post.call_count, 6)

        # Verify the Pi webhook payloads
        pi_call_1 = mock_post.call_args_list[4]
        pi_url_1 = pi_call_1[1]["url"]
        self.assertIn("192.168.1.50", pi_url_1)
        self.assertIn("/webhooks/calendly", pi_url_1)

        pi_call_2 = mock_post.call_args_list[5]
        pi_url_2 = pi_call_2[1]["url"]
        self.assertIn("192.168.1.51", pi_url_2)

        # Verify stats were incremented
        event_uri = "https://api.calendly.com/event_types/ET_001"
        self.assertEqual(
            self.mock_wf.settings[c.CONF_EVENT_STATS][event_uri], 1
        )

    @patch("workflow.web.post")
    def test_e2e_paid_link_without_stripe_configured(self, mock_post):
        """E2E: Attempting paid link without Stripe key raises properly"""
        def get_password_no_stripe(key):
            if key == c.STRIPE_API_KEY:
                raise PasswordNotFound()
            return "test_calendly_token"

        self.mock_wf.get_password.side_effect = get_password_no_stripe

        controller = Controller(self.mock_wf)
        self.assertFalse(controller.stripe_enabled)

        with self.assertRaises(Exception) as ctx:
            controller.create_paid_link("ET_001", 5000)

        self.assertIn("Stripe is not configured", str(ctx.exception))

    @patch("workflow.web.post")
    @patch("workflow.web.get")
    def test_e2e_single_use_link_still_works_without_stripe(self, mock_get, mock_post):
        """E2E: Original single-use link flow is unaffected by Stripe integration"""
        def get_password_no_stripe(key):
            if key == c.STRIPE_API_KEY:
                raise PasswordNotFound()
            return "test_calendly_token"

        self.mock_wf.get_password.side_effect = get_password_no_stripe
        self.mock_wf.settings = SettingsDict({
            c.CONF_EVENT_STATS: {},
            c.CONF_PI_ENDPOINTS: [],
        })

        calendly_response = Mock()
        calendly_response.status_code = 201
        calendly_response.json.return_value = {
            "resource": {"booking_url": MOCK_CALENDLY_BOOKING_URL}
        }
        mock_post.return_value = calendly_response

        controller = Controller(self.mock_wf)
        link = controller.create_single_use_link(
            "https://api.calendly.com/event_types/ET_001"
        )

        self.assertEqual(link, MOCK_CALENDLY_BOOKING_URL)
        self.assertEqual(mock_post.call_count, 1)


class E2EEventTypeCachingFlowTest(unittest.TestCase):
    """Tests the event type caching and ordering flow end-to-end"""

    def setUp(self):
        self.mock_wf = Mock()
        self.mock_wf.get_password.return_value = "test_token"
        self.mock_wf.settings = SettingsDict({
            c.CONF_EVENT_STATS: {
                "https://api.calendly.com/event_types/ET_002": 15,
                "https://api.calendly.com/event_types/ET_001": 3,
            },
            c.CONF_PI_ENDPOINTS: [],
        })

    @patch("calendly_client.CalendlyClient.get_current_user")
    @patch("calendly_client.CalendlyClient.get_all_event_types_of_user")
    def test_e2e_cache_ordered_event_types(
        self, mock_get_all, mock_get_user
    ):
        """E2E: Fetch events from Calendly -> order by stats -> cache"""
        mock_get_user.return_value = "https://api.calendly.com/users/TESTUSER"
        mock_get_all.return_value = list(MOCK_EVENT_TYPES)

        controller = Controller(self.mock_wf)
        controller.cache_ordered_event_types()

        self.mock_wf.cache_data.assert_called_once()
        cached_data = self.mock_wf.cache_data.call_args[0][1]

        # ET_002 should be first (15 hits vs 3 hits)
        self.assertEqual(cached_data[0]["name"], "60-Minute Deep Dive")
        self.assertEqual(cached_data[1]["name"], "30-Minute Consultation")


class E2EWebhookRoutingFlowTest(unittest.TestCase):
    """Tests webhook routing to Pis end-to-end"""

    def setUp(self):
        self.mock_wf = Mock()
        self.mock_wf.settings = {
            c.CONF_PI_ENDPOINTS: [
                {
                    "host": "192.168.1.50",
                    "port": 8420,
                    "label": "pi-office",
                    "active": True,
                },
                {
                    "host": "192.168.1.51",
                    "port": 8420,
                    "label": "pi-studio",
                    "active": False,
                },
            ]
        }

    @patch("workflow.web.post")
    def test_e2e_calendly_webhook_routes_only_to_active_pis(self, mock_post):
        """E2E: Calendly webhook only hits active Pi endpoints"""
        response_mock = Mock()
        response_mock.status_code = 200
        mock_post.return_value = response_mock

        router = WebhookRouter(self.mock_wf)
        payload = {
            "event": "invitee.created",
            "payload": {
                "event_type": {
                    "uuid": "ET_001",
                    "name": "30-Minute Consultation",
                },
                "invitee": {
                    "name": "Jane Doe",
                    "email": "jane@example.com",
                },
            },
        }

        results = router.route_calendly_webhook(payload)

        # Only 1 active endpoint should receive the webhook
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["endpoint"], "pi-office")
        self.assertTrue(results[0]["success"])
        self.assertEqual(mock_post.call_count, 1)

    @patch("workflow.web.post")
    def test_e2e_stripe_webhook_routes_payment_success(self, mock_post):
        """E2E: Stripe payment_intent.succeeded webhook routes to Pis"""
        response_mock = Mock()
        response_mock.status_code = 200
        mock_post.return_value = response_mock

        router = WebhookRouter(self.mock_wf)
        payload = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_abc123",
                    "amount": 5000,
                    "currency": "usd",
                    "metadata": {
                        "calendly_link": MOCK_CALENDLY_BOOKING_URL,
                        "event_type": "ET_001",
                    },
                }
            },
        }

        results = router.route_stripe_webhook(payload)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["success"])

        call_args = mock_post.call_args
        url = call_args[1]["url"]
        self.assertIn("/webhooks/stripe", url)

    @patch("workflow.web.post")
    def test_e2e_partial_pi_failure_doesnt_break_flow(self, mock_post):
        """E2E: If one Pi is down, others still get the webhook"""
        self.mock_wf.settings[c.CONF_PI_ENDPOINTS] = [
            {"host": "192.168.1.50", "port": 8420, "label": "pi-office", "active": True},
            {"host": "192.168.1.52", "port": 8420, "label": "pi-garage", "active": True},
        ]

        ok_response = Mock()
        ok_response.status_code = 200

        mock_post.side_effect = [Exception("Connection refused"), ok_response]

        router = WebhookRouter(self.mock_wf)
        results = router.route_calendly_webhook({"event": "test"})

        self.assertEqual(len(results), 2)
        self.assertFalse(results[0]["success"])
        self.assertTrue(results[1]["success"])

    @patch("workflow.web.get")
    def test_e2e_pi_health_check_mixed_status(self, mock_get):
        """E2E: Health check reports mixed status across Pis"""
        healthy = Mock()
        healthy.status_code = 200

        mock_get.side_effect = [healthy, Exception("offline")]

        router = WebhookRouter(self.mock_wf)
        results = router.health_check()

        self.assertEqual(len(results), 2)
        self.assertTrue(results[0]["healthy"])
        self.assertFalse(results[1]["healthy"])


class E2EEndpointManagementTest(unittest.TestCase):
    """Tests Pi endpoint CRUD operations end-to-end"""

    def setUp(self):
        self.mock_wf = Mock()
        self.mock_wf.settings = SettingsDict({c.CONF_PI_ENDPOINTS: None})

    def test_e2e_add_multiple_pis_then_route(self):
        """E2E: Add multiple Pis, verify all receive broadcasts"""
        router = WebhookRouter(self.mock_wf)

        router.add_endpoint("192.168.1.50", label="pi-office")
        router.add_endpoint("192.168.1.51", port=9000, label="pi-studio")
        router.add_endpoint("192.168.1.52", label="pi-garage")

        active = router.get_active_endpoints()
        self.assertEqual(len(active), 3)

    def test_e2e_add_then_remove_endpoint(self):
        """E2E: Add a Pi, remove it, verify it's gone"""
        router = WebhookRouter(self.mock_wf)
        router.add_endpoint("192.168.1.50", label="temporary")

        self.assertEqual(len(router.get_active_endpoints()), 1)

        router.remove_endpoint("192.168.1.50")
        self.assertEqual(len(router.get_active_endpoints()), 0)


class E2EPriceConfigurationTest(unittest.TestCase):
    """Tests Stripe price configuration per event type"""

    def setUp(self):
        self.mock_wf = Mock()
        self.mock_wf.get_password.return_value = "test_token"
        self.mock_wf.settings = SettingsDict({
            c.CONF_EVENT_STATS: {},
            c.CONF_STRIPE_PRICES: None,
            c.CONF_PI_ENDPOINTS: [],
        })

    def test_e2e_set_and_get_event_type_price(self):
        """E2E: Set a price for an event type, retrieve it"""
        controller = Controller(self.mock_wf)
        event_uri = "https://api.calendly.com/event_types/ET_001"

        controller.set_event_type_price(event_uri, 7500)

        price = controller.get_event_type_price(event_uri)
        self.assertEqual(price, 7500)

    def test_e2e_get_price_returns_none_for_unconfigured(self):
        """E2E: Unconfigured event type returns None"""
        controller = Controller(self.mock_wf)
        price = controller.get_event_type_price("nonexistent")
        self.assertIsNone(price)


if __name__ == "__main__":
    unittest.main()
