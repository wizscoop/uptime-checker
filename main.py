import csv
from datetime import datetime
import os
import time
import requests

# Configuration
TARGETS_FILE = "targets.txt"
LOG_FILE = "uptime_log.csv"
CHECK_INTERVAL_SECONDS = 30
TIMEOUT_SECONDS = 5


def load_targets(file_path: str = TARGETS_FILE) -> list[str]:
    """Reads URLs from a file, ignoring empty lines and comments."""
    if not os.path.exists(file_path):
        # Create a starter file if it doesn't exist yet
        sample_targets = [
            "https://github.com",
            "https://google.com",
            "https://httpstat.us/500",  # Simulates an internal server error
            "https://httpstat.us/404",  # Simulates a missing page
        ]
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(sample_targets) + "\n")
        print(f"[i] Created default '{file_path}' with sample URLs.\n")
        return sample_targets

    with open(file_path, "r", encoding="utf-8") as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]


def log_result(
    url: str,
    status: str,
    status_code: str | int,
    latency_ms: str | int,
    log_file: str = LOG_FILE,
):
    """Appends check results with an ISO timestamp into a CSV spreadsheet."""
    file_exists = os.path.exists(log_file)
    with open(log_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(
                ["Timestamp", "URL", "Status", "StatusCode", "LatencyMS"]
            )
        writer.writerow(
            [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                url,
                status,
                status_code,
                latency_ms,
            ]
        )


def check_site(url: str):
    """Sends a GET request, tracks response latency, and handles errors."""
    try:
        start_time = time.perf_counter()
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
        latency_ms = round((time.perf_counter() - start_time) * 1000)

        if response.status_code == 200:
            status = "UP"
            print(f"  [UP]      {url:<32} {response.status_code} ({latency_ms}ms)")
        else:
            status = "WARN"
            print(f"  [WARN]    {url:<32} {response.status_code} ({latency_ms}ms)")

        log_result(url, status, response.status_code, latency_ms)

    except requests.exceptions.Timeout:
        print(f"  [TIMEOUT] {url:<32} Exceeded {TIMEOUT_SECONDS}s limit")
        log_result(url, "TIMEOUT", "TIMEOUT", "N/A")

    except requests.exceptions.ConnectionError:
        print(f"  [DOWN]    {url:<32} Unreachable / DNS failure")
        log_result(url, "DOWN", "DOWN", "N/A")

    except requests.exceptions.RequestException as err:
        print(f"  [ERROR]   {url:<32} {err}")
        log_result(url, "ERROR", "ERR", "N/A")


def main():
    targets = load_targets()

    if not targets:
        print(f"[!] No valid URLs found in {TARGETS_FILE}. Exiting.")
        return

    print("====================================================")
    print(f" Monitoring {len(targets)} URLs every {CHECK_INTERVAL_SECONDS} seconds")
    print(f" Logging results to: {LOG_FILE}")
    print(" Press Ctrl + C to stop the monitor")
    print("====================================================\n")

    try:
        while True:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] Checking endpoints:")

            for url in targets:
                check_site(url)

            print(f"\nNext check in {CHECK_INTERVAL_SECONDS}s...\n")
            time.sleep(CHECK_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n[!] Monitor halted by user. Exiting cleanly.")


if __name__ == "__main__":
    main()