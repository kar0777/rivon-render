# RIVON video #3 — „Restauracja w starym mieście” (gazebos replace parasols)

Concept: old-town Polish street, restaurant terrace with five open parasols. Parasols fold and sink into the paving,
RIVON gazebos assemble over the tables (Stopa → post → Trojak → beams → hip roof), lights come on, guests enjoy it.
24 s, 30 fps, 720 frames (0…719), vertical 1080×1920. No text, no brand names, no close-up faces.

## Files
- `build_restaurant.py` — procedural Blender scene + all animation (frames, camera, DOF). One place to change timing: `UMB_*`, `ASM_*`, `CAM_KEYS`.
- `render_restaurant.py` — renders frames `f0000.png…` (resumable). Used locally and by `.github/workflows/render-restaurant.yml`.
- `cad/*.stl` — exact tessellation (0.05 mm) of the three RIVON STEP files (mm). Imported 1:1, scaled ×0.001, never edited. `tools/step_to_stl.py` regenerates them.
- `tools/fit_check.py` — BVH check that no timber (posts, beams) intersects the RIVON meshes in the finished gazebo (run with `bpy`).
- Textures: reused from `../dzialka/textures` (Poly Haven, CC0).

## Timeline
0–118 parasols open, guests seated · 118–290 parasols fold one by one and sink · 214+ gazebo g starts (stagger 26 f):
Stopa +0, post +14, Trojak +44, beams +74, rafters +102, roof +124, lights +154 · 400–720 reveal, camera moves along the street.

## Geometry used (from the STEP files)
- Stopa / Trojak: square tube 100×100 mm, wall 2 mm, inner 96×96 mm → timber 90×90 mm.
- Trojak is used turned upside down: the vertical socket (floor 98 mm below its top in CAD) sits on the post top, arms point to +X/+Y and are rotated 90° per corner; beams engage 150 mm... see `gazebo()`.
- Checked: timber vs metal has 0 intersections with 0.5 mm clearance (only face contact at post top / plate).

## Rules (from the owner)
Free assets only. Never start the full final render before the owner writes exactly «Утверждаю, запускай финальный рендер» after reviewing ≥5 control frames.
