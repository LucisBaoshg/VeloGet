import urllib.request
import ssl
import shutil
from pathlib import Path

# Setup context
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://github.com/yt-dlp/yt-dlp/archive/refs/heads/master.zip"
dest_path = Path("debug_update.zip")

print(f"Downloading from: {url}")

try:
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    with urllib.request.urlopen(req, context=ctx) as response:
        print(f"Response Code: {response.getcode()}")
        print(f"URL (Final): {response.geturl()}")
        print("--- Headers ---")
        for k, v in response.info().items():
            print(f"{k}: {v}")
        print("--- End Headers ---")
        
        # Read first 500 bytes to check content
        partial = response.read(500)
        print("--- First 500 Bytes ---")
        try:
            print(partial.decode('utf-8'))
        except:
            print(f"<Binary Data: {len(partial)} bytes>")
            print(partial)
        print("--- End Content ---")
        
        # Don't save full file for now
        
except Exception as e:
    print(f"Error: {e}")
