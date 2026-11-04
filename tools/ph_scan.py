"""Poly Haven (CC0) catalogue scan: lists HDRIs/models and downloads small thumbnails of the relevant ones.
Runs on GitHub Actions (open internet). Output dir argv[1]."""
import json, sys, urllib.request, pathlib
out = pathlib.Path(sys.argv[1]); (out / "thumbs").mkdir(parents=True, exist_ok=True)
H = {"User-Agent": "rivon-render/1.0 (github.com/kar0777/rivon-render)"}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=60).read()
hd = json.loads(get("https://api.polyhaven.com/assets?t=hdris"))
md = json.loads(get("https://api.polyhaven.com/assets?t=models"))
json.dump({"hdris": hd, "models": md}, open(out / "catalogue.json", "w"))
keys_h = ("urban", "suburban", "street", "garden", "house", "village", "park", "field", "yard", "backyard", "cafe", "town", "plaza", "courtyard", "terrace", "patio")
keys_m = ("house", "building", "shed", "barn", "cabin", "garage", "cottage", "gazebo", "fence", "carport", "pergola", "bbq", "grill", "sofa", "chair", "table", "kitchen")
sel = []
for k, v in hd.items():
    t = " ".join(v.get("tags", []) + v.get("categories", []) + [k, v.get("name", "")]).lower()
    if "outdoor" in v.get("categories", []) and any(x in t for x in keys_h): sel.append(("hdri", k))
for k, v in md.items():
    t = " ".join(v.get("tags", []) + v.get("categories", []) + [k, v.get("name", "")]).lower()
    if any(x in t for x in keys_m): sel.append(("model", k))
print("selected", len(sel))
for kind, k in sel:
    try:
        (out / "thumbs" / f"{kind}_{k}.png").write_bytes(get(f"https://cdn.polyhaven.com/asset_img/thumbs/{k}.png?width=256&height=144" if kind == "hdri" else f"https://cdn.polyhaven.com/asset_img/thumbs/{k}.png?width=256&height=256"))
    except Exception as e:
        print("thumb fail", k, e)
json.dump(sel, open(out / "selected.json", "w"))
