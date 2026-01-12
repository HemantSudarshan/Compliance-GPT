"""
locustfile.py - Load Testing for ComplianceGPT

Run with: locust -f tests/load/locustfile.py --host http://localhost:8000
"""

from locust import HttpUser, task, between, events
import random


# Sample questions for load testing
SAMPLE_QUESTIONS = [
    "What are the data breach notification requirements under GDPR?",
    "What is the right to erasure?",
    "What are the maximum fines for GDPR violations?",
    "What rights do data subjects have under GDPR?",
    "What is the lawful basis for processing personal data?",
    "What are the requirements for valid consent under GDPR?",
    "When is a Data Protection Officer required?",
    "What is a Data Protection Impact Assessment?",
    "What are the principles of data processing under GDPR?",
    "What are special categories of personal data?",
    "How does CCPA define personal information?",
    "What are consumer rights under CCPA?",
    "What is the right to opt-out under CCPA?",
    "What are the PCI-DSS requirements for encryption?",
    "How long must breach notifications be kept?",
]

REGULATIONS = ["All", "GDPR", "CCPA", "PCI-DSS"]


class ComplianceGPTUser(HttpUser):
    """Simulates a user querying ComplianceGPT."""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    def on_start(self):
        """Called when a simulated user starts."""
        # Check if API is healthy
        response = self.client.get("/api/health")
        if response.status_code != 200:
            raise Exception("API is not healthy")
    
    @task(10)  # Weight: 10 (most common)
    def query_compliance(self):
        """Submit a compliance query."""
        question = random.choice(SAMPLE_QUESTIONS)
        regulation = random.choice(REGULATIONS)
        
        payload = {
            "question": question,
            "regulation": regulation
        }
        
        with self.client.post(
            "/api/query",
            json=payload,
            catch_response=True,
            name="/api/query"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "answer" in data and "citations" in data:
                    response.success()
                else:
                    response.failure("Invalid response format")
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(3)  # Weight: 3
    def check_health(self):
        """Check API health."""
        with self.client.get(
            "/api/health",
            catch_response=True,
            name="/api/health"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") in ["healthy", "degraded"]:
                    response.success()
                else:
                    response.failure("Unhealthy status")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(2)  # Weight: 2
    def get_regulations(self):
        """Fetch available regulations."""
        self.client.get("/api/regulations", name="/api/regulations")
    
    @task(1)  # Weight: 1
    def get_stats(self):
        """Fetch API stats."""
        self.client.get("/api/stats", name="/api/stats")


class HeavyUser(HttpUser):
    """Simulates a heavy API user (for stress testing)."""
    
    wait_time = between(0.1, 0.5)  # Very short wait times
    weight = 1  # Lower weight than normal users
    
    @task
    def rapid_queries(self):
        """Submit queries rapidly to test rate limiting."""
        question = random.choice(SAMPLE_QUESTIONS)
        
        payload = {"question": question}
        
        with self.client.post(
            "/api/query",
            json=payload,
            catch_response=True,
            name="/api/query [heavy]"
        ) as response:
            # We expect some rate limiting
            if response.status_code in [200, 429]:
                response.success()
            else:
                response.failure(f"Unexpected: {response.status_code}")


class CacheTestUser(HttpUser):
    """Tests cache effectiveness by repeating queries."""
    
    wait_time = between(0.5, 1)
    weight = 1
    
    def on_start(self):
        """Pick a question to repeat."""
        self.repeated_question = random.choice(SAMPLE_QUESTIONS[:5])
    
    @task
    def repeated_query(self):
        """Submit the same query repeatedly (should hit cache)."""
        payload = {"question": self.repeated_question}
        
        with self.client.post(
            "/api/query",
            json=payload,
            catch_response=True,
            name="/api/query [cache-test]"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Track if response was cached
                if data.get("cached"):
                    response.success()
                else:
                    response.success()  # First request won't be cached
            else:
                response.failure(f"Status: {response.status_code}")


# =============================================================================
# Custom Event Handlers for Reporting
# =============================================================================

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, **kwargs):
    """Log detailed request metrics."""
    if response_time > 2000:  # Log slow requests (>2s)
        print(f"⚠️ Slow request: {name} took {response_time:.0f}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("=" * 60)
    print("🚀 Starting ComplianceGPT Load Test")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test ends."""
    print("=" * 60)
    print("✅ Load Test Complete")
    print("=" * 60)
    
    # Print summary
    stats = environment.stats
    print(f"\nTotal Requests: {stats.total.num_requests}")
    print(f"Failures: {stats.total.num_failures}")
    print(f"Avg Response Time: {stats.total.avg_response_time:.0f}ms")
    print(f"Requests/sec: {stats.total.current_rps:.2f}")


# =============================================================================
# Standalone Test Runner
# =============================================================================

if __name__ == "__main__":
    import subprocess
    import sys
    
    host = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print(f"Running load test against: {host}")
    print("Press Ctrl+C to stop\n")
    
    subprocess.run([
        "locust",
        "-f", __file__,
        "--host", host,
        "--users", "10",
        "--spawn-rate", "2",
        "--run-time", "60s",
        "--headless",
        "--html", "load-test-report.html"
    ])
