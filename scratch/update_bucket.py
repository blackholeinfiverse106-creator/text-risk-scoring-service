import os

files_to_update = [
    r"test_live_bucket_storage.py",
    r"run_backend.py",
    r"RUNTIME_CONVERGENCE_AUDIT.md",
    r"REVIEW_PACKET.md",
    r"LIVE_ECOSYSTEM_PROOF.md",
    r"demo_pipeline.py",
    r"docs\ECOSYSTEM_ALIGNMENT_AUDIT.md",
    r"docs\end_to_end_pipeline.md",
    r"demo_output_v2.txt",
    r"app\layer5_bucket.py"
]

old_url = "https://bhiv-bucket-i1l6.onrender.com"
new_url = "http://163.128.209.18:8012"
old_domain = "bhiv-bucket-i1l6.onrender.com"
new_domain = "163.128.209.18:8012"

for filepath in files_to_update:
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        updated_content = content.replace(old_url, new_url).replace(old_domain, new_domain)
        
        if content != updated_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(updated_content)
            print(f"Updated {filepath}")
