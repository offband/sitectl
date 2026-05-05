from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from sitectl.audit import run_audit
from sitectl.cli import app
from sitectl.config import DEFAULT_EXCLUDES, SiteConfig, default_config_path, load_config
from sitectl.crawler import crawl
from sitectl.robots import validate_robots_text
from sitectl.security import redact, scan_pages
from sitectl.sitemap import generate_sitemap, validate_sitemap_text

FIXTURE = Path(__file__).parent / "fixtures" / "static_site"


def test_local_crawl_maps_index_urls_and_blocks_external() -> None:
    result = crawl(str(FIXTURE), SiteConfig(), "https://example.test")

    assert [page.url for page in result.pages] == [
        "https://example.test/about",
        "https://example.test",
    ]
    assert result.network.requests == 0


def test_default_excludes_ignore_cloudflare_utility_links(tmp_path: Path) -> None:
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text(
        '<a href="/cdn-cgi/l/email-protection#abc">Email</a><a href="/real-missing">Bad</a>'
    )

    report = run_audit(str(site), SiteConfig(), "https://example.test")
    evidence = {finding.evidence for finding in report.findings}

    assert "https://example.test/cdn-cgi/l/email-protection" not in evidence
    assert "https://example.test/real-missing" in evidence


def test_sitemap_generate_and_validate() -> None:
    result = crawl(str(FIXTURE), SiteConfig(), "https://example.test")
    xml = generate_sitemap(result)

    assert "https://example.test/about" in xml
    assert validate_sitemap_text(xml) == []
    assert validate_sitemap_text("<nope>")[0].code == "sitemap.invalid_xml"


def test_robots_validation() -> None:
    assert validate_robots_text("User-agent: *\nDisallow: /admin\n") == []

    findings = validate_robots_text("Sitemap: /sitemap.xml\nBadLine")

    assert {finding.code for finding in findings} == {
        "robots.relative_sitemap",
        "robots.syntax",
        "robots.no_user_agent",
    }


def test_config_loading(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    config_dir = home / ".sitectl"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text('timeout = 2\nexcludes = ["global/*"]\n')
    monkeypatch.setenv("HOME", str(home))
    config_path = tmp_path / "sitectl.toml"
    config_path.write_text(
        'base_url = "https://example.test"\nmax_depth = 1\nexcludes = ["admin/*"]\n'
    )

    config = load_config(config_path)

    assert config.base_url == "https://example.test"
    assert config.max_depth == 1
    assert config.timeout == 2
    assert config.excludes == (*DEFAULT_EXCLUDES, "global/*", "admin/*")
    assert default_config_path() == config_dir / "config.toml"


def test_secret_redaction() -> None:
    result = crawl(str(FIXTURE), SiteConfig(), "https://example.test")
    findings = scan_pages(result.pages)

    assert findings[0].code == "secret.generic_token"
    assert "[REDACTED]" in findings[0].evidence
    assert redact("short") == "[REDACTED]"


def test_audit_finds_links_metadata_and_secrets() -> None:
    report = run_audit(str(FIXTURE), SiteConfig(), "https://example.test")
    codes = {finding.code for finding in report.findings}

    assert "link.broken_internal" in codes
    assert "link.broken_anchor" in codes
    assert "meta.missing_description" in codes
    assert "secret.generic_token" in codes
    assert "sitemap.missing" in codes
    assert "robots.missing" in codes
    assert report.network.requests == 0


def test_cli_help_and_audit_json(tmp_path: Path) -> None:
    runner = CliRunner()
    help_result = runner.invoke(app, ["crawl", "--help"])
    output = tmp_path / "audit.json"
    audit_result = runner.invoke(
        app,
        ["audit", str(FIXTURE), "--base-url", "https://example.test", "--output", str(output)],
    )

    assert help_result.exit_code == 0
    assert audit_result.exit_code == 1
    data = json.loads(output.read_text())
    assert data["pages_scanned"] == 2
    assert data["network"]["requests"] == 0


def test_config_cli_commands(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    runner = CliRunner()

    init_result = runner.invoke(app, ["config", "init"])
    show_result = runner.invoke(app, ["config", "show", "--resolved"])
    stdout_result = runner.invoke(app, ["config", "init", "--stdout"])

    assert init_result.exit_code == 0
    assert (home / ".sitectl" / "config.toml").exists()
    assert show_result.exit_code == 0
    assert '"privacy": "strict"' in show_result.output
    assert stdout_result.exit_code == 0
    assert "max_depth = 3" in stdout_result.output
