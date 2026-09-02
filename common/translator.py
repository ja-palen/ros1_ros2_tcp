import importlib, yaml

def load_type(type_name):
    p = type_name.split("/")
    if len(p) == 2:
        package, name = p
    elif len(p) == 3 and p[1] == "msg":
        package, name = p[0], p[2]
    else:
        raise ValueError("Invalid ROS message type: " + type_name)
    return getattr(importlib.import_module(package + ".msg"), name)

def get_field(obj, path):
    for part in path.split("."):
        obj = getattr(obj, part)
    return obj

def set_field(obj, path, value):
    parts = path.split(".")
    for part in parts[:-1]:
        obj = getattr(obj, part)
    setattr(obj, parts[-1], value)

def json_value(v):
    if v is None or isinstance(v, (str, int, float, bool)): return v
    if isinstance(v, (list, tuple)): return [json_value(x) for x in v]
    try: return float(v)
    except (TypeError, ValueError): return str(v)

def _paths(sf, side):
    # supports {ros1: a.b, ros2: a.c} for side-specific names, or legacy {from,to}
    if "ros1" in sf and "ros2" in sf:
        local = sf[side]
        other = sf["ros2" if side == "ros1" else "ros1"]
        # wire key uses ros2 name as canonical
        key = sf["ros2"]
        return local, key, other
    # legacy: from=key on wire and on the "encoding" side; to=field on decoding side
    return sf["from"], sf["from"], sf["to"]

def _encode_element(elem, subfields, side):
    out = {}
    for sf in subfields:
        local, key, _ = _paths(sf, side)
        out[key] = json_value(get_field(elem, local))
    return out

def _decode_element(cls, data, subfields, side):
    msg = cls()
    for sf in subfields:
        local, key, _ = _paths(sf, side)
        if key in data:
            set_field(msg, local, data[key])
    return msg

class Translator:
    def __init__(self, mapping, debug=False, side=None):
        # side is "ros1" or "ros2"; required for list_of and for per-side field paths
        self.mapping, self.debug, self.side = mapping, debug, side

    def log(self, s):
        if self.debug: print("[TRANSLATOR] " + s, flush=True)

    def encode(self, msg):
        fields = {}
        for m in self.mapping["fields"]:
            local, key, _ = _paths(m, self.side)
            v = get_field(msg, local)
            lo = m.get("list_of")
            if lo is not None:
                fields[key] = [_encode_element(e, lo["fields"], self.side) for e in v]
            else:
                fields[key] = json_value(v)
        self.log("encode %s fields=%s" % (self.mapping["name"], fields))
        return fields

    def decode(self, fields, msg):
        for m in self.mapping["fields"]:
            local, key, _ = _paths(m, self.side)
            if key not in fields: continue
            lo = m.get("list_of")
            if lo is not None:
                if self.side is None:
                    raise ValueError("Translator needs side='ros1'|'ros2' for list_of mappings")
                cls = load_type(lo[self.side + "_type"])
                items = [_decode_element(cls, d, lo["fields"], self.side) for d in fields[key]]
                set_field(msg, local, items)
            else:
                set_field(msg, local, fields[key])
        self.log("decode %s fields=%s" % (self.mapping["name"], fields))
        return msg

def load_config(filename):
    with open(filename) as f: cfg = yaml.safe_load(f) or {}
    if not cfg.get("mappings"): raise ValueError("No mappings configured")
    return cfg
