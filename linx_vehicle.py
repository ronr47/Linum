#!/usr/bin/env python3

import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HOST = "127.0.0.1"
PORT = 8081

lock = threading.RLock()
adapter = None
adapter_host = None
adapter_port = None
last_error = None


class ELM327:
    def __init__(self, host, port):
        self.host = host
        self.port = int(port)
        self.sock = None
        self.lock = threading.RLock()

    def connect(self):
        self.close()

        s = socket.create_connection(
            (self.host, self.port), timeout=4
        )
        s.settimeout(2)
        self.sock = s

        for command in (
            "ATZ", "ATE0", "ATL0", "ATS0",
            "ATH0", "ATSP0"
        ):
            self.command(command)

        return True

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None

    def command(self, command):
        with self.lock:
            if not self.sock:
                raise ConnectionError("OBD adapter is disconnected")

            self.sock.sendall((command + "\r").encode("ascii"))
            result = bytearray()
            deadline = time.monotonic() + 5

            while time.monotonic() < deadline:
                try:
                    chunk = self.sock.recv(1024)
                    if not chunk:
                        raise ConnectionError("Adapter connection closed")

                    result.extend(chunk)

                    if b">" in result:
                        break

                except socket.timeout:
                    if result:
                        break

            if not result:
                raise TimeoutError("No response from OBD adapter")

            text = result.decode("ascii", errors="replace")
            text = text.replace(">", " ")
            text = text.replace("\r", " ")
            text = text.replace("\n", " ")
            return text.strip()

    def data_bytes(self, response, service, pid=None):
        clean = response.upper()

        if any(x in clean for x in (
            "UNABLE TO CONNECT", "NO DATA",
            "STOPPED", "CAN ERROR", "BUS ERROR"
        )):
            return None

        tokens = clean.split()
        values = []

        for token in tokens:
            if len(token) == 2:
                try:
                    values.append(int(token, 16))
                except ValueError:
                    pass

        for i in range(len(values)):
            if values[i] == service:
                if pid is None:
                    return values[i + 1:]
                if i + 1 < len(values) and values[i + 1] == pid:
                    return values[i + 2:]

        return None

    def read_pid(self, pid):
        response = self.command("01" + pid)
        data = self.data_bytes(response, 0x41, int(pid, 16))

        if data is None:
            return None

        if pid == "0C" and len(data) >= 2:
            return round(((data[0] * 256) + data[1]) / 4)

        if pid == "0D" and len(data) >= 1:
            return data[0]

        if pid == "05" and len(data) >= 1:
            return data[0] - 40

        if pid == "11" and len(data) >= 1:
            return round(data[0] * 100 / 255, 1)

        if pid == "42" and len(data) >= 2:
            return round(((data[0] * 256) + data[1]) / 1000, 2)

        return None

    def read_dtcs(self):
        response = self.command("03")
        data = self.data_bytes(response, 0x43)

        if data is None:
            return [], response

        codes = []
        prefixes = "PCBU"

        for i in range(0, len(data) - 1, 2):
            a, b = data[i], data[i + 1]

            if a == 0 and b == 0:
                continue

            prefix = prefixes[(a >> 6) & 3]
            digit = (a >> 4) & 3
            code = (
                prefix
                + str(digit)
                + format(a & 15, "X")
                + format((b >> 4) & 15, "X")
                + format(b & 15, "X")
            )
            codes.append(code)

        return codes, response


def get_adapter():
    with lock:
        return adapter


def connect_adapter(host, port):
    global adapter, adapter_host, adapter_port, last_error

    new_adapter = ELM327(host, port)
    new_adapter.connect()

    with lock:
        if adapter:
            adapter.close()

        adapter = new_adapter
        adapter_host = host
        adapter_port = int(port)
        last_error = None

    return True


def disconnect_adapter():
    global adapter, adapter_host, adapter_port

    with lock:
        if adapter:
            adapter.close()

        adapter = None
        adapter_host = None
        adapter_port = None


def get_telemetry():
    global last_error

    elm = get_adapter()

    if not elm:
        return {
            "connected": False,
            "status": "DISCONNECTED",
            "error": last_error,
            "values": {}
        }

    values = {}

    try:
        with elm.lock:
            values["engine_rpm"] = elm.read_pid("0C")
            values["vehicle_speed_kmh"] = elm.read_pid("0D")
            values["coolant_temperature_c"] = elm.read_pid("05")
            values["throttle_percent"] = elm.read_pid("11")
            values["control_module_voltage"] = elm.read_pid("42")

        return {
            "connected": True,
            "status": "CONNECTED",
            "adapter": adapter_host,
            "port": adapter_port,
            "timestamp": time.time(),
            "values": values,
            "error": None
        }

    except Exception as exc:
        last_error = str(exc)
        disconnect_adapter()

        return {
            "connected": False,
            "status": "CONNECTION LOST",
            "values": {},
            "error": last_error
        }


HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport"
 content="width=device-width,initial-scale=1,maximum-scale=1">
