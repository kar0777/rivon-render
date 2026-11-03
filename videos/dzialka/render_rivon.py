"""RIVON film renderer. Run with Blender (free, 5.x):
  blender -b RIVON_film2_scene.blend -P render_rivon.py -- --preset test
  blender -b RIVON_film2_scene.blend -P render_rivon.py -- --preset final --out frames
Presets:  test  = 3 frames, full quality (to measure time/memory)
          approved = 900x1600, 24 spp, same as the approved control frames (fast; post/finish.py scales to 1080x1920)
          draft = 720x1280, 48 spp (fast preview of the whole film)
          light = 1080x1920, 128 spp, lighter textures/grass (for 16 GB machines)
          lite  = 1080x1920, 96 spp, minimum memory (for 8 GB machines)
          final = 1080x1920, 256 spp, full textures (needs >=16 GB RAM or a 12+ GB GPU)
The render is resumable: frames that already exist are skipped, so you can stop (Ctrl+C) and start again.
Frames are written as f0000.png ... f1679.png; then run post/finish.py."""
import bpy, sys, os, time, argparse
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--preset", default="test", choices=["test", "approved", "draft", "light", "lite", "final"])
ap.add_argument("--out", default="frames"); ap.add_argument("--start", type=int, default=0); ap.add_argument("--end", type=int, default=1679)
ap.add_argument("--step", type=int, default=1); ap.add_argument("--frames", default=""); ap.add_argument("--blend", default="")
ap.add_argument("--seed", type=int, default=-1); ap.add_argument("--spp", type=int, default=0); ap.add_argument("--w", type=int, default=0); ap.add_argument("--h", type=int, default=0); ap.add_argument("--persist", type=int, default=0); ap.add_argument("--device", default="auto")
a = ap.parse_args(argv)
if a.blend: bpy.ops.wm.open_mainfile(filepath=a.blend)
sc = bpy.context.scene
P = {"test": dict(spp=64, scale=1.0, tex=1024, grass=0.6), "approved": dict(spp=24, scale=900 / 1080, tex=1024, grass=0.6), "draft": dict(spp=48, scale=2 / 3, tex=1024, grass=0.5),
     "light": dict(spp=128, scale=1.0, tex=1024, grass=0.6), "lite": dict(spp=96, scale=1.0, tex=512, grass=0.3), "final": dict(spp=256, scale=1.0, tex=2048, grass=1.0)}[a.preset]
if a.spp: P["spp"] = a.spp

# ---- device: Metal (Apple), OptiX/CUDA (NVIDIA), HIP (AMD), oneAPI (Intel), else CPU -------------------------
sc.render.engine = 'CYCLES'; dev = "CPU"
try:
    cp = bpy.context.preferences.addons['cycles'].preferences
    for t in ([a.device] if a.device not in ("auto", "cpu") else ["METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"]):
        try: cp.compute_device_type = t; cp.get_devices()
        except Exception: continue
        gpus = [d for d in cp.devices if d.type != 'CPU']
        if gpus:
            for d in cp.devices: d.use = d.type != 'CPU' or t == 'METAL'
            dev = t; sc.cycles.device = 'GPU'; break
    if dev == "CPU": sc.cycles.device = 'CPU'
except Exception as e: print("device setup:", e)
print("RENDER DEVICE:", dev)

# ---- quality ------------------------------------------------------------------------------------------------
if a.seed >= 0: sc.cycles.seed = a.seed; sc.cycles.use_animated_seed = False   # fixed noise pattern in every frame -> no flicker between frames
sc.cycles.samples = P["spp"]; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.012
sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'; sc.cycles.denoising_quality = 'HIGH' if a.preset == "final" else 'BALANCED'
sc.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'; sc.cycles.denoising_prefilter = 'ACCURATE'
if hasattr(sc.cycles, "denoising_use_gpu"): sc.cycles.denoising_use_gpu = dev != "CPU"
sc.render.resolution_x = int(round(1080 * P["scale"] / 2) * 2); sc.render.resolution_y = int(round(1920 * P["scale"] / 2) * 2); sc.render.resolution_percentage = 100
sc.render.use_persistent_data = bool(a.persist)
if a.w: sc.render.resolution_x = a.w; sc.render.resolution_y = a.h
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.compression = 12

# ---- memory savers (8 GB machines): shrink big textures in memory only, thin out grass ----------------------
KEEP_FULL = ("olive_veneer", "teak_veneer", "asphalt_track", "wood_model", "beige_wall")   # hero materials stay sharp
for im in bpy.data.images:
    if im.source != 'FILE': continue
    w, h = im.size; cap = P["tex"] if not any(k in im.name for k in KEEP_FULL) else 2048
    if max(w, h) > cap: im.scale(max(1, w * cap // max(w, h)), max(1, h * cap // max(w, h)))
if P["grass"] < 1:
    for ob in bpy.data.objects:
        for ps in ob.particle_systems: ps.settings.count = max(100, int(ps.settings.count * P["grass"]))

# ---- render loop ---------------------------------------------------------------------------------------------
out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
frames = [1199, 225, 420] if a.preset == "test" else list(range(a.start, a.end + 1, a.step))
if a.preset == "test": frames = [30, 225, 420]
if a.frames: frames = [int(x) for x in a.frames.split(",")]
t0 = time.time(); done = 0
for k, f in enumerate(frames):
    path = os.path.join(out, "f%04d.png" % f)
    if os.path.exists(path): continue
    sc.frame_set(f + 1); sc.render.filepath = path; ts = time.time()
    bpy.ops.render.render(write_still=True)
    done += 1; el = time.time() - t0; left = (len(frames) - k - 1) * el / done
    print("FRAME %d  %.0fs   ETA %.1f h" % (f, time.time() - ts, left / 3600), flush=True)
print("DONE", out)
