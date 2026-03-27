import asyncio
import argparse
import os
import sys
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

ALL_PAGES = {
    "dashboard": "/dashboard",
    "trades": "/dashboard/trades",
    "playbooks": "/dashboard/playbooks",
    "reports-overview": "/dashboard/reports/overview",
    "reports-monthly": "/dashboard/reports/monthly",
    "reports-yearly": "/dashboard/reports/yearly",
    "reports-calendar": "/dashboard/reports/calendar",
    "reports-weekday": "/dashboard/reports/weekday",
    "reports-hourly": "/dashboard/reports/hourly",
    "import": "/dashboard/import",
    "settings": "/dashboard/settings",
    "accounts": "/dashboard/accounts",
    "connections": "/dashboard/connections",
    "tags": "/dashboard/tags",
    "tax": "/dashboard/tax",
    "help": "/help",
}


async def login(page, base_url: str, username: str, password: str) -> None:
    """Navigate to login page and authenticate.

    Raises SystemExit with a descriptive message if login fails.
    """
    login_url = f"{base_url}/login"
    print(f"[login] Navigating to {login_url}...")
    await page.goto(login_url)
    await page.wait_for_load_state("networkidle")

    # Fill credentials using the actual field IDs (#username / #password)
    try:
        await page.wait_for_selector("#username", timeout=10_000)
    except PlaywrightTimeout:
        print(
            "[error] Login page did not load — could not find #username field.",
            file=sys.stderr,
        )
        sys.exit(1)

    await page.fill("#username", username)
    await page.fill("#password", password)
    await page.click('button[type="submit"]')

    # Wait for successful redirect to /dashboard
    try:
        await page.wait_for_url("**/dashboard**", timeout=10_000)
    except PlaywrightTimeout:
        # Try to surface an error message shown on the page
        error_text = ""
        for selector in ['[role="alert"]', '[class*="error"]', '[class*="alert"]']:
            try:
                el = page.locator(selector).first
                if await el.is_visible():
                    error_text = await el.inner_text()
                    break
            except Exception:
                pass

        msg = f"Login failed (still at {page.url})"
        if error_text:
            msg += f" — server message: {error_text.strip()}"
        print(f"[error] {msg}", file=sys.stderr)
        sys.exit(1)

    print("[login] Login successful.")


async def capture_page(page, name: str, url: str, save_dir: str) -> None:
    """Navigate to *url* and save a full-page screenshot.

    Uses networkidle for most pages, but falls back to domcontentloaded + a
    fixed sleep for pages that keep long-polling or WebSocket connections open.
    """
    print(f"[capture] {name}  →  {url}")
    try:
        await page.goto(url, wait_until="networkidle", timeout=20_000)
    except Exception:
        # Some pages hold open connections (SSE/WS/polling) and never reach
        # networkidle — use domcontentloaded instead
        await page.goto(url, wait_until="domcontentloaded", timeout=20_000)

    # Extra wait for charts / animations to settle
    await asyncio.sleep(2)

    # Sanity check: detect silent auth redirect back to login page
    if "/login" in page.url:
        raise RuntimeError(
            f"Session expired — redirected to login while capturing '{name}'"
        )

    out_path = os.path.join(save_dir, f"{name}.png")
    await page.screenshot(path=out_path, full_page=True)
    print(f"           saved: {out_path}")


async def run(args: argparse.Namespace) -> None:
    os.makedirs(args.save_dir, exist_ok=True)

    # Resolve which pages to visit
    if "all" in args.pages:
        pages_to_visit = list(ALL_PAGES.keys())
    else:
        unknown = [p for p in args.pages if p not in ALL_PAGES]
        if unknown:
            print(f"[error] Unknown page(s): {', '.join(unknown)}", file=sys.stderr)
            print(f"        Available: {', '.join(ALL_PAGES)}", file=sys.stderr)
            sys.exit(1)
        pages_to_visit = args.pages

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 1280×900 is a comfortable desktop viewport
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()

        # --- Login (aborts the process on failure) ---
        await login(page, args.base_url, args.username, args.password)

        # --- Screenshot loop ---
        failed: list[str] = []
        for name in pages_to_visit:
            url = f"{args.base_url}{ALL_PAGES[name]}"
            try:
                await capture_page(page, name, url, args.save_dir)
            except Exception as exc:
                print(f"[warn] Failed to capture '{name}': {exc}", file=sys.stderr)
                failed.append(name)

        await browser.close()

        print(
            f"\nDone — {len(pages_to_visit) - len(failed)}/{len(pages_to_visit)} pages captured."
        )
        print(f"Screenshots saved to: {os.path.abspath(args.save_dir)}")
        if failed:
            print(f"[warn] Failed pages: {', '.join(failed)}", file=sys.stderr)
            sys.exit(2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Capture full-page screenshots of the Trade Journal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Available pages: {', '.join(ALL_PAGES)}\n\nUse --pages all to capture everything.",
    )
    parser.add_argument(
        "--base-url", default="http://localhost:3000", help="App base URL"
    )
    parser.add_argument("--username", required=True, help="Login username")
    parser.add_argument("--password", required=True, help="Login password")
    parser.add_argument(
        "--save-dir", default="tmp/screenshots", help="Output directory"
    )
    parser.add_argument(
        "--pages",
        nargs="+",
        default=["all"],
        metavar="PAGE",
        help="Pages to capture (space-separated) or 'all'",
    )

    asyncio.run(run(parser.parse_args()))
