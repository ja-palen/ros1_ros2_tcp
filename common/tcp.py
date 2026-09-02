import json, socket, struct, threading, time

HEADER = struct.Struct(">I")

class TCPConnection:
    def __init__(self, host, port, reconnect=1.0, debug=False):
        self.host, self.port = host, int(port)
        self.reconnect, self.debug = float(reconnect), debug
        self.sock = None
        # separate locks so a blocked recv() cannot stall send()
        self.send_lock = threading.Lock()
        self.recv_lock = threading.Lock()
        self.state_lock = threading.Lock()

    def log(self, s):
        if self.debug: print("[TCP] " + s, flush=True)

    def connect(self):
        with self.state_lock:
            if self.sock is not None: return True
            try:
                s = socket.create_connection((self.host, self.port), timeout=2)
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                s.settimeout(None)  # revert to blocking; connect() set a 2s timeout
                self.sock = s
                self.log("connected %s:%s" % (self.host, self.port))
                return True
            except OSError as e:
                self.log("connect failed: %s" % e)
                return False

    def close(self):
        with self.state_lock:
            s, self.sock = self.sock, None
        if s:
            try: s.close()
            except OSError: pass

    def send(self, packet):
        payload = json.dumps(packet, separators=(",", ":"), allow_nan=False).encode()
        with self.send_lock:
            s = self.sock
            if not s: return False
            try:
                s.sendall(HEADER.pack(len(payload)) + payload)
                self.log("send mapping=%s bytes=%d" % (packet.get("mapping"), len(payload)))
                return True
            except OSError:
                self.close()
                return False

    def receive(self):
        with self.recv_lock:
            s = self.sock
            if not s: return None
            try:
                h = self._exact(s, HEADER.size)
                if h is None: self.close(); return None
                n = HEADER.unpack(h)[0]
                if n > 64*1024*1024: raise ValueError("frame too large")
                p = self._exact(s, n)
                if p is None: self.close(); return None
                packet = json.loads(p.decode())
                self.log("receive mapping=%s bytes=%d" % (packet.get("mapping"), n))
                return packet
            except Exception:
                self.close()
                return None

    def _exact(self, s, n):
        data = b""
        while len(data) < n:
            chunk = s.recv(n-len(data))
            if not chunk: return None
            data += chunk
        return data

class TCPServer:
    def __init__(self, host, port, debug=False):
        self.host, self.port, self.debug = host, int(port), debug
        self.server = None
        self.client = None
        # separate locks so a blocked recv() cannot stall send()
        self.send_lock = threading.Lock()
        self.recv_lock = threading.Lock()
        self.state_lock = threading.Lock()

    def log(self, s):
        if self.debug: print("[TCP] " + s, flush=True)

    def start(self):
        self.server = socket.socket()
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(1)
        self.log("listening %s:%s" % (self.host, self.port))

    def accept(self):
        while True:
            try:
                c, addr = self.server.accept()
                c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                with self.state_lock:
                    old, self.client = self.client, c
                if old:
                    try: old.close()
                    except OSError: pass
                self.log("accepted %s" % (addr,))
                return True
            except OSError:
                if self.server is None: return False

    def send(self, packet):
        payload = json.dumps(packet, separators=(",", ":"), allow_nan=False).encode()
        with self.send_lock:
            c = self.client
            if not c: return False
            try:
                c.sendall(HEADER.pack(len(payload)) + payload)
                self.log("send mapping=%s bytes=%d" % (packet.get("mapping"), len(payload)))
                return True
            except OSError:
                self._drop()
                return False

    def receive(self):
        with self.recv_lock:
            c = self.client
            if not c: return None
            try:
                h = self._exact(c, HEADER.size)
                if h is None: self._drop(); return None
                n = HEADER.unpack(h)[0]
                if n > 64*1024*1024: raise ValueError("frame too large")
                p = self._exact(c, n)
                if p is None: self._drop(); return None
                packet = json.loads(p.decode())
                self.log("receive mapping=%s bytes=%d" % (packet.get("mapping"), n))
                return packet
            except Exception:
                self._drop()
                return None

    def _exact(self, c, n):
        data = b""
        while len(data) < n:
            chunk = c.recv(n-len(data))
            if not chunk: return None
            data += chunk
        return data

    def _drop(self):
        with self.state_lock:
            c, self.client = self.client, None
        if c:
            try: c.close()
            except OSError: pass

    def close(self):
        self._drop()
        with self.state_lock:
            srv, self.server = self.server, None
        if srv:
            try: srv.close()
            except OSError: pass
