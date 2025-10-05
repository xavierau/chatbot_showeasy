import uvicorn
import os

# Load environment variables FIRST before importing any application modules
from config.env import load_environment
load_environment()

# Now import app after environment is loaded
from app.api.main import app

if __name__ == "__main__":
    host = os.getenv("API_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("API_SERVER_PORT", 8000))
    uvicorn.run(app, host=host, port=port)
