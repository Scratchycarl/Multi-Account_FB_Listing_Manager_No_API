import os
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from database import save_listing, clear_all_listings, clear_listings_for_account, save_insights

# Global state to track progress in the UI
scrape_state = {
    "is_scraping": False,
    "current_account": "",
    "progress": 0,
    "total": 0,
    "message": ""
}

# Looks for any state files in the directory representing logged-in FB sessions
# e.g., 'account1_state.json', 'carl_state.json'
def get_state_files():
    return [f for f in os.listdir('.') if f.endswith('_state.json')]

def scrape_marketplace_for_account(account_id, state_file_path):
    print(f"Scraping marketplace for account: {account_id}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Load the saved session state
        try:
            context = browser.new_context(storage_state=state_file_path)
        except Exception as e:
            print(f"Failed to load state for {account_id}: {e}")
            browser.close()
            return
            
        page = context.new_page()
        page.goto('https://www.facebook.com/marketplace/you/selling?state=LIVE&status[0]=IN_STOCK')
        
        # Wait for listings to load
        time.sleep(5)
        
        # Scroll to load more items
        for _ in range(3):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # --- NEW PARSING LOGIC FOR 'SELLING' PAGE ---
        import re
        
        # The cards on the 'Selling' page usually have this very specific inline style property
        items = soup.find_all('div', style=lambda value: value and 'card-corner-radius' in value)
        
        for item in items:
            try:
                item_html = str(item)
                
                # 1. URL Extraction: Facebook hides the normal <a> tags, but the item ID is usually buried in the "Boost listing" or similar URLs
                match = re.search(r'target_id=(\d+)', item_html)
                if match:
                    url = f"https://www.facebook.com/marketplace/item/{match.group(1)}"
                else:
                    url = f"https://www.facebook.com/marketplace/you/selling" # Fallback
                    
                # 2. Image Extraction
                img_tag = item.find('img')
                image_url = img_tag['src'] if img_tag else ''
                
                # 3. Title Extraction: We can grab this from the specific styling Facebook uses for the 2-line title wrap
                title = "Unknown"
                title_span = item.find('span', style=lambda v: v and '-webkit-line-clamp: 2' in v)
                if title_span:
                    title = title_span.get_text().strip()
                else:
                    # Fallback to pulling it from the aria-label of the main clickable div
                    clickable_div = item.find('div', attrs={'role': 'button', 'aria-label': True})
                    if clickable_div and not clickable_div['aria-label'].startswith('Mark'):
                        title = clickable_div['aria-label']
                
                # 4. Price Extraction: It's usually the text block containing a currency symbol
                price = "N/A"
                text_content = item.get_text(separator='|')
                parts = [p.strip() for p in text_content.split('|') if p.strip()]
                for part in parts:
                    if '$' in part or 'Free' in part or part.startswith('CA$'):
                        price = part
                        break
                
                # Skip the "Create New Listing" ghost card or any completely empty parsing results
                if title == "Unknown" or title == "Create new listing" or not title:
                    continue
                
                save_listing(account_id, title, price, url, image_url)
            except Exception as e:
                print(f"Error parsing item: {e}")
                
        browser.close()

def scrape_insights_for_account(account_id, state_file_path, period="Last 7 days"):
    print(f"Scraping insights for account: {account_id} for period: {period}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(storage_state=state_file_path)
        except Exception as e:
            print(f"Failed to load state for {account_id}: {e}")
            browser.close()
            return
            
        page = context.new_page()
        page.goto('https://www.facebook.com/marketplace/you/insights')
        
        # Wait for the dashboard to load initially
        time.sleep(5)
        
        # Change the time period if needed
        try:
            combo = page.locator('div[aria-label="Selected time period for insights data"]').first
            if combo.is_visible(timeout=3000):
                combo.click()
                time.sleep(1)
                
                # Look for the option with the matching text (e.g., "Last 14 days")
                option = page.locator(f'span:text-is("{period}")').first
                if option.is_visible(timeout=3000):
                    option.click()
                    # Wait for network requests and DOM updates to settle after changing the date range
                    time.sleep(6)
                else:
                    print(f"Could not find period option: {period}")
                    time.sleep(2)
        except Exception as e:
            print(f"Error changing time period: {e}")
            time.sleep(2)
        
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        metrics = {"clicks": "0", "saves": "0", "shares": "0", "followers": "0"}
        
        labels_map = {
            "clicks on listings": "clicks",
            "listing saves": "saves",
            "listing shares": "shares",
            "marketplace followers": "followers"
        }
        
        # Facebook uses span[dir="auto"] for most text elements on this dashboard
        # The number value almost always precedes the label text in the DOM
        spans = soup.find_all('span', dir='auto')
        texts = [s.get_text().strip() for s in spans if s.get_text().strip()]
        
        for i, text in enumerate(texts):
            clean_text = text.lower()
            if clean_text in labels_map:
                key = labels_map[clean_text]
                # Grab the text block immediately before the label
                if i > 0:
                    val = texts[i-1]
                    # Double check it actually contains digits (e.g. "788" or "1.2K")
                    if any(char.isdigit() for char in val):
                        metrics[key] = val
                    
        save_insights(account_id, metrics["clicks"], metrics["saves"], metrics["shares"], metrics["followers"], period)
        browser.close()

def run_insight_scrapers(selected_accounts=None, period="Last 7 days"):
    global scrape_state
    
    all_state_files = get_state_files()
    if not all_state_files:
        return

    if selected_accounts:
        state_files = [f"{acc}_state.json" for acc in selected_accounts if f"{acc}_state.json" in all_state_files]
    else:
        state_files = all_state_files

    if not state_files:
        return
        
    scrape_state["is_scraping"] = True
    scrape_state["total"] = len(state_files)
    scrape_state["progress"] = 0
    scrape_state["message"] = "Starting insights scrape..."
        
    try:
        for index, state_file in enumerate(state_files):
            account_id = state_file.replace('_state.json', '')
            scrape_state["current_account"] = account_id
            scrape_state["progress"] = index + 1
            scrape_state["message"] = f"Pulling insights for {account_id} ({index + 1}/{len(state_files)})..."
            
            scrape_insights_for_account(account_id, state_file, period)
    except Exception as e:
        print(f"Error during insights loop: {e}")
    finally:
        scrape_state["is_scraping"] = False
        scrape_state["message"] = "Finished!"
        scrape_state["current_account"] = ""
        scrape_state["progress"] = 0
        scrape_state["total"] = 0

def run_scrapers(selected_accounts=None):
    global scrape_state
    
    all_state_files = get_state_files()
    if not all_state_files:
        print("No state files found.")
        return

    # Determine which to scrape
    if selected_accounts:
        state_files = [f"{acc}_state.json" for acc in selected_accounts if f"{acc}_state.json" in all_state_files]
    else:
        state_files = all_state_files

    if not state_files:
        print("No valid selected accounts found.")
        return
        
    scrape_state["is_scraping"] = True
    scrape_state["total"] = len(state_files)
    scrape_state["progress"] = 0
    scrape_state["message"] = "Clearing old listings from database..."
    
    print(scrape_state["message"])
    
    # Only clear the database for the accounts we are about to re-scrape
    if not selected_accounts:
        clear_all_listings()
    else:
        for state_file in state_files:
            acc_id = state_file.replace('_state.json', '')
            clear_listings_for_account(acc_id)
        
    try:
        for index, state_file in enumerate(state_files):
            account_id = state_file.replace('_state.json', '')
            scrape_state["current_account"] = account_id
            scrape_state["progress"] = index + 1
            scrape_state["message"] = f"Scraping account {account_id} ({index + 1}/{len(state_files)})..."
            
            scrape_marketplace_for_account(account_id, state_file)
    except Exception as e:
        print(f"Error during scraping loop: {e}")
    finally:
        scrape_state["is_scraping"] = False
        scrape_state["message"] = "Finished!"
        scrape_state["current_account"] = ""
        scrape_state["progress"] = 0
        scrape_state["total"] = 0

if __name__ == '__main__':
    run_scrapers()
