"""Load test: `locust -f loadtest/locustfile.py --host http://localhost:8000` (needs .[dev]).
Headless example: locust -f loadtest/locustfile.py --host http://localhost:8000 -u 20 -r 5 -t 60s --headless --csv results/load
Set CIQ_RATE_LIMIT high on the server (e.g. 100000) or you will measure the rate limiter."""
import os
import random

from locust import HttpUser, between, task

TEXTS = [
    "Unauthorized charge on my card. I did not make these transactions and the bank denied my dispute.",
    "The mortgage servicer started foreclosure while my loan modification was still pending.",
    "A collector keeps calling about a debt that is not mine and refuses to send validation.",
    "Bank closed my checking account without notice and froze my funds for weeks.",
    "A wrong late payment is on my credit report and the bureau closed my dispute without review.",
]
HEADERS = {"X-API-Key": os.getenv("CIQ_API_KEY", "")} if os.getenv("CIQ_API_KEY") else {}


class ComplaintUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(5)
    def triage(self):
        self.client.post("/triage", json={"text": random.choice(TEXTS)}, headers=HEADERS)

    @task(2)
    def draft(self):
        self.client.post("/draft", json={"text": random.choice(TEXTS)}, headers=HEADERS)

    @task(1)
    def health(self):
        self.client.get("/health")
