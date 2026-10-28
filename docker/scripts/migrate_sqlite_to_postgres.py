#!/usr/bin/env python3
"""
Migration script: SQLite → PostgreSQL
Direct database connections (no Flask) to avoid auto-seeding issues.

Usage (from within the app container):
    python /app/docker/scripts/migrate_sqlite_to_postgres.py
"""
import os
import sys
import sqlite3
import psycopg2
import psycopg2.extras

SQLITE_PATH = os.environ.get('SQLITE_DB_PATH', '/app/backend/instance/app.db')
PG_URL = os.environ.get('DATABASE_URL', 'postgresql://budget_user:password@db:5432/budget')

# Table insertion order respecting foreign key dependencies
TABLE_ORDER = [
    'roles',
    'permissions',
    'users',
    'role_permissions',
    'user_roles',
    'email_templates',
    'email_queue',
    'user_settings',
    'ComptesBancaires',
    'categories',
    'devices',
    'device_login_history',
    'budgets',
    'budget_history',
    'transactions',
    'notifications',
    'notification_preferences',
    'reports',
    'menu_items',
]

def get_boolean_columns(pg_cur):
    """Query PostgreSQL to find all boolean columns per table."""
    pg_cur.execute("""
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND data_type = 'boolean'
    """)
    bool_cols = {}
    for table_name, col_name in pg_cur.fetchall():
        bool_cols.setdefault(table_name, set()).add(col_name)
    return bool_cols


def parse_pg_url(url):
    """Parse DATABASE_URL into psycopg2 connection params."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'dbname': parsed.path.lstrip('/'),
        'user': parsed.username,
        'password': parsed.password,
    }


def get_sqlite_data(sqlite_path):
    """Read all data from SQLite."""
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    data = {}
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'alembic_version'")
    tables = [row[0] for row in cursor.fetchall()]

    for table_name in tables:
        cursor.execute(f'SELECT * FROM "{table_name}"')
        rows = cursor.fetchall()
        if rows:
            columns = [desc[0] for desc in cursor.description]
            data[table_name] = {
                'columns': columns,
                'rows': [dict(row) for row in rows]
            }
            print(f"  Read {len(rows)} rows from '{table_name}'")
        else:
            print(f"  Skipping '{table_name}' (empty)")

    conn.close()
    return data


def convert_booleans(row, bool_cols):
    """Convert SQLite 0/1 to Python booleans for boolean columns."""
    converted = {}
    for key, value in row.items():
        if key in bool_cols and value is not None:
            converted[key] = bool(value)
        else:
            converted[key] = value
    return converted


def main():
    if not os.path.exists(SQLITE_PATH):
        print(f"ERROR: SQLite database not found at {SQLITE_PATH}")
        sys.exit(1)

    pg_params = parse_pg_url(PG_URL)
    pg_conn = psycopg2.connect(**pg_params)
    pg_conn.autocommit = False
    pg_cur = pg_conn.cursor()

    print(f"\n{'='*60}")
    print("SQLite -> PostgreSQL Migration")
    print(f"{'='*60}")

    # Check if already migrated
    pg_cur.execute("SELECT COUNT(*) FROM users")
    user_count = pg_cur.fetchone()[0]
    if user_count > 0:
        print(f"\nWARNING: PostgreSQL already contains {user_count} users.")
        print("Migration aborted to prevent duplicates.")
        pg_conn.close()
        sys.exit(1)

    # Read SQLite data
    print(f"\n--- Reading from SQLite: {SQLITE_PATH}")
    data = get_sqlite_data(SQLITE_PATH)

    if not data:
        print("No data found in SQLite database.")
        pg_conn.close()
        sys.exit(0)

    # Truncate all tables (disable FK checks, skip missing tables)
    print(f"\n--- Clearing PostgreSQL tables")
    pg_cur.execute("SET session_replication_role = 'replica'")
    pg_cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    existing_tables = {row[0] for row in pg_cur.fetchall()}
    for table_name in TABLE_ORDER:
        if table_name in existing_tables:
            pg_cur.execute(f'TRUNCATE TABLE "{table_name}" CASCADE')
    pg_conn.commit()
    print("  Tables cleared.")

    # Determine insertion order
    ordered_tables = []
    for table in TABLE_ORDER:
        if table in data:
            ordered_tables.append(table)
    for table in data:
        if table not in ordered_tables:
            ordered_tables.append(table)

    # Detect boolean columns from PostgreSQL schema
    boolean_columns = get_boolean_columns(pg_cur)

    # Insert data (only into existing PostgreSQL tables)
    print(f"\n--- Inserting into PostgreSQL")
    for table_name in ordered_tables:
        if table_name not in existing_tables:
            print(f"  Skipping '{table_name}' (table not in PostgreSQL)")
            continue
        table_data = data[table_name]
        columns = table_data['columns']
        rows = table_data['rows']

        if not rows:
            continue

        bool_cols = boolean_columns.get(table_name, set())
        col_list = ', '.join(f'"{c}"' for c in columns)
        placeholders = ', '.join([f'%({c})s' for c in columns])
        sql = f'INSERT INTO "{table_name}" ({col_list}) VALUES ({placeholders})'

        try:
            for row in rows:
                converted = convert_booleans(row, bool_cols)
                pg_cur.execute(sql, converted)
            pg_conn.commit()
            print(f"  Inserted {len(rows)} rows into '{table_name}'")
        except Exception as e:
            pg_conn.rollback()
            print(f"  ERROR inserting into '{table_name}': {e}")
            raise

    # Reset sequences
    print(f"\n--- Resetting sequences")
    pg_cur.execute("""
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND column_default LIKE 'nextval%%'
    """)
    sequences = pg_cur.fetchall()
    for table_name, col_name in sequences:
        try:
            pg_cur.execute(f"""
                SELECT setval(
                    pg_get_serial_sequence('"{table_name}"', '{col_name}'),
                    COALESCE((SELECT MAX("{col_name}") FROM "{table_name}"), 1),
                    true
                )
            """)
            val = pg_cur.fetchone()[0]
            print(f"  Sequence for {table_name}.{col_name} reset to {val}")
        except Exception:
            pg_conn.rollback()

    # Re-enable FK checks
    pg_cur.execute("SET session_replication_role = 'origin'")
    pg_conn.commit()
    pg_conn.close()

    print(f"\n{'='*60}")
    print("Migration completed successfully!")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
