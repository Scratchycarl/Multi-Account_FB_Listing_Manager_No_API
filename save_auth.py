import os
from playwright.sync_api import sync_playwright

def main():
    print("=== Facebook Session Saver ===")
    account_name = input("Enter a name for this account (e.g., 'account1', 'burnerA'): ").strip()
    if not account_name:
        print("Account name cannot be empty. Exiting.")
        return

    state_file = f"{account_name}_state.json"

    with sync_playwright() as p:
        print(f"\nLaunching browser to log into {account_name}...")
        # Launch headful so you can manually log in and handle 2FA
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://www.facebook.com/")
        
        print("\n*** ACTION REQUIRED ***")
        print("1. Log in to Facebook in the browser window that just opened.")
        print("2. Complete any 2FA or Captcha checks.")
        print("3. Once you are fully logged in and see your News Feed, come back to this terminal.")
        input("\nPress ENTER here ONLY AFTER you are fully logged in... ")

        # Save the session state
        context.storage_state(path=state_file)
        print(f"\n✅ Boom! Session saved successfully to {state_file}!")

        browser.close()

if __name__ == "__main__":
    main()
