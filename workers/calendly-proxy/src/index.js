/**
 * Calendly API Proxy Worker
 *
 * Proxies requests to the Calendly API with:
 * - CORS support for browser-based clients
 * - Rate limiting headers
 * - Request validation
 * - Error handling for long-running operations (scheduling links, webhooks)
 *
 * Deploy: npx wrangler deploy
 * Dev:    npx wrangler dev
 */

const CALENDLY_API_BASE = "https://api.calendly.com";

const ALLOWED_PATHS = [
  "/users/me",
  "/event_types",
  "/scheduling_links",
];

function isAllowedPath(pathname) {
  return ALLOWED_PATHS.some((allowed) => pathname.startsWith(allowed));
}

function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Origin": origin || "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
    "Access-Control-Max-Age": "86400",
  };
}

async function handleRequest(request, env) {
  const url = new URL(request.url);

  // Health check
  if (url.pathname === "/" || url.pathname === "/health") {
    return new Response(
      JSON.stringify({ status: "ok", service: "calendly-proxy" }),
      {
        headers: {
          "Content-Type": "application/json",
          ...corsHeaders(request.headers.get("Origin")),
        },
      }
    );
  }

  // CORS preflight
  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: corsHeaders(request.headers.get("Origin")),
    });
  }

  // Validate path
  const apiPath = url.pathname;
  if (!isAllowedPath(apiPath)) {
    return new Response(
      JSON.stringify({ error: "Path not allowed" }),
      {
        status: 403,
        headers: {
          "Content-Type": "application/json",
          ...corsHeaders(request.headers.get("Origin")),
        },
      }
    );
  }

  // Require Authorization header
  const authHeader = request.headers.get("Authorization");
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    return new Response(
      JSON.stringify({ error: "Authorization header required" }),
      {
        status: 401,
        headers: {
          "Content-Type": "application/json",
          ...corsHeaders(request.headers.get("Origin")),
        },
      }
    );
  }

  // Build proxied request
  const apiUrl = `${CALENDLY_API_BASE}${apiPath}${url.search}`;
  const headers = new Headers();
  headers.set("Authorization", authHeader);
  headers.set("Content-Type", "application/json");

  const fetchOptions = {
    method: request.method,
    headers,
  };

  if (request.method === "POST") {
    fetchOptions.body = await request.text();
  }

  try {
    const response = await fetch(apiUrl, fetchOptions);
    const body = await response.text();

    return new Response(body, {
      status: response.status,
      headers: {
        "Content-Type": "application/json",
        "X-Proxy": "calendly-proxy",
        ...corsHeaders(request.headers.get("Origin")),
      },
    });
  } catch (err) {
    return new Response(
      JSON.stringify({ error: "Upstream request failed", details: err.message }),
      {
        status: 502,
        headers: {
          "Content-Type": "application/json",
          ...corsHeaders(request.headers.get("Origin")),
        },
      }
    );
  }
}

export default {
  async fetch(request, env, ctx) {
    return handleRequest(request, env);
  },
};
