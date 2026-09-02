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

class Translator:
    def __init__(self, mapping, debug=False):
        self.mapping, self.debug = mapping, debug

    def log(self, s):
        if self.debug: print("[TRANSLATOR] " + s, flush=True)

    def encode(self, msg):
        fields = {}
        for m in self.mapping["fields"]:
            fields[m["from"]] = json_value(get_field(msg, m["from"]))
        self.log("encode %s fields=%s" % (self.mapping["name"], fields))
        return fields

    def decode(self, fields, msg):
        for m in self.mapping["fields"]:
            if m["from"] in fields:
                set_field(msg, m["to"], fields[m["from"]])
        self.log("decode %s fields=%s" % (self.mapping["name"], fields))
        return msg

def load_config(filename):
    with open(filename) as f: cfg = yaml.safe_load(f) or {}
    if not cfg.get("mappings"): raise ValueError("No mappings configured")
    return cfg
