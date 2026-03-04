#!/usr/bin/python
# encoding: utf-8
import constants as c
from calendly_client import CalendlyClient, CalendlyClientException
from calendly_client import active_filter as ACTIVE_FILTER
from stripe_client import StripeClient, StripeClientException
from webhook_router import WebhookRouter

from workflow import Workflow3, PasswordNotFound

log = Workflow3().logger


class Controller:
    calendly_client = None
    stripe_client = None

    def __init__(self, wf):
        access_token = wf.get_password(c.ACCESS_TOKEN)
        self.calendly_client = CalendlyClient(access_token)

        try:
            stripe_key = wf.get_password(c.STRIPE_API_KEY)
            self.stripe_client = StripeClient(stripe_key)
            self.stripe_enabled = True
        except PasswordNotFound:
            self.stripe_client = None
            self.stripe_enabled = False

        self.stats = Stats(wf)
        self.webhook_router = WebhookRouter(wf)
        self.wf = wf

    def create_single_use_link(self, event_type):
        try:
            link = self.calendly_client.create_link(event_type, 1)
            self.stats.increment(event_type)
            return link

        except CalendlyClientException:
            raise Exception("Request to create link failed.")

    def create_paid_link(self, event_type, amount_cents, currency=None):
        if not self.stripe_enabled:
            raise Exception("Stripe is not configured. Set your Stripe API key first.")

        if currency is None:
            currency = self.wf.settings.get(c.CONF_STRIPE_CURRENCY) or "usd"

        try:
            calendly_link = self.calendly_client.create_link(event_type, 1)

            event_name = self._get_event_type_name(event_type)
            product_name = "Calendly: %s" % (event_name or "Consultation")

            product = self.stripe_client.create_product(
                name=product_name,
                description="Single-use scheduling link payment",
            )

            price = self.stripe_client.create_price(
                product_id=product["id"],
                amount_cents=amount_cents,
                currency=currency,
            )

            payment_link = self.stripe_client.create_payment_link(
                price_id=price["id"],
                metadata={
                    "calendly_link": calendly_link,
                    "event_type": event_type,
                },
            )

            self.stats.increment(event_type)

            self._notify_pis(
                "paid_link_created",
                {
                    "calendly_link": calendly_link,
                    "payment_url": payment_link["url"],
                    "amount_cents": amount_cents,
                    "currency": currency,
                    "event_type": event_type,
                },
            )

            return {
                "calendly_link": calendly_link,
                "payment_url": payment_link["url"],
                "payment_link_id": payment_link["id"],
            }

        except StripeClientException as e:
            raise Exception("Stripe payment link creation failed: %s" % str(e))
        except CalendlyClientException:
            raise Exception("Calendly link creation failed.")

    def _get_event_type_name(self, event_type_uri):
        cached = self.wf.cached_data(c.CACHE_EVENT_TYPES, None, max_age=0)
        if cached:
            for et in cached:
                if et.get("uri") == event_type_uri:
                    return et.get("name")
        return None

    def _notify_pis(self, event, data):
        if self.webhook_router.get_active_endpoints():
            try:
                self.webhook_router.route_calendly_webhook(
                    {"event": event, "data": data}
                )
            except Exception as e:
                log.warning("Failed to notify Pis: %s" % str(e))

    def get_event_type_price(self, event_type_uri):
        prices = self.wf.settings.get(c.CONF_STRIPE_PRICES) or {}
        return prices.get(event_type_uri)

    def set_event_type_price(self, event_type_uri, amount_cents):
        prices = self.wf.settings.get(c.CONF_STRIPE_PRICES)
        if prices is None:
            prices = {}
        prices[event_type_uri] = amount_cents
        self.wf.settings[c.CONF_STRIPE_PRICES] = prices
        self.wf.settings.save()

    def get_current_user(self):
        user = self.calendly_client.get_current_user()
        if user is None:
            raise Exception("Failed loading Event Types. Could not determine current user.")

        return user

    def cache_ordered_event_types(self):
        user = self.get_current_user()
        ordered_event_types = self.get_ordered_event_types(user)
        self.wf.cache_data(c.CACHE_EVENT_TYPES, ordered_event_types)

    def get_ordered_event_types(self, user):

        unordered_event_types = self.calendly_client.get_all_event_types_of_user(user, the_filter=ACTIVE_FILTER)
        if not unordered_event_types:
            return []

        event_stats = self.stats.get_stats()
        if not event_stats:
            return unordered_event_types

        for event_stats_item in event_stats.items():
            for i in range(len(unordered_event_types)):
                needle = unordered_event_types[i]
                if needle["uri"] == event_stats_item[0]:
                    unordered_event_types[i]["event_stats"] = event_stats_item[1]

        ordered_event_types = sorted(unordered_event_types, key=lambda event_type: event_type["event_stats"] if "event_stats" in event_type else -1, reverse=True)

        return ordered_event_types


class Stats:

    def __init__(self, wf):
        event_stats = wf.settings.get(c.CONF_EVENT_STATS)
        if event_stats is None:
            wf.settings[c.CONF_EVENT_STATS] = {}

        self.wf = wf

    def increment(self, event_type):
        log.debug("in: Incrementing Stats for %s" % event_type)
        if event_type in self.wf.settings[c.CONF_EVENT_STATS]:
            current_count = self.wf.settings[c.CONF_EVENT_STATS][event_type]
            self.wf.settings[c.CONF_EVENT_STATS][event_type] = current_count + 1
        else:
            self.wf.settings[c.CONF_EVENT_STATS][event_type] = 1

        self.wf.settings.save()

    def get_stats(self):
        return self.wf.settings[c.CONF_EVENT_STATS]


