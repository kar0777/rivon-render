"""Download CC0 Poly Haven HDRIs on a runner with open internet. argv: job.json out_dir"""
import json, sys, urllib.request, pathlib
job = json.load(open(sys.argv[1])); out = pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
H = {"User-Agent": "rivon-render/1.0 (github.com/kar0777/rivon-render)"}
res = job.get("hdri_res", "4k")
for k in job.get("hdris", []):
    info = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://api.polyhaven.com/files/{k}", headers=H), timeout=60).read())
    u = info["hdri"][res]["hdr"]["url"]
    print(k, u, flush=True)
    data = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=600).read()
    (out / f"{k}_{res}.hdr").write_bytes(data); print("  bytes", len(data), flush=True)
