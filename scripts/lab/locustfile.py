"""
Antar — Locust Concurrency Load Test (Phase L5.4)
Simulates realistic concurrent officer traffic (50 users, spawn rate 5/s)
against chat streaming, forecast hotspots, map tiles, and health probes.
"""
import json
import os
import random
from pathlib import Path
from locust import HttpUser, task, between

ROOT = Path(__file__).resolve().parent.parent.parent
GOLD_FILE = ROOT / "docs" / "gold" / "gold_questions.jsonl"

SAMPLE_QUESTIONS = [
    "How many FIRs were registered in Mysuru City in 2023?",
    "Top crime types in Bengaluru City this year",
    "Which districts have the most vehicle theft?",
    "How many theft cases were registered in Bengaluru City in 2023?",
    "Which police stations in Mysuru City have the most burglary?",
    "Compare burglary in Belagavi Dist and Dharwad in 2023?",
    "How many murder cases were registered in Kalaburagi in 2023?",
    "Show me FIR C00418",
    "How many FIRs were registered today?",
]

if GOLD_FILE.exists():
    try:
        with open(GOLD_FILE, "r", encoding="utf-8") as f:
            en_qs = [json.loads(line)["question"] for line in f if json.loads(line).get("lang") == "en"]
            if en_qs:
                SAMPLE_QUESTIONS = en_qs
    except Exception:
        pass


class AntarOfficerUser(HttpUser):
    wait_time = between(1.0, 3.0)

    def on_start(self):
        self.officer_id = f"OFFICER-{random.randint(1000, 9999)}"
        self.role = "Inspector"
        self.headers = {
            "Content-Type": "application/json",
            "X-Role": self.role,
            "X-Officer": self.officer_id,
        }
        # Mint token if secret is present
        secret = os.environ.get("ANTAR_AUTH_SECRET", "")
        if len(secret) >= 32:
            try:
                from app.core.auth_middleware import mint_token
                token = mint_token(self.officer_id, self.role, ttl_s=3600, secret=secret)
                self.headers["Authorization"] = f"Bearer {token}"
            except Exception:
                pass

    @task(5)
    def chat_query(self):
        q = random.choice(SAMPLE_QUESTIONS)
        payload = {
            "question": q,
            "session_id": f"locust-{self.officer_id}",
            "lang": "en",
        }
        self.client.post("/api/chat", json=payload, headers=self.headers, name="/api/chat")

    @task(2)
    def forecast_hotspots(self):
        self.client.get(
            "/api/forecast/hotspots?horizon=7&category=ALL&unit=station&limit=10",
            headers=self.headers,
            name="/api/forecast/hotspots",
        )

    @task(2)
    def map_status(self):
        self.client.get(
            "/api/map/hotspots?time_filter=7d",
            headers=self.headers,
            name="/api/map/hotspots",
        )

    @task(1)
    def health_check(self):
        self.client.get("/api/health", name="/api/health")
