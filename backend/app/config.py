import os
from pathlib import Path

# Use cached local weights without network lookup delays
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_PERSIST_DIR = str(DATA_DIR / "chroma_db")
DOCS_STORAGE_DIR = str(DATA_DIR / "documents")
SAMPLE_DOCS_DIR = str(BASE_DIR / "sample_docs")

# Load environment variables
load_dotenv(BASE_DIR / ".env")

# NVIDIA Nemotron Inference API configuration
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
# Officially supported Nemotron models
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3.5-bolt-e4b")

# RAG & Embedding configuration
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION_NAME = "ieee_rag_knowledge_base"
DEFAULT_TOP_K = 4
SIMILARITY_THRESHOLD = 0.35  # Cosine similarity threshold for relevance

# Ingestion settings
CHUNK_SIZE = 650  # Characters
CHUNK_OVERLAP = 120  # Characters
MAX_FILE_SIZE_MB = 20
ALLOWED_EXTENSIONS = {".pdf"}

# Ensure directories exist
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
os.makedirs(DOCS_STORAGE_DIR, exist_ok=True)
os.makedirs(SAMPLE_DOCS_DIR, exist_ok=True)
