import urllib.request
import json

queries = [
    ("Rust Bounties", "label:bounty+state:open+language:rust"),
    ("Python / Systems Bounties", "label:bounty+state:open+language:python")
]

headers = {"User-Agent": "LinumBountyScout/1.0"}

for label, q in queries:
    url = f"https://api.github.com/search/issues?q={q}&sort=created&order=desc"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("items", [])[:5]
            print(f"\n⚡ {label.upper()} ({len(items)} found)\n" + "=" * 65)
            for item in items:
                num = item.get("number")
                title = item.get("title")
                link = item.get("html_url")
                created = item.get("created_at", "")[:10]
                print(f"📌 #{num}: {title}")
                print(f"   🔗 {link}")
                print(f"   📅 Posted: {created}\n")
    except Exception as e:
        print(f"Error querying {label}: {e}")
