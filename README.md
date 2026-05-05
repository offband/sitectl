# sitectl

**A local-first site hygiene CLI for sitemaps, robots files, internal links, metadata,
and privacy-safe release checks.**

`sitectl` is for people who want to inspect a site before publishing it without sending
page content to a hosted scanner, SEO dashboard, analytics service, or browser extension.
It crawls a local static build or HTTP target, checks the site surfaces that search engines
and users depend on, and reports problems in a terminal-friendly format that also works in CI.

The goal is simple: catch broken discovery, broken navigation, and accidental sensitive-data
exposure before a site ships.

## Why This Exists

Site release checks are often split across hosted SEO tools, one-off scripts, and manual
browser testing. That works until you need a repeatable command that can run locally, in CI,
and against a private build artifact.

`sitectl` keeps that workflow close to the project:

- Crawl static folders like `./dist`, `./public`, or `./build`
- Crawl HTTP targets like local dev servers or staging URLs
- Generate and validate `sitemap.xml`
- Validate `robots.txt`
- Check internal links and anchors
- Flag missing metadata and canonical mismatches
- Scan HTML, headers, and selected static assets for likely exposed secrets
- Emit deterministic JSON for automation

## Privacy Model

`sitectl` is local-first by default.

- No telemetry
- No third-party service calls
- No uploaded page content
- No external link checking in v1
- Likely secrets are redacted in findings
- HTTP commands print a network summary when requests are made

When you point `sitectl` at a folder, it reads local files only. When you point it at a URL,
it crawls same-origin pages and blocks external navigation.

## Responsible Use

Only run `sitectl` against sites, systems, and build artifacts you own or are authorized to
test. Even though `sitectl` is designed to be conservative and same-origin by default, it
still performs automated crawling and HTTP requests when pointed at a URL.

## Install

The recommended install path matches the other Offband Python CLI tools:

```bash
brew install pipx
pipx ensurepath
pipx install git+https://github.com/offband/sitectl.git
```

After installing, restart your shell if `pipx ensurepath` asks you to, then run:

```bash
sitectl --help
```

Upgrade from GitHub:

```bash
pipx upgrade sitectl
```

Uninstall:

```bash
pipx uninstall sitectl
```

## Install For Development

This repo uses [`uv`](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/offband/sitectl.git
cd sitectl
uv sync --extra dev
```

Run checks:

```bash
uv run pytest
uv run ruff check .
```

Run the CLI from the repo:

```bash
uv run sitectl --help
```

## Quickstart

Audit a static build folder:

```bash
sitectl audit ./dist --base-url https://example.com
```

Write a JSON audit report:

```bash
sitectl audit ./dist --base-url https://example.com --output audit.json
sitectl report audit.json
```

Generate a sitemap:

```bash
sitectl sitemap generate ./dist \
  --base-url https://example.com \
  --output sitemap.xml
```

Validate existing discovery files:

```bash
sitectl sitemap validate ./dist/sitemap.xml
sitectl robots validate ./dist/robots.txt
```

Check internal links:

```bash
sitectl links check ./dist --base-url https://example.com
```

Audit a local dev server:

```bash
sitectl audit http://localhost:3000
```

## Commands

| Command | Purpose |
| --- | --- |
| `sitectl crawl TARGET` | Crawl a local folder or same-origin HTTP target. |
| `sitectl audit TARGET` | Run the v1 site hygiene audit. |
| `sitectl report AUDIT_JSON` | Render a terminal summary from audit JSON. |
| `sitectl sitemap generate TARGET` | Generate sitemap XML from discovered pages. |
| `sitectl sitemap validate FILE_OR_URL` | Validate sitemap XML. |
| `sitectl robots validate FILE_OR_URL` | Validate `robots.txt`. |
| `sitectl links check TARGET` | Check internal links and anchors. |
| `sitectl config path` | Print resolved config file paths. |
| `sitectl config init` | Write a starter config to `~/.sitectl/config.toml`. |
| `sitectl config show` | Print raw or resolved config. |

`TARGET` can be a local folder or an `http://` / `https://` URL.

## Configuration

Every command works with flags. For personal defaults across projects, initialize a global
config:

```bash
sitectl config init
```

That writes:

```text
~/.sitectl/config.toml
```

You can also print the starter config:

```bash
sitectl config init --stdout
```

For repeatable project defaults, add `sitectl.toml` to a repo:

```toml
base_url = "https://example.com"
max_depth = 3
timeout = 10
user_agent = "sitectl/0.1 local-first"
excludes = ["admin/*", "*.draft.html"]
privacy = "strict"
```

Config precedence is:

```text
built-in defaults < ~/.sitectl/config.toml < sitectl.toml or --config < CLI flags
```

Use a project config explicitly with:

```bash
sitectl audit ./dist --config sitectl.toml
```

CLI flags override config values. User-defined `excludes` are appended to built-in safety
excludes such as `/cdn-cgi/*`.

Inspect config:

```bash
sitectl config path
sitectl config show
sitectl config show --resolved
```

## Exit Codes

`sitectl` is designed for CI.

- `0`: command completed without error-level findings
- `1`: crawl errors, broken internal links, invalid XML, or other error-level findings

Warnings are reported but do not currently fail the command unless they are paired with an
error-level finding.

## Current Status

This is an early v1 implementation. It is useful today for static site checks and local
release hygiene, with a deliberately small surface area.

Planned next improvements:

- GitHub Actions workflow
- HTTP fixture test coverage
- Configurable CI strictness with `--fail-on warning|error`
- Richer terminal summaries for JSON reports

## Development Without `uv`

Standard Python tooling also works:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
ruff check .
```
