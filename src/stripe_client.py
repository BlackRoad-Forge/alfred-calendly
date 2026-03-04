#!/usr/bin/python
# encoding: utf-8

import json
import base64

import constants as c
from workflow import Workflow3, web

log = Workflow3().logger


class StripeClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.auth_header = "Basic %s" % base64.b64encode(
            ("%s:" % api_key).encode("utf-8")
        ).decode("utf-8")

    def _headers(self):
        return {
            "Authorization": self.auth_header,
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def create_product(self, name, description=None):
        log.debug("in: create_product")
        data = {"name": name}
        if description:
            data["description"] = description

        response = web.post(
            url="%s%s" % (c.STRIPE_API_BASE_URL, c.STRIPE_PRODUCTS_URI),
            headers=self._headers(),
            data=data,
        )

        if response.status_code != 200:
            log.error(
                "Creating product failed. Stripe returned status [%s]."
                % response.status_code
            )
            log.error(response.json())
            raise StripeClientException("Failed to create product")

        return response.json()

    def create_price(self, product_id, amount_cents, currency="usd"):
        log.debug("in: create_price")
        response = web.post(
            url="%s%s" % (c.STRIPE_API_BASE_URL, c.STRIPE_PRICES_URI),
            headers=self._headers(),
            data={
                "product": product_id,
                "unit_amount": amount_cents,
                "currency": currency,
            },
        )

        if response.status_code != 200:
            log.error(
                "Creating price failed. Stripe returned status [%s]."
                % response.status_code
            )
            log.error(response.json())
            raise StripeClientException("Failed to create price")

        return response.json()

    def create_payment_link(self, price_id, metadata=None):
        log.debug("in: create_payment_link")
        data = {"line_items[0][price]": price_id, "line_items[0][quantity]": 1}

        if metadata:
            for key, value in metadata.items():
                data["metadata[%s]" % key] = value

        response = web.post(
            url="%s%s" % (c.STRIPE_API_BASE_URL, c.STRIPE_PAYMENT_LINKS_URI),
            headers=self._headers(),
            data=data,
        )

        if response.status_code != 200:
            log.error(
                "Creating payment link failed. Stripe returned status [%s]."
                % response.status_code
            )
            log.error(response.json())
            raise StripeClientException("Failed to create payment link")

        return response.json()

    def create_checkout_session(
        self, price_id, success_url, cancel_url=None, metadata=None
    ):
        log.debug("in: create_checkout_session")
        data = {
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": 1,
            "mode": "payment",
            "success_url": success_url,
        }

        if cancel_url:
            data["cancel_url"] = cancel_url

        if metadata:
            for key, value in metadata.items():
                data["metadata[%s]" % key] = value

        response = web.post(
            url="%s%s" % (c.STRIPE_API_BASE_URL, c.STRIPE_CHECKOUT_SESSIONS_URI),
            headers=self._headers(),
            data=data,
        )

        if response.status_code != 200:
            log.error(
                "Creating checkout session failed. Stripe returned status [%s]."
                % response.status_code
            )
            log.error(response.json())
            raise StripeClientException("Failed to create checkout session")

        return response.json()

    def list_prices(self, product_id=None, active=True):
        log.debug("in: list_prices")
        params = {"active": "true" if active else "false"}
        if product_id:
            params["product"] = product_id

        response = web.get(
            url="%s%s" % (c.STRIPE_API_BASE_URL, c.STRIPE_PRICES_URI),
            headers=self._headers(),
            params=params,
        )

        if response.status_code != 200:
            log.error(
                "Listing prices failed. Stripe returned status [%s]."
                % response.status_code
            )
            raise StripeClientException("Failed to list prices")

        return response.json().get("data", [])


class StripeClientException(Exception):
    pass
