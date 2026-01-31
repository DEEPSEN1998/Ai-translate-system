import urllib.request
import json
import time

URL = "http://127.0.0.1:8000/translate"
DATA = {
    "texts": ["About Satin Rose Salon & Spa"],
    "target_lang": "hi"
}

def post_request(url, data):
    start = time.perf_counter()
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'))
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req) as response:
            resp_body = json.loads(response.read().decode('utf-8'))
            end = time.perf_counter()
            rtt = (end - start) * 1000
            return resp_body, rtt
    except Exception as e:
        return None, 0

def benchmark():
    print("Starting Detailed Benchmark...")
    
    # Request 1
    resp, rtt = post_request(URL, DATA)
    if resp:
        print(f"Request 1:")
        print(f"  Total Round Trip: {rtt:.2f}ms")
        print(f"  Server Internal: {resp.get('proc_time_ms', 'N/A')}ms")
        print(f"  Network/IO Overhead: {rtt - resp.get('proc_time_ms', 0):.2f}ms")
    
    # Request 2 (Cached)
    resp, rtt = post_request(URL, DATA)
    if resp:
        print(f"\nRequest 2 (CACHED):")
        print(f"  Total Round Trip: {rtt:.2f}ms")
        print(f"  Server Internal: {resp.get('proc_time_ms', 'N/A')}ms")
        print(f"  Network/IO Overhead: {rtt - resp.get('proc_time_ms', 0):.2f}ms")
        
        server_time = resp.get('proc_time_ms', 999)
        if server_time < 3:
            print("\nSUCCESS: Server logic is extremely fast (< 3ms)!")
        elif server_time < 10:
            print("\nOK: Server logic is fast (< 10ms).")
        else:
            print("\nINFO: Server logic is taking longer than expected. Check if 'cache.json' is being written repeatedly.")

if __name__ == "__main__":
    benchmark()
