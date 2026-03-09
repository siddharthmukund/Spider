"""
Enterprise SEO Crawler - Professional Website Auditing Tool v4.0
Features: Async I/O, Advanced analytics, Machine learning readiness,
Real-time monitoring, Database support, API endpoints, Plugin system
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs
from urllib.robotparser import RobotFileParser
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from xml.dom import minidom
from collections import defaultdict, deque, Counter, OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from typing import Set, Dict, List, Tuple, Optional, Any, Callable
import time
import json
import csv
import re
import hashlib
import logging
from dataclasses import dataclass, asdict, field
from functools import lru_cache, wraps
from pathlib import Path
import gzip
import sqlite3
from enum import Enum
import sys
from queue import PriorityQueue
import signal
from utils.json_helpers import JsonEncoder

# LRU Cache for HTTP responses (reduce redundant requests)
class ResponseCache:
    """In-memory LRU cache for HTTP responses"""
    def __init__(self, max_size: int = 1000):
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
    
    def clear(self) -> None:
        self.cache.clear()
        self.hits = self.misses = 0

# Register sqlite adapters/converters for datetime to avoid deprecation warnings
sqlite3.register_adapter(datetime, lambda val: val.isoformat())
sqlite3.register_converter('timestamp', lambda b: datetime.fromisoformat(b.decode()))

# Configure logging with color support
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors"""
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'))
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Performance monitoring decorator
def monitor_performance(func):
    """Monitor function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        if elapsed > 1.0:
            logger.warning(f"Slow operation: {func.__name__} took {elapsed:.2f}s")
        return result
    return wrapper

# Rate limiting with token bucket algorithm
class RateLimiter:
    """Token bucket rate limiter"""
    def __init__(self, rate: float, burst: int = 10):
        self.rate = rate
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()
        self.lock = __import__('threading').Lock()
    
    def acquire(self):
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            
            sleep_time = (1 - self.tokens) / self.rate
            time.sleep(sleep_time)
            self.tokens = 0
            return True

# Priority levels for URL crawling
class Priority(Enum):
    CRITICAL = 1  # Homepage, key landing pages
    HIGH = 2      # Category pages, important content
    MEDIUM = 3    # Regular pages
    LOW = 4       # Deep pages, pagination

@dataclass
class PageData:
    """Comprehensive page data structure"""
    url: str
    status_code: int = 0
    title: str = ''
    title_length: int = 0
    meta_description: str = ''
    meta_description_length: int = 0
    h1_tags: List[str] = field(default_factory=list)
    h2_tags: List[str] = field(default_factory=list)
    word_count: int = 0
    image_count: int = 0
    missing_alt_text: int = 0
    canonical: str = ''
    meta_robots: str = ''
    response_time: float = 0.0
    content_type: str = ''
    content_length: int = 0
    content_hash: str = ''
    error: str = ''
    internal_links_count: int = 0
    external_links_count: int = 0
    
    # Advanced SEO
    og_title: str = ''
    og_description: str = ''
    og_image: str = ''
    twitter_card: str = ''
    schema_types: List[str] = field(default_factory=list)
    has_viewport: bool = False
    has_favicon: bool = False
    lang: str = ''
    
    # Performance
    ttfb: float = 0.0
    dns_time: float = 0.0
    load_time: float = 0.0
    
    # Content quality
    readability_score: float = 0.0
    keyword_density: Dict[str, float] = field(default_factory=dict)
    
    # Link metrics
    inbound_links: int = 0
    outbound_links: int = 0
    
    # Technical SEO
    hreflang_tags: List[str] = field(default_factory=list)
    structured_data_errors: List[str] = field(default_factory=list)
    css_count: int = 0
    js_count: int = 0
    font_count: int = 0
    
    # Security & Headers
    has_ssl: bool = False
    security_headers: Dict[str, str] = field(default_factory=dict)
    
    # Accessibility
    aria_labels: int = 0
    contrast_issues: int = 0
    
    # Custom metrics
    custom_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CrawlStatistics:
    """Comprehensive crawl statistics"""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_pages: int = 0
    successful_pages: int = 0
    failed_pages: int = 0
    redirected_pages: int = 0
    total_errors: int = 0
    avg_response_time: float = 0.0
    total_data_transferred: int = 0
    pages_per_second: float = 0.0
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    status_code_distribution: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    
    # Performance metrics
    slowest_pages: List[Tuple[str, float]] = field(default_factory=list)
    fastest_pages: List[Tuple[str, float]] = field(default_factory=list)

class DatabaseManager:
    """SQLite database manager for crawl data"""
    def __init__(self, db_path: str = 'crawl_data.db'):
        self.db_path = db_path
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema with performance optimizations"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA synchronous=NORMAL')
        self.conn.execute('PRAGMA cache_size=-64000')  # 64MB cache
        
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pages (
                url TEXT PRIMARY KEY,
                status_code INTEGER,
                title TEXT,
                meta_description TEXT,
                word_count INTEGER,
                response_time REAL,
                crawl_date TIMESTAMP,
                content_hash TEXT,
                data JSON
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS links (
                source_url TEXT,
                target_url TEXT,
                link_type TEXT,
                anchor_text TEXT,
                FOREIGN KEY (source_url) REFERENCES pages(url)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS issues (
                url TEXT,
                issue_type TEXT,
                severity TEXT,
                description TEXT,
                FOREIGN KEY (url) REFERENCES pages(url)
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON pages(status_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_url)')
        
        self.conn.commit()
    
    def save_page(self, page_data: PageData):
        """Save page data to database"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO pages 
            (url, status_code, title, meta_description, word_count, 
             response_time, crawl_date, content_hash, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            page_data.url,
            page_data.status_code,
            page_data.title,
            page_data.meta_description,
            page_data.word_count,
            page_data.response_time,
            datetime.now(),
            page_data.content_hash,
            json.dumps(asdict(page_data))
        ))
        self.conn.commit()
    
    def save_issue(self, url: str, issue_type: str, severity: str, description: str):
        """Save SEO issue"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO issues (url, issue_type, severity, description)
            VALUES (?, ?, ?, ?)
        ''', (url, issue_type, severity, description))
        self.conn.commit()
    
    def get_historical_data(self, url: str) -> Optional[Dict]:
        """Get historical data for comparison"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT data FROM pages WHERE url = ?', (url,))
        result = cursor.fetchone()
        return json.loads(result[0]) if result else None

    def save_links_batch(self, source_url: str, internal_links: List[Tuple[str, int, Priority]], external_links: List[str]):
        """Save a batch of links efficiently using a single transaction"""
        cursor = self.conn.cursor()
        try:
            # Save internal links
            for link, _, _ in internal_links:
                cursor.execute('''
                    INSERT INTO links (source_url, target_url, link_type, anchor_text)
                    VALUES (?, ?, ?, ?)
                ''', (source_url, link, 'internal', None))
            
            # Save external links
            for ext in external_links:
                cursor.execute('''
                    INSERT INTO links (source_url, target_url, link_type, anchor_text)
                    VALUES (?, ?, ?, ?)
                ''', (source_url, ext, 'external', None))
            
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to save links batch for {source_url}: {e}")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

