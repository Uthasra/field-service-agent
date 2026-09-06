"""Configuration. Everything comes from environment variables so the same
code runs against Groq (free tier) today and Azure OpenAI later."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MANUAL_DIR = DATA_DIR / "manuals"
INDEX_PATH = DATA_DIR / "manual_index.npz"
DB_PATH = DATA_DIR / "fsm.db"

# --- LLM -------------------------------------------------------------------
# Any OpenAI-compatible endpoint. Swap these three values to change provider.
#   Groq   : https://api.groq.com/openai/v1
#   Azure  : https://<resource>.openai.azure.com/openai/v1
#   Ollama : http://localhost:11434/v1
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")

# --- Retrieval -------------------------------------------------------------
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_WORDS = int(os.getenv("CHUNK_WORDS", "120"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "30"))
TOP_K = int(os.getenv("TOP_K", "4"))
# Ablation switch: forces the lexical retriever even when vectors exist, so the
# two retrieval arms can be compared without reinstalling anything.
FORCE_LEXICAL = os.getenv("FORCE_LEXICAL", "false").lower() == "true"

# --- Agent -----------------------------------------------------------------
MAX_TOOL_ROUNDS = int(os.getenv("MAX_TOOL_ROUNDS", "6"))
# When false, the agent may read but never write. Useful for red-team runs.
ALLOW_WRITES = os.getenv("ALLOW_WRITES", "true").lower() == "true"
