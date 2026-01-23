"""Quick test to verify database connection and basic queries"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "bps_database.db"

print("Testing database connection...")
print(f"Database path: {DB_PATH}")
print(f"Database exists: {DB_PATH.exists()}")

if DB_PATH.exists():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Test basic query
    cursor.execute("SELECT COUNT(*) FROM bps_models")
    count = cursor.fetchone()[0]
    print(f"✓ Database connection successful!")
    print(f"✓ Found {count} models in database")
    
    # Test a few more queries
    cursor.execute("SELECT COUNT(*) FROM modelers")
    modeler_count = cursor.fetchone()[0]
    print(f"✓ Found {modeler_count} modelers")
    
    cursor.execute("SELECT COUNT(*) FROM bps_indicators")
    species_count = cursor.fetchone()[0]
    print(f"✓ Found {species_count} species indicators")
    
    conn.close()
    print("\n✅ All tests passed! Database is ready to use.")
else:
    print("❌ Database file not found!")
