import uvicorn
from app.api.main import app
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    host = os.getenv("API_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("API_SERVER_PROT", 8000))
    uvicorn.run(app, host=host, port=port)
