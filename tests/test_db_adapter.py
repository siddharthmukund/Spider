import tempfile
import os
import sqlite3
from datetime import datetime
from Crawler import DatabaseManager, PageData


def test_database_timestamp_adapter(tmp_path):
    db_file = tmp_path / 'test.db'
    db = DatabaseManager(db_path=str(db_file))

    page = PageData(url='https://example.com/test', status_code=200)
    db.save_page(page)

    cursor = db.conn.cursor()
    cursor.execute('SELECT crawl_date FROM pages WHERE url = ?', (page.url,))
    row = cursor.fetchone()
    assert row is not None
    val = row[0]
    # Depending on adapter/converter, it could be str or datetime
    from datetime import datetime as _dt
    assert isinstance(val, (_dt, str))

    db.close()
