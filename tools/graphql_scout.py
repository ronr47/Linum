import subprocess
import json

gql_query = """
{
  search(query: "bounty in:title,body language:rust state:open sort:updated-desc", type: ISSUE, first: 10) {
    nodes {
      ... on Issue {
        number
        title
        url
        repository {
          nameWithOwner
        }
        updatedAt
      }
    }
  }
}
"""

res = subprocess.run(["gh", "api", "graphql", "-f", f"query={gql_query}"], capture_output=True, text=True)

if res.returncode != 0:
    print(f"Error querying GitHub API: {res.stderr}")
else:
    data = json.loads(res.stdout)
    nodes = data.get("data", {}).get("search", {}).get("nodes", [])
    print("\n" + "=" * 65)
    print(f"⚡ RECENT ACTIVE RUST BOUNTY ISSUES ({len(nodes)} found)")
    print("=" * 65)
    for n in nodes:
        repo = n.get("repository", {}).get("nameWithOwner", "Unknown")
        num = n.get("number", "")
        title = n.get("title", "")
        url = n.get("url", "")
        print(f"📦 {repo} #{num}")
        print(f"   📌 {title}")
        print(f"   🔗 {url}\n")
