import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

DB_PATH = 'database/school_management.db'

def seed_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Add Super Admin
    cursor.execute('''
        INSERT OR IGNORE INTO users (name, email, password_hash, role)
        VALUES (?, ?, ?, ?)
    ''', ('Super Admin', 'admin@school.com', generate_password_hash('admin123'), 'super_admin'))
    
    # Add School
    cursor.execute('''
        INSERT OR IGNORE INTO schools (name, email, phone, subscription_start, subscription_end, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('Demo School', 'school@demo.com', '9876543210', 
          datetime.now().date(), (datetime.now() + timedelta(days=365)).date(), 'active'))
    
    # Add School Admin
    cursor.execute('''
        INSERT OR IGNORE INTO users (name, email, password_hash, role, school_id)
        VALUES (?, ?, ?, ?, ?)
    ''', ('School Admin', 'schooladmin@demo.com', generate_password_hash('admin123'), 'school_admin', 1))
    
    # Add Classes
    classes = ['Nursery', 'LKG', 'UKG', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']
    for class_name in classes:
        cursor.execute('''
            INSERT OR IGNORE INTO classes (school_id, class_name)
            VALUES (?, ?)
        ''', (1, class_name))
    
    conn.commit()
    conn.close()
    print("Database seeded successfully!")

if __name__ == '__main__':
    seed_database()
