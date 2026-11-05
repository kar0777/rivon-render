"""v5 edit: the opening is cut to 3.5 s.  Output timeline = blender frames 55..129 (shot 1), 156..185 (shot 2), 186..780 (rest) = 700 frames.
usage:  python3 remap.py events <events.json> <events_cut.json>
        python3 remap.py frames <rendered_frames_dir> <out_dir>      (symlinks f0000.png ... f0699.png in output order)"""
import sys, os, json
KEEP = [(55, 129), (156, 185), (186, 780)]                   # inclusive blender frame ranges
SRC = [f for a, b in KEEP for f in range(a, b + 1)]          # output index i -> blender frame SRC[i]
def new_frame(f):
    """blender frame -> output blender-style frame (1-based); frames dropped by the cut snap to the next kept frame"""
    for i, s in enumerate(SRC):
        if s >= f: return i + 1
    return len(SRC)
if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "events":
        ev = json.load(open(sys.argv[2])); out = []
        for e in ev:
            e = dict(e)
            if e["name"] == "VAN_SPEED":
                v = e["v"]; e["v"] = [v[f - 1] for f in SRC if f <= len(v)]; e["f0"], e["f1"] = 1, len(e["v"])
            else:
                e["f0"], e["f1"] = new_frame(e["f0"]), new_frame(e["f1"])
            out.append(e)
        json.dump(out, open(sys.argv[3], "w")); print("events", len(out), "frames", len(SRC))
    elif mode == "frames":
        src, dst = sys.argv[2], sys.argv[3]; os.makedirs(dst, exist_ok=True)
        for i, f in enumerate(SRC):
            p = os.path.join(src, "f%04d.png" % (f - 1)); assert os.path.exists(p), p
            q = os.path.join(dst, "f%04d.png" % i)
            if os.path.lexists(q): os.remove(q)
            os.symlink(os.path.abspath(p), q)
        print("linked", len(SRC))
