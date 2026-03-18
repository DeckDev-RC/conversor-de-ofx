import uvicorn
import os
import sys

# When frozen by PyInstaller, module paths are already configured.
# When running from source, add parent dir so 'backend' package resolves.
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app

if __name__ == "__main__":
    # Get port from env or default to 8199
    port = int(os.environ.get("PORT", 8199))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
