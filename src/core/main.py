import sys
from dotenv import load_dotenv

load_dotenv(override=True)

from src.core.pipeline import run_pipeline

if __name__ == "__main__":
    query_arg = sys.argv[1] if len(sys.argv) > 1 else "Latest advances in Agentic AI architectures"
    run_pipeline(query_arg)