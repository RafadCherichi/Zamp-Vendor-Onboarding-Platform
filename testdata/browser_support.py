"""Portable browser launch for isolated acceptance and demo scripts."""
import os
from playwright.sync_api import Error


def launch_browser(playwright, **options):
    executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if executable:
        return playwright.chromium.launch(executable_path=executable, **options)
    try:
        return playwright.chromium.launch(**options)
    except Error as error:
        if "executable doesn't exist" not in str(error).lower():
            raise
        # Use an installed Chrome when the bundled test engine is unavailable.
        return playwright.chromium.launch(channel="chrome", **options)
