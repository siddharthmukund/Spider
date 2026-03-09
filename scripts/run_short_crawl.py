#!/usr/bin/env python3
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from Crawler import AdvancedSEOCrawler

out='seo_audit_output'
os.makedirs(out, exist_ok=True)
log_path = os.path.join(out, 'last_run.log')
with open(log_path, 'w') as log:
    log.write('Starting short crawl...\n')
    try:
        c=AdvancedSEOCrawler(base_url='https://example.com', max_pages=5, max_workers=2, timeout=3, respect_robots=False, db_path=os.path.join(out,'crawl_data.db'))
        c.progress_callback = lambda completed, total: log.write(f'PROGRESS: {completed}/{total}\n')
        c.metrics_callback = lambda url, rt, status: log.write(f'METRIC: {url} time={rt:.2f}s status={status}\n')
        c.crawl()
        report = os.path.join(out, 'seo_report.json')
        c.generate_seo_report(report)
        log.write(f'Report written to {report}\n')
    except Exception as e:
        log.write('Error: ' + str(e) + '\n')
    log.write('Done\n')
