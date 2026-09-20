import sys
import os

# Ensure the 'app' module can be imported when running from the root
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.main import main

if __name__ == "__main__":
    main()
