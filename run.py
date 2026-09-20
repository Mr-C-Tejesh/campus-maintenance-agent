import sys
import os
import argparse

# Ensure the 'app' module can be imported when running from the root
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app.main import main


def parse_args():
    parser = argparse.ArgumentParser(
        description="Campus/Facility Infrastructure Decision-Support Agent"
    )
    parser.add_argument(
        "--server", "-s",
        action="store_true",
        help="Start the FastAPI backend server"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Server host (default: 0.0.0.0)"
    )
    default_port = int(os.getenv("PORT", "8000"))
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=default_port,
        help=f"Server port (default: {default_port})"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn hot reloading"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    if args.server:
        import uvicorn
        print(f"Starting API server on http://{args.host}:{args.port}")
        uvicorn.run("app.api:app", host=args.host, port=args.port, reload=args.reload)
    else:
        main()
