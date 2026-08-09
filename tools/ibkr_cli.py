#!/usr/bin/env python3
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""IBKR Flex CLI — download trades via IBKR Flex Query.

Subcommands:
  fetch      Request and download a Flex Query report to an XML file.

Requires env vars IBKR_FLEX_TOKEN (or FLEX_TOKEN) and IBKR_FLEX_QUERY_ID (or FLEX_QUERY_ID).
These are read from the environment or a `.env` file next to this script (or in the project root).
"""

import argparse
import logging
import os
import sys
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.WARNING, format="%(levelname)s [%(name)s] %(message)s")

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore[assignment]

if load_dotenv is not None:
    # Look for a .env in the current working directory, then next to the tool, then in the project root.
    _here = Path(__file__).resolve().parent
    for _candidate in (Path.cwd() / ".env", _here / ".env", _here.parent / ".env"):
        if _candidate.exists():
            load_dotenv(_candidate)
            break

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    sys.exit("rich not installed. Run: pip install rich")

console = Console()

DEFAULT_OUTPUT_FILE = Path.cwd() / "ibkr_flex_query.xml"
FLEX_API_VERSION = "3"
FLEX_BASE_URL = "https://gdcdyn.interactivebrokers.com/Universal/servlet"
POLL_INTERVAL = 2
MAX_POLL_ATTEMPTS = 30


def _get_env_or_exit(keys: list[str]) -> str:
    """Check a list of env var keys and return the first one found."""
    for key in keys:
        val = os.environ.get(key)
        if val:
            return val.strip()
    sys.exit(f"ERROR: Missing environment variable. Set one of: {', '.join(keys)} in .env or the environment.")


def _text(elem: ET.Element | None) -> str | None:
    if elem is None:
        return None
    return (elem.text or "").strip() or None


def fetch_flex_report(token: str, query_id: str, period: str | None = None) -> str:
    """Execute the two-step Flex API request-and-poll workflow."""
    # 1. SendRequest
    url = f"{FLEX_BASE_URL}/FlexStatementService.SendRequest"
    params = {"t": token, "q": query_id, "v": FLEX_API_VERSION}
    if period:
        params["period"] = period
    
    query_string = urllib.parse.urlencode(params)
    full_url = f"{url}?{query_string}"
    
    req = urllib.request.Request(full_url, headers={"User-Agent": "TradeSensei-IBKRCli/1.0"})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            xml_data = response.read()
    except urllib.error.HTTPError as exc:
        sys.exit(f"ERROR: HTTP {exc.code} during Flex SendRequest: {exc.read().decode('utf-8', errors='ignore')}")
    except Exception as exc:
        sys.exit(f"ERROR: Failed to contact IBKR Flex API: {exc}")
        
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as exc:
        sys.exit(f"ERROR: Invalid XML in SendRequest response: {exc}")
        
    status = _text(root.find("Status"))
    if status != "Success":
        err = _text(root.find("ErrorMessage")) or "Unknown error"
        code = _text(root.find("ErrorCode"))
        sys.exit(f"ERROR: Flex SendRequest failed (Code {code}): {err}")
        
    ref_code = _text(root.find("ReferenceCode"))
    if not ref_code:
        sys.exit("ERROR: Invalid Flex SendRequest response: missing ReferenceCode.")
        
    console.print(f"[dim]Got ReferenceCode: {ref_code}. Waiting for report generation...[/dim]")
    
    # 2. GetStatement
    get_url = f"{FLEX_BASE_URL}/FlexStatementService.GetStatement"
    get_params = {"t": token, "q": ref_code, "v": FLEX_API_VERSION}
    get_query = urllib.parse.urlencode(get_params)
    get_full_url = f"{get_url}?{get_query}"
    
    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        time.sleep(POLL_INTERVAL)
        
        req = urllib.request.Request(get_full_url, headers={"User-Agent": "TradeSensei-IBKRCli/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                xml_data = response.read()
        except urllib.error.HTTPError as exc:
            sys.exit(f"ERROR: HTTP {exc.code} during Flex GetStatement: {exc.read().decode('utf-8', errors='ignore')}")
        except Exception as exc:
            sys.exit(f"ERROR: Failed to poll Flex report: {exc}")
            
        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError as exc:
            sys.exit(f"ERROR: Invalid XML in GetStatement response: {exc}")
            
        if root.tag == "FlexQueryResponse":
            return xml_data.decode("utf-8")
            
        status = _text(root.find("Status"))
        if status == "Warn":
            code = _text(root.find("ErrorCode"))
            if code and "1018" in code:
                # 1018 = report still being generated, keep polling.
                continue
                
        err = _text(root.find("ErrorMessage")) or "Unknown error"
        sys.exit(f"ERROR: Flex GetStatement failed (status={status}): {err}")
        
    sys.exit(f"ERROR: Report not ready after {MAX_POLL_ATTEMPTS} attempts.")


def cmd_fetch(args) -> None:
    """Fetch a Flex Query report and save to XML."""
    token = _get_env_or_exit(["IBKR_FLEX_TOKEN", "FLEX_TOKEN"])
    query_id = _get_env_or_exit(["IBKR_FLEX_QUERY_ID", "FLEX_QUERY_ID"])
    
    period = args.period
    if args.since:
        now = datetime.now(UTC)
        period = (now - timedelta(days=args.since)).strftime("%Y%m%d")
    
    console.print(
        Panel(
            f"[bold]Query ID:[/bold] {query_id}\n"
            f"[bold]Period:[/bold] {period or 'Default (from query config)'}\n"
            f"[bold]Output:[/bold] {args.output}",
            title="[bold cyan]IBKR Flex Fetcher",
            border_style="cyan",
        )
    )
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Requesting Flex Query...", total=None)
        
        xml_result = fetch_flex_report(token, query_id, period)
        
        progress.update(task, description="Saving output...")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(xml_result, encoding="utf-8")
        
    console.print(f"\n[green]✓ Saved → [bold]{args.output}[/bold][/green]")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="IBKR CLI — manage and fetch Flex Query reports.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    fetch_parser = subparsers.add_parser(
        "fetch",
        help="Fetch a Flex Query report and save to XML.",
        description=(
            "Requests a Flex Query from IBKR and waits for its generation. "
            "You can narrow down the timeframe using either --period or --since. "
            "If neither is provided, IBKR will use the default timeframe configured "
            "for your query in the web portal."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    # Mutually exclusive group for period/since
    group = fetch_parser.add_mutually_exclusive_group()
    group.add_argument(
        "--period", 
        help="Specific period filter. IBKR accepts formats like YYYYMMDD (e.g. 20230101) or ranges (e.g. 20230101-20231231)."
    )
    group.add_argument(
        "--since", 
        type=int,
        metavar="DAYS",
        help="Fetch trades from the last X days. Automatically formats to YYYYMMDD and passes as period."
    )
    
    fetch_parser.add_argument("--output", "-o", type=Path, default=DEFAULT_OUTPUT_FILE, help="Output XML file path")
    
    args = parser.parse_args()
    
    if args.command == "fetch":
        cmd_fetch(args)


if __name__ == "__main__":
    main()
