import sqlite3

DB_NAME = 'bps_database.db'
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("=" * 60)
print("DATABASE SCHEMA INSPECTION")
print("=" * 60)

for table in tables:
    table_name = table[0]
    print(f"\n=== Table: {table_name} ===")
    
    # Get column information
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    print("Columns:")
    for col in columns:
        col_id, col_name, col_type, not_null, default_val, pk = col
        pk_str = " (PRIMARY KEY)" if pk else ""
        null_str = " NOT NULL" if not_null else ""
        print(f"  - {col_name}: {col_type}{null_str}{pk_str}")
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"Row count: {count}")
    
    # Show a sample row
    if count > 0:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
        sample = cursor.fetchone()
        col_names = [desc[0] for desc in cursor.description]
        print("Sample row:")
        for name, value in zip(col_names, sample):
            print(f"  {name}: {value}")

conn.close()
