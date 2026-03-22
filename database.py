import sqlite3

DB_NAME = 'listings.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT,
            title TEXT,
            price TEXT,
            url TEXT,
            image_url TEXT,
            UNIQUE(account_id, url)
        )
    ''')
    try:
        c.execute("ALTER TABLE insights ADD COLUMN period TEXT DEFAULT 'Last 7 days'")
    except:
        pass # Column already exists or table doesn't exist yet

    # We create a new history table that doesn't use account_id as a primary key
    # so we can stack multiple insight snapshots over time.
    c.execute('''
        CREATE TABLE IF NOT EXISTS insights_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id TEXT,
            clicks TEXT,
            saves TEXT,
            shares TEXT,
            followers TEXT,
            period TEXT,
            last_updated DATETIME DEFAULT (datetime('now','localtime'))
        )
    ''')
    conn.commit()
    conn.close()

def save_insights(account_id, clicks, saves, shares, followers, period="Last 7 days"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        # We use standard INSERT here to stack data
        c.execute('''
            INSERT INTO insights_history (account_id, clicks, saves, shares, followers, period, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now','localtime'))
        ''', (account_id, clicks, saves, shares, followers, period))
        conn.commit()
    except Exception as e:
        print(f"Error saving insights: {e}")
    finally:
        conn.close()

def get_all_insights():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        # Order by account, then by newest timestamp first
        c.execute('SELECT account_id, clicks, saves, shares, followers, period, last_updated FROM insights_history ORDER BY account_id, last_updated DESC')
        results = c.fetchall()
    except:
        results = []
    finally:
        conn.close()
        
    # Group the results into a dictionary by account_id so the UI can iterate through them cleanly
    grouped = {}
    for row in results:
        acc_id = row[0]
        if acc_id not in grouped:
            grouped[acc_id] = []
        grouped[acc_id].append(row)
        
    return grouped

def save_listing(account_id, title, price, url, image_url):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT OR IGNORE INTO listings (account_id, title, price, url, image_url)
            VALUES (?, ?, ?, ?, ?)
        ''', (account_id, title, price, url, image_url))
        conn.commit()
    except Exception as e:
        print(f"Error saving listing: {e}")
    finally:
        conn.close()

def get_all_listings():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT account_id, title, price, url, image_url FROM listings ORDER BY id DESC')
    results = c.fetchall()
    conn.close()
    return results

def clear_all_listings():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM listings')
    conn.commit()
    conn.close()

def clear_listings_for_account(account_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('DELETE FROM listings WHERE account_id = ?', (account_id,))
    conn.commit()
    conn.close()
