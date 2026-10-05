import time
import requests

TARGET_URL = "https://github.com"
TIMEOUT_SECONDS = 5


def check_status(url: str):
    print(f"Checking {url}...")
    try:
        start_time = time.perf_counter()
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
        latency_ms = round((time.perf_counter() - start_time) * 1000)

        if response.status_code == 200:
            print(f"[UP] {url} responded with status 200 in {latency_ms}ms")
        else:
            print(
                f"[WARN] {url} returned status {response.status_code} in {latency_ms}ms"
            )

    except requests.exceptions.Timeout:
        print(f"[TIMEOUT] {url} took longer than {TIMEOUT_SECONDS}s to respond")
    except requests.exceptions.ConnectionError:
        print(f"[DOWN] Could not reach {url} (DNS failure or server offline)")
    except requests.exceptions.RequestException as err:
        print(f"[ERROR] An unexpected error occurred: {err}")


if __name__ == "__main__":
    check_status(TARGET_URL)