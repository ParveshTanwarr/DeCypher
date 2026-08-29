import requests

TOR_PROXY = "socks5h://127.0.0.1:9050"

proxies = {
    "http": TOR_PROXY,
    "https": TOR_PROXY,
}

url = "https://check.torproject.org/"

try:
    response = requests.get(
        url,
        proxies=proxies,
        timeout=30
    )

    print("Status:", response.status_code)
    print(
        "Connected through Tor:",
        "Congratulations" in response.text
    )

except Exception as e:
    print("Tor connection failed:")
    print(e)