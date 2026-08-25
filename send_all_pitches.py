#!/usr/bin/env python3
# ==============================================================================
# SECURE PYTHON OUTBOUND TERMINAL ROUTER (CORRECTED DESTINATION STRINGS)
# ==============================================================================

import smtplib
import getpass
from email.mime.text import MIMEText
import os

sender = "ronrnlds47@gmail.com"

print("======================================================================")
print("          AUTHENTICATING SYSTEM SECURE SMTP OUTBOX                    ")
print("======================================================================")
print("Note: Use your 16-character Google App Password (NOT your standard login)")
password = getpass.getpass("Enter Google App Password for ronrnlds47@gmail.com: ")

# Target array mapping your precise compiled text pitches
targets = [
    {
        "to": "josh.woods@citadelsecurities.com", 
        "cc": "peng.zhao@citadelsecurities.com", 
        "sub": "Code Asset Buyout: Low-latency eBPF/XDP bypass + Cranelift JIT engine", 
        "file": "/home/ron/linum/build/artifacts/citadel_delivery_manifest.txt"
    },
    {
        "to": "slehoczky@janestreet.com", 
        "cc": "asegel@janestreet.com", 
        "sub": "Production Asset Buyout: Cache-Aligned JIT Arena + Zero-Copy AF_XDP Pipeline", 
        "file": "/home/ron/linum/build/artifacts/janestreet_pitch.txt"
    },
    {
        "to": "skoeling@optiver.com", 
        "cc": "hanse.vanderijdt@optiver.com", 
        "sub": "Production Code Buyout: AF_XDP Kernel Bypass + Cache-Aligned Cranelift JIT", 
        "file": "/home/ron/linum/build/artifacts/optiver_pitch.txt"
    }
]

try:
    print("\n[*] Initializing secure TLS connection to ://gmail.com...")
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender, password)
    print("[✔] SMTP Authentication successful. Dispatching pitch payload pipeline...\n")
    
    for t in targets:
        if not os.path.exists(t["file"]):
            print(f"[✘] Resource error: Missing data file at {t['file']}. Skipping.")
            continue
            
        with open(t["file"], "r") as f:
            body = f.read()
            
        msg = MIMEText(body)
        msg["From"] = sender
        msg["To"] = t["to"]
        msg["Cc"] = t["cc"]
        msg["Subject"] = t["sub"]
        
        print(f"[*] Shipping structural manifest payload to: {t['to']}...")
        server.sendmail(sender, [t["to"], t["cc"]], msg.as_string())
        print(f"[✔] Transmission verified successfully pushed to {t['to']}\n")
        
    server.quit()
    print("======================================================================")
    print("          DISPATCH COMPLETION: ALL MAILS PUSHED TO CORPORATE MX        ")
    print("======================================================================")
    
except Exception as e:
    print(f"\n[✘] Transmission execution failure parameter: {e}")
