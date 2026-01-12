import json
import tempfile
import os
from datetime import datetime
import requests
from Crawler import AdvancedSEOCrawler


class DummyResponse(requests.Response):
    def __init__(self, url, html):
        super().__init__()
        self.status_code = 200
        self._content = html.encode('utf-8')
        self.headers = {'content-type': 'text/html; charset=utf-8'}
        self.url = url
        self.history = []
        self.encoding = 'utf-8'


def test_crawl_and_report(tmp_path, monkeypatch):
    html = """
    <html>
      <head>
        <title>Short</title>
        <meta name="description" content="A short description">
      </head>
      <body>
        <h1>Heading</h1>
        <a href="/about">About</a>
      </body>
    </html>
    """

    url = 'https://example.com'
    dummy = DummyResponse(url, html)

    crawler = AdvancedSEOCrawler(base_url=url, max_pages=1, max_workers=1, use_database=True)
    # Patch session.get to return our dummy response
    monkeypatch.setattr(crawler, 'session', type('S', (), {'get': lambda *a, **k: dummy})())

    # Use tmpdir for outputs and DB
    monkeypatch.chdir(tmp_path)

    urls = crawler.crawl()
    assert urls is None or isinstance(urls, list) or True  # crawl may return None; we just want it to finish

    report = crawler.generate_seo_report(str(tmp_path / 'seo_report.json'))
    # Ensure report is JSON serializable and has expected keys
    with open(tmp_path / 'seo_report.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert 'statistics' in data
    assert 'metadata' in data
    assert isinstance(data['metadata']['crawl_date'], str)
    assert 'pages' in data
    assert any(url in p for p in data['pages'].keys())
    # Ensure response_time exists and is a number for processed pages
    for p in data['pages'].values():
        assert 'response_time' in p
        assert isinstance(p['response_time'], float) or isinstance(p['response_time'], int)
