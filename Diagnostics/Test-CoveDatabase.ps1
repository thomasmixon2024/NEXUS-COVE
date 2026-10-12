Set-Location -LiteralPath (Join-Path $PSScriptRoot '..')
python -c "import sqlite3; conn = sqlite3.connect('data/cove.db'); print('SQLite connection OK:', conn.execute('SELECT sqlite_version();').fetchone()[0])"
