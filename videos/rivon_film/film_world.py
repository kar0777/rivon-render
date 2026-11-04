"""Per-scene real-photo surroundings (Poly Haven CC0 HDRIs): world lighting + a ground-projected camera-only dome + a
local textured ground that fades into the photographed ground.  The pergola is never touched here."""
import math
import numpy as np
import bpy, mathutils
from film_lib import *   # noqa

HDRI = HERE / "hdri"
_cache = {}


def load_hdr(fid, res="4k"):
    img = bpy.data.images.load(str(HDRI / f"{fid}_{res}.hdr"), check_existing=True)
    img.colorspace_settings.name = "Linear Rec.709"
    return img


def hdr_stats(img):
    """Mean radiance of the ground near the horizon and cosine-weighted mean radiance of the upper hemisphere (irradiance/pi)."""
    if img.name in _cache: return _cache[img.name]
    w, h = img.size
    a = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(a); a = a.reshape(h, w, 4)[:, :, :3]
    a = a[::4, ::4]; h2, w2 = a.shape[:2]
    el = (np.arange(h2)[:, None] + 0.5) / h2 * math.pi - math.pi / 2          # elevation per row (row 0 = bottom)
    gmask = ((el < -0.10) & (el > -0.55))[:, 0]
    ground = a[gmask].reshape(-1, 3).mean(0)
    row = a.mean(1)                                                                # (h2,3)
    wr = np.where(el[:, 0] > 0, np.sin(el[:, 0]) * np.cos(el[:, 0]), 0.0); wr /= wr.sum()
    sky = (row * wr[:, None]).sum(0)
    _cache[img.name] = (ground, sky); return ground, sky


def make_world(fid, rot_z, strength=1.0):
    w = bpy.data.worlds.new(f"w_{fid}"); w.use_nodes = True; nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground"); bg.inputs["Strength"].default_value = strength
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value = (0, 0, -rot_z)
    tex = nt.nodes.new("ShaderNodeTexEnvironment"); tex.image = load_hdr(fid)
    nt.links.new(tc.outputs["Generated"], mp.inputs[0]); nt.links.new(mp.outputs[0], tex.inputs[0])
    nt.links.new(tex.outputs[0], bg.inputs[0]); nt.links.new(bg.outputs[0], out.inputs[0])
    return w


