import os
from dotenv import load_dotenv

load_dotenv()

GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_PROJECT_ID = int(os.getenv("GITLAB_PROJECT_ID", "0"))
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
AI_BASE_URL = os.getenv("AI_BASE_URL")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL")
AI_FALLBACK_MODEL = os.getenv("AI_FALLBACK_MODEL")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_MEMORY_REPOSITORY = os.getenv("GITHUB_MEMORY_REPOSITORY")
GITHUB_MEMORY_BRANCH = os.getenv("GITHUB_MEMORY_BRANCH", "main")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
PORT = int(os.getenv("PORT", 8000))
DASHBOARD_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "DASHBOARD_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

CLAUDE_MODEL = "claude-sonnet-4-5"
CLAUDE_MAX_TOKENS = 2000
CLAUDE_TEMPERATURE = 0.0
LLM_MODEL = AI_MODEL or CLAUDE_MODEL

LORE_INDEX_SLUG = "LORE-INDEX"
MEMORY_SLUG_PREFIX = "LORE-MEMORY-"
LORE_SPEC_SLUG_PREFIX = "LORE-SPEC-"
