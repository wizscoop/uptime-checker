import concurrent.futures
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
MAX_WORKERS = 10  # Number of parallel threads

# ANSI Terminal Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# In-memory state tracking to detect state changes between runs
previous_states: dict[str, str] = {}


def load_targets(file_path: str = TARGETS_FILE) -> list[str]:
    """Reads target URLs from a file, creating defaults if missing."""
    if not os.path.exists(file_path):
        sample_targets = [
            "https://github.com",
            "https://google.com",
            "https://httpstat.us/500",  # Simulates an internal server error
            "https://httpstat.us/404",  # Simulates a missing resource
            "https://nonexistent-domain-test123.org",  # Simulates DNS failure
        ]
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(sample_targets) + "\n")
        print(f"{CYAN}[i] Created default '{file_path}' with sample URLs.{RESET}\n")
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
    """Appends response metrics into a CSV log file."""
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


def check_site(url: str) -> dict:
    """Pings a single URL and returns structured metrics."""
    try:
        start_time = time.perf_counter()
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
        latency_ms = round((time.perf_counter() - start_time) * 1000)

        status = "UP" if response.status_code == 200 else "WARN"
        return {
            "url": url,
            "status": status,
            "code": response.status_code,
            "latency": latency_ms,
            "detail": f"{response.status_code} ({latency_ms}ms)",
        }

    except requests.exceptions.Timeout:
        return {
            "url": url,
            "status": "TIMEOUT",
            "code": "TIMEOUT",
            "latency": "N/A",
            "detail": f"Timed out after {TIMEOUT_SECONDS}s",
        }

    except requests.exceptions.ConnectionError:
        return {
            "url": url,
            "status": "DOWN",
            "code": "DOWN",
            "latency": "N/A",
            "detail": "Unreachable / DNS error",
        }

    except requests.exceptions.RequestException as err:
        return {
            "url": url,
            "status": "ERROR",
            "code": "ERR",
            "latency": "N/A",
            "detail": str(err),
        }


def process_result(result: dict):
    """Prints colorized output, checks for state changes, and writes to log."""
    url = result["url"]
    status = result["status"]
    last_status = previous_states.get(url)

    # 1. State-transition detection
    if last_status is not None and last_status != status:
        if status in ("DOWN", "TIMEOUT", "WARN") and last_status == "UP":
            print(
                f"  {RED}{BOLD}>>> STATE ALERT: {url} transitioned from {last_status} to {status}! <<<{RESET}"
            )
        elif status == "UP" and last_status in ("DOWN", "TIMEOUT", "WARN"):
            print(
                f"  {GREEN}{BOLD}>>> RECOVERY: {url} is back UP (was {last_status})! <<<{RESET}"
            )

    previous_states[url] = status

    # 2. Color formatting
    if status == "UP":
        tag = f"{GREEN}[UP]{RESET}"
    elif status == "WARN":
        tag = f"{YELLOW}[WARN]{RESET}"
    else:
        tag = f"{RED}[{status}]{RESET}"

    # 3. Print aligned line output
    print(f"  {tag:<18} {url:<45} {result['detail']}")

    # 4. Save to CSV
    log_result(url, status, result["code"], result["latency"])


def run_batch_checks(targets: list[str]):
    """Executes checks across all URLs concurrently."""
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:
        # executor.map runs checks in parallel and yields them in original order
        results = executor.map(check_site, targets)
        for res in results:
            process_result(res)


def main():
    targets = load_targets()
    if not targets:
        print(f"{RED}[!] No targets found in {TARGETS_FILE}. Exiting.{RESET}")
        return

    print(f"{BOLD}===================================================={RESET}")
    print(
        f"{CYAN} Parallel Uptime Monitor: Tracking {len(targets)} endpoints{RESET}"
    )
    print(f" Checks running concurrently every {CHECK_INTERVAL_SECONDS} seconds")
    print(f" Saving logs to: {LOG_FILE}")
    print(f" Press {YELLOW}Ctrl + C{RESET} to exit cleanly")
    print(f"{BOLD}===================================================={RESET}\n")

    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{BOLD}[{timestamp}] Scanning targets...{RESET}")

            run_batch_checks(targets)

            print(f"\nNext check in {CHECK_INTERVAL_SECONDS}s...\n")
            time.sleep(CHECK_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}[!] Monitor stopped by user. Goodbye!{RESET}")


if __name__ == "__main__":
    main()