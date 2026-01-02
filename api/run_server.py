"""Run the API server."""

import sys
from pathlib import Path

# Add parent directory to path so we can import api module and other modules
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

import uvicorn

if __name__ == "__main__":
    # Run from parent directory context
    # Use 127.0.0.1 instead of 0.0.0.0 for browser access
    # Or use 0.0.0.0 if you need external access, but access via localhost:8000
    uvicorn.run(
        "api.server:app",
        host="127.0.0.1",  # Use 127.0.0.1 for local access, or 0.0.0.0 for all interfaces
        port=8000,
        reload=False,  # Disable reload to avoid import issues
        log_level="info"
    )

