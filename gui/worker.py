import logging
import threading
import time
from pathlib import Path
from typing import Optional
from PySide6.QtCore import QObject, Signal
from Crawler import AdvancedSEOCrawler


class Worker(QObject):
    """Runs the crawler in a background thread and emits signals for UI updates."""
    log = Signal(str)
    # Emit (completed, total)
    progress = Signal(int, int)
    # Metrics: url, response_time, status_code
    metrics = Signal(str, float, int)
    # Estimated remaining time in seconds
    eta = Signal(float)
    # real-time PPS
    pps = Signal(float)
    cache_stats = Signal(dict)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self._thread: Optional[threading.Thread] = None
        self._crawler: Optional[AdvancedSEOCrawler] = None
        self._stop_requested = False
        self._start_time: float = 0
        # Metrics tracking
        self._avg_response: float = 0.0
        self._samples: int = 0
        self._fastest: float = float('inf')
        self._slowest: float = 0.0
        self._last_completed: int = 0
        self._last_total: int = 0

    def start(self, base_url: str, max_pages: int, max_workers: int, output_dir: str):
        if self._thread and self._thread.is_alive():
            self.log.emit('Worker already running')
            return
        
        self._start_time = time.time()
        self._samples = 0
        self._avg_response = 0.0
        self._fastest = float('inf')
        self._slowest = 0.0
        output_path = Path(output_dir or '.')
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            self.log.emit(f'Warning: Could not create output directory {output_path}')

        def _target():
            try:
                # Set up crawler (place DB into output dir)
                db_path = str(output_path / 'crawl_data.db')
                try:
                    crawler = AdvancedSEOCrawler(base_url=base_url, max_pages=max_pages, max_workers=max_workers, db_path=db_path)
                except TypeError:
                    # fallback for older/simple constructors used in tests
                    crawler = AdvancedSEOCrawler(base_url, max_pages, max_workers)
                self._crawler = crawler

                # Attach a logging handler to route logs to the UI
                class QtLogHandler(logging.Handler):
                    def __init__(self, emitter):
                        super().__init__()
                        self.emitter = emitter

                    def emit(self, record):
                        try:
                            msg = self.format(record)
                            self.emitter(msg)
                        except Exception:
                            pass

                handler = QtLogHandler(lambda m: self.log.emit(m))
                handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'))
                logging.getLogger().addHandler(handler)

                # Attach progress callback
                try:
                    def _progress_cb(completed, total):
                        try:
                            self._last_completed = completed
                            self._last_total = total
                            self.progress.emit(completed, total)
                            # Emit ETA based on running average
                            if self._samples > 0:
                                remaining = max(0, total - completed)
                                eta_seconds = remaining * self._avg_response
                                self.eta.emit(eta_seconds)
                        except Exception:
                            pass
                    crawler.progress_callback = _progress_cb
                except Exception:
                    pass

                # Attach metrics callback
                try:
                    def _metrics_cb(url, response_time, status_code):
                        try:
                            # Update running stats
                            self._samples += 1
                            # Running average
                            self._avg_response = ((self._avg_response * (self._samples - 1)) + response_time) / self._samples
                            self._fastest = min(self._fastest, response_time)
                            self._slowest = max(self._slowest, response_time)
                            self.metrics.emit(url, response_time, status_code)
                            
                            # Calculate and emit PPS
                            elapsed = time.time() - self._start_time
                            if elapsed > 0:
                                pps_val = self._samples / elapsed
                                self.pps.emit(pps_val)
                        except Exception:
                            pass
                    crawler.metrics_callback = _metrics_cb
                except Exception:
                    pass

                # Run crawl
                crawler.crawl()

                # Write report
                report_path = str(output_path / 'seo_report.json')
                crawler.generate_seo_report(report_path)
                try:
                    stats = crawler.get_cache_statistics()
                    self.cache_stats.emit(stats)
                    self.log.emit(
                        f"Cache stats: {stats['cache_hits']} hits, {stats['cache_misses']} misses ({stats['hit_rate_percent']}% hit rate)"
                    )
                except Exception:
                    pass

                self.log.emit(f'Finished. Report saved to {report_path}')
                self.finished.emit(report_path)
            except Exception as e:
                self.error.emit(str(e))
            finally:
                # Remove handler to avoid duplicate logs
                try:
                    logging.getLogger().removeHandler(handler)
                except Exception:
                    pass

        self._thread = threading.Thread(target=_target, daemon=True)
        self._thread.start()
        self.log.emit('Worker thread started')

    def stop(self):
        if self._crawler:
            # Signal the crawler to stop gracefully
            self._crawler.interrupted = True
            self.log.emit('Stop requested')
        else:
            self.log.emit('No active crawler to stop')

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
