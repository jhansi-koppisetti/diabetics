import sqlite3

def init_db():
    conn = sqlite3.connect('glycoguardian.db')
    cursor = conn.cursor()
    
    # Users Table with Phone column
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, 
        email TEXT UNIQUE, 
        phone TEXT, 
        password TEXT, 
        join_date TEXT)''')
    
    # Reports Table with Type column
    cursor.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT, 
        result TEXT, 
        risk_color TEXT, 
        type TEXT, 
        date TEXT)''')
    
    conn.commit()
    conn.close()
    print("Database Reset: Tables created with Phone and Type columns!")

if __name__ == "__main__":
    init_db()