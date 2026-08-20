import json

with open("pitch_payload.json", "r") as f:
    p = json.load(f)

print("\n" + "=" * 65)
print("📧 COPY & PASTE TO: community@digitalocean.com")
print(f"📌 SUBJECT: Pitch: {p['title']}")
print("=" * 65 + "\n")

print(f"""Hi DigitalOcean Editorial Team,

I would like to submit a technical proposal for the Write for DOnations program.

Title: {p['title']}

Summary:
{p['summary']}

Proposed Outline:
""" + "\n".join(p['outline']) + f"""

Technical Reference & Code:
- Repository: {p['portfolio']}
- Author GitHub: https://github.com/ronr47

Best regards,
{p['author']}
{p['email']}
""")
print("=" * 65)
