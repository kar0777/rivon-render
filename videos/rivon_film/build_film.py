"""Scene assembly for the RIVON film: Polish plot (assets.blend) + exact-STEP pergola + per-application props.
Open assets.blend, call prepare() once, then apply_env(name) / set_shot(shot) before every frame."""
import math, sys
from pathlib import Path
import numpy as np
import bpy, mathutils
sys.path.insert(0, str(Path(__file__).resolve().parent))
from film_lib import *      # noqa
import film_envs as E

# ---- environment placement: PLOT (the whole Polish plot) is rotated/moved, the pergola stays at the world origin
def _plot(F, W, rot_deg=0.0):
    r = math.radians(rot_deg); R = np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])
    loc = np.array(W) - R @ np.array(F)
    return (loc[0], loc[1], 0.0), r

ENVS = {
    "lab":        dict(kind="lab"),
    "carport":    dict(kind="plot", plot=_plot((6.6, 12.25), (0.0, 0.0)), car=True, pad=False),
    "barbecue":   dict(kind="plot", plot=_plot((-3.35, 2.35), (0.0, 0.0)), car=False, pad=True),
    "kitchen":    dict(kind="plot", plot=_plot((-0.25, 12.1), (0.0, 3.8)), car=False, pad=True),
    "lounge":     dict(kind="plot", plot=_plot((-3.35, 2.35), (0.0, 0.0), 90), car=False, pad=True),
    "commercial": dict(kind="plot", plot=_plot((-0.25, 12.1), (3.8, 0.0), -90), car=False, pad=True),
}

# ---- camera shots (low, wide, close: the pergola must read as big, heavy and strong)
SHOTS = {
    "S0_lab":        dict(env="lab",        loc=(6.6, -7.9, 1.0), tgt=(0.0, 0.0, 1.5), lens=28),
    "S1_carport":    dict(env="carport",    loc=(7.6, -7.8, 1.05), tgt=(0.0, 0.0, 1.5), lens=27),
    "S2_barbecue":   dict(env="barbecue",   loc=(-6.4, -7.0, 1.05), tgt=(0.0, 0.0, 1.5), lens=27),
    "S3_kitchen":    dict(env="kitchen",    loc=(6.3, -6.3, 1.1), tgt=(0.0, 0.3, 1.5), lens=27),
    "S4_lounge":     dict(env="lounge",     loc=(6.2, 6.0, 1.15), tgt=(0.0, 0.0, 1.5), lens=27),
    "S5_commercial": dict(env="commercial", loc=(-7.0, -5.6, 1.1), tgt=(0.0, 0.0, 1.5), lens=27),
}
SHOT_ORDER = list(SHOTS)

_state = {"env": None}


def prepare(w, h, spp):
    sc = bpy.context.scene
    # relink textures / HDRI to the repo copy
    for img in bpy.data.images:
        if img.filepath:
            fn = Path(bpy.path.abspath(img.filepath.replace("\\", "/"))).name
            if (TEX / fn).exists(): img.filepath = str(TEX / fn)
    # whole plot -> PLOT_COLL, parented to one empty (so it can be moved/rotated as a unit)
    plot_coll = collection("PLOT_COLL")
    plot = bpy.data.objects.new("PLOT", None); plot_coll.objects.link(plot)
    for o in list(bpy.data.objects):
        if o is plot or o.parent is not None: continue
        if o.type in ("CAMERA", "LIGHT"): bpy.data.objects.remove(o, do_unlink=True); continue
        o.parent = plot; link(o, plot_coll)
    for o in bpy.data.objects:
        if o.parent is not None and o is not plot and o.name not in plot_coll.objects: link(o, plot_coll)
    # natural lawn: the stock colour was neon green; desaturate/darken the base shader of the plot lawn
    lm = bpy.data.materials.get("lawn")
    if lm and lm.use_nodes:
        for n in lm.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                bc = n.inputs["Base Color"]
                if not bc.is_linked: bc.default_value = (0.085, 0.13, 0.04, 1)
                else:
                    hs = lm.node_tree.nodes.new("ShaderNodeHueSaturation"); hs.inputs["Saturation"].default_value = 0.88; hs.inputs["Value"].default_value = 0.8
                    src = bc.links[0].from_socket; lm.node_tree.links.new(src, hs.inputs["Color"]); lm.node_tree.links.new(hs.outputs[0], bc)
    build_pergola("PERGOLA")
    lab = collection("LAB"); E.build_lab(lab)
    collection("ENV_PROPS"); collection("ENV_PAD")
    # sun (outdoor key light)
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 4.2; sun.angle = math.radians(0.8); sun.color = (1.0, 0.86, 0.70)
    so = bpy.data.objects.new("sun", sun); collection("LIGHTS").objects.link(so)
    el, az = math.radians(22), math.radians(215)
    d = -mathutils.Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    so.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    # camera
    cam = bpy.data.cameras.new("film_cam"); co = bpy.data.objects.new("film_cam", cam); collection("CAMERA_RIG").objects.link(co)
    sc.camera = co; cam.clip_start = 0.05; cam.clip_end = 400
    # lab world
    lw = bpy.data.worlds.new("lab_world"); lw.use_nodes = True
    lw.node_tree.nodes["Background"].inputs["Color"].default_value = (0.012, 0.016, 0.024, 1)
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = spp
    sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 4
    sc.cycles.transparent_max_bounces = 8; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.02
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.render.image_settings.file_format = "PNG"; sc.render.film_transparent = False
    sc.view_settings.view_transform = "Khronos PBR Neutral"; sc.view_settings.look = "None"; sc.view_settings.exposure = 0.15
    _state["world_outdoor"] = sc.world; _state["lab_world"] = lw
    return sc


def _excl(name, on):
    lc = bpy.context.view_layer.layer_collection.children.get(name)
    if lc is not None: lc.exclude = on


def _hide_car(on):
    car = bpy.data.objects.get("car")
    if car is None: return
    stack = [car]
    while stack:
        o = stack.pop(); o.hide_render = on; o.hide_viewport = on
        stack += list(o.children)


def apply_env(name):
    if _state["env"] == name: return
    sc = bpy.context.scene; cfg = ENVS[name]
    for cn in ("ENV_PROPS", "ENV_PAD"):
        c = bpy.data.collections[cn]
        for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
    lab = cfg["kind"] == "lab"
    _excl("LAB", not lab); _excl("PLOT_COLL", lab)
    bpy.data.objects["sun"].hide_render = lab
    sc.world = _state["lab_world"] if lab else _state["world_outdoor"]
    if not lab:
        loc, rot = cfg["plot"]; p = bpy.data.objects["PLOT"]; p.location = loc; p.rotation_euler = (0, 0, rot)
        _hide_car(not cfg.get("car"))
        if cfg.get("pad"):
            box("PAD_paving", (4.5, 7.2, 0.12), (0, 0, -0.048), E.M("paving"), bpy.data.collections["ENV_PAD"], 0, 0.004)
    if name in E.PROPS: E.PROPS[name](bpy.data.collections["ENV_PROPS"])
    _state["env"] = name


def set_shot(shot, w=None):
    s = SHOTS[shot]; apply_env(s["env"])
    cam = bpy.data.objects["film_cam"]; cam.location = s["loc"]; cam.data.lens = s["lens"]
    cam.rotation_euler = mathutils.Vector(np.array(s["tgt"]) - np.array(s["loc"])).to_track_quat("-Z", "Y").to_euler()
