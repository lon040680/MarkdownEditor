import argparse
import uvicorn
from app.main import app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Markdown Editor Backend")
    parser.add_argument("--port", type=int, default=48765, help="Port to listen on")
    args = parser.parse_args()

    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="info")
