"""Merge sub-agent reports (_agent/*.json) into code.json and recompute coverage."""
import json, glob, os, re
files = {}
corr = []
for p in sorted(glob.glob(os.path.join(os.path.dirname(__file__) or ".", "_agent", "*.json"))):
    r = json.load(open(p))
    if not isinstance(r, dict):
        continue
    for f in r.get("files", []):
        if f.get("status") in ("done", "ok", "complete", "completed", "created", "modified"):
            f["status"] = "written"
        p = f["path"]
        if p.startswith("config/") or p.startswith("care/nhcx/"):
            p = "care/" + p
        f["path"] = p
        files[p] = {**files.get(p, {}), **f}
    corr += r.get("corrections", [])
cov = {k: set() for k in "SACFDG"}
key = {"screens": "S", "apis": "A", "callbacks": "C", "fhir": "F", "database": "D", "gateway": "G"}
for f in files.values():
    if f.get("status") != "written":
        continue
    for k, ids in (f.get("implements") or {}).items():
        for i in ids:
            m = re.match(r"([SACFDG])(\d+)", i)
            if m and k in key:
                cov[m.group(1)].add(m.group(1) + m.group(2))
num = lambda s: int(re.sub(r"\D", "", s) or 0)
out = {"files": list(files.values()), "coverage": {k: sorted(v, key=num) for k, v in cov.items()}, "corrections": corr}
json.dump(out, open("code.json", "w"), indent=1)
print(len(files), {k: len(v) for k, v in out["coverage"].items()})
