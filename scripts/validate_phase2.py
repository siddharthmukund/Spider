#!/usr/bin/env python3
"""
Phase 2 Security Validation Script

Validates that all Phase 2 security features are properly implemented.
"""

import sys
import os
import importlib.util
from pathlib import Path


def check_module_exists(module_path: str) -> bool:
    """Check if a Python module exists."""
    try:
        spec = importlib.util.find_spec(module_path)
        return spec is not None
    except (ModuleNotFoundError, ValueError):
        return False


def check_file_exists(file_path: str) -> bool:
    """Check if a file exists."""
    return Path(file_path).exists()


def validate_phase2():
    """Validate Phase 2 implementation."""
    print("=" * 60)
    print("Phase 2: Security Hardening - Validation Report")
    print("=" * 60)
    print()
    
    all_checks_passed = True
    
    # 1. Security Modules
    print("📦 Security Modules")
    modules = [
        ("webapp.security.auth", "Authentication"),
        ("webapp.security.ssrf", "SSRF Protection"),
        ("webapp.security.rate_limit", "Rate Limiting"),
        ("webapp.security.audit", "Audit Logging"),
    ]
    
    for module_path, name in modules:
        exists = check_module_exists(module_path)
        status = "✅" if exists else "❌"
        print(f"  {status} {name}: {module_path}")
        if not exists:
            all_checks_passed = False
    print()
    
    # 2. Integration with main.py
    print("🔌 Integration Points")
    checks = []
    
    if check_module_exists("webapp.main"):
        try:
            import webapp.main as main_module
            
            # Check for security imports
            has_auth = hasattr(main_module, 'verify_api_key')
            checks.append(("Authentication imported", has_auth))
            
            # Check for rate limiter
            has_rate_limiter = hasattr(main_module, 'rate_limiter')
            checks.append(("Rate limiter initialized", has_rate_limiter))
            
            # Check for audit logger (named 'audit' in main.py)
            has_audit = hasattr(main_module, 'audit')
            checks.append(("Audit logger initialized", has_audit))
            
        except Exception as e:
            checks.append(("main.py import", False))
            print(f"  ⚠️  Error importing main.py: {e}")
    else:
        checks.append(("main.py exists", False))
    
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")
        if not passed:
            all_checks_passed = False
    print()
    
    # 3. Test Files
    print("🧪 Test Suite")
    test_files = [
        "tests/security/test_security.py",
        "tests/api/test_start_endpoint.py",
        "tests/api/test_status_endpoint.py",
    ]
    
    for test_file in test_files:
        exists = check_file_exists(test_file)
        status = "✅" if exists else "❌"
        print(f"  {status} {test_file}")
        if not exists:
            all_checks_passed = False
    print()
    
    # 4. Documentation
    print("📚 Documentation")
    docs = [
        "docs/PHASE2_COMPLETION.md",
        "webapp/README.md",
    ]
    
    for doc_file in docs:
        exists = check_file_exists(doc_file)
        status = "✅" if exists else "❌"
        print(f"  {status} {doc_file}")
        if not exists:
            all_checks_passed = False
    print()
    
    # 5. Environment Configuration
    print("⚙️  Environment Configuration")
    env_checks = [
        ("WEBAPP_API_KEY", os.getenv("WEBAPP_API_KEY")),
        ("RATE_LIMIT_MAX", os.getenv("RATE_LIMIT_MAX", "60 (default)")),
        ("RATE_LIMIT_WINDOW", os.getenv("RATE_LIMIT_WINDOW", "60 (default)")),
    ]
    
    for var_name, value in env_checks:
        is_set = value is not None
        status = "✅" if is_set else "⚠️ "
        display_value = value if value else "Not set"
        print(f"  {status} {var_name}: {display_value}")
    print()
    
    # 6. Security Classes
    print("🔐 Security Classes")
    
    try:
        from webapp.security.ssrf import SSRFValidator
        print("  ✅ SSRFValidator")
        
        # Test SSRF validator
        is_valid, error = SSRFValidator.validate("https://example.com")
        if is_valid:
            print("    ✅ Accepts valid URLs")
        else:
            print(f"    ❌ Failed to accept valid URL: {error}")
            all_checks_passed = False
        
        is_valid, error = SSRFValidator.validate("http://localhost/")
        if not is_valid:
            print("    ✅ Blocks localhost")
        else:
            print("    ❌ Failed to block localhost")
            all_checks_passed = False
            
    except ImportError as e:
        print(f"  ❌ Failed to import SSRFValidator: {e}")
        all_checks_passed = False
    
    try:
        from webapp.security.rate_limit import RateLimiter
        print("  ✅ RateLimiter")
        
        # Test rate limiter
        limiter = RateLimiter(requests_per_minute=10)
        if limiter.check("test_client"):
            print("    ✅ Allows requests under limit")
        else:
            print("    ❌ Incorrectly blocked request")
            all_checks_passed = False
            
    except ImportError as e:
        print(f"  ❌ Failed to import RateLimiter: {e}")
        all_checks_passed = False
    
    try:
        from webapp.security.audit import AuditLogger, AuditEvent
        print("  ✅ AuditLogger")
        
        # Check event types
        event_types = [e.value for e in AuditEvent]
        expected_events = [
            "auth.success",
            "auth.failure",
            "security.ssrf_blocked",
            "security.rate_limited",
            "crawl.start",
            "crawl.complete"
        ]
        if all(e in event_types for e in expected_events):
            print(f"    ✅ All event types defined ({len(event_types)} total)")
        else:
            missing = [e for e in expected_events if e not in event_types]
            print(f"    ❌ Missing event types: {missing}")
            all_checks_passed = False
            
    except ImportError as e:
        print(f"  ❌ Failed to import AuditLogger: {e}")
        all_checks_passed = False
    
    print()
    
    # Final Summary
    print("=" * 60)
    if all_checks_passed:
        print("✅ Phase 2 Validation: PASSED")
        print()
        print("All security features are properly implemented and integrated.")
        print()
        print("Next Steps:")
        print("  1. Set WEBAPP_API_KEY environment variable")
        print("  2. Run tests: pytest tests/security/ -v")
        print("  3. Start server: uvicorn webapp.main:app --reload")
        print("  4. Test with authentication: See docs/PHASE2_COMPLETION.md")
        return 0
    else:
        print("❌ Phase 2 Validation: FAILED")
        print()
        print("Some security features are missing or misconfigured.")
        print("Please review the errors above and fix them.")
        return 1


if __name__ == "__main__":
    # Add project root to path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    exit_code = validate_phase2()
    sys.exit(exit_code)