<meta name="theme-color" content="#07111f">
<title>LINX Vehicle Control</title>
<style>
:root {
  color-scheme:dark;
  --bg:#07111f;
  --panel:#0d1b2b;
  --line:#20364c;
  --text:#e4efff;
  --cyan:#36e1df;
  --green:#4dff9a;
  --red:#ff647c;
  --muted:#8da6c1;
}
*{box-sizing:border-box}
body{
  margin:0;background:var(--bg);color:var(--text);
  font:15px system-ui,sans-serif
}
header{
  padding:19px 15px;background:#0b1828;
  border-bottom:1px solid var(--line)
}
h1{font-size:23px;letter-spacing:2px;margin:0}
.subtitle{color:var(--muted);font-size:12px}
main{max-width:900px;margin:auto;padding:12px}
.panel{
  background:var(--panel);border:1px solid var(--line);
  border-radius:13px;padding:14px;margin-bottom:12px
}
h2{font-size:15px;margin:0 0 12px}
.row{display:flex;gap:8px;flex-wrap:wrap}
input,button{
  border:1px solid #34506b;border-radius:8px;
  padding:12px;background:#12263a;color:var(--text);
  font-size:14px
}
input{min-width:0;flex:1;width:100%}
button{cursor:pointer}
button.primary{background:#075b65;border-color:var(--cyan)}
button:disabled{opacity:.5}
label{display:block;flex:1;min-width:110px;color:var(--muted)}
label input{display:block;margin-top:6px}
.status{font-weight:700;color:#ffc76b}
.status.online{color:var(--green)}
.status.offline{color:var(--red)}
.grid{
  display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
  gap:10px
}
.metric{
  background:#091522;border:1px solid var(--line);
  border-radius:12px;padding:15px;min-height:120px
}
.metric .name{font-size:11px;color:var(--muted);letter-spacing:1px}
.metric .value{font-size:30px;font-weight:750;margin-top:10px}
.metric .unit{font-size:12px;color:var(--muted)}
.note{font-size:12px;color:var(--muted);line-height:1.6}
#message{white-space:pre-wrap;overflow-wrap:anywhere}
#codes{font-size:19px;font-weight:700}
@media(min-width:600px){
 .grid{grid-template-columns:repeat(3,minmax(0,1fr))}
}
</style>
</head>
<body>
<header>
  <h1>LINX <span style="color:#36e1df">VEHICLE</span></h1>
  <div class="subtitle">NAVARA DIAGNOSTICS · LIVE OBD-II</div>
</header>
<main>
<section class="panel">
  <h2>ADAPTER CONNECTION</h2>
  <div id="status" class="status offline">● DISCONNECTED</div>
  <div class="row" style="margin-top:12px">
    <label>Adapter IP / Host
      <input id="host" value="192.168.0.10"
       autocomplete="off" spellcheck="false">
    </label>
    <label>TCP Port
      <input id="port" type="number" value="35000">
    </label>
  </div>
  <div class="row" style="margin-top:12px">
    <button id="connect" class="primary" onclick="connectOBD()">
      CONNECT
    </button>
    <button onclick="disconnectOBD()">DISCONNECT</button>
  </div>
  <p class="note">
    Enter the actual address and port of your Wi-Fi OBD-II adapter.
    The default values are examples, not a detected adapter.
  </p>
  <div id="message" class="note"></div>
</section>

<section class="panel">
  <h2>LIVE ENGINE DATA</h2>
  <div class="grid">
    <div class="metric">
      <div class="name">ENGINE RPM</div>
      <div class="value" id="rpm">--</div>
      <div class="unit">revolutions/min</div>
    </div>
    <div class="metric">
      <div class="name">VEHICLE SPEED</div>
      <div class="value" id="speed">--</div>
      <div class="unit">km/h</div>
    </div>
    <div class="metric">
      <div class="name">COOLANT TEMP</div>
      <div class="value" id="coolant">--</div>
      <div class="unit">°C</div>
    </div>
    <div class="metric">
      <div class="name">THROTTLE</div>
      <div class="value" id="throttle">--</div>
      <div class="unit">percent</div>
    </div>
    <div class="metric">
      <div class="name">CONTROL MODULE VOLTAGE</div>
      <div class="value" id="voltage">--</div>
      <div class="unit">volts</div>
    </div>
    <div class="metric">
      <div class="name">DATA LINK</div>
      <div class="value" id="link" style="font-size:19px">OFFLINE</div>
      <div class="unit">adapter communication</div>
    </div>
  </div>
  <p class="note">
    Unsupported PIDs appear as --. Values are read from the adapter;
    the control module voltage PID may not be supported by every vehicle.
  </p>
</section>

<section class="panel">
  <h2>DIAGNOSTIC TROUBLE CODES</h2>
  <button class="primary" id="scan" onclick="scanCodes()">
    SCAN FAULT CODES
  </button>
  <p id="codes">No scan performed</p>
  <div id="codeMessage" class="note"></div>
  <p class="note">
    Reads standard emissions-related OBD-II codes. Manufacturer-specific
    body, ABS, airbag, and transmission modules may require other tools.
  </p>
</section>

<section class="panel">
  <h2>VEHICLE CONTROL INTEGRATION</h2>
  <div class="note">
    <p>Engine diagnostics: OBD-II interface.</p>
    <p>Lights, locks, climate, and radio: vehicle-specific interface required.</p>
    <p>Remote start: compatible dedicated remote-start hardware required.</p>
    <p id="integration">Control hardware has not been configured.</p>
  </div>
</section>
</main>
<script>
const $ = id => document.getElementById(id);

async function api(path, options={}) {
  const response = await fetch(path, {
    cache:'no-store',
    headers:{'Content-Type':'application/json'},
    ...options
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}

function setStatus(connected, text) {
  const s = $('status');
  s.className = 'status ' + (connected ? 'online' : 'offline');
  s.textContent = (connected ? '● ' : '● ') + text;
}

function display(id, value, suffix='') {
  $(id).textContent =
    value === null || value === undefined ? '--' : value + suffix;
}

async function connectOBD() {
  $('connect').disabled = true;
  $('message').textContent = 'Connecting to adapter...';

  try {
    const result = await api('/api/connect', {
      method:'POST',
      body:JSON.stringify({
        host:$('host').value.trim(),
        port:Number($('port').value)
      })
    });

    setStatus(true, 'ADAPTER CONNECTED');
    $('message').textContent = result.message;
    await refresh();
  } catch (error) {
    setStatus(false, 'CONNECTION FAILED');
    $('message').textContent = error.message;
  } finally {
    $('connect').disabled = false;
  }
}

async function disconnectOBD() {
  try {
    await api('/api/disconnect', {method:'POST',body:'{}'});
  } catch (_) {}
  setStatus(false, 'DISCONNECTED');
  $('message').textContent = 'Adapter disconnected.';
  $('link').textContent = 'OFFLINE';
  for (const id of ['rpm','speed','coolant','throttle','voltage']) {
    display(id, null);
  }
}

async function refresh() {
  try {
    const data = await api('/api/telemetry');
    if (!data.connected) {
      setStatus(false, data.status || 'DISCONNECTED');
      $('link').textContent = 'OFFLINE';
      if (data.error) $('message').textContent = data.error;
      return;
    }

    setStatus(true, 'ADAPTER CONNECTED');
    $('link').textContent = 'ONLINE';

    const v = data.values;
    display('rpm', v.engine_rpm);
    display('speed', v.vehicle_speed_kmh);
    display('coolant', v.coolant_temperature_c);
    display('throttle', v.throttle_percent, '%');
    display('voltage', v.control_module_voltage, ' V');
    $('message').textContent =
      'Connected to ' + data.adapter + ':' + data.port;
  } catch (error) {
    $('message').textContent = error.message;
  }
}

async function scanCodes() {
  $('scan').disabled = true;
  $('codes').textContent = 'Scanning...';
  $('codeMessage').textContent = '';

  try {
    const data = await api('/api/dtc');
    $('codes').textContent = data.codes.length
      ? data.codes.join(', ')
      : 'No standard stored codes reported';
    $('codeMessage').textContent =
      data.codes.length
        ? 'Record the codes before diagnosis.'
        : 'This is not a guarantee that every vehicle module is fault-free.';
  } catch (error) {
    $('codes').textContent = 'Scan unavailable';
    $('codeMessage').textContent = error.message;
  } finally {
    $('scan').disabled = false;
  }
}

setInterval(refresh, 2000);
refresh();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/telemetry":
            self.send_json(200, get_telemetry())
            return

        self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        global last_error

        path = urlparse(self.path).path

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 4096:
                self.send_json(413, {"error": "Request too large"})
                return

            body = self.rfile.read(length) if length else b"{}"
            data = json.loads(body)

            if path == "/api/connect":
                host = str(data.get("host", "")).strip()
                port = int(data.get("port", 35000))

                if not host or len(host) > 253:
                    raise ValueError("Enter a valid adapter host")

                if not 1 <= port <= 65535:
                    raise ValueError("TCP port must be between 1 and 65535")

                connect_adapter(host, port)

                self.send_json(200, {
                    "connected": True,
                    "message": "Adapter connected. Waiting for vehicle data."
                })
                return

            if path == "/api/disconnect":
                disconnect_adapter()
                self.send_json(200, {"connected": False})
                return

            if path == "/api/dtc":
                elm = get_adapter()

                if not elm:
                    self.send_json(409, {
                        "error": "Connect an OBD-II adapter first"
                    })
                    return

                with elm.lock:
                    codes, raw = elm.read_dtcs()

                self.send_json(200, {
                    "codes": codes,
                    "raw_response": raw
                })
                return

            self.send_json(404, {"error": "Not found"})

        except Exception as exc:
            last_error = str(exc)
            self.send_json(502, {"error": str(exc)})

    def log_message(self, fmt, *args):
        print("[LINX]", fmt % args)


if __name__ == "__main__":
    print("LINX Vehicle Control")
    print("Dashboard: http://127.0.0.1:8081")
    print("OBD-II TCP adapter integration enabled.")
    print("Press Ctrl+C to stop.")

    server = ThreadingHTTPServer((HOST, PORT), Handler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping LINX...")
    finally:
        disconnect_adapter()
        server.server_close()
