from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).parent.parent
PATH_TO_ENV = BASE_DIR / ".env"

load_dotenv(PATH_TO_ENV)

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
