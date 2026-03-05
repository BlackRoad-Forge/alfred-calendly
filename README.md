# Calendly for Alfred || Schedule Calendly Events with Alfred

[![CI](https://github.com/blackboxprogramming/alfred-calendly/actions/workflows/ci.yml/badge.svg)](https://github.com/blackboxprogramming/alfred-calendly/actions/workflows/ci.yml)
[![Alfred Workflow](https://img.shields.io/badge/Alfred-Workflow-5b2585)](https://alfredapp.com)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/blackboxprogramming/alfred-calendly?label=latest%20release)](https://github.com/blackboxprogramming/alfred-calendly/releases)
[![GitHub](https://img.shields.io/github/license/blackboxprogramming/alfred-calendly)](https://github.com/blackboxprogramming/alfred-calendly/blob/primary/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/blackboxprogramming/alfred-calendly)](https://github.com/blackboxprogramming/alfred-calendly/stargazers)
[![GitHub all releases](https://img.shields.io/github/downloads/blackboxprogramming/alfred-calendly/total)](https://github.com/blackboxprogramming/alfred-calendly/releases)

Create single-use Calendly scheduling links directly from Alfred. Type `cy` to get started.

## Use Cases

### Requesting Single-Use-Links for Event Types

![alfred-calendly](single_use_link.gif)

## Preparation

- You need an [Alfred Powerpack](https://www.alfredapp.com/powerpack/) License.
- You need a paid [Calendly](https://calendly.com) subscription.
- During initial setup you will be asked to provide a [Calendly Personal Access Token](https://calendly.com/integrations/api_webhooks).

## Installation

1. Download the latest release from the [Releases page](https://github.com/blackboxprogramming/alfred-calendly/releases).
2. Double-click the `.alfredworkflow` file to install.
3. Open Alfred and type `cy` to begin setup.

## Build from Source

```shell
git clone https://github.com/blackboxprogramming/alfred-calendly.git
cd alfred-calendly
make && make install
```

## Running Tests

```shell
cd src
pip install mock pytest
python -m pytest calendly_client_test.py controller_test.py -v
```

## Architecture

| Component | Description |
|-----------|-------------|
| `src/calendly_client.py` | Calendly API client (event types, scheduling links) |
| `src/controller.py` | Business logic layer (caching, stats, link creation) |
| `src/cy_filter.py` | Alfred script filter for event type search |
| `src/cy_handler.py` | Event handler for user actions |
| `src/cy_preload_event_types.py` | Background cache refresh |
| `workers/calendly-proxy/` | Cloudflare Worker API proxy |

## Cloudflare Worker (API Proxy)

An optional Cloudflare Worker proxy is included in `workers/calendly-proxy/` for:

- CORS-enabled browser access to the Calendly API
- Request validation and path allowlisting
- Centralized error handling for longer-running operations

### Deploy the Worker

```shell
cd workers/calendly-proxy
npm install
npx wrangler deploy
```

Requires `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` environment variables (or Wrangler login).

## CI/CD

- **CI**: Tests (Python 3.11, 3.12), linting (flake8), and build on every push/PR
- **Release**: Automated `.alfredworkflow` artifact on version tags (`v*`)
- **Automerge**: Dependabot PRs are auto-merged after CI passes
- **Worker Deploy**: Cloudflare Worker deploys on changes to `workers/`
- **Security**: All GitHub Actions pinned to commit hashes; Dependabot monitors for updates

## Security

- API tokens stored in macOS Keychain (never on disk)
- All API communication over HTTPS
- See [SECURITY.md](SECURITY.md) for vulnerability reporting

## License

[MIT](LICENSE) - Copyright (c) 2021 Sebastian Warnke