def build_dome(coll, fid, rot_z, h_cap=1.7, rmax=220.0, nu=360, nv=180):
    """Camera-only mesh: sky on a sphere, ground flattened onto z=0 (ground projection). UVs = equirect coordinates of the
    capture direction, so the photo is sampled exactly as the world lighting does."""
    u = (np.arange(nu + 1) / nu); v = (np.arange(nv + 1) / nv)
    U, V = np.meshgrid(u, v)
    az = (U - 0.5) * 2 * math.pi; el = (V - 0.5) * math.pi
    # Blender equirect: u = atan2(dir.y, -dir.x)/(2pi)+0.5  ->  dir.x = -cos(az')*..., use the exact inverse
    ez = np.sin(el)
    ang = (U - 0.5) * 2 * math.pi
    ex = -np.cos(ang) * np.cos(el); ey = np.sin(ang) * np.cos(el)
    exy = np.maximum(np.hypot(ex, ey), 1e-6)
    s = np.full_like(ez, rmax)
    below = ez < -1e-4
    s[below] = np.minimum(h_cap / (-ez[below]), rmax / exy[below])
    P = np.stack([ex * s, ey * s, h_cap + ez * s - 0.03], -1).reshape(-1, 3)
    faces = []
    idx = lambda i, j: i * (nu + 1) + j
    for i in range(nv):
        for j in range(nu):
            faces.append((idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)))
    me = bpy.data.meshes.new(f"dome_{fid}"); me.from_pydata(P.tolist(), [], faces); me.update()
    uv = me.uv_layers.new(name="UVMap")
    uvs = np.stack([U, V], -1).reshape(-1, 2)
    loops = np.empty(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", loops)
    uv.data.foreach_set("uv", uvs[loops].ravel())
    m = bpy.data.materials.new(f"dome_mat_{fid}"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = "UVMap"
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = load_hdr(fid); tex.interpolation = "Linear"; tex.extension = "EXTEND"
    nt.links.new(uvn.outputs[0], tex.inputs[0]); nt.links.new(tex.outputs[0], em.inputs[0]); nt.links.new(em.outputs[0], out.inputs[0])
    me.materials.append(m)
    ob = bpy.data.objects.new(f"DOME_{fid}", me); ob.rotation_euler = (0, 0, rot_z); link(ob, coll)
    for k in ("visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter", "visible_shadow"):
        if hasattr(ob, k): setattr(ob, k, False)
    return ob


def ground_disc(coll, fid, tex_diff, tex_rough, scale, radius=46.0, fade=(16.0, 40.0), albedo_gain=1.6, bump=None):
    """Diffuse textured ground (receives the pergola's shadow) whose colour is matched to the photographed ground and which
    fades to transparent so the projected photo continues seamlessly."""
    ground, sky = hdr_stats(load_hdr(fid))
    # albedo so that albedo * (irradiance/pi) == photographed ground radiance
    alb = np.clip(ground / np.maximum(sky, 1e-3) * albedo_gain, 0.03, 0.55)
    m = bpy.data.materials.new(f"ground_{fid}"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs["Object"], mp.inputs[0])
    def img(fn, cs):
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(str(TEX / fn), check_existing=True)
        t.image.colorspace_settings.name = cs; t.projection = "BOX"; t.projection_blend = 0.2
        nt.links.new(mp.outputs[0], t.inputs[0]); return t
    if tex_diff == "PROC_LAWN":
        # procedural mown lawn: two-scale noise between darker/lighter shades of the photo-matched albedo
        n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 6.0 * scale; n1.inputs["Detail"].default_value = 8.0
        n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 140.0; n2.inputs["Detail"].default_value = 3.0
        nt.links.new(tc.outputs["Object"], n1.inputs[0]); nt.links.new(tc.outputs["Object"], n2.inputs[0])
        mx2 = nt.nodes.new("ShaderNodeMix"); mx2.data_type = "FLOAT"; mx2.inputs[0].default_value = 0.35
        nt.links.new(n1.outputs["Fac"], mx2.inputs[2]); nt.links.new(n2.outputs["Fac"], mx2.inputs[3])
        cr = nt.nodes.new("ShaderNodeValToRGB")
        cr.color_ramp.elements[0].color = (*(alb * 0.55), 1.0); cr.color_ramp.elements[1].color = (*(alb * 1.45), 1.0)
        cr.color_ramp.elements[0].position = 0.3; cr.color_ramp.elements[1].position = 0.7
        nt.links.new(mx2.outputs[0], cr.inputs[0]); nt.links.new(cr.outputs[0], b.inputs["Base Color"])
        bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.9; bm.inputs["Distance"].default_value = 0.03
        nt.links.new(n2.outputs["Fac"], bm.inputs["Height"]); nt.links.new(bm.outputs[0], b.inputs["Normal"])
        tex_rough = None
    else:
        d = img(tex_diff, "sRGB")
        # normalise the texture to its own mean so the mean colour equals the photo-matched albedo
        ti = d.image; arr = np.empty(ti.size[0] * ti.size[1] * 4, np.float32)
        ti.pixels.foreach_get(arr); mean = arr.reshape(-1, 4)[::97, :3].mean(0) + 1e-4
        k = alb / mean
        mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1.0
        mul.inputs[7].default_value = (float(k[0]), float(k[1]), float(k[2]), 1.0)
        nt.links.new(d.outputs[0], mul.inputs[6]); nt.links.new(mul.outputs[2], b.inputs["Base Color"])
    if tex_rough:
        r = img(tex_rough, "Non-Color"); nt.links.new(r.outputs[0], b.inputs["Roughness"])
    b.inputs["Roughness"].default_value = 0.9
    # radial fade (object-space distance)
    ln = nt.nodes.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"; nt.links.new(tc.outputs["Object"], ln.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = fade[0]; mr.inputs[2].default_value = fade[1]
    mr.inputs[3].default_value = 0.0; mr.inputs[4].default_value = 1.0; mr.interpolation_type = "SMOOTHSTEP"
    nt.links.new(ln.outputs["Value"], mr.inputs[0]); nt.links.new(mr.outputs[0], mx.inputs[0])
    nt.links.new(b.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs[0])
    me = bpy.data.meshes.new(f"ground_{fid}")
    ang = np.linspace(0, 2 * math.pi, 96, endpoint=False)
    verts = [(0, 0, 0)] + [(radius * math.cos(a), radius * math.sin(a), 0) for a in ang]
    faces = [(0, 1 + i, 1 + (i + 1) % 96) for i in range(96)]
    me.from_pydata(verts, [], faces); me.update(); me.materials.append(m)
    ob = bpy.data.objects.new(f"GROUND_{fid}", me); link(ob, coll)
    ob.location = (0, 0, 0.0)
    return ob
