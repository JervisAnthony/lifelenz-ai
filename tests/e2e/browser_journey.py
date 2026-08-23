"""Real-browser MVP journey for the LifeLenz web and API boundaries."""

from __future__ import annotations

import os
import re
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

BASE_URL = os.environ.get("LIFELENZ_E2E_BASE_URL", "http://127.0.0.1:4173").rstrip("/")
ARTIFACT_DIR = Path(os.environ.get("LIFELENZ_E2E_ARTIFACT_DIR", ".e2e-artifacts"))
EMAIL = "browser-e2e@example.com"
ACCOUNT_PASSWORD_ENV = "LIFELENZ_E2E_ACCOUNT_PASSWORD"


def account_password() -> str:
    """Return the externally supplied synthetic E2E account password."""
    value = os.environ.get(ACCOUNT_PASSWORD_ENV)
    if not value:
        raise RuntimeError(f"{ACCOUNT_PASSWORD_ENV} must be set for browser E2E runs")
    if len(value) < 12:
        raise RuntimeError(f"{ACCOUNT_PASSWORD_ENV} must contain at least 12 characters")
    return value


def app_url(path: str) -> str:
    """Return one absolute web URL for the configured E2E origin."""
    return f"{BASE_URL}{path}"


def expect_definition_value(page: Page, label: str, value: str) -> None:
    """Assert one definition-list value by its visible term."""
    term = page.get_by_text(label, exact=True)
    value_locator = term.locator("xpath=following-sibling::dd")
    expect(value_locator).to_have_text(value)


