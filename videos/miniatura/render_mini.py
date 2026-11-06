"""Frame renderer for RIVON "Miniatura".  python3 render_mini.py -- --frames 0,120,254 --w 540 --h 960 --spp 64 --out DIR [--blur]
(or blender -b -P render_mini.py -- ...).  Writes f####.png, skips frames that already exist (resumable)."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(k, d=None):
    return a[a.index(k) + 1] if k in a else d
import build_mini as B
W, H, SPP = int(arg("--w", 540)), int(arg("--h", 960)), int(arg("--spp", 32))
out = Path(arg("--out", "out")); out.mkdir(parents=True, exist_ok=True)
frames = [int(x) for x in arg("--frames", "0").split(",")] if "--frames" in a else list(range(int(arg("--start", 0)), int(arg("--end", 0)) + 1))
sc = B.prepare(W, H, SPP)
for f in frames:
    p = out / f"f{f:04d}.png"
    if p.exists(): print("FRAME", f, "exists"); continue
    t = time.time()
    B.apply_frame(f, motion_blur="--blur" in a)
    sc.render.filepath = str(p); bpy.ops.render.render(write_still=True)
    print("FRAME", f, "ok", round(time.time() - t, 1), "s", flush=True)
