"""Render RIVON video #3 frames (Blender 5.x, Cycles CPU).
  blender -b -P render_restaurant.py -- --w 1080 --h 1920 --spp 64 --start 0 --end 719 --out frames
  blender -b -P render_restaurant.py -- --w 540 --h 960 --spp 64 --frames 20,140,260 --out control
The scene is built procedurally on start (about a second), STL connectors in cad/ come from the RIVON STEP files.
Resumable: frames that already exist are skipped. Files are f0000.png ... f0719.png."""
import sys, os, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
import build_restaurant as B

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
ap = argparse.ArgumentParser()
ap.add_argument("--w", type=int, default=1080); ap.add_argument("--h", type=int, default=1920)
ap.add_argument("--spp", type=int, default=64)
ap.add_argument("--start", type=int, default=0); ap.add_argument("--end", type=int, default=B.NFR - 1)
ap.add_argument("--frames", default=""); ap.add_argument("--out", default="frames")
ap.add_argument("--persist", type=int, default=0)
a = ap.parse_args(argv)

B.build(w=a.w, h=a.h, spp=a.spp)
sc = bpy.context.scene
sc.cycles.device = 'CPU'
sc.render.use_persistent_data = bool(a.persist)
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.compression = 12
out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
frames = [int(x) for x in a.frames.split(",")] if a.frames else list(range(a.start, a.end + 1))
t0 = time.time(); done = 0
for k, f in enumerate(frames):
    path = os.path.join(out, "f%04d.png" % f)
    if os.path.exists(path): continue
    sc.frame_set(f); sc.render.filepath = path; ts = time.time()
    bpy.ops.render.render(write_still=True)
    done += 1
    print("FRAME %d  %.0fs" % (f, time.time() - ts), flush=True)
print("DONE", out)
