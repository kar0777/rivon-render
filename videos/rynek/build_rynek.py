"""RIVON video #4 - Stary Rynek w Poznaniu: restaurant swaps its folding parasols for RIVON gazebos (flat roof).
Procedural Blender scene. See NOTES.md. Coordinates: X along the facade row (camera looks +X), Y across (+Y = facades), Z up."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rynek_core import *
import rynek_town as T
import rynek_people as P
import rynek_gazebo as Z
FPS, NFR = 30, 840

def setup_render(w=1080, h=1920, spp=64):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = NFR
    sc.cycles.samples = spp; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.015
    sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 3; sc.cycles.sample_clamp_indirect = 8
    sc.view_settings.view_transform = 'AgX'
    try: sc.view_settings.look = 'Medium High Contrast'
    except Exception: pass
    sc.view_settings.exposure = -0.45

def build_world():
    sc = bpy.context.scene
    w = bpy.data.worlds.new("sky"); sc.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    sky = nt.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_elevation = math.radians(46); sky.sun_rotation = math.radians(235); sky.sun_disc = False
    sky.air_density = 1.0; sky.aerosol_density = 0.6; sky.ozone_density = 2.4
    bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = 0.35
    out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(sky.outputs['Color'], bg.inputs['Color']); nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    sun = bpy.data.lights.new("sun", 'SUN'); sun.energy = 3.0; sun.angle = math.radians(1.2); sun.color = (1.0, 0.92, 0.8)
    so = bpy.data.objects.new("sun", sun); sc.collection.objects.link(so)
    d = Vector((-0.32, -0.42, 0.85)).normalized()
    so.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return so

def build_camera():
    sc = bpy.context.scene
    cam = bpy.data.cameras.new("cam"); cam.lens = 26; cam.clip_start = 0.05; cam.clip_end = 900
    co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
    tgt = bpy.data.objects.new("cam_target", None); sc.collection.objects.link(tgt)
    cam.dof.use_dof = True; cam.dof.focus_object = tgt; cam.dof.aperture_fstop = 3.4
    tc = co.constraints.new('TRACK_TO'); tc.target = tgt; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'
    return co, tgt

def build_town():
    T.build_materials_town()
    box("paving", (600, 600, 0.3), (60, -120, -0.15), M['cobble'], grain=False)
    box("terrace", (80, 4.4, 0.03), (24, 2.75, 0.0), M['slabs'], grain=False)
    # restaurant row, facing -Y (y = 5), x from -40 to 135
    row = [(-40, 8.0, 4, 'cream', 'ogee'), (-32, 6.6, 3, 'salmon', 'tri'), (-25.4, 7.4, 4, 'mint', 'step'), (-18, 7.0, 4, 'ochre', 'flat'),
           (-11, 6.2, 3, 'blue', 'tri'), (-4.8, 8.2, 4, 'rose', 'ogee'),
           (3.4, 7.4, 4, 'yellow', 'tri'), (10.8, 6.4, 4, 'teal', 'ogee'), (17.2, 8.6, 4, 'salmon', 'step'), (25.8, 7.0, 3, 'cream', 'ogee'),
           (32.8, 6.2, 4, 'sage', 'tri'), (39.0, 8.0, 4, 'apricot', 'flat'), (47.0, 6.8, 4, 'blue', 'ogee'), (53.8, 7.4, 3, 'rose', 'tri'),
           (61.2, 7.0, 4, 'mint', 'step'), (68.2, 8.4, 4, 'ochre', 'ogee'), (76.6, 6.6, 4, 'lilac', 'tri'), (83.2, 7.8, 3, 'cream', 'flat'),
           (91.0, 7.0, 4, 'salmon', 'ogee'), (98.0, 8.2, 4, 'yellow', 'tri'), (106.2, 6.8, 4, 'teal', 'step'), (113.0, 7.6, 4, 'terra', 'ogee'),
           (120.6, 7.0, 3, 'grey', 'tri'), (127.6, 8.0, 4, 'white', 'ogee')]
    for i, (x0, w, fl, wl, gb) in enumerate(row):
        gr = 'arcade' if (i % 5 == 2) else 'shop'
        T.kamienica("row%d" % i, (x0, 5.0), 0.0, w, fl, wl, gb, seed=100 + i, ground=gr, lit=(0 <= x0 <= 40), awning=(gr == 'shop' and 0 <= x0 <= 45))
    # far row (y=-62, facing +Y)
    far = [(-30 + i * 7.3, 6.8 + (i % 3) * 0.6, 3 + (i % 2), T.WALLS and list(T.WALLS)[(i * 5) % len(T.WALLS)], ['tri', 'ogee', 'step', 'flat'][i % 4]) for i in range(20)]
    for i, (x0, w, fl, wl, gb) in enumerate(far):
        T.kamienica("far%d" % i, (x0 + w, -62.0), math.pi, w, fl, wl, gb, seed=300 + i, ground='shop')
    T.ratusz((57.0, -8.0), -math.pi / 2)
    # Domki Budnicze: arcaded little houses behind the Ratusz
    x = 78.0
    for i, (w, wl, gb) in enumerate([(5.0, 'salmon', 'ogee'), (4.6, 'mint', 'tri'), (5.2, 'yellow', 'ogee'), (4.8, 'blue', 'step'), (5.0, 'rose', 'ogee')]):
        T.kamienica("budnik%d" % i, (x + w, -22.0), math.pi, w, 2, wl, gb, seed=500 + i, ground='arcade')
        x += w
    T.fountain(36.0, -17.0); T.pillory(50.0, -24.0)
    for x in (10, 24, 38, 52):
        T.lamp_post(x, -5.0)
    for x in (14.7, 20.1, 25.5, 30.9, 36.3):
        T.planter_tree(x, 2.85)

GAZ_X = [12.0, 17.4, 22.8, 28.2, 33.6]
GAZ_Y = 2.85
UMB_T0, UMB_STEP = 84, 12
G0_ASM, G0_DIS = 152, 318
RE_ASM, RE_STEP, RE_SPEED = 420, 13, 0.7

CAM_KEYS = [  # frame, camera location, look-at target, f-stop
    (0,   (2.5, -2.4, 1.6),   (16.0, 3.0, 2.2), 4.0),
    (120, (5.5, -2.2, 1.6),   (15.0, 3.0, 1.9), 4.0),
    (156, (7.6, -0.8, 1.2),   (11.0, 2.0, 0.8), 3.0),
    (186, (9.0, 0.45, 0.62),  (10.45, 1.40, 0.28), 1.8),
    (214, (9.2, 0.60, 1.05),  (10.45, 1.40, 1.30), 1.8),
    (244, (9.0, 0.45, 1.75),  (10.55, 1.45, 2.30), 1.8),
    (272, (8.5, 0.60, 1.95),  (11.30, 1.50, 2.30), 1.8),
    (300, (6.8, -2.6, 2.20),  (12.0, 2.85, 2.40), 3.2),
    (320, (6.6, -3.0, 2.0),   (12.0, 2.85, 2.5), 3.2),
    (360, (8.0, -3.4, 2.4),   (12.5, 2.85, 2.2), 3.2),
    (415, (3.0, -4.0, 2.4),   (14.0, 2.85, 2.2), 3.4),
    (500, (8.0, -4.3, 2.7),   (22.0, 2.85, 2.1), 3.4),
    (600, (14.5, -3.9, 2.1),  (26.0, 2.85, 1.7), 3.4),
    (720, (20.0, -3.7, 1.9),  (30.0, 3.0, 1.7), 3.4),
    (839, (28.0, -3.5, 1.9),  (50.0, -10.0, 4.5), 4.0),
]


def animate_camera(co, tgt):
    for f, loc, t, fs in CAM_KEYS:
        co.location = loc; co.keyframe_insert('location', frame=f)
        tgt.location = t; tgt.keyframe_insert('location', frame=f)
        co.data.dof.aperture_fstop = fs; co.data.dof.keyframe_insert('aperture_fstop', frame=f)


def build_restaurant():
    P.build_materials_people(); Z.build_materials_gaz()
    rr = random.Random(5)
    for g, cx in enumerate(GAZ_X):
        ppl, troot = P.table_group(g, cx, GAZ_Y, guests=(g != 0))
        P.animate_guests(ppl, 0, NFR, rr)
        fabric = M['canopy_a'] if g % 2 == 0 else M['canopy_b']
        ob, parts, clo = Z.parasol(cx, GAZ_Y, fabric)
        Z.animate_parasol(ob, parts, clo, UMB_T0 + g * UMB_STEP)
        if g == 0: Z.gazebo(g, cx, GAZ_Y, [(G0_ASM, 1.0), (RE_ASM, RE_SPEED)], dismantle=G0_DIS)
        else: Z.gazebo(g, cx, GAZ_Y, [(RE_ASM + g * RE_STEP, RE_SPEED)])
    # pigeons on the cobbles
    for i in range(9):
        T.pigeon(rr.uniform(4, 40), rr.uniform(-3.5, -0.2), rr.uniform(0, 6.28), rr)


def build(w=1080, h=1920, spp=64, full=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    setup_render(w, h, spp); build_world(); build_town()
    co, tgt = build_camera()
    if full:
        build_restaurant(); animate_camera(co, tgt); finalize_anim()
    return co, tgt
