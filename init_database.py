"""
Database Initialization Script for RecruteIA

This script initializes the Supabase PostgreSQL database with the proper schema.
Run this ONCE before deploying to production.

Usage:
    python init_database.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text, inspect
from config import settings
import src.api.models as models

def init_database():
    """Initialize the database schema."""
    
    database_url = settings.database_url
    
    print(f"🔧 Initializing database: {database_url}")
    print("-" * 80)
    
    # Create engine
    engine = create_engine(
        database_url,
        echo=True,  # Show SQL statements
        connect_args={"sslmode": "require"} if "postgresql" in database_url else {}
    )
    
    # Test connection
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            conn.commit()
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    # Check existing tables
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    print(f"\n📊 Existing tables: {existing_tables if existing_tables else 'None'}")
    
    # Create schema
    print("\n📝 Creating schema...")
    try:
        models.Base.metadata.create_all(bind=engine)
        print("✅ Schema created successfully")
    except Exception as e:
        print(f"❌ Schema creation failed: {e}")
        return False
    
    # Verify tables were created
    inspector = inspect(engine)
    new_tables = inspector.get_table_names()
    print(f"\n✨ Tables created:")
    for table in new_tables:
        columns = [f"{col['name']} ({col['type']})" for col in inspector.get_columns(table)]
        print(f"  • {table}")
        for col in columns:
            print(f"    - {col}")
    
    print("\n" + "=" * 80)
    print("✅ DATABASE INITIALIZATION COMPLETE")
    print("=" * 80)
    print(f"\nDatabase: {database_url}")
    print(f"Tables created: {len(new_tables)}")
    print("\nTables:")
    for table in sorted(new_tables):
        print(f"  ✓ {table}")
    
    return True

def get_schema_visualization():
    """Get a text visualization of the database schema."""
    
    database_url = settings.database_url
    engine = create_engine(
        database_url,
        connect_args={"sslmode": "require"} if "postgresql" in database_url else {}
    )
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    print("\n" + "=" * 80)
    print("📊 DATABASE SCHEMA VISUALIZATION")
    print("=" * 80)
    
    for table_name in sorted(tables):
        print(f"\n📋 {table_name.upper()}")
        print("-" * 80)
        
        columns = inspector.get_columns(table_name)
        for col in columns:
            col_type = str(col['type'])
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            print(f"  • {col['name']:<25} {col_type:<20} {nullable}")
        
        # Get primary keys
        pk = inspector.get_pk_constraint(table_name)
        if pk['constrained_columns']:
            print(f"\n  🔑 Primary Key: {', '.join(pk['constrained_columns'])}")
        
        # Get foreign keys
        fks = inspector.get_foreign_keys(table_name)
        if fks:
            print(f"\n  🔗 Foreign Keys:")
            for fk in fks:
                print(f"     {fk['constrained_columns']} → {fk['referred_table']}.{fk['referred_columns']}")
        
        # Get indexes
        indexes = inspector.get_indexes(table_name)
        if indexes:
            print(f"\n  📑 Indexes:")
            for idx in indexes:
                print(f"     {idx['name']}: {idx['column_names']}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize RecruteIA database")
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Show schema visualization without initializing"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all tables before recreating (WARNING: data loss!)"
    )
    
    args = parser.parse_args()
    
    if args.visualize:
        try:
            get_schema_visualization()
        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
    else:
        if args.drop:
            print("⚠️  WARNING: Dropping all tables...")
            database_url = settings.database_url
            engine = create_engine(
                database_url,
                connect_args={"sslmode": "require"} if "postgresql" in database_url else {}
            )
            models.Base.metadata.drop_all(bind=engine)
            print("✅ All tables dropped")
        
        success = init_database()
        
        if success:
            print("\n📊 Schema visualization:")
            get_schema_visualization()
            sys.exit(0)
        else:
            sys.exit(1)
