"""MCP (Model Context Protocol) stdio server for KherveMol.

This module is the *client-facing half* of KherveMol's MCP support.
It speaks JSON-RPC 2.0 over stdin/stdout -- the transport every MCP host
(Claude Desktop, Claude Code, Cursor, Zed, Continue, ...) knows how to
launch -- and forwards each ``tools/call`` to a running KherveMol
window over a loopback socket (see ``mcp_bridge.py``).

The split matters: the tools have to edit the live molecule and read
back what the viewer is showing, so they must run inside the
application's GUI thread.  The MCP host, by contrast, wants to spawn a
short-lived subprocess it owns.  This file is that subprocess; it
deliberately imports **no Qt and no third-party package**, so it starts
in milliseconds and works from any Python.

Run it directly with::

    python -m khervemol.mcp_server

or, through the launcher / a frozen build::

    python KherveMol.py --mcp-server
    KherveMol.exe --mcp-server

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import sys
from typing import Any, List, Optional


# -- Protocol constants -------------------------------------------------

#: Spec revisions we know how to speak.  We echo the client's choice
#: when it is one of these, otherwise we answer with our newest.
SUPPORTED_PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
LATEST_PROTOCOL = SUPPORTED_PROTOCOLS[0]

SERVER_NAME = "khervemol"

#: Endpoint file written by the in-app bridge; names host, port, token.
ENDPOINT_FILENAME = "mcp-bridge.json"

#: Environment override for the state directory (tests, portable setups).
STATE_DIR_ENV = "KHERVEMOL_STATE_DIR"

_CONNECT_TIMEOUT = 5.0    # seconds to establish the bridge socket
_CALL_TIMEOUT = 300.0     # a big crystal build is legitimately slow


# -- Endpoint discovery -------------------------------------------------

def state_dir() -> str:
    """Directory holding KherveMol's per-user runtime state.

    Kept free of Qt so both halves of the MCP stack agree on the path
    without the stdio server having to import PyQt5.
    """
    override = os.environ.get(STATE_DIR_ENV)
    if override:
        return override
    if sys.platform.startswith("win"):
        base = (os.environ.get("LOCALAPPDATA")
                or os.path.expanduser("~\\AppData\\Local"))
        return os.path.join(base, "KherveMol")
    if sys.platform == "darwin":
        return os.path.expanduser(
            "~/Library/Application Support/KherveMol")
    base = (os.environ.get("XDG_CONFIG_HOME")
            or os.path.expanduser("~/.config"))
    return os.path.join(base, "KherveMol")


def endpoint_path() -> str:
    """Full path of the bridge endpoint description file."""
    return os.path.join(state_dir(), ENDPOINT_FILENAME)


def read_endpoint(path: Optional[str] = None) -> Optional[dict]:
    """Load the endpoint file, or None when the app is not serving."""
    try:
        with open(path or endpoint_path(), "r", encoding="utf-8") as fh:
            info = json.load(fh)
    except Exception:
        return None
    if not isinstance(info, dict) or "port" not in info:
        return None
    return info


_NOT_RUNNING = (
    "KherveMol is not reachable.\n\n"
    "The MCP server drives a live KherveMol window, so the "
    "application must be running with its bridge enabled:\n"
    "  1. Start KherveMol.\n"
    "  2. Enable AI > Connect to Claude (MCP)...\n"
    "Then retry -- no need to restart this MCP connection."
)


class BridgeError(RuntimeError):
    """Raised when the running application cannot be reached."""


#: Sent to the client on initialize.  The host writes its own system
#: prompt, so everything a model must know before driving someone
#: else's open molecule has to travel with the connection.
_INSTRUCTIONS = """\
These tools drive a LIVE KherveMol window -- a desktop app that draws \
chemical compounds, crystals, surfaces, nanostructures, polymers and \
reactions in 3D (ball-and-stick, space-filling, sticks) with a 2D \
skeletal sketch beside it. Everything you do appears immediately in the \
window the user has open. Lengths are in angstroms; angles you pass are \
in degrees.

