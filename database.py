import sqlite3

def create_tables():
    conn = sqlite3.connect('bot_database2.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        user_id INTEGER UNIQUE,
        username TEXT
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ads (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        title TEXT,
        description TEXT,
        photo TEXT,
        price REAL,
        message_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    conn.commit()
    conn.close()

def add_ad(user_id, title, description, photo, price, message_id):
    conn = sqlite3.connect('bot_database2.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO ads (user_id, title, description, photo, price, message_id) VALUES (?, ?, ?, ?, ?, ?)', 
                   (user_id, title, description, photo, price, message_id))
    conn.commit()
    conn.close()

def delete_ad(ad_id):
    conn = sqlite3.connect('bot_database2.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM ads WHERE id = ?', (ad_id,))
    conn.commit()
    conn.close()


def add_user(user_id, username):
    conn = sqlite3.connect('bot_database2.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('bot_database2.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_ads(user_id):
    conn = sqlite3.connect('bot_database2.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ads WHERE user_id = ?', (user_id,))
    ads = cursor.fetchall()
    conn.close()
    return ads

def get_ad(ad_id):
    conn = sqlite3.connect('bot_database2.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ads WHERE id = ?', (ad_id,))
    ad = cursor.fetchone()
    conn.close()
    return ad

def update_ad(ad_id, title, description, photo, price):
    conn = sqlite3.connect('bot_database2.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE ads SET title = ?, description = ?, photo = ?, price = ? WHERE id = ?',
                   (title, description, photo, price, ad_id))
    conn.commit()
    conn.close()

create_tables()
