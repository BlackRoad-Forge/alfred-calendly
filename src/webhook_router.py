#!/usr/bin/python
# encoding: utf-8

import json

import constants as c
from workflow import Workflow3, web

log = Workflow3().logger


class WebhookRouter:
    def __init__(self, wf):
        self.wf = wf
        self.endpoints = wf.settings.get(c.CONF_PI_ENDPOINTS) or []

    def add_endpoint(self, host, port=None, label=None):
        if port is None:
            port = c.DEFAULT_PI_PORT

        endpoint = {
            "host": host,
            "port": port,
            "label": label or host,
            "active": True,
        }

        endpoints = self.wf.settings.get(c.CONF_PI_ENDPOINTS) or []
        endpoints.append(endpoint)
        self.wf.settings[c.CONF_PI_ENDPOINTS] = endpoints
        self.wf.settings.save()
        self.endpoints = endpoints
        return endpoint

    def remove_endpoint(self, host):
        endpoints = self.wf.settings.get(c.CONF_PI_ENDPOINTS) or []
        self.wf.settings[c.CONF_PI_ENDPOINTS] = [
            ep for ep in endpoints if ep["host"] != host
        ]
        self.wf.settings.save()
        self.endpoints = self.wf.settings[c.CONF_PI_ENDPOINTS]

    def get_active_endpoints(self):
        return [ep for ep in self.endpoints if ep.get("active", True)]

    def route_calendly_webhook(self, payload):
        log.debug("in: route_calendly_webhook")
        return self._broadcast(c.WEBHOOK_ROUTE_CALENDLY, payload)

    def route_stripe_webhook(self, payload):
        log.debug("in: route_stripe_webhook")
        return self._broadcast(c.WEBHOOK_ROUTE_STRIPE, payload)

    def _broadcast(self, route, payload):
        results = []
        active_endpoints = self.get_active_endpoints()

        if not active_endpoints:
            log.warning("No active Pi endpoints configured for webhook routing.")
            return results

        for endpoint in active_endpoints:
            url = "http://%s:%s%s" % (endpoint["host"], endpoint["port"], route)
            try:
                response = web.post(
                    url=url,
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(payload),
                )
                results.append(
                    {
                        "endpoint": endpoint["label"],
                        "status": response.status_code,
                        "success": 200 <= response.status_code < 300,
                    }
                )
                log.debug(
                    "Routed to %s:%s -> %s"
                    % (endpoint["host"], endpoint["port"], response.status_code)
                )
            except Exception as e:
                log.error("Failed to route to %s: %s" % (endpoint["host"], str(e)))
                results.append(
                    {
                        "endpoint": endpoint["label"],
                        "status": 0,
                        "success": False,
                        "error": str(e),
                    }
                )

        return results

    def health_check(self):
        results = []
        for endpoint in self.endpoints:
            url = "http://%s:%s/health" % (endpoint["host"], endpoint["port"])
            try:
                response = web.get(url=url)
                results.append(
                    {
                        "endpoint": endpoint["label"],
                        "host": endpoint["host"],
                        "port": endpoint["port"],
                        "healthy": response.status_code == 200,
                        "status": response.status_code,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "endpoint": endpoint["label"],
                        "host": endpoint["host"],
                        "port": endpoint["port"],
                        "healthy": False,
                        "error": str(e),
                    }
                )
        return results


class PiWebhookServer:
    """
    Minimal webhook receiver to run on Raspberry Pi.
    Usage:
        python webhook_router.py --serve --port 8420

    Handles incoming webhooks from the Alfred workflow router
    for both Calendly events and Stripe payment events.
    """

    @staticmethod
    def create_app():
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
        except ImportError:
            from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

        class WebhookHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length) if content_length else b""

                try:
                    payload = json.loads(body) if body else {}
                except (ValueError, TypeError):
                    payload = {}

                if self.path == c.WEBHOOK_ROUTE_CALENDLY:
                    WebhookHandler.handle_calendly(payload)
                    self._respond(200, {"status": "ok", "type": "calendly"})
                elif self.path == c.WEBHOOK_ROUTE_STRIPE:
                    WebhookHandler.handle_stripe(payload)
                    self._respond(200, {"status": "ok", "type": "stripe"})
                else:
                    self._respond(404, {"error": "unknown route"})

            def do_GET(self):
                if self.path == "/health":
                    self._respond(200, {"status": "healthy"})
                else:
                    self._respond(404, {"error": "not found"})

            def _respond(self, code, data):
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(data).encode("utf-8"))

            @staticmethod
            def handle_calendly(payload):
                event = payload.get("event", "unknown")
                print("[Calendly] Received event: %s" % event)
                log_path = "/tmp/calendly_webhooks.jsonl"
                with open(log_path, "a") as f:
                    f.write(json.dumps(payload) + "\n")

            @staticmethod
            def handle_stripe(payload):
                event_type = payload.get("type", "unknown")
                print("[Stripe] Received event: %s" % event_type)
                log_path = "/tmp/stripe_webhooks.jsonl"
                with open(log_path, "a") as f:
                    f.write(json.dumps(payload) + "\n")

        return HTTPServer, WebhookHandler

    @staticmethod
    def run(port=None):
        if port is None:
            port = c.DEFAULT_PI_PORT
        HTTPServer, WebhookHandler = PiWebhookServer.create_app()
        server = HTTPServer(("0.0.0.0", port), WebhookHandler)
        print("Pi Webhook Server running on port %d" % port)
        print("  Calendly webhooks -> %s" % c.WEBHOOK_ROUTE_CALENDLY)
        print("  Stripe webhooks   -> %s" % c.WEBHOOK_ROUTE_STRIPE)
        print("  Health check      -> /health")
        server.serve_forever()


if __name__ == "__main__":
    import sys

    port = c.DEFAULT_PI_PORT
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])

    PiWebhookServer.run(port)