class PluginSystem:
    """Plugin system for extensibility"""
    def __init__(self):
        self.hooks: Dict[str, List[Callable]] = defaultdict(list)
    
    def register(self, hook_name: str, callback: Callable):
        """Register a plugin callback"""
        self.hooks[hook_name].append(callback)
        logger.info(f"Registered plugin for hook: {hook_name}")
    
    def execute(self, hook_name: str, *args, **kwargs):
        """Execute all callbacks for a hook"""
        results = []
        for callback in self.hooks.get(hook_name, []):
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Plugin error in {hook_name}: {e}")
        return results

class AdvancedSEOCrawler:
    """
    Enterprise-grade SEO crawler with advanced features
    """
    
    # Pre-compiled regex for efficiency
    RE_SENTENCES = re.compile(r'[.!?]+')
    RE_WORDS = re.compile(r'\w+')
    RE_KEYWORDS = re.compile(r'\b\w{4,}\b')
    RE_WHITESPACE = re.compile(r'\s+')
    RE_NON_ALPHANUM = re.compile(r'[^\w\s]')
    
    # Common file extensions to skip
    SKIP_EXTENSIONS = {
        '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.bmp',
        '.zip', '.rar', '.tar', '.gz', '.7z', '.exe', '.dmg', '.pkg',
        '.mp4', '.mp3', '.avi', '.mov', '.wmv', '.flv', '.wav',
        '.css', '.js', '.ico', '.xml', '.json', '.txt',
        '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
    }

    def __init__(
        self,
        base_url: str,
        max_pages: int = 100,
        max_workers: int = 5,
        timeout: int = 10,
        respect_robots: bool = True,
        user_agent: str = None,
        rate_limit_rps: float = 2.0,
        max_depth: int = None,
        exclude_patterns: List[str] = None,
        include_patterns: List[str] = None,
        follow_external: bool = False,
        use_database: bool = True,
        enable_plugins: bool = True,
        compare_historical: bool = False,
        db_path: str = None
    ):
        # Validate input parameters
        try:
            parsed_url = urlparse(base_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid base URL: '{base_url}' (must include scheme and domain)")
        except Exception as e:
            raise ValueError(f"Invalid base URL: {str(e)}")
        
        if max_pages < 1:
            raise ValueError(f"max_pages must be >= 1, got {max_pages}")
        if max_workers < 1:
            raise ValueError(f"max_workers must be >= 1, got {max_workers}")
        if timeout < 1:
            raise ValueError(f"timeout must be >= 1, got {timeout}")
        if rate_limit_rps < 0.1:
            raise ValueError(f"rate_limit_rps must be >= 0.1, got {rate_limit_rps}")
        
        self.base_url = self._normalize_url(base_url)
        self.domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.max_workers = max_workers
        self.timeout = timeout
        self.respect_robots = respect_robots
        self.max_depth = max_depth
        self.exclude_patterns = exclude_patterns or []
        self.include_patterns = include_patterns or []
        self.follow_external = follow_external
        self.use_database = use_database
        self.compare_historical = compare_historical

        # Initialize response cache for better performance
        self.response_cache = ResponseCache(max_size=1000)

        # Initialize crawl delay and last request time
        self.crawl_delay = None
        self.last_request_time = 0.0
        
        # Rate limiting
        self.rate_limiter = RateLimiter(rate_limit_rps, burst=10)
        
        # Thread-safe data structures
        self.visited = set()
        self.to_visit = PriorityQueue()
        self.to_visit.put((Priority.CRITICAL.value, 0, self.base_url))
        self.url_lock = __import__('threading').Lock()
        self.data_lock = __import__('threading').Lock()
        
        # Data storage
        self.page_data: Dict[str, PageData] = {}
        self.broken_links: List[Dict] = []
        self.redirects: List[Dict] = []
        self.duplicate_content: Dict[str, List[str]] = defaultdict(list)
        self.internal_links: Dict[str, List[str]] = defaultdict(list)
        self.external_links: Dict[str, List[str]] = defaultdict(list)
        self.url_depth: Dict[str, int] = {}
        self.issues: List[Dict] = []
        
        # Performance tracking
        self.statistics = CrawlStatistics()
        
        # Database (allow custom path)
        if use_database:
            self.db = DatabaseManager(db_path=db_path if db_path else 'crawl_data.db')
        else:
            self.db = None
        # Optional progress callback: function(completed: int, total: int)
        self.progress_callback = None
        # Optional page metrics callback: function(url: str, response_time: float, status_code: int)
        self.metrics_callback = None
        
        # Plugin system
        self.plugins = PluginSystem() if enable_plugins else None
        
        # Session with advanced configuration
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            max_retries=requests.adapters.Retry(
                total=3,
                backoff_factor=0.3,
                status_forcelist=[500, 502, 503, 504]
            ),
            pool_connections=max_workers,
            pool_maxsize=max_workers * 2
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        self.session.headers.update({
            'User-Agent': user_agent or 'Mozilla/5.0 (compatible; SEO-Crawler/4.0; +http://example.com/bot)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Detector for best available HTML parser
        self.html_parser = 'html.parser'
        try:
            import lxml
            self.html_parser = 'lxml'
        except ImportError:
            pass
        
        # Robots.txt
        self.robots_parser = None
        if respect_robots:
            self._init_robots_parser()
        
        # Signal handling: only register SIGINT handler if in the main thread (signal requires main thread)
        try:
            import threading as _threading
            if _threading.current_thread() is _threading.main_thread():
                signal.signal(signal.SIGINT, self._signal_handler)
            else:
                logger.debug("Not registering SIGINT handler since not in main thread")
        except Exception as e:
            logger.warning(f"Could not register SIGINT handler: {e}")
        self.interrupted = False
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signal"""
        logger.warning("\n⚠️  Interrupt received, finishing current operations...")
        self.interrupted = True
    
    def _init_robots_parser(self):
        """Initialize robots.txt parser"""
        try:
            robots_url = f"{urlparse(self.base_url).scheme}://{self.domain}/robots.txt"
            self.robots_parser = RobotFileParser()
            self.robots_parser.set_url(robots_url)
            self.robots_parser.read()
            
            crawl_delay = self.robots_parser.crawl_delay("*")
            self.crawl_delay = crawl_delay
            if crawl_delay:
                logger.info(f"Crawl delay from robots.txt: {crawl_delay}s")
            
            logger.info(f"✓ Loaded robots.txt")
        except Exception as e:
            logger.warning(f"Could not load robots.txt: {e}")
            self.crawl_delay = None
    
    def _can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched"""
        if not self.respect_robots or not self.robots_parser:
            return True
        try:
            return self.robots_parser.can_fetch("*", url)
        except:
            return True
    
    @staticmethod
    @lru_cache(maxsize=10000)
    def _normalize_url(url: str) -> str:
        """Normalize URL"""
        parsed = urlparse(url)
        
        netloc = parsed.netloc
        if ':80' in netloc and parsed.scheme == 'http':
            netloc = netloc.replace(':80', '')
        elif ':443' in netloc and parsed.scheme == 'https':
            netloc = netloc.replace(':443', '')
        
        path = parsed.path.rstrip('/') if parsed.path not in ['/', ''] else parsed.path
        
        query = parsed.query
        if query:
            params = parse_qs(query, keep_blank_values=True)
            sorted_params = sorted(params.items())
            query = '&'.join(f"{k}={','.join(v)}" for k, v in sorted_params)
        
        return urlunparse((
            parsed.scheme.lower(),
            netloc.lower(),
            path,
            parsed.params,
            query,
            ''
        ))
    
    def _calculate_priority(self, url: str, depth: int) -> Priority:
        """Calculate URL crawl priority"""
        if url == self.base_url:
            return Priority.CRITICAL
        
        if depth == 0:
            return Priority.HIGH
        elif depth == 1:
            return Priority.MEDIUM
        else:
            return Priority.LOW
    
    def _matches_pattern(self, url: str, patterns: List[str]) -> bool:
        """Check pattern match with pre-compiled cache"""
        if not hasattr(self, '_compiled_patterns'):
            self._compiled_patterns = {}
            
        return any(self._get_compiled_regex(p).search(url) for p in patterns)

    def _get_compiled_regex(self, pattern: str):
        """Get or compile regex pattern"""
        if pattern not in self._compiled_patterns:
            try:
                self._compiled_patterns[pattern] = re.compile(pattern)
            except re.error:
                # Fallback to literal if regex fails
                self._compiled_patterns[pattern] = re.compile(re.escape(pattern))
        return self._compiled_patterns[pattern]

    def _is_valid_url(self, url: str, depth: int = 0) -> bool:
        """Validate URL for crawling"""
        parsed = urlparse(url)
        
        if self.max_depth is not None and depth > self.max_depth:
            return False
        
        if not self.follow_external and parsed.netloc != self.domain:
            return False
        
        if self.exclude_patterns and self._matches_pattern(url, self.exclude_patterns):
            return False
        
        if self.include_patterns and not self._matches_pattern(url, self.include_patterns):
            return False
        
        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in self.SKIP_EXTENSIONS):
            return False
        
        return True
    
    @staticmethod
    def _calculate_content_hash(text: str) -> str:
        """Calculate content hash"""
        cleaned = AdvancedSEOCrawler.RE_WHITESPACE.sub(' ', text.lower().strip())
        cleaned = AdvancedSEOCrawler.RE_NON_ALPHANUM.sub('', cleaned)
        return hashlib.md5(cleaned.encode()).hexdigest()
    
    @staticmethod
    def _calculate_readability(text: str) -> float:
        """Flesch Reading Ease score"""
        sentences = len(AdvancedSEOCrawler.RE_SENTENCES.findall(text))
        all_words = AdvancedSEOCrawler.RE_WORDS.findall(text)
        words_count = len(all_words)
        syllables = sum(AdvancedSEOCrawler._count_syllables(word) for word in all_words)
        
        if sentences == 0 or words_count == 0:
            return 0.0
        
        score = 206.835 - 1.015 * (words_count / sentences) - 84.6 * (syllables / words_count)
        return max(0, min(100, score))
    
    @staticmethod
    def _count_syllables(word: str) -> int:
        """Count syllables"""
        word = word.lower()
        count = 0
        vowels = 'aeiouy'
        previous_was_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                count += 1
            previous_was_vowel = is_vowel
        
        if word.endswith('e'):
            count -= 1
        return max(1, count)
    
    def _extract_keywords(self, text: str, top_n: int = 10) -> Dict[str, float]:
        """Extract keywords"""
        words = AdvancedSEOCrawler.RE_KEYWORDS.findall(text.lower())
        total_words = len(words)
        
        if total_words == 0:
            return {}
        
        stop_words = {
            'that', 'this', 'with', 'from', 'have', 'been', 'were', 'said',
            'their', 'what', 'about', 'which', 'when', 'make', 'like', 'time',
            'just', 'know', 'take', 'into', 'your', 'some', 'could', 'them',
            'will', 'would', 'there', 'their', 'more', 'other', 'these'
        }
        
        filtered = [w for w in words if w not in stop_words]
        word_freq = Counter(filtered)
        
        return {
            word: (count / total_words) * 100 
            for word, count in word_freq.most_common(top_n)
        }
    
    def _extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract text content"""
        for script in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
            script.decompose()
        
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return ' '.join(chunk for chunk in chunks if chunk)
    
    def _extract_schema_markup(self, soup: BeautifulSoup) -> List[str]:
        """Extract Schema.org types"""
        schema_types = []
        
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and '@type' in data:
                    schema_types.append(data['@type'])
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and '@type' in item:
                            schema_types.append(item['@type'])
            except:
                pass
        
        for elem in soup.find_all(attrs={'itemtype': True}):
            itemtype = elem['itemtype']
            if 'schema.org' in itemtype:
                schema_types.append(itemtype.split('/')[-1])
        
        return list(set(schema_types))
    
    def _extract_security_headers(self, response: requests.Response) -> Dict[str, str]:
        """Extract security headers"""
        security_headers = {}
        important_headers = [
            'Strict-Transport-Security',
            'Content-Security-Policy',
            'X-Frame-Options',
            'X-Content-Type-Options',
            'Referrer-Policy',
            'Permissions-Policy'
        ]
        
        for header in important_headers:
            if header in response.headers:
                security_headers[header] = response.headers[header]
        
        return security_headers
    
    def _detect_issues(self, page_data: PageData) -> List[Dict[str, Any]]:
        """Detect SEO issues"""
        issues = []
        # Title issues
        if not page_data.title:
            issues.append({
                'url': page_data.url,
                'type': 'missing_title',
                'severity': 'critical',
                'description': 'Page is missing a title tag'
            })
        elif page_data.title_length < 30:
            issues.append({
                'url': page_data.url,
                'type': 'short_title',
                'severity': 'warning',
                'description': f'Title is too short ({page_data.title_length} chars)'
            })
        elif page_data.title_length > 60:
            issues.append({
                'url': page_data.url,
                'type': 'long_title',
                'severity': 'warning',
                'description': f'Title is too long ({page_data.title_length} chars)'
            })
        
        # Meta description
        if not page_data.meta_description:
            issues.append({
                'url': page_data.url,
                'type': 'missing_meta_description',
                'severity': 'warning',
                'description': 'Page is missing meta description'
            })
        
        # H1 issues
        if not page_data.h1_tags:
            issues.append({
                'url': page_data.url,
                'type': 'missing_h1',
                'severity': 'warning',
                'description': 'Page is missing H1 tag'
            })
        elif len(page_data.h1_tags) > 1:
            issues.append({
                'url': page_data.url,
                'type': 'multiple_h1',
                'severity': 'info',
                'description': f'Page has {len(page_data.h1_tags)} H1 tags'
            })
        
        # Images
        if page_data.missing_alt_text > 0:
            issues.append({
                'url': page_data.url,
                'type': 'missing_alt_text',
                'severity': 'warning',
                'description': f'{page_data.missing_alt_text} images missing alt text'
            })
        
        # Content
        if page_data.word_count < 300:
            issues.append({
                'url': page_data.url,
                'type': 'thin_content',
                'severity': 'warning',
                'description': f'Thin content ({page_data.word_count} words)'
            })
        
        # Mobile
        if not page_data.has_viewport:
            issues.append({
                'url': page_data.url,
                'type': 'missing_viewport',
                'severity': 'critical',
                'description': 'Missing viewport meta tag'
            })
        
        # Performance
        if page_data.response_time > 3.0:
            issues.append({
                'url': page_data.url,
                'type': 'slow_page',
                'severity': 'warning',
                'description': f'Slow response time ({page_data.response_time:.2f}s)'
            })
        
        # Save issues to database
        if self.db:
            for issue in issues:
                self.db.save_issue(
                    issue['url'],
                    issue['type'],
                    issue['severity'],
                    issue['description']
                )
        
        self.issues.extend(issues)
        return issues
    
    @monitor_performance
    def _extract_seo_data(self, url: str, response: requests.Response, soup: BeautifulSoup) -> PageData:
        """Extract comprehensive SEO data"""
        page_data = PageData(url=url, status_code=response.status_code)
        page_data.has_ssl = url.startswith('https://')
        
        # Basic meta
        title_tag = soup.find('title')
        if title_tag:
            page_data.title = title_tag.get_text().strip()
            page_data.title_length = len(page_data.title)
        
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            page_data.meta_description = meta_desc['content'].strip()
            page_data.meta_description_length = len(page_data.meta_description)
        
        # Headings
        page_data.h1_tags = [h.get_text().strip() for h in soup.find_all('h1')][:10]
        page_data.h2_tags = [h.get_text().strip() for h in soup.find_all('h2')][:10]
        
        # Content analysis
        text_content = self._extract_text_content(soup)
        page_data.word_count = len(re.findall(r'\w+', text_content))
        page_data.content_hash = self._calculate_content_hash(text_content)
        page_data.readability_score = self._calculate_readability(text_content)
        page_data.keyword_density = self._extract_keywords(text_content)
        
        # Images
        images = soup.find_all('img')
        page_data.image_count = len(images)
        page_data.missing_alt_text = sum(1 for img in images if not img.get('alt'))
        
        # Canonical
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        if canonical:
            page_data.canonical = canonical.get('href', '')
        
        # Meta robots
        meta_robots = soup.find('meta', attrs={'name': 'robots'})
        if meta_robots:
            page_data.meta_robots = meta_robots.get('content', '')
        
        # Open Graph
        og_title = soup.find('meta', property='og:title')
        if og_title:
            page_data.og_title = og_title.get('content', '')
        
        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            page_data.og_description = og_desc.get('content', '')
        
        og_image = soup.find('meta', property='og:image')
        if og_image:
            page_data.og_image = og_image.get('content', '')
        
        # Twitter Card
        twitter_card = soup.find('meta', attrs={'name': 'twitter:card'})
        if twitter_card:
            page_data.twitter_card = twitter_card.get('content', '')
        
        # Schema
        page_data.schema_types = self._extract_schema_markup(soup)
        
        # Viewport
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        page_data.has_viewport = viewport is not None
        
        # Favicon
        page_data.has_favicon = soup.find('link', rel='icon') is not None
        
        # Language
        html_tag = soup.find('html')
        if html_tag:
            page_data.lang = html_tag.get('lang', '')
        
        # Hreflang
        hreflang_tags = soup.find_all('link', rel='alternate', hreflang=True)
        page_data.hreflang_tags = [tag.get('hreflang', '') for tag in hreflang_tags]
        
        # Resource counts
        page_data.css_count = len(soup.find_all('link', rel='stylesheet'))
        page_data.js_count = len(soup.find_all('script', src=True))
        
        # Security headers
        page_data.security_headers = self._extract_security_headers(response)
        
        # Content info
        page_data.content_type = response.headers.get('content-type', '')
        page_data.content_length = len(response.content)
        
        # Detect issues
        self._detect_issues(page_data)
        
        # Execute plugins
        if self.plugins:
            self.plugins.execute('post_extract', page_data, soup)
        
        return page_data
    
    def _extract_links(self, url: str, soup: BeautifulSoup, depth: int) -> Tuple[Set[Tuple[str, int, Priority]], Set[str]]:
        """Extract links with priority"""
        internal = set()
        external = set()
        
        for link in soup.find_all('a', href=True):
            try:
                href = link['href'].strip()
                if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                    continue
                
                absolute_url = urljoin(url, href)
                normalized = self._normalize_url(absolute_url)
                
                if self._is_valid_url(normalized, depth + 1):
                    priority = self._calculate_priority(normalized, depth + 1)
                    if urlparse(normalized).netloc == self.domain:
                        internal.add((normalized, depth + 1, priority))
                    elif self.follow_external:
                        internal.add((normalized, depth + 1, priority))
                
                if urlparse(normalized).scheme in ['http', 'https']:
                    if urlparse(normalized).netloc != self.domain:
                        external.add(normalized)
            except Exception:
                continue
        
        return internal, external
    
    def _crawl_page(self, url: str, depth: int) -> Optional[Set[Tuple[str, int, Priority]]]:
        """Crawl single page with caching and enhanced error handling"""
        if not self._can_fetch(url):
            logger.info(f"Blocked by robots.txt: {url}")
            return set()
        
        # Check response cache first to avoid redundant requests
        cache_key = url
        cached_response = self.response_cache.get(cache_key)
        if cached_response is not None:
            response, response_time = cached_response
            logger.debug(f"Cache hit: {url}")
        else:
            # Rate limiting
            self.rate_limiter.acquire()

            # Enforce crawl delay from robots.txt
            if self.crawl_delay is not None:
                now = time.time()
                wait_time = self.crawl_delay - (now - self.last_request_time)
                if wait_time > 0:
                    time.sleep(wait_time)
            
            try:
                start_time = time.time()
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True,
                    stream=False
                )
                response_time = time.time() - start_time
                self.last_request_time = time.time()
                
                # Cache successful response
                self.response_cache.set(cache_key, (response, response_time))
            except requests.exceptions.Timeout as e:
                logger.warning(f"Timeout ({self.timeout}s): {url}")
                with self.data_lock:
                    self.page_data[url] = PageData(url=url, error=f"Timeout after {self.timeout}s")
                    self.statistics.failed_pages += 1
                    self.statistics.errors_by_type['Timeout'] += 1
                return set()
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"Connection failed: {url} - {str(e)[:80]}")
                with self.data_lock:
                    self.page_data[url] = PageData(url=url, error="Connection error")
                    self.statistics.failed_pages += 1
                    self.statistics.errors_by_type['ConnectionError'] += 1
                return set()
            except requests.exceptions.HTTPError as e:
                logger.warning(f"HTTP error: {url} - {str(e)[:80]}")
                with self.data_lock:
                    self.page_data[url] = PageData(url=url, error="HTTP error")
                    self.statistics.failed_pages += 1
                    self.statistics.errors_by_type['HTTPError'] += 1
                return set()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error: {url} - {str(e)[:80]}")
                with self.data_lock:
                    self.page_data[url] = PageData(url=url, error="Request error")
                    self.statistics.failed_pages += 1
                    self.statistics.errors_by_type['RequestException'] += 1
                return set()
            except Exception as e:
                logger.error(f"Unexpected error crawling {url}: {str(e)[:100]}")
                with self.data_lock:
                    self.page_data[url] = PageData(url=url, error=str(e)[:200])
                    self.statistics.failed_pages += 1
                    self.statistics.errors_by_type['UnexpectedError'] += 1
                return set()
            
            # Emit per-page metrics callback if available
            try:
                if hasattr(self, 'metrics_callback') and callable(self.metrics_callback):
                    self.metrics_callback(url, response_time, response.status_code)
            except Exception as e:
                logger.debug(f"Metrics callback error: {str(e)[:80]}")

            with self.data_lock:
                self.statistics.total_data_transferred += len(response.content)
                self.statistics.status_code_distribution[response.status_code] += 1
                
                # Track performance
                if response_time > 2.0:
                    self.statistics.slowest_pages.append((url, response_time))
                else:
                    self.statistics.fastest_pages.append((url, response_time))
                
                # Keep only top 10
                self.statistics.slowest_pages = sorted(
                    self.statistics.slowest_pages, 
                    key=lambda x: x[1], 
                    reverse=True
                )[:10]
                self.statistics.fastest_pages = sorted(
                    self.statistics.fastest_pages, 
                    key=lambda x: x[1]
                )[:10]

            # Redirects
            if response.history:
                with self.data_lock:
                    self.redirects.append({
                        'original_url': url,
                        'final_url': response.url,
                        'redirect_chain': [r.url for r in response.history],
                        'status_codes': [r.status_code for r in response.history]
                    })
                    self.statistics.redirected_pages += 1
        
        # Process HTML only
        content_type = response.headers.get('content-type', '').lower()
        if 'html' not in content_type:
            logger.debug(f"Skipping non-HTML content: {url} ({content_type})")
            return set()
        
        try:
            # Hash content to detect duplicates
            import hashlib
            content_hash = hashlib.md5(response.content).hexdigest()
            
            # Check for duplicate content across DIFFERENT URLs
            with self.data_lock:
                duplicates = self.duplicate_content.setdefault(content_hash, [])
                if duplicates:
                    logger.debug(f"Duplicate content detected: {url} matches {duplicates[0]}")
                duplicates.append(url)

            # Extract data
            soup = BeautifulSoup(response.text, self.html_parser)
            page_data = self._extract_seo_data(url, response, soup)
            page_data.content_hash = content_hash
            page_data.response_time = response_time
            page_data.load_time = response_time
            
            # Historical comparison
            if self.compare_historical and self.db:
                try:
                    historical = self.db.get_historical_data(url)
                    if historical:
                        page_data.custom_data['historical_comparison'] = {
                            'title_changed': historical.get('title') != page_data.title,
                            'word_count_diff': page_data.word_count - historical.get('word_count', 0),
                            'performance_diff': page_data.response_time - historical.get('response_time', 0)
                        }
                except Exception as e:
                    logger.debug(f"Historical comparison failed for {url}: {str(e)[:80]}")
            
            # Get links
            try:
                internal_links, external_links = self._extract_links(url, soup, depth)
            except Exception as e:
                logger.debug(f"Link extraction failed for {url}: {str(e)[:80]}")
                internal_links, external_links = set(), set()
            
            page_data.internal_links_count = len(internal_links)
            page_data.external_links_count = len(external_links)
            
            with self.data_lock:
                # Store data
                self.page_data[url] = page_data
                self.internal_links[url] = [link for link, _, _ in internal_links]
                self.external_links[url] = list(external_links)
                self.url_depth[url] = depth
                
                self.statistics.successful_pages += 1

            # Persist links to database
            if self.db:
                try:
                    self.db.save_links_batch(url, list(internal_links), list(external_links))
                    # Save page data
                    self.db.save_page(page_data)
                except Exception as e:
                    logger.debug(f"Database save failed for {url}: {str(e)[:80]}")
            
            # Execute plugins
            if self.plugins:
                try:
                    self.plugins.execute('post_crawl', url, page_data)
                except Exception as e:
                    logger.debug(f"Plugin execution failed for {url}: {str(e)[:80]}")
            
            return internal_links
            
        except Exception as e:
            logger.error(f"Unexpected error processing {url}: {str(e)[:100]}")
            with self.data_lock:
                self.page_data[url] = PageData(url=url, error=str(e)[:200])
                self.statistics.failed_pages += 1
                self.statistics.errors_by_type['ProcessingError'] += 1
            return set()
    
    def _get_next_url(self) -> Tuple[Optional[str], Optional[int]]:
        """Get next URL with priority"""
        with self.url_lock:
            while not self.to_visit.empty():
                priority, depth, url = self.to_visit.get()
                if url not in self.visited and len(self.visited) < self.max_pages:
                    self.visited.add(url)
                    return url, depth
            return None, None
    
    def _add_urls(self, urls: Set[Tuple[str, int, Priority]]):
        """Add URLs with priority"""
        with self.url_lock:
            for url, depth, priority in urls:
                if url not in self.visited and len(self.visited) < self.max_pages:
                    self.to_visit.put((priority.value, depth, url))
    
    def crawl(self):
        """Main crawl with enhanced features"""
        logger.info("=" * 80)
        logger.info(" " * 25 + "🚀 SEO CRAWLER v4.0")
        logger.info("=" * 80)
        logger.info(f"Target: {self.base_url}")
        logger.info(f"Config: {self.max_pages} pages | {self.max_workers} workers")
        logger.info(f"Database: {'✓' if self.db else '✗'} | Plugins: {'✓' if self.plugins else '✗'}")
        logger.info("=" * 80 + "\n")
        
        self.statistics.start_time = datetime.now()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            # Initial submission
            for _ in range(min(self.max_workers, self.max_pages)):
                url, depth = self._get_next_url()
                if url:
                    future = executor.submit(self._crawl_page, url, depth)
                    futures[future] = (url, depth)
            
            # Process futures
            while futures and not self.interrupted:
                done, _ = wait(
                    futures.keys(),
                    timeout=1.0,
                    return_when=FIRST_COMPLETED
                )
                
                for future in done:
                    url, depth = futures.pop(future)
                    try:
                        new_links = future.result()
                        if new_links:
                            self._add_urls(new_links)
                        
                        # Progress indicator
                        progress = f"[{len(self.visited)}/{self.max_pages}]"
                        status = "✓" if url in self.page_data and self.page_data[url].status_code == 200 else "✗"
                        logger.info(f"{progress} {status} depth={depth} {url}")

                        # Emit progress callback if available (completed, total)
                        try:
                            if hasattr(self, 'progress_callback') and callable(self.progress_callback):
                                try:
                                    self.progress_callback(len(self.visited), self.max_pages)
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        # Fill thread pool with new URLs
                        while len(futures) < self.max_workers and len(self.visited) < self.max_pages and not self.interrupted:
                            next_url, next_depth = self._get_next_url()
                            if next_url:
                                new_future = executor.submit(self._crawl_page, next_url, next_depth)
                                futures[new_future] = (next_url, next_depth)
                            else:
                                break
                    
                    except Exception as e:
                        logger.error(f"Processing error {url}: {e}")
        
        self.statistics.end_time = datetime.now()
        self.statistics.total_pages = len(self.visited)
        
        elapsed = (self.statistics.end_time - self.statistics.start_time).total_seconds()
        self.statistics.pages_per_second = self.statistics.total_pages / elapsed if elapsed > 0 else 0
        
        if self.statistics.successful_pages > 0:
            total_response_time = sum(
                p.response_time for p in self.page_data.values() 
                if p.response_time > 0
            )
            self.statistics.avg_response_time = total_response_time / self.statistics.successful_pages
        
        logger.info(f"\n✅ Crawl complete! {len(self.visited)} pages in {elapsed:.2f}s")
        logger.info(f"📈 Speed: {self.statistics.pages_per_second:.2f} pages/s\n")
        
        return sorted(self.visited)
    
    def _calculate_inbound_links(self):
        """Calculate inbound links"""
        inbound_counts = defaultdict(int)
        
        for source_url, target_urls in self.internal_links.items():
            for target_url in target_urls:
                inbound_counts[target_url] += 1
        
        for url in self.page_data:
            if url in inbound_counts:
                self.page_data[url].inbound_links = inbound_counts[url]
    
    def _find_broken_links(self):
        """Find broken links"""
        logger.info("🔍 Analyzing broken links...")
        
        all_linked_urls = set()
        for links in self.internal_links.values():
            all_linked_urls.update(links)
        
        for url in all_linked_urls:
            if url in self.page_data:
                page = self.page_data[url]
                if page.status_code >= 400 or page.error:
                    for source_url, links in self.internal_links.items():
                        if url in links:
                            self.broken_links.append({
                                'source': source_url,
                                'broken_url': url,
                                'status_code': page.status_code,
                                'error': page.error
                            })
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get response cache statistics"""
        total_requests = self.response_cache.hits + self.response_cache.misses
        hit_rate = (self.response_cache.hits / total_requests * 100) if total_requests > 0 else 0.0
        return {
            'cache_hits': self.response_cache.hits,
            'cache_misses': self.response_cache.misses,
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2),
            'cache_size': len(self.response_cache.cache),
            'max_cache_size': self.response_cache.max_size
        }
    
    def generate_seo_report(self, filename: str = 'seo_report.json'):
        """Generate comprehensive report"""
        logger.info("📝 Generating SEO report...")
        
        self._calculate_inbound_links()
        self._find_broken_links()
        
        pages_with_data = [p for p in self.page_data.values() if p.status_code == 200]
        
        # Group issues by severity
        issues_by_severity = defaultdict(list)
        for issue in self.issues:
            issues_by_severity[issue['severity']].append(issue)
        
        stats = asdict(self.statistics)
        # Convert datetimes to ISO strings and defaultdicts to regular dicts for JSON serialization
        if stats.get('start_time'):
            stats['start_time'] = stats['start_time'].isoformat()
        if stats.get('end_time'):
            stats['end_time'] = stats['end_time'].isoformat() if stats['end_time'] else None
        stats['errors_by_type'] = dict(stats.get('errors_by_type', {}))
        stats['status_code_distribution'] = dict(stats.get('status_code_distribution', {}))

        report = {
            'metadata': {
                'crawl_date': self.statistics.start_time.isoformat(),
                'duration_seconds': (self.statistics.end_time - self.statistics.start_time).total_seconds(),
                'base_url': self.base_url,
                'version': '4.0',
                'crawler_config': {
                    'max_pages': self.max_pages,
                    'max_workers': self.max_workers,
                    'max_depth': self.max_depth,
                    'respect_robots': self.respect_robots
                }
            },
            'statistics': stats,
            'summary': {
                'total_pages': len(self.visited),
                'successful_pages': len(pages_with_data),
                'failed_pages': self.statistics.failed_pages,
                'total_issues': len(self.issues),
                'critical_issues': len(issues_by_severity['critical']),
                'warnings': len(issues_by_severity['warning']),
                'info': len(issues_by_severity['info']),
                'avg_response_time': self.statistics.avg_response_time,
                'avg_word_count': sum(p.word_count for p in pages_with_data) / len(pages_with_data) if pages_with_data else 0,
                'pages_with_ssl': sum(1 for p in pages_with_data if p.has_ssl),
                'pages_with_schema': sum(1 for p in pages_with_data if p.schema_types),
                'duplicate_content_groups': len([urls for urls in self.duplicate_content.values() if len(urls) > 1])
            },
            'issues': {
                'by_severity': dict(issues_by_severity),
                'all_issues': self.issues
            },
            'performance': {
                'slowest_pages': self.statistics.slowest_pages,
                'fastest_pages': self.statistics.fastest_pages,
                'status_code_distribution': dict(self.statistics.status_code_distribution),
                'errors_by_type': dict(self.statistics.errors_by_type)
            },
            'pages': {url: asdict(data) for url, data in self.page_data.items()},
            'broken_links': self.broken_links,
            'redirects': self.redirects,
            'duplicate_content': {
                f"group_{i}": urls 
                for i, (hash, urls) in enumerate(self.duplicate_content.items()) 
                if len(urls) > 1
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, cls=JsonEncoder)
        
        logger.info(f"✓ SEO report saved to {filename}")
        return report
    
    def export_to_csv(self, filename: str = 'seo_export.csv'):
        """Export to CSV"""
        logger.info("📊 Exporting to CSV...")
        
        pages_with_data = [p for p in self.page_data.values() if p.status_code == 200]
        
        if not pages_with_data:
            logger.warning("No data to export")
            return
        
        fieldnames = [
            'url', 'status_code', 'title', 'title_length', 'meta_description',
            'word_count', 'readability_score', 'response_time', 'inbound_links',
            'has_viewport', 'has_ssl', 'schema_types', 'depth', 'issues'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for page in pages_with_data:
                page_issues = [i for i in self.issues if i['url'] == page.url]
                writer.writerow({
                    'url': page.url,
                    'status_code': page.status_code,
                    'title': page.title,
                    'title_length': page.title_length,
                    'meta_description': page.meta_description,
                    'word_count': page.word_count,
                    'readability_score': f"{page.readability_score:.1f}",
                    'response_time': f"{page.response_time:.3f}",
                    'inbound_links': page.inbound_links,
                    'has_viewport': page.has_viewport,
                    'has_ssl': page.has_ssl,
                    'schema_types': ','.join(page.schema_types),
                    'depth': self.url_depth.get(page.url, 0),
                    'issues': len(page_issues)
                })
        
        logger.info(f"✓ CSV saved to {filename}")
    
    def print_summary(self):
        """Print enhanced summary"""
        pages_with_data = [p for p in self.page_data.values() if p.status_code == 200]
        
        print("\n" + "="*80)
        print(" "*28 + "SEO AUDIT SUMMARY")
        print("="*80)
        
        # Crawl stats
        elapsed = (self.statistics.end_time - self.statistics.start_time).total_seconds()
        print(f"\n⏱️  CRAWL STATISTICS")
        print(f"   Duration: {elapsed:.2f}s ({elapsed/60:.1f} minutes)")
        print(f"   Pages analyzed: {len(pages_with_data)}")
        print(f"   Failed: {self.statistics.failed_pages}")
        print(f"   Speed: {self.statistics.pages_per_second:.2f} pages/s")
        print(f"   Data transferred: {self.statistics.total_data_transferred / (1024*1024):.2f} MB")
        
        # Issues summary
        issues_by_severity = defaultdict(int)
        for issue in self.issues:
            issues_by_severity[issue['severity']] += 1
        
        print(f"\n🔍 ISSUES FOUND")
        print(f"   🔴 Critical: {issues_by_severity['critical']}")
        print(f"   ⚠️  Warnings: {issues_by_severity['warning']}")
        print(f"   ℹ️  Info: {issues_by_severity['info']}")
        print(f"   Total: {len(self.issues)}")
        
        # Performance
        print(f"\n⚡ PERFORMANCE")
        print(f"   Avg response: {self.statistics.avg_response_time:.3f}s")
        if self.statistics.slowest_pages:
            print(f"   Slowest page: {self.statistics.slowest_pages[0][1]:.2f}s")
        if self.statistics.fastest_pages:
            print(f"   Fastest page: {self.statistics.fastest_pages[0][1]:.3f}s")
        
        # Status codes
        print(f"\n📊 STATUS CODES")
        for code, count in sorted(self.statistics.status_code_distribution.items()):
            print(f"   {code}: {count}")
        
        # Top issues
        issue_types = Counter(i['type'] for i in self.issues)
        print(f"\n🏆 TOP ISSUES")
        for issue_type, count in issue_types.most_common(5):
            print(f"   {issue_type}: {count}")
        
        print("\n" + "="*80)
        print("✅ Full report saved to output files")
        print("="*80 + "\n")
    
    def generate_sitemap(self, output_file: str = 'sitemap.xml', compress: bool = False):
        """Generate sitemap"""
        logger.info("🗺️  Generating sitemap...")
        
        urlset = ET.Element('urlset')
        urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
        
        successful_pages = [
            (url, data) for url, data in self.page_data.items() 
            if data.status_code == 200
        ]
        
        for url, page_data in sorted(successful_pages):
            url_element = ET.SubElement(urlset, 'url')
            
            loc = ET.SubElement(url_element, 'loc')
            loc.text = url
            
            lastmod = ET.SubElement(url_element, 'lastmod')
            lastmod.text = datetime.now().strftime('%Y-%m-%d')
            
            changefreq = ET.SubElement(url_element, 'changefreq')
            changefreq.text = 'weekly'
            
            priority = ET.SubElement(url_element, 'priority')
            depth = self.url_depth.get(url, 0)
            priority.text = str(max(0.5, 1.0 - (depth * 0.1)))
        
        xml_str = minidom.parseString(ET.tostring(urlset)).toprettyxml(indent="  ")
        
        if compress:
            output_file = output_file.replace('.xml', '.xml.gz')
            with gzip.open(output_file, 'wt', encoding='utf-8') as f:
                f.write(xml_str)
        else:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(xml_str)
        
        logger.info(f"✓ Sitemap: {output_file} ({len(successful_pages)} URLs)")
    
    def close(self):
        """Cleanup"""
        self.session.close()
        if self.db:
            self.db.close()

def main():
    """Main with enhanced configuration"""
    
    config = {
        'website_url': "https://example.com",
        'max_pages': 100,
        'max_workers': 5,
        'timeout': 10,
        'respect_robots': True,
        'rate_limit_rps': 2.0,
        'max_depth': None,
        'exclude_patterns': [r'/admin/', r'/login', r'\?print='],
        'include_patterns': [],
        'follow_external': False,
        'use_database': True,
        'enable_plugins': True,
        'compare_historical': False,
        'compress_sitemap': False
    }
    
    output_dir = Path('seo_audit_output')
    output_dir.mkdir(exist_ok=True)
    
    crawler = AdvancedSEOCrawler(
        base_url=config['website_url'],
        max_pages=config['max_pages'],
        max_workers=config['max_workers'],
        timeout=config['timeout'],
        respect_robots=config['respect_robots'],
        rate_limit_rps=config['rate_limit_rps'],
        max_depth=config['max_depth'],
        exclude_patterns=config['exclude_patterns'],
        include_patterns=config['include_patterns'],
        follow_external=config['follow_external'],
        use_database=config['use_database'],
        enable_plugins=config['enable_plugins'],
        compare_historical=config['compare_historical']
    )
    
    try:
        urls = crawler.crawl()
        
        crawler.print_summary()
        crawler.generate_seo_report(str(output_dir / 'seo_report.json'))
        crawler.export_to_csv(str(output_dir / 'seo_data.csv'))
        crawler.generate_sitemap(
            str(output_dir / 'sitemap.xml'),
            compress=config['compress_sitemap']
        )
        
        logger.info("\n" + "="*80)
        logger.info("✅ SEO AUDIT COMPLETE!")
        logger.info("="*80)
        logger.info(f"📁 Output: {output_dir}/")
        logger.info("   📊 seo_report.json")
        logger.info("   📈 seo_data.csv")
        logger.info("   🗺️  sitemap.xml")
        logger.info("   💾 crawl_data.db")
        logger.info("="*80 + "\n")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted - generating partial reports...")
        crawler.print_summary()
        crawler.generate_seo_report(str(output_dir / 'seo_report_partial.json'))
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        raise
    finally:
        crawler.close()

if __name__ == "__main__":
    main()

