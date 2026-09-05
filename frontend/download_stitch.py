import json
import urllib.request
import os

with open(r"C:\Users\somag\.gemini\antigravity\brain\7749246c-378a-4fe5-9a82-a0b636de6508\.system_generated\steps\538\output.txt", "r") as f:
    data = json.load(f)

os.makedirs("stitch_screens", exist_ok=True)

for screen in data.get("screens", []):
    title = screen.get("title", "unknown").replace(" ", "_").replace("/", "_")
    html_info = screen.get("htmlCode", {})
    url = html_info.get("downloadUrl")
    if url:
        print(f"Downloading {title}...")
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as response:
                html = response.read().decode()
                with open(f"stitch_screens/{title}.html", "w", encoding="utf-8") as out:
                    out.write(html)
        except Exception as e:
            print(f"Failed to download {title}: {e}")
