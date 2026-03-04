#!/usr/bin/python
# encoding: utf-8

import unittest
import json

from mock import Mock, patch, call

import constants as c
from conftest import SettingsDict
from webhook_router import WebhookRouter


class WebhookRouterTest(unittest.TestCase):
    def setUp(self):
        self.mock_wf = Mock()
        self.mock_wf.settings = {c.CONF_PI_ENDPOINTS: []}

    def test_add_endpoint_default_port(self):
        self.mock_wf.settings = SettingsDict({c.CONF_PI_ENDPOINTS: None})
        router = WebhookRouter(self.mock_wf)
        endpoint = router.add_endpoint("192.168.1.100")

        self.assertEqual(endpoint["host"], "192.168.1.100")
        self.assertEqual(endpoint["port"], c.DEFAULT_PI_PORT)
        self.assertTrue(endpoint["active"])

    def test_add_endpoint_custom_port(self):
        self.mock_wf.settings = SettingsDict({c.CONF_PI_ENDPOINTS: None})
        router = WebhookRouter(self.mock_wf)
        endpoint = router.add_endpoint("192.168.1.100", port=9000, label="Pi-Kitchen")

        self.assertEqual(endpoint["port"], 9000)
        self.assertEqual(endpoint["label"], "Pi-Kitchen")

    def test_remove_endpoint(self):
        self.mock_wf.settings = SettingsDict({
            c.CONF_PI_ENDPOINTS: [
                {"host": "192.168.1.100", "port": 8420, "label": "pi1", "active": True},
                {"host": "192.168.1.101", "port": 8420, "label": "pi2", "active": True},
            ]
        })
        router = WebhookRouter(self.mock_wf)
        router.remove_endpoint("192.168.1.100")

        remaining = self.mock_wf.settings[c.CONF_PI_ENDPOINTS]
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["host"], "192.168.1.101")

    def test_get_active_endpoints_filters_inactive(self):
        self.mock_wf.settings = {
            c.CONF_PI_ENDPOINTS: [
                {"host": "192.168.1.100", "port": 8420, "label": "pi1", "active": True},
                {"host": "192.168.1.101", "port": 8420, "label": "pi2", "active": False},
            ]
        }
        router = WebhookRouter(self.mock_wf)
        active = router.get_active_endpoints()

        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["host"], "192.168.1.100")

    @patch("workflow.web.post")
    def test_route_calendly_webhook_broadcasts_to_all_active(self, mock_post):
        self.mock_wf.settings = {
            c.CONF_PI_ENDPOINTS: [
                {"host": "192.168.1.100", "port": 8420, "label": "pi1", "active": True},
                {"host": "192.168.1.101", "port": 8420, "label": "pi2", "active": True},
            ]
        }
        response_mock = Mock()
        response_mock.status_code = 200
        mock_post.return_value = response_mock

        router = WebhookRouter(self.mock_wf)
        payload = {"event": "invitee.created", "data": {"name": "Test"}}
        results = router.route_calendly_webhook(payload)

        self.assertEqual(len(results), 2)
        self.assertTrue(results[0]["success"])
        self.assertTrue(results[1]["success"])
        self.assertEqual(mock_post.call_count, 2)

    @patch("workflow.web.post")
    def test_route_stripe_webhook_broadcasts(self, mock_post):
        self.mock_wf.settings = {
            c.CONF_PI_ENDPOINTS: [
                {"host": "192.168.1.100", "port": 8420, "label": "pi1", "active": True},
            ]
        }
        response_mock = Mock()
        response_mock.status_code = 200
        mock_post.return_value = response_mock

        router = WebhookRouter(self.mock_wf)
        payload = {"type": "payment_intent.succeeded", "data": {"amount": 5000}}
        results = router.route_stripe_webhook(payload)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["success"])

        call_args = mock_post.call_args
        url = call_args[1]["url"] if "url" in call_args[1] else call_args[0][0]
        self.assertIn("/webhooks/stripe", url)

    @patch("workflow.web.post")
    def test_route_handles_endpoint_failure(self, mock_post):
        self.mock_wf.settings = {
            c.CONF_PI_ENDPOINTS: [
                {"host": "192.168.1.100", "port": 8420, "label": "pi1", "active": True},
            ]
        }
        mock_post.side_effect = Exception("Connection refused")

        router = WebhookRouter(self.mock_wf)
        results = router.route_calendly_webhook({"event": "test"})

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["success"])
        self.assertIn("error", results[0])

    def test_route_returns_empty_when_no_endpoints(self):
        self.mock_wf.settings = {c.CONF_PI_ENDPOINTS: []}
        router = WebhookRouter(self.mock_wf)
        results = router.route_calendly_webhook({"event": "test"})

        self.assertEqual(len(results), 0)

    @patch("workflow.web.get")
    def test_health_check_healthy(self, mock_get):
        self.mock_wf.settings = {
            c.CONF_PI_ENDPOINTS: [
                {"host": "192.168.1.100", "port": 8420, "label": "pi1", "active": True},
            ]
        }
        response_mock = Mock()
        response_mock.status_code = 200
        mock_get.return_value = response_mock

        router = WebhookRouter(self.mock_wf)
        results = router.health_check()

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["healthy"])

    @patch("workflow.web.get")
    def test_health_check_unhealthy(self, mock_get):
        self.mock_wf.settings = {
            c.CONF_PI_ENDPOINTS: [
                {"host": "192.168.1.100", "port": 8420, "label": "pi1", "active": True},
            ]
        }
        mock_get.side_effect = Exception("timeout")

        router = WebhookRouter(self.mock_wf)
        results = router.health_check()

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["healthy"])


if __name__ == "__main__":
    unittest.main()
