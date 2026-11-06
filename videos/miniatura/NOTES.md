# RIVON video #5 - "Miniatura" (22 s, 9:16, 30 fps, 660 frames)

Hook: a carport pergola model stands on a carpenter's work table (tilt-shift look). The camera dives into the model,
pushes into the logo face of a Trojak 3D and - hidden cut - pulls back from the same connector at full size on a real Polish plot.
Low hero orbit around the carport with the owner's Dodge RAM under a clear polycarbonate roof, then the camera pushes into the
opposite Trojak and the second hidden cut returns to the workshop (loop). End card: RIVON wordmark + "Zamów łączniki RIVON".

## How the illusion works
- `CORE` collection (plot coordinates, pergola at the origin) = exact-STEP pergola from `../rivon_film/layout.json`, roof, RAM, drive, lawn, thujas.
  It is rendered at full size (real plot) and as a 1:25 collection instance `MODEL` on the work table in `SHOP` (x = 320 m).
- `FAR` (house, neighbours, street, trees) is visible only for the real plot.
- One camera spline in plot coordinates (`mini_anim.py`); desk frames are mapped through the model transform, so both sides of each
  cut show identical geometry. The aperture is scaled by the model factor at the cut (equivalent depth of field), then it closes.
- One sun lamp for both places (window of the workshop faces the sun), so the connector is lit the same way on both sides of a cut.
- Motion blur: camera keyed at f and f+0.5 in the place of frame f, shutter START -> blur never straddles a cut.

## Files
`build_mini.py` scene · `mini_anim.py` timeline + subtitles · `render_mini.py` renderer (resumable) · `post/finish_mini.py` grade/text/MP4.
Local: `pip install bpy==5.2.3` then `python3 render_mini.py -- --frames 0,150 --w 540 --h 960 --spp 48 --out out`.
CI: `.github/workflows/render-mini.yml`, push branch `mini/<name>` with run.json.

## Rules (owner)
Free assets only. Connector geometry/logo final (exact STEP meshes only). New environment per video. No full final render before the owner
writes exactly «Утверждаю, запускай финальный рендер» after reviewing >= 5 control frames.
