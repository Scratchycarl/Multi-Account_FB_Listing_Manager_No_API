# FB Marketplace Manager GUI

A powerful, multi-account Facebook Marketplace management dashboard built with Flask, Playwright, and SQLite. 

This tool allows you to seamlessly manage, view, scrape, and pull insights for multiple Facebook Marketplace seller accounts from a centralized, mobile-friendly web app on your local network.

## Features

- **Multi-Account Support**: Add and manage as many Facebook burner/seller accounts as you need.
- **Background Scraping**: Uses a headless Playwright browser to scrape your active listings ("Selling" page) across all accounts without freezing up the UI.
- **Smart "Mark Sold"**: Automatically navigates to individual listings in the background, clicks "Mark out of stock / Sold", deletes the local database entry, and triggers a background re-scrape.
- **Local Browser View**: Instantly spawns a visible, isolated Chromium window logged into the correct account when you click "View" on the host machine.
- **Mobile Friendly (PWA)**: Access the dashboard via your phone or tablet on your local Wi-Fi. "View" buttons intelligently open native Safari tabs when used on a remote device.
- **Insights History**: Scrapes and stacks your Facebook Marketplace performance metrics (Clicks, Saves, Shares, Followers) over time, separated by time ranges (7/14/30 days).

## Setup & Installation

**Prerequisites:** You must have Python 3 installed on your machine.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Scratchycarl/FB_Marketplace_Manager_GUI.git
   cd FB_Marketplace_Manager_GUI
   ```

2. **Install Python Dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Install Playwright Browsers:**
   Playwright requires its own specific browser binaries to run headless/headful automation.
   ```bash
   playwright install chromium
   ```

4. **Run the App:**
   ```bash
   python3 app.py
   ```

5. **Access the Dashboard:**
   - On the machine running the code: Open `http://localhost:5000`
   - On your phone/tablet: Open `http://<YOUR_COMPUTER_IP_ADDRESS>:5000`

## Adding Accounts

1. Navigate to the **"Accounts / Config"** tab in the web GUI.
2. Enter a nickname for your account (e.g., `account1` or `john_doe`).
3. Click **"Open Login Window"**. A physical browser window will pop up on your host machine.
4. Manually log into Facebook in that window. Complete any 2FA or captcha requests.
5. Once you are fully logged in and see the Facebook homepage, **close the browser window** (click the red 'X').
6. The app will automatically capture your session state and save it securely as `account_name_state.json`.

*Note: Session state files (`*_state.json`) contain sensitive authentication cookies and are ignored by Git.*

## Disclaimer

This tool uses Playwright for web scraping. Facebook frequently changes its DOM structure, CSS classes, and anti-bot mechanisms. If the scraper stops pulling titles or insights, the BeautifulSoup HTML selectors in `scraper.py` may need to be updated to match Facebook's latest frontend changes.