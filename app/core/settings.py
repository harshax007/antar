"""
Antar — Application Settings
Reads from .env file via pydantic-settings
"""

import base64
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Catalyst env-var workaround ───────────────────────────────────────────────
# Catalyst AppSail's env-var UI rejects VALUES that start with a digit, which breaks Zoho
# OAuth creds (they look like "1000.xxxx"). Fix: store the value base64-encoded under a
# "<NAME>_B64" key — base64 of "1000..." starts with a letter, so it passes the validator —
# and we decode it back into the plain env var here, BEFORE settings load. No call-site
# changes; if the plain var is already set, the _B64 form is ignored.
for _k in ("QUICKML_CLIENT_ID", "QUICKML_CLIENT_SECRET", "QUICKML_REFRESH_TOKEN",
           "QUICKML_ACCESS_TOKEN", "ANTAR_SESSION_KEY"):
    _b64 = os.environ.get(_k + "_B64")
    if _b64 and not os.environ.get(_k):
        try:
            os.environ[_k] = base64.b64decode(_b64).decode("utf-8").strip()
        except Exception:
            pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Catalyst Platform
    CATALYST_PROJECT_ID: str = ""
    CATALYST_PROJECT_SECRET: str = ""
    CATALYST_PROJECT_KEY: str = ""
    CATALYST_ENV: str = "development"

    # Stratus
    STRATUS_BUCKET_NAME: str = "antar-files"

    # Which language model, if any (app/services/llm.py). Unset = QuickML when its
    # credentials are present, otherwise none. "openai_compatible" is any server that speaks
    # /chat/completions, including a local one (Ollama: http://localhost:11434/v1).
    ANTAR_LLM_PROVIDER: str = ""        # quickml | openai_compatible | none
    ANTAR_LLM_BASE_URL: str = ""
    ANTAR_LLM_API_KEY: str = ""
    ANTAR_LLM_MODEL: str = ""

    # What may leave the building (app/core/egress.py). Unset = the configured endpoints and
    # the fixed feature services; "none" = nothing; or a comma-separated list of hosts.
    ANTAR_EGRESS_ALLOW: str = ""

    # QuickML LLM
    QUICKML_CLIENT_ID: str = ""
    QUICKML_CLIENT_SECRET: str = ""
    QUICKML_LLM_MODEL: str = "Qwen-3.6-Instruct"              # Default base model
    QUICKML_CHAT_MODEL: str = "GLM-4.7-Flash"                 # Dedicated fast model for /ask & chat interface
    # Public calendar the forecast reads festival DATES from (iCalendar). Only the date of
    # a festival on a fixed list is taken from it. Empty = built-in dates only.
    ANTAR_EVENT_FEED_URL: str = ("https://calendar.google.com/calendar/ical/"
                                 "en.indian%23holiday%40group.v.calendar.google.com/public/basic.ics")
    QUICKML_DEFAULT_MODEL: str = "Qwen-3.6-35B"               # Analytical model for non-chat screens & agents
    QUICKML_VISION_MODEL: str = "VL-Qwen3.6-35B-A3B"          # Vision-Language model for scanned evidence
    QUICKML_LLM_MAX_TOKENS: int = 4096   # NOTE: QuickML treats this as TOTAL context (input+output)
    QUICKML_LLM_TEMPERATURE: float = 0.3
    # Endpoint + auth (from the Catalyst QuickML console — paste your real values into .env)
    QUICKML_LLM_ENDPOINT_URL: str = ""          # e.g. https://api.catalyst.zoho.in/quickml/v2/project/<pid>/llm/chat
    QUICKML_CHAT_ENDPOINT_URL: str = ""         # e.g. https://api.catalyst.zoho.in/quickml/v1/project/<pid>/glm/chat
    QUICKML_VISION_ENDPOINT_URL: str = ""       # e.g. https://api.catalyst.zoho.in/quickml/v1/project/<pid>/vlm/chat
    QUICKML_ORG_ID: str = ""                     # CATALYST-ORG header value (your Zoho org id)
    QUICKML_TOKEN_URL: str = "https://accounts.zoho.in/oauth/v2/token"
    QUICKML_SCOPE: str = "QuickML.deployment.READ"   # confirmed from the console
    QUICKML_AUTH_MODE: str = "oauth"            # "oauth" | "apikey" | "none"
    QUICKML_SOID: str = ""                       # scope-owner-id for client_credentials (default ZohoCatalyst.<org>)
    QUICKML_ACCESS_TOKEN: str = ""              # paste a token directly for quick testing (skips token fetch)
    QUICKML_API_KEY: str = ""                    # if the endpoint uses a direct API key/header
    QUICKML_REFRESH_TOKEN: str = ""              # refresh-token grant (durable; preferred for the app)

    # Cron secret
    CRON_SECRET_KEY: str = "change-me-in-production"

    # VAPID (Push Notifications)
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_EMAIL: str = "mailto:antar@example.com"

    # Bhashini
    BHASHINI_API_KEY: str = ""
    BHASHINI_USER_ID: str = ""

    # App
    ALLOWED_ORIGINS: str = "http://localhost:3000"   # comma-separated; use allowed_origins_list
    DEMO_MODE: bool = False
    APP_PORT: int = 8000
    PROMPT_VERSION: str = "v1"

    # Second Brain
    # BAAI/bge-small-en-v1.5: same 384-dim as MiniLM, top MTEB retrieval scores at ~33MB.
    # Scores tend to be lower than MiniLM (BGE uses CLS pooling + normalisation), so
    # threshold is tuned down to 0.60 (empirically equivalent recall).
    BRAIN_EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    BRAIN_COSINE_TOP_K: int = 5
    BRAIN_SIMILARITY_THRESHOLD: float = 0.60

    # Logging
    LOG_LEVEL: str = "INFO"

    # ── Security posture (app/core/security.py, docs/SECURITY.md) ──
    # "production" turns on the fail-closed behaviour: API docs hidden, HSTS sent, the
    # default cron secret refused, and a loud startup warning if identity is still the
    # unsigned X-Role header. CATALYST_ENV=production has the same effect.
    ANTAR_ENV: str = "development"
    # When set, every /api/* call must carry `Authorization: Bearer <token>` minted with
    # this secret (scripts/mint_token.py); X-Role / X-Officer are then ignored entirely.
    # Empty = demo header identity (anyone can claim any role — never ship that).
    ANTAR_AUTH_SECRET: str = ""
    ANTAR_TOKEN_TTL_S: int = 8 * 3600          # one shift
    # Who may sign in (app/core/accounts.py). ANTAR_USERS is a JSON object of accounts for
    # a container; otherwise the file is read. Written by scripts/set_password.py - only
    # salted hashes, never a password.
    ANTAR_USERS: str = ""
    ANTAR_USERS_FILE: str = "auth_users.json"
    # Proxies in front of the app that append to X-Forwarded-For (AppSail gateway = 1).
    # 0 = ignore the header and rate-limit on the socket address.
    ANTAR_TRUSTED_PROXY_HOPS: int = 1
    ANTAR_MAX_BODY_MB: int = 12                # evidence scans arrive as base64 JSON
    ANTAR_EXPOSE_DOCS: bool = False            # force /docs on in production (debug only)

    # ── Observability (all optional; layer is inert unless OBS_ENABLED=True) ──
    OBS_ENABLED: bool = True              # master switch — off in prod until proven
    OBS_DIR: str = "data_sessions/obs"     # relative to antar-backend root
    OBS_JUDGE_SAMPLE: float = 0.05         # 5% random sample judged (flagged always judged)
    OBS_JUDGE_ENABLED: bool = True         # set False to cut ALL judge token spend
    OBS_COST_PER_1K: float = 0.0           # $ per 1k tokens; 0.0 => cost column shows $0.00
    OBS_SPIKE_K: float = 2.0               # latency/token spike = > baseline_p95 * K
    OBS_JSONL_MAX_MB: int = 64             # rotate obs_spans.jsonl past this size

    @property
    def allowed_origins_list(self) -> list[str]:
        """CORS origins as a list (ALLOWED_ORIGINS is a comma-separated string in .env)."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


# Singleton — import this everywhere
settings = Settings()
