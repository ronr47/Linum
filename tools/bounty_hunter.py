import json
import subprocess

# Strict search queries targeting real reward platforms & verified stars
queries = [
    'bounty in:title,body language:rust stars:>50 is:open sort:updated-desc',
    'algora in:body language:rust is:open sort:updated-desc',
    'polar in:body language:python stars:>100 is:open sort:updated-desc'
]

seen = set()
print("\n" + "=" * 65 + "\n⚡ VERIFIED ACTIVE REWARD ISSUES\n" + "=" * 65)

for q in queries:
    cmd = ["gh", "api", "graphql", "-f", f"""query={{
      search(query: "{q}", type: ISSUE, first: 10) {{
        nodes {{
          ... on Issue {{
            number
            title
            url
            repository {{
              nameWithOwner
              stargazerCount
            }}
          }}
        }}
      }}
    }}"""]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        data = json.loads(res.stdout).get("data", {}).get("search", {}).get("nodes", [])
        for issue in data:
            url = issue.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            repo = issue["repository"]["nameWithOwner"]
            stars = issue["repository"]["stargazerCount"]
            print(f"📦 [{stars}⭐] {repo} #{issue['number']}")
            print(f"   📌 {issue['title']}")
            print(f"   🔗 {url}\n")
