from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from sitectl.audit import run_audit
from sitectl.config import (
    SiteConfig,
    default_config_path,
    dump_default_config,
    dump_resolved_config,
    load_config,
    resolved_config_paths,
)
from sitectl.crawler import crawl, fetch_text
from sitectl.models import Finding
from sitectl.reporting import (
    crawl_to_dict,
    exit_code,
    print_audit,
    print_crawl,
    print_findings,
    write_json,
)
from sitectl.robots import read_robots, validate_robots_text
from sitectl.sitemap import generate_sitemap, read_sitemap, validate_sitemap_text

app = typer.Typer(help="Local-first site hygiene CLI.")
sitemap_app = typer.Typer(help="Generate and validate sitemaps.")
robots_app = typer.Typer(help="Validate robots.txt files.")
links_app = typer.Typer(help="Check internal links.")
config_app = typer.Typer(help="Manage sitectl config files.")
app.add_typer(sitemap_app, name="sitemap")
app.add_typer(robots_app, name="robots")
app.add_typer(links_app, name="links")
app.add_typer(config_app, name="config")


ConfigOpt = Annotated[Path | None, typer.Option("--config", help="Optional config TOML path.")]
BaseUrlOpt = Annotated[
    str | None, typer.Option("--base-url", help="Base URL for local folder targets.")
]
OutputOpt = Annotated[
    str | None, typer.Option("--output", "-o", help="Write JSON or artifact output path.")
]
JsonOpt = Annotated[bool, typer.Option("--json", help="Emit JSON to stdout.")]


