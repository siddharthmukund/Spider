"""Package initializer for the webapp API.

This file ensures that the `webapp` directory is recognized as a Python
package in tests and other imports. It can also be used to expose top-level
symbols if needed.
"""

# We don't currently need to expose anything at package import time, but
# having this file makes `import webapp` work as expected.  
__version__ = "0.1.0"  # placeholder
