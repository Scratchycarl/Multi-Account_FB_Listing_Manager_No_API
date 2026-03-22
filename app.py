from flask import Flask, render_template, jsonify, request, redirect, url_for
import threading
import glob
import os
from database import init_db, get_all_listings, clear_listings_for_account, get_all_insights
from scraper import run_scrapers, scrape_marketplace_for_account, scrape_state, run_insight_scrapers
from actions import mark_out_of_stock, view_listing_in_browser, create_new_session, delete_session

app = Flask(__name__)

# Initialize the database on startup
init_db()

@app.route('/')
def index():
    # If no state files exist, direct them to configure accounts first
    state_files = glob.glob('*_state.json')
    if not state_files:
        return redirect(url_for('accounts'))
        
    accounts = [f.replace('_state.json', '') for f in state_files]
    listings = get_all_listings()
    return render_template('index.html', listings=listings, accounts=accounts)

@app.route('/accounts')
def accounts():
    state_files = glob.glob('*_state.json')
    accounts = [f.replace('_state.json', '') for f in state_files]
    return render_template('accounts.html', accounts=accounts)

@app.route('/api/accounts/add', methods=['POST'])
def add_account():
    data = request.json
    account_name = data.get('account_name')
    if not account_name:
        return jsonify({"success": False, "message": "Account name missing."})
    
    result = create_new_session(account_name)
    return jsonify(result)

@app.route('/api/accounts/delete', methods=['POST'])
def remove_account():
    data = request.json
    account_name = data.get('account_name')
    if not account_name:
        return jsonify({"success": False})
        
    delete_session(account_name)
    clear_listings_for_account(account_name)
    return jsonify({"success": True})

@app.route('/insights')
def insights():
    state_files = glob.glob('*_state.json')
    if not state_files:
        return redirect(url_for('accounts'))
        
    accounts = [f.replace('_state.json', '') for f in state_files]
    grouped_insights = get_all_insights()
    return render_template('insights.html', accounts=accounts, grouped_insights=grouped_insights)

@app.route('/scrape_insights', methods=['POST'])
def scrape_insights():
    if not scrape_state.get('is_scraping'):
        data = request.json or {}
        selected_accounts = data.get('accounts')
        period = data.get('period', 'Last 7 days')
        thread = threading.Thread(target=run_insight_scrapers, args=(selected_accounts, period))
        thread.start()
        return jsonify({"status": "Started", "is_scraping": True})
    return jsonify({"status": "Already scraping", "is_scraping": True})

@app.route('/scrape', methods=['POST'])
def scrape():
    # Only start if not already scraping
    if not scrape_state.get('is_scraping'):
        data = request.json or {}
        selected_accounts = data.get('accounts')
        thread = threading.Thread(target=run_scrapers, args=(selected_accounts,))
        thread.start()
        return jsonify({"status": "Started", "is_scraping": True})
    return jsonify({"status": "Already scraping", "is_scraping": True})

@app.route('/api/scrape_status')
def get_scrape_status():
    return jsonify(scrape_state)

@app.route('/action/view', methods=['POST'])
def action_view():
    data = request.json
    account_id = data.get('account_id')
    url = data.get('url')
    
    if not account_id or not url:
        return jsonify({"success": False, "message": "Missing account_id or url"})
        
    result = view_listing_in_browser(account_id, url)
    return jsonify(result)

@app.route('/action/out_of_stock', methods=['POST'])
def action_out_of_stock():
    data = request.json
    account_id = data.get('account_id')
    url = data.get('url')
    
    if not account_id or not url:
        return jsonify({"success": False, "message": "Missing account_id or url"})
        
    result = mark_out_of_stock(account_id, url)
    
    if result.get("success"):
        # Delete old listings for this specific account
        clear_listings_for_account(account_id)
        
        # Fire off a background thread to re-scrape only this account
        state_file = f"{account_id}_state.json"
        thread = threading.Thread(target=scrape_marketplace_for_account, args=(account_id, state_file))
        thread.start()
        
    return jsonify(result)

if __name__ == '__main__':
    # host='0.0.0.0' makes the server accessible across your local network
    app.run(host='0.0.0.0', debug=True, port=5000)