START with get_document_info (what is on screen), then look before you \
build: the library is large and every entry is built from real data, so \
NEVER type atom coordinates by hand.
- search_library(text) finds anything by name, formula or SMILES across \
the whole library and says which build tool takes it. list_molecules \
(~490 compounds by family; `compound` returns one in full), list_crystals \
(FCC/BCC/HCP metals, diamond/zinc-blende semiconductors, salts, oxides, \
perovskites, quartz, graphite, MoS2... with lattice, space group, density \
and their usual surfaces), list_polymers and list_reactions list the rest.
- build_molecule takes a library key/name/formula OR any SMILES you know \
(ethanol CCO, caffeine Cn1cnc2c1c(=O)n(C)c(=O)n2C). It embeds real 3D \
geometry with true bond lengths and angles. mode "add" merges a second \
molecule into what is on screen as a separate fragment.
- build_crystal: a library crystal repeated nx x ny x nz cells. \
build_surface: a slab cut along any Miller plane -- Si(111), Cu(100), \
rutile (110), quartz (0001), GaN (10-10) -- with `repeat` and `layers`, \
and optionally an `adsorbate` (smiles, compound, or 'current' = the \
molecule on screen) placed above it: height, dx, dy, mode \
flat/upright/as drawn, spin. build_nano: graphene (layers, stacking AB/\
ABA/ABC/AA, twist), nanoribbons, quantum dots, graphite, defects, \
nanotubes (n, m), fullerenes (C20..C200). build_polymer: a preset or a \
custom repeat-unit SMILES, n units, head/tail caps. build_reaction: \
write it like a chemist ('2 H2 + O2 -> 2 H2O', 'N2 + 3 H2 <=> 2 NH3'); \
leave coefficients out and it balances them and REPORTS whether atoms \
and charge balance -- tell the user when they do not. play:true runs the \
animated film (reactants approach, bonds break, atoms rearrange, new \
bonds form, products separate); play_reaction plays / pauses / stops it \
and set_reaction_progress scrubs it so you can render_view any stage.
- Each build REPLACES the molecule on screen (except mode "add"), and \
the user's unsaved work is real: offer save_document before replacing \
something they drew by hand.

Editing the molecule on screen (molecules only -- crystals, surfaces and \
reaction scenes are fixed): add_atom bonds a new element to an anchor \
atom at its real bond length and refuses a bond the valence cannot carry; \
fill_hydrogens caps free valences; bond_atoms / set_bond_order / \
delete_bond / delete_atom / move_atom change the graph. Atom indices \
come from get_structure and SHIFT after a delete_atom -- re-read them. \
keep_molecule saves the molecule on screen to the user's 'My molecules' \
shelf, from where build_molecule('@Name') reloads it and build_reaction \
takes '@Name' as a species with its exact geometry.

LOOK at what you built: render_view returns a PNG of the 3D view as an \
image. Do this after anything non-trivial. It can render from another \
angle or style without touching the user's own view (az, el, style, \
labels). set_view changes the user's view (named view, az/el, style \
ball_and_stick / space_filling / sticks, renderer gl / classic, atom \
labels, bond spread, polyhedra); select_atoms just points at atoms. \
properties gives formula, molecular \
weight and (with RDKit) logP, TPSA, InChI. Files: new_document, \
add_to_surface puts more molecules on a slab, move_adsorbate slides / \
turns one and remove_adsorbate takes it off. \
open_document / save_document (.kmol), export_image (PNG), export_svg \
(opens in KhervePaint), export_model (3D printing / mesh files STL, 3MF, \
OBJ, PLY, GLB with size in mm per angstrom; or chemistry files XYZ, MOL, \
SDF, PDB, CIF -- the format follows the extension).

