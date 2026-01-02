"""Run the API server from project root."""

import sys
from pathlib import Path

# Ensure we're in the project root
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.server:app",
        host="127.0.0.1",  # Use 127.0.0.1 for local access, or 0.0.0.0 for all interfaces (then access via localhost:8000)
        port=8000,
        reload=True,
        log_level="info"
    )

