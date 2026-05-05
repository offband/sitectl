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

## Install For Development

This repo uses [`uv`](https://github.com/astral-sh/uv).

```bash
git clone <your-remote-url> sitectl
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
uv run sitectl audit ./dist --base-url https://example.com
```

Write a JSON audit report:

```bash
uv run sitectl audit ./dist --base-url https://example.com --output audit.json
uv run sitectl report audit.json
```

Generate a sitemap:

```bash
uv run sitectl sitemap generate ./dist \
  --base-url https://example.com \
  --output sitemap.xml
```

Validate existing discovery files:

```bash
uv run sitectl sitemap validate ./dist/sitemap.xml
uv run sitectl robots validate ./dist/robots.txt
```

Check internal links:

```bash
uv run sitectl links check ./dist --base-url https://example.com
```

Audit a local dev server:

```bash
uv run sitectl audit http://localhost:3000
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

`TARGET` can be a local folder or an `http://` / `https://` URL.

## Configuration

Every command works with flags. For personal defaults across projects, copy the example
config to `~/.sitectl`:

```bash
cp .sitectl.example ~/.sitectl
```

For repeatable project defaults, add `sitectl.toml`:

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
built-in defaults < ~/.sitectl < sitectl.toml or --config < CLI flags
```

Use a project config explicitly with:

```bash
uv run sitectl audit ./dist --config sitectl.toml
```

CLI flags override config values. User-defined `excludes` are appended to built-in safety
excludes such as `/cdn-cgi/*`.

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
- `sitectl config show` and `sitectl config init`
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