Working rules:
- A tool error says what to change: fix it, do not retry the same call.
- Tell the user what you built and which library entry you used; if the \
library had no match and you used SMILES, say so.
- The user controls what you may do (AI > Connect to Claude). A \
refusal naming an access level is their setting, not a bug -- tell them \
what you needed rather than working around it.
"""


# ── Bridge client ──────────────────────────────────────────────────

class BridgeClient:
    """Line-delimited JSON client for the in-app bridge.

    Connects lazily and reconnects on demand so that the MCP host may
    start this process before (or after) KherveMol itself, and so a
    restart of the application does not require a restart of the host.
    """

    def __init__(self, endpoint_file: Optional[str] = None):
        self._endpoint_file = endpoint_file
        self._sock: Optional[socket.socket] = None
        self._buf = b""
        self._token = ""
        self._next_id = 0

    # ── Connection handling ─────────────────────────────────────

    def close(self):
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
        self._sock = None
        self._buf = b""

    def _connect(self):
        info = read_endpoint(self._endpoint_file)
        if info is None:
            raise BridgeError(_NOT_RUNNING)
        self._token = str(info.get("token", ""))
        host = str(info.get("host", "127.0.0.1"))
        port = int(info["port"])
        try:
            sock = socket.create_connection(
                (host, port), timeout=_CONNECT_TIMEOUT)
        except OSError as exc:
            # A stale endpoint file (app killed without cleanup) looks
            # exactly like "not running" from here — say so plainly
            # rather than leaking a connection-refused traceback.
            raise BridgeError(f"{_NOT_RUNNING}\n\n(socket error: {exc})")
        sock.settimeout(_CALL_TIMEOUT)
        self._sock = sock
        self._buf = b""

    def _readline(self) -> bytes:
        assert self._sock is not None
        while b"\n" not in self._buf:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise BridgeError(
                    "KherveMol closed the connection mid-request. "
                    "The application may have quit.")
            self._buf += chunk
        line, _, self._buf = self._buf.partition(b"\n")
        return line

    def request(self, method: str, params: Optional[dict] = None) -> Any:
        """Send one request, returning its ``result`` payload."""
        for attempt in (0, 1):
            if self._sock is None:
                self._connect()
            self._next_id += 1
            payload = {
                "id": self._next_id,
                "token": self._token,
                "method": method,
                "params": params or {},
            }
            try:
                assert self._sock is not None
                self._sock.sendall(
                    (json.dumps(payload) + "\n").encode("utf-8"))
                line = self._readline()
            except BridgeError:
                self.close()
                if attempt == 0:
                    continue          # app restarted: reconnect once
                raise
            except OSError as exc:
                self.close()
                if attempt == 0:
                    continue
                raise BridgeError(f"Bridge I/O error: {exc}")
            try:
                reply = json.loads(line.decode("utf-8"))
            except Exception:
                self.close()
                raise BridgeError("Malformed reply from KherveMol.")
            if reply.get("error"):
                raise BridgeError(str(reply["error"]))
            return reply.get("result")
        raise BridgeError(_NOT_RUNNING)


# ── Result shaping ─────────────────────────────────────────────────

#: Key a tool result uses to hand back a rendered picture.  An app
#: that could only describe itself in JSON would be half blind, so this
#: travels to the model as a real MCP image block.
IMAGE_KEY = "image_png_base64"


def tool_content(result: Any) -> List[dict]:
    """MCP content blocks for a bridge tool result.

    A result carrying a PNG becomes an image block (plus the rest of
    the result as text), so the model can actually look at the part.
    """
    if isinstance(result, dict) and result.get(IMAGE_KEY):
        data = str(result[IMAGE_KEY])
        rest = {k: v for k, v in result.items() if k != IMAGE_KEY}
        blocks: List[dict] = [{"type": "image", "data": data,
                               "mimeType": "image/png"}]
        if rest:
            blocks.append({"type": "text",
                           "text": json.dumps(rest, indent=2,
                                              default=str)})
        return blocks
    return [{"type": "text",
             "text": json.dumps(result, indent=2, default=str)}]


def valid_png_b64(data: str) -> bool:
    """True when *data* decodes to something with a PNG signature."""
    try:
        raw = base64.b64decode(data, validate=True)
    except Exception:
        return False
    return raw[:8] == b"\x89PNG\r\n\x1a\n"


# ── MCP server ─────────────────────────────────────────────────────

def _log(msg: str):
    """Diagnostics go to stderr — stdout carries the protocol."""
    sys.stderr.write(f"[khervemol-mcp] {msg}\n")
    sys.stderr.flush()


class McpServer:
    """Minimal, dependency-free MCP server over stdio."""

    def __init__(self, bridge: BridgeClient):
        self._bridge = bridge
        self._tools_cache: Optional[List[dict]] = None

    # ── Dispatch ────────────────────────────────────────────────

    def handle(self, msg: dict) -> Optional[dict]:
        """Handle one JSON-RPC message; None means 'no reply'."""
        method = msg.get("method")
        msg_id = msg.get("id")
        if method is None:                    # a response — ignore
            return None
        try:
            if method == "initialize":
                result = self._initialize(msg.get("params") or {})
            elif method in ("notifications/initialized",
                            "notifications/cancelled",
                            "initialized"):
                return None                   # notifications: no reply
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": self._list_tools()}
            elif method == "tools/call":
                result = self._call_tool(msg.get("params") or {})
            elif method in ("resources/list", "resources/templates/list"):
                # Declared empty rather than unsupported so hosts that
                # probe every capability do not surface an error.
                key = ("resourceTemplates"
                       if method.endswith("templates/list")
                       else "resources")
                result = {key: []}
            elif method == "prompts/list":
                result = {"prompts": []}
            else:
                if msg_id is None:
                    return None
                return _error(msg_id, -32601, f"Unknown method: {method}")
        except BridgeError as exc:
            if msg_id is None:
                return None
            return _error(msg_id, -32000, str(exc))
        except Exception as exc:              # never take the loop down
            if msg_id is None:
                return None
            return _error(msg_id, -32603, f"Internal error: {exc}")
        if msg_id is None:
            return None
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    # ── Methods ─────────────────────────────────────────────────

    def _initialize(self, params: dict) -> dict:
        asked = params.get("protocolVersion")
        version = (asked if asked in SUPPORTED_PROTOCOLS
                   else LATEST_PROTOCOL)
        # Best-effort: the app may not be up yet, and initialize must
        # never fail for that reason.
        app_version = "unknown"
        try:
            status = self._bridge.request("get_status")
            app_version = str((status or {}).get("version", "unknown"))
        except Exception:
            pass
        return {
            "protocolVersion": version,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {},
                "prompts": {},
            },
            "serverInfo": {
                "name": SERVER_NAME,
                "title": "KherveMol",
                "version": app_version,
            },
            "instructions": _INSTRUCTIONS,
        }

    def _list_tools(self) -> List[dict]:
        if self._tools_cache is None:
            tools = self._bridge.request("list_tools") or []
            self._tools_cache = [
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "inputSchema": t.get(
                        "input_schema", {"type": "object",
                                         "properties": {}}),
                }
                for t in tools
            ]
        return self._tools_cache

    def _call_tool(self, params: dict) -> dict:
        name = params.get("name")
        if not name:
            raise BridgeError("tools/call requires a tool name.")
        args = params.get("arguments") or {}
        result = self._bridge.request(
            "call_tool", {"name": name, "input": args})
        is_error = isinstance(result, dict) and "error" in result
        return {"content": tool_content(result), "isError": bool(is_error)}


def _error(msg_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id,
            "error": {"code": code, "message": message}}


# ── Entry point ────────────────────────────────────────────────────

def serve(endpoint_file: Optional[str] = None) -> int:
    """Run the stdio loop until stdin closes."""
    bridge = BridgeClient(endpoint_file)
    server = McpServer(bridge)
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    _log(f"listening on stdio; endpoint="
         f"{endpoint_file or endpoint_path()}")
    while True:
        line = stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line.decode("utf-8"))
        except Exception as exc:
            _log(f"bad JSON on stdin: {exc}")
            continue
        # A host may batch messages into a JSON array.
        batch = msg if isinstance(msg, list) else [msg]
        replies = [r for r in (server.handle(m) for m in batch)
                   if r is not None]
        for reply in replies:
            stdout.write((json.dumps(reply) + "\n").encode("utf-8"))
        if replies:
            stdout.flush()
    bridge.close()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    endpoint_file = None
    if "--endpoint" in args:
        i = args.index("--endpoint")
        if i + 1 < len(args):
            endpoint_file = args[i + 1]
    return serve(endpoint_file)


if __name__ == "__main__":
    sys.exit(main())