@app.command(name="crawl")
def crawl_cmd(
    target: Annotated[str | None, typer.Argument(help="Local folder or HTTP URL to crawl.")] = None,
    config: ConfigOpt = None,
    base_url: BaseUrlOpt = None,
    output: OutputOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """Crawl a local folder or HTTP target.

    Examples:

      sitectl crawl https://example.com
      sitectl crawl ./dist --base-url https://example.com
    """
    target = _require_target(target, base_url, "crawl")
    cfg = _merge(load_config(config), base_url=base_url, output=output)
    result = crawl(target, cfg, cfg.base_url)
    data = crawl_to_dict(result)
    if output or json_output:
        write_json(data, output)
    else:
        print_crawl(result)
    raise typer.Exit(1 if result.errors else 0)


@sitemap_app.command("generate")
def sitemap_generate(
    target: Annotated[str | None, typer.Argument(help="Local folder or HTTP URL to crawl.")] = None,
    base_url: Annotated[
        str | None,
        typer.Option("--base-url", help="Required when TARGET is a local folder."),
    ] = None,
    config: ConfigOpt = None,
    output: Annotated[
        str | None, typer.Option("--output", "-o", help="Write sitemap XML path.")
    ] = None,
) -> None:
    """Generate sitemap XML from discovered pages.

    Examples:

      sitectl sitemap generate ./dist --base-url https://example.com
      sitectl sitemap generate https://example.com
    """
    target = _require_target(target, base_url, "sitemap generate")
    cfg = _merge(load_config(config), base_url=base_url)
    result = crawl(target, cfg, cfg.base_url)
    xml = generate_sitemap(result)
    if output:
        Path(output).write_text(xml + "\n")
    else:
        typer.echo(xml)
    raise typer.Exit(1 if result.errors else 0)


@sitemap_app.command("validate")
def sitemap_validate(
    source: Annotated[str, typer.Argument(help="Sitemap file path or HTTP URL.")],
    config: ConfigOpt = None,
) -> None:
    """Validate a sitemap file or URL."""
    text = _read_source(source, load_config(config))
    findings = validate_sitemap_text(text, source)
    print_findings(findings)
    raise typer.Exit(exit_code(findings))


@robots_app.command("validate")
def robots_validate(
    source: Annotated[str, typer.Argument(help="robots.txt file path or HTTP URL.")],
    config: ConfigOpt = None,
) -> None:
    """Validate a robots.txt file or URL."""
    text = _read_source(source, load_config(config), robots=True)
    findings = validate_robots_text(text, source)
    print_findings(findings)
    raise typer.Exit(exit_code(findings))


@links_app.command("check")
def links_check(
    target: Annotated[str | None, typer.Argument(help="Local folder or HTTP URL to crawl.")] = None,
    config: ConfigOpt = None,
    base_url: BaseUrlOpt = None,
    output: OutputOpt = None,
) -> None:
    """Check internal links and anchors.

    Examples:

      sitectl links check https://example.com
      sitectl links check ./dist --base-url https://example.com
    """
    from sitectl.links import check_links

    target = _require_target(target, base_url, "links check")
    cfg = _merge(load_config(config), base_url=base_url, output=output)
    result = crawl(target, cfg, cfg.base_url)
    findings = check_links(result)
    if output:
        write_json({"findings": [asdict(finding) for finding in findings]}, output)
    else:
        print_findings(findings)
    raise typer.Exit(exit_code(findings))


@app.command()
def audit(
    target: Annotated[str | None, typer.Argument(help="Local folder or HTTP URL to audit.")] = None,
    config: ConfigOpt = None,
    base_url: BaseUrlOpt = None,
    output: OutputOpt = None,
    json_output: JsonOpt = False,
) -> None:
    """Run the v1 site hygiene audit.

    Examples:

      sitectl audit https://example.com
      sitectl audit ./dist --base-url https://example.com
    """
    target = _require_target(target, base_url, "audit")
    cfg = _merge(load_config(config), base_url=base_url, output=output)
    report = run_audit(target, cfg, cfg.base_url)
    if output or json_output:
        write_json(report.to_dict(), output)
    else:
        print_audit(report)
    raise typer.Exit(exit_code(report.findings))


@app.command()
def report(
    audit_json: Annotated[Path, typer.Argument(help="Audit JSON file produced by sitectl audit.")],
) -> None:
    """Render a terminal summary from audit JSON."""
    data = json.loads(audit_json.read_text())
    findings = [Finding(**finding) for finding in data.get("findings", [])]
    print_findings(findings)


@config_app.command("path")
def config_path(
    config: ConfigOpt = None,
) -> None:
    """Print resolved config file paths."""
    paths = resolved_config_paths(config)
    if paths:
        for path in paths:
            typer.echo(path)
    else:
        typer.echo(default_config_path())


@config_app.command("init")
def config_init(
    config: ConfigOpt = None,
    force: Annotated[
        bool, typer.Option("--force", help="Overwrite an existing config file.")
    ] = False,
    stdout: Annotated[
        bool, typer.Option("--stdout", help="Print config instead of writing it.")
    ] = False,
) -> None:
    """Write or print a starter config."""
    content = dump_default_config()
    if stdout:
        typer.echo(content, nl=False)
        return
    target = config or default_config_path()
    if target.exists() and not force:
        raise typer.BadParameter(f"config file already exists at {target}; use --force")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    typer.echo(f"Wrote {target}")


@config_app.command("show")
def config_show(
    config: ConfigOpt = None,
    resolved: Annotated[bool, typer.Option("--resolved", help="Print merged config.")] = False,
) -> None:
    """Print raw or resolved config."""
    if resolved:
        typer.echo(json.dumps(dump_resolved_config(load_config(config)), indent=2, sort_keys=True))
        return
    paths = resolved_config_paths(config)
    if not paths:
        typer.echo(dump_default_config(), nl=False)
        return
    for index, path in enumerate(paths):
        if index:
            typer.echo()
        typer.echo(f"# {path}")
        typer.echo(path.read_text(), nl=False)


def _read_source(source: str, config: SiteConfig, robots: bool = False) -> str:
    if source.startswith(("http://", "https://")):
        return fetch_text(source, config)
    return read_robots(source) if robots else read_sitemap(source)


def _require_target(target: str | None, base_url: str | None, command: str) -> str:
    if target:
        return target
    if base_url and base_url.startswith(("http://", "https://")):
        typer.secho(
            f"Missing TARGET. For a live site, put the URL after the command:\n\n"
            f"  sitectl {command} {base_url}\n\n"
            "--base-url is only for local folder targets, for example:\n\n"
            f"  sitectl {command} ./dist --base-url {base_url}",
            fg=typer.colors.RED,
            err=True,
        )
    else:
        typer.secho(
            f"Missing TARGET.\n\n"
            f"Examples:\n"
            f"  sitectl {command} https://example.com\n"
            f"  sitectl {command} ./dist --base-url https://example.com",
            fg=typer.colors.RED,
            err=True,
        )
    raise typer.Exit(2)


def _merge(
    config: SiteConfig,
    *,
    base_url: str | None = None,
    output: str | None = None,
) -> SiteConfig:
    return SiteConfig(
        base_url=base_url or config.base_url,
        excludes=config.excludes,
        max_depth=config.max_depth,
        timeout=config.timeout,
        user_agent=config.user_agent,
        output=output or config.output,
        privacy=config.privacy,
    )


def main() -> None:
    app()
