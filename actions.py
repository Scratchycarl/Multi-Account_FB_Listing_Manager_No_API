import re
import subprocess
import os
from playwright.sync_api import sync_playwright

def _create_session_task(account_name):
    script = f"""
from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto('https://www.facebook.com/')
        print("Waiting for page close...")
        page.wait_for_event("close", timeout=0)
        context.storage_state(path='{account_name}_state.json')
        browser.close()
except Exception as e:
    pass
"""
    script_path = f"/tmp/create_fb_session_{account_name}.py"
    with open(script_path, "w") as f:
        f.write(script)
        
    subprocess.Popen(["python3", script_path], cwd="/Users/carl/.openclaw/workspace/fb-marketplace-gui")

def create_new_session(account_name):
    _create_session_task(account_name)
    return {"success": True, "message": "Browser opened! Please log in, handle any 2FA, and then CLOSE the browser window to save your session automatically. Refresh this page when done."}

def delete_session(account_name):
    path = f"{account_name}_state.json"
    if os.path.exists(path):
        os.remove(path)
    return {"success": True}

def view_listing_in_browser(account_id, url):
    # We use a detached subprocess to spawn a visible browser, this way it doesn't block the Flask web server
    script = f"""
from playwright.sync_api import sync_playwright

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state='{account_id}_state.json')
        page = context.new_page()
        page.goto('{url}')
        # Wait infinitely until the user manually closes the page/browser
        page.wait_for_event("close", timeout=0)
        browser.close()
except Exception as e:
    pass
"""
    script_path = f"/tmp/open_fb_browser_{account_id}.py"
    with open(script_path, "w") as f:
        f.write(script)
        
    subprocess.Popen(
        ["python3", script_path], 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL, 
        cwd="/Users/carl/.openclaw/workspace/fb-marketplace-gui"
    )
    return {"success": True, "message": "Browser opened!"}

def mark_out_of_stock(account_id, url):
    state_file = f"{account_id}_state.json"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(storage_state=state_file)
            except Exception as e:
                browser.close()
                return {"success": False, "message": f"Failed to load state for {account_id}: {str(e)}"}

            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded")
            
            # Wait for React to fully render the buttons
            page.wait_for_timeout(5000)
            
            # Approach 1: Use Playwright's robust role/name locators (ignores nested spans)
            btn = page.get_by_role("button", name=re.compile(r"Mark as Sold|Mark out of stock", re.IGNORECASE)).first
            
            if btn.is_visible(timeout=3000):
                btn.click()
                page.wait_for_timeout(3000)
                browser.close()
                return {"success": True, "message": "Marked out of stock / sold!"}
            
            # Approach 2: Direct text match fallback
            for text in ["Mark as Sold", "Mark out of stock"]:
                fallback = page.locator(f"text={text}").first
                if fallback.is_visible(timeout=2000):
                    fallback.click()
                    page.wait_for_timeout(3000)
                    browser.close()
                    return {"success": True, "message": f"Success ({text})!"}
            
            # If we STILL can't find it, take a screenshot so we can see what the headless browser sees
            debug_path = f"debug_{account_id}.png"
            page.screenshot(path=debug_path)
            browser.close()
            return {"success": False, "message": f"Button not found. Saved {debug_path} to see what went wrong."}
                
    except Exception as e:
        return {"success": False, "message": str(e)}