def complete_registration_and_profile(page: Page) -> None:
    """Create an account, authenticate it, and complete first-time onboarding."""
    password = account_password()
    page.goto(app_url("/register"))
    expect(page.get_by_role("heading", name="Create your account")).to_be_visible()
    page.get_by_label("Email address").fill(EMAIL)
    page.get_by_label("Password", exact=True).fill(password)
    page.get_by_label("Confirm password").fill(password)
    page.get_by_role("button", name="Create account").click()

    expect(page.get_by_text("Account created. Sign in to continue.")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/login$"))
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Sign in").click()

    expect(page.get_by_role("heading", name="Set up your wellness profile")).to_be_visible()
    page.get_by_label("Display name (optional)").fill("Browser E2E")
    page.get_by_role("button", name="Complete setup").click()

    expect(page.get_by_role("heading", name="Wellness summary")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/app/?$"))


def exercise_record_lifecycle(page: Page) -> None:
    """Create, correct, and deliberately delete one hydration record."""
    page.goto(app_url("/app/records"))
    expect(page.get_by_role("heading", name="Wellness records", exact=True)).to_be_visible()
    page.get_by_role("button", name=re.compile(r"^Hydration\b")).click()
    page.get_by_label("Volume (milliliters)").fill("500")
    page.get_by_role("button", name="Save hydration record").click()
    expect(page.get_by_text("Hydration record saved.")).to_be_visible()

    page.get_by_role("button", name="Browse full history").click()
    expect(page.get_by_text("1 record found")).to_be_visible()
    history = page.get_by_role("list", name="Filtered wellness record history")
    history.get_by_role("button", name="Correct record").click()

    correction = page.locator('section[aria-label="Correct hydration record"]')
    expect(correction).to_be_visible()
    correction.get_by_label("Volume (milliliters)").fill("600")
    correction.get_by_role("button", name="Save hydration record").click()
    expect(page.get_by_text("Hydration record corrected.")).to_be_visible()

    history = page.get_by_role("list", name="Filtered wellness record history")
    history.get_by_role("button", name="Delete record").click()
    confirmation = page.get_by_role("group", name="Delete hydration record")
    confirmation.get_by_role("button", name="Delete record").click()
    expect(page.get_by_text("Hydration record deleted.")).to_be_visible()
    expect(page.get_by_text("No records match these filters")).to_be_visible()


def exercise_csv_import(page: Page) -> None:
    """Validate and commit one synthetic hydration CSV through the browser."""
    page.goto(app_url("/app/records/import"))
    expect(page.get_by_role("heading", name="Select and validate a CSV")).to_be_visible()
    page.get_by_label("Record category").select_option("hydration")
    csv_content = (
        "recorded_at,volume_value,volume_unit,beverage_type,notes\n"
        "2026-08-23T00:00:00+00:00,750,milliliters,water,browser e2e import\n"
    )
    page.get_by_label("CSV file").set_input_files(
        {
            "name": "hydration-e2e.csv",
            "mimeType": "text/csv",
            "buffer": csv_content.encode("utf-8"),
        }
    )
    expect(page.get_by_text(re.compile(r"Selected hydration-e2e\.csv"))).to_be_visible()
    page.get_by_role("button", name="Validate CSV").click()

    expect(page.get_by_role("heading", name="Validation report")).to_be_visible()
    expect_definition_value(page, "Total rows", "1")
    expect_definition_value(page, "Invalid rows", "0")
    expect_definition_value(page, "Duplicate rows", "0")
    expect_definition_value(page, "Ready rows", "1")
    expect(page.get_by_text("No validation issues were reported.")).to_be_visible()

    page.get_by_role("button", name="Import ready rows").click()
    expect(
        page.get_by_text("Import confirmed: 1 row imported and 0 duplicates skipped.")
    ).to_be_visible()


def verify_dashboard_summary(page: Page) -> None:
    """Confirm imported data reaches the real dashboard summary workflow."""
    page.goto(app_url("/app"))
    expect(page.get_by_role("heading", name="Wellness summary")).to_be_visible()
    expect(page.get_by_role("heading", name="Water intake")).to_be_visible()
    expect(page.get_by_text("750 mL").first).to_be_visible()
    expect(
        page.get_by_text("No mathematical direction is available from this summary yet.")
    ).to_be_visible()


def exercise_goal_creation(page: Page) -> None:
    """Create one user-defined goal through the authenticated web workflow."""
    page.goto(app_url("/app/goals"))
    expect(page.get_by_role("heading", name="Wellness goals")).to_be_visible()
    page.get_by_label("Metric").select_option("water_intake")
    page.get_by_label("Target value").fill("2000")
    page.get_by_label("Status").select_option("active")
    page.get_by_label("Title (optional)").fill("Hydration intention")
    page.get_by_role("button", name="Create goal").click()

    expect(page.get_by_text("Wellness goal created.")).to_be_visible()
    expect(page.get_by_role("heading", name="Hydration intention")).to_be_visible()
    expect(page.get_by_text("2,000 milliliters")).to_be_visible()


def verify_logout_boundary(page: Page) -> None:
    """Verify client logout and subsequent protected-route redirection."""
    page.get_by_role("button", name="Sign out").click()
    expect(page.get_by_role("heading", name="Welcome back")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/login$"))

    page.goto(app_url("/app"))
    expect(page.get_by_role("heading", name="Welcome back")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/login$"))


def run_journey(page: Page) -> None:
    """Exercise the critical MVP browser journey against live services."""
    complete_registration_and_profile(page)
    exercise_record_lifecycle(page)
    exercise_csv_import(page)
    verify_dashboard_summary(page)
    exercise_goal_creation(page)
    verify_logout_boundary(page)


def main() -> None:
    """Launch Chromium and run the isolated browser journey."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    page_errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(locale="en-US", timezone_id="UTC")
        page = context.new_page()
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        try:
            run_journey(page)
            if page_errors:
                raise AssertionError(f"Browser page errors were reported: {page_errors}")
        except Exception:
            page.screenshot(path=str(ARTIFACT_DIR / "browser-e2e-failure.png"), full_page=True)
            raise
        finally:
            context.close()
            browser.close()

    print("LifeLenz browser E2E journey passed.")


if __name__ == "__main__":
    main()
