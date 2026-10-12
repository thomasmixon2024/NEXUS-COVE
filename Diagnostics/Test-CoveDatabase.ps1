Set-Location "C:\Users\Thomas\Projects\NEXUS-COVE-1.0"
python -c "import sqlite3; conn = sqlite3.connect('data/cove.db'); print('SQLite connection OK:', conn.execute('SELECT sqlite_version();').fetchone()[0])"
