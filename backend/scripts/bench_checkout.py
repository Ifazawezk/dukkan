"""Measure the API the way a till uses it.

Builds a throwaway SQLite database, applies the migrations, seeds the demo
shop, starts a real uvicorn server and sends requests one at a time over a
keep-alive HTTP connection, like a single till on the same machine.

    python scripts/bench_checkout.py
    python scripts/bench_checkout.py --requests 1000

Nothing touches your own database. The numbers depend on the machine, so the
script prints what it ran on along with the results.
"""

import argparse
import http.client
import json
import os
import platform
import random
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PORT = 8123


class Client:
    def __init__(self) -> None:
        self.connection = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
        self.headers: dict[str, str] = {}

    def request(self, method: str, path: str, body=None, form=None):
        headers = dict(self.headers)
        data = None
        if body is not None:
            data = json.dumps(body)
            headers["Content-Type"] = "application/json"
        if form is not None:
            data = urllib.parse.urlencode(form)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        self.connection.request(method, f"/api{path}", data, headers)
        response = self.connection.getresponse()
        payload = response.read()
        return response.status, json.loads(payload) if payload else None


def wait_for_server(process: subprocess.Popen) -> None:
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError("the server stopped during startup")
        try:
            status, _ = Client().request("GET", "/health")
            if status == 200:
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("the server did not start in time")


def timed(samples: list[float], client: Client, method: str, path: str, body=None):
    started = time.perf_counter()
    status, payload = client.request(method, path, body)
    samples.append((time.perf_counter() - started) * 1000)
    if status >= 400:
        raise RuntimeError(f"{method} {path} failed with {status}: {payload}")
    return payload


def percentile(samples: list[float], percent: int) -> float:
    return statistics.quantiles(samples, n=100, method="inclusive")[percent - 1]


def report(name: str, samples: list[float]) -> None:
    print(
        f"{name:<22} n={len(samples):<5} "
        f"p50={percentile(samples, 50):7.1f} ms  "
        f"p95={percentile(samples, 95):7.1f} ms  "
        f"max={max(samples):7.1f} ms"
    )


def run(requests: int, directory: str) -> None:
    db_path = Path(directory) / "bench.db"
    env = {**os.environ, "DUKKAN_DATABASE_URL": f"sqlite:///{db_path.as_posix()}"}

    def python(*args: str) -> None:
        subprocess.run(
            [sys.executable, "-m", *args],
            cwd=BACKEND_DIR,
            env=env,
            check=True,
            capture_output=True,
        )

    python("alembic", "upgrade", "head")
    started = time.perf_counter()
    python("app.cli", "seed")
    print(f"Seeding the 45 day demo shop took {time.perf_counter() - started:.1f} s")

    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--port",
            str(PORT),
            "--log-level",
            "warning",
        ],
        cwd=BACKEND_DIR,
        env=env,
    )
    try:
        wait_for_server(server)
        client = Client()
        _, login = client.request(
            "POST", "/auth/login", form={"username": "manager", "password": "dukkan123"}
        )
        client.headers["Authorization"] = f"Bearer {login['access_token']}"
        branch_id = login["user"]["branch_id"]

        _, page = client.request("GET", f"/products?limit=500&branch_id={branch_id}")
        products = page["items"]
        # Enough stock that the run measures selling, not running out.
        for product in products:
            client.request(
                "POST",
                "/inventory/adjustments",
                {
                    "product_id": product["id"],
                    "branch_id": branch_id,
                    "reason": "count_correction",
                    "quantity_change": 20_000,
                },
            )

        rng = random.Random(2026)
        scans: list[float] = []
        checkouts: list[float] = []
        reports: list[float] = []
        for _ in range(requests):
            basket = rng.sample(products, 3)
            for product in basket:
                code = urllib.parse.quote(product["barcode"])
                timed(scans, client, "GET", f"/products/lookup?code={code}&branch_id={branch_id}")
            timed(
                checkouts,
                client,
                "POST",
                "/sales",
                {
                    "branch_id": branch_id,
                    "items": [{"product_id": p["id"], "quantity": 1} for p in basket],
                    "payments": [{"method": "cash", "amount": 1000}],
                },
            )
        for _ in range(max(requests // 10, 20)):
            timed(reports, client, "GET", "/reports/summary")

        print(f"\n{platform.system()} {platform.release()}, Python {platform.python_version()}")
        print("SQLite file database, one client, keep-alive connection, uvicorn with one worker\n")
        report("Barcode lookup", scans)
        report("Checkout (3 items)", checkouts)
        report("30 day summary report", reports)
    finally:
        server.terminate()
        server.wait(timeout=10)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--requests", type=int, default=500, help="checkouts to run (default 500)")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        run(args.requests, directory)


if __name__ == "__main__":
    main()
