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

def _encode_element(elem, subfields):
    return {sf["from"]: json_value(get_field(elem, sf["from"])) for sf in subfields}

def _decode_element(cls, data, subfields):
    msg = cls()
    for sf in subfields:
        if sf["from"] in data:
            set_field(msg, sf["to"], data[sf["from"]])
    return msg

class Translator:
    def __init__(self, mapping, debug=False, side=None):
        # side is "ros1" or "ros2"; required only for mappings that use list_of
        self.mapping, self.debug, self.side = mapping, debug, side

    def log(self, s):
        if self.debug: print("[TRANSLATOR] " + s, flush=True)

    def encode(self, msg):
        fields = {}
        for m in self.mapping["fields"]:
            v = get_field(msg, m["from"])
            lo = m.get("list_of")
            if lo is not None:
                fields[m["from"]] = [_encode_element(e, lo["fields"]) for e in v]
            else:
                fields[m["from"]] = json_value(v)
        self.log("encode %s fields=%s" % (self.mapping["name"], fields))
        return fields

    def decode(self, fields, msg):
        for m in self.mapping["fields"]:
            if m["from"] not in fields: continue
            lo = m.get("list_of")
            if lo is not None:
                if self.side is None:
                    raise ValueError("Translator needs side='ros1'|'ros2' for list_of mappings")
                cls = load_type(lo[self.side + "_type"])
                items = [_decode_element(cls, d, lo["fields"]) for d in fields[m["from"]]]
                set_field(msg, m["to"], items)
            else:
                set_field(msg, m["to"], fields[m["from"]])
        self.log("decode %s fields=%s" % (self.mapping["name"], fields))
        return msg

def load_config(filename):
    with open(filename) as f: cfg = yaml.safe_load(f) or {}
    if not cfg.get("mappings"): raise ValueError("No mappings configured")
    return cfg
