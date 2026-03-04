# Commands
CMD_OBTAIN_ACCESS_TOKEN = "obtain_access_token"
CMD_SET_ACCESS_TOKEN = "set_access_token"
CMD_SINGLE_USE_LINK = "single_use_link"
CMD_PAID_LINK = "paid_link"
CMD_SET_STRIPE_KEY = "set_stripe_key"
CMD_SET_PI_ENDPOINT = "set_pi_endpoint"
CMD_BROWSE_URL = "browse_url"
CMD_LOGOUT = "logout"
CMD_RESET = "reset"

# Passwords
ACCESS_TOKEN = "calendly_alfred_access_token"
STRIPE_API_KEY = "calendly_alfred_stripe_api_key"

# Settings
CONF_REDIRECT_URL = "redirect_url"
CONF_EVENT_STATS = "event_stats"
CONF_STRIPE_ENABLED = "stripe_enabled"
CONF_STRIPE_CURRENCY = "stripe_currency"
CONF_STRIPE_PRICES = "stripe_prices"
CONF_PI_ENDPOINTS = "pi_endpoints"
CONF_WEBHOOK_SECRET = "webhook_secret"

# Cache IDs
CACHE_EVENT_TYPES = "event_types"

# URLs
CALENDLY_API_BASE_URL = "https://api.calendly.com"
CALENDLY_API_WEB_HOOKS_URL = "https://calendly.com/integrations/api_webhooks"
CALENDLY_TOKEN_URI = "/token"
CALENDLY_CURRENT_USER_URI = "/users/me"
CALENDLY_EVENT_TYPES_URI = "/event_types"
CALENDLY_SCHEDULING_LINK_URI = "/scheduling_links"

# Stripe
STRIPE_API_BASE_URL = "https://api.stripe.com/v1"
STRIPE_PAYMENT_LINKS_URI = "/payment_links"
STRIPE_CHECKOUT_SESSIONS_URI = "/checkout/sessions"
STRIPE_PRICES_URI = "/prices"
STRIPE_PRODUCTS_URI = "/products"

# Webhook routing
WEBHOOK_ROUTE_CALENDLY = "/webhooks/calendly"
WEBHOOK_ROUTE_STRIPE = "/webhooks/stripe"
DEFAULT_PI_PORT = 8420
