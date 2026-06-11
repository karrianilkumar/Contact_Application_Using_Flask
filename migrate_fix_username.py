# from app import app, db
# from sqlalchemy import text, inspect

# with app.app_context():
#     conn = db.engine.connect()
#     dialect = db.engine.dialect.name

#     print("Checking user table structure... (dialect=%s)" % dialect)

#     if dialect == 'sqlite':
#         # SQLite: recreate table to change NOT NULL constraint
#         res = conn.execute(text("PRAGMA table_info('user')"))
#         cols = {row[1]: row for row in res.fetchall()}

#         if 'username' in cols and cols['username'][3] == 1:
#             print("username column exists and is NOT NULL. Recreating user table without NOT NULL on username...")

#             # Create backup of existing data
#             conn.execute(text("CREATE TABLE user_backup AS SELECT * FROM user;"))
#             print("Backup created")

#             # Drop old table
#             conn.execute(text("DROP TABLE user"))

#             # Create new table with nullable username
#             conn.execute(text("""
#                 CREATE TABLE user (
#                     id INTEGER PRIMARY KEY AUTOINCREMENT,
#                     name VARCHAR(100) NOT NULL,
#                     email VARCHAR(120) NOT NULL UNIQUE,
#                     password_hash VARCHAR(200) NOT NULL,
#                     role VARCHAR(20) DEFAULT 'user',
#                     username VARCHAR(80)
#                 )
#             """))
#             print("New user table created")

#             # Restore data, filling NULL names with email
#             conn.execute(text("""
#                 INSERT INTO user (id, name, email, password_hash, role, username)
#                 SELECT id, COALESCE(name, email), email, password_hash, role, username FROM user_backup
#             """))
#             print("Data restored")

#             # Drop backup
#             conn.execute(text("DROP TABLE user_backup"))
#             print("Backup dropped")
#         else:
#             print("No action needed for SQLite 'user' table")

#     else:
#         # Non-SQLite (e.g., Postgres): use SQLAlchemy inspector and run ALTER TABLE to drop NOT NULL
#         try:
#             insp = inspect(db.engine)
#             cols = {c['name']: c for c in insp.get_columns('user')}
#         except Exception as e:
#             print("Could not inspect 'user' table:", e)
#             conn.close()
#             raise

#         if 'username' in cols:
#             nullable = cols['username'].get('nullable', True)
#             if not nullable:
#                 print("Making 'username' column nullable on Postgres")
#                 conn.execute(text('ALTER TABLE "user" ALTER COLUMN username DROP NOT NULL'))
#                 print("Altered column to be nullable")
#             else:
#                 print("'username' column already nullable on Postgres")
#         else:
#             print("No 'username' column found on Postgres 'user' table")

#     conn.close()
#     print("Migration complete")
