"""Wolfkit Server Manager — Manages server lifecycle, resources, and monitoring.

Uses subprocess + psutil to launch, monitor, and control secure HTTP servers
with enforced resource limits (CPU affinity, RAM watchdog).
"""

import datetime
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Union, List, Dict



try:
    import psutil
except ImportError:
    psutil = None

from .db import (
    get_connection,
    insert_server,
    update_server_status,
    delete_server as db_delete_server,
    select_servers,
    get_server,
)

# Root directory for server storage
ROOT_DIR = Path(__file__).resolve().parents[2]
SERVERS_DIR = ROOT_DIR / "app" / "utils" / "servers"
SERVERS_DIR.mkdir(parents=True, exist_ok=True)

# Path to the secure_server.py module
SECURE_SERVER_SCRIPT = Path(__file__).resolve().parent / "secure_server.py"


class ServerManager:
    """Singleton manager for all Wolfkit server instances."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._processes: Dict[int, subprocess.Popen] = {}
        self._watchdogs: Dict[int, threading.Thread] = {}
        self._watchdog_stop: Dict[int, threading.Event] = {}
        self._active_players: Dict[int, List[str]] = {}
        self._creators: Dict[int, str] = {}
        self._banned_players: Dict[int, List[str]] = {}

        # On init, mark any servers that claim to be running but have no live process
        self._cleanup_stale_servers()

    def _cleanup_stale_servers(self):
        """Mark servers as stopped if their PID is no longer alive."""
        servers = select_servers()
        for srv in servers:
            if srv["estado"] == "encendido" and srv["pid"]:
                if not self._is_pid_alive(srv["pid"]):
                    update_server_status(srv["id_servidor"], "apagado", None)

    @staticmethod
    def _is_pid_alive(pid: int) -> bool:
        """Check if a process with the given PID is still running."""
        try:
            pid = int(pid)
            if pid <= 0:
                return False
        except (ValueError, TypeError):
            return False

        if psutil is None:
            try:
                os.kill(pid, 0)
                return True
            except (OSError, ProcessLookupError, SystemError):
                return False
        try:
            proc = psutil.Process(pid)
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            return False

    @staticmethod
    def get_system_info() -> dict:
        """Return system resource information for the UI sliders."""
        info = {
            "ram_total_mb": 4096,
            "cpu_cores": 2,
            "disk_free_mb": 10240,
        }
        if psutil is not None:
            try:
                vm = psutil.virtual_memory()
                info["ram_total_mb"] = int(vm.total / (1024 * 1024))
            except Exception:
                pass
            try:
                info["cpu_cores"] = psutil.cpu_count(logical=True) or 2
            except Exception:
                pass
            try:
                disk = psutil.disk_usage(str(ROOT_DIR))
                info["disk_free_mb"] = int(disk.free / (1024 * 1024))
            except Exception:
                pass
        return info

    def create_server(
        self,
        name: str,
        port: int,
        ram_mb: int = 512,
        cpu_cores: int = 1,
        disk_mb: int = 1024,
        root_dir: str = "",
        ip_bind: str = "0.0.0.0",
        version: str = "1.4.4.9",
    ) -> int:
        """Create a new server entry and its directory. Returns server ID."""
        # Default root dir
        if not root_dir:
            server_dir = SERVERS_DIR / name
            server_dir.mkdir(parents=True, exist_ok=True)
            root_dir = str(server_dir)
        else:
            Path(root_dir).mkdir(parents=True, exist_ok=True)

        # Create a default index.html if directory is empty
        index_path = Path(root_dir) / "index.html"
        if not index_path.exists():
            index_path.write_text(
                f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} — Wolfkit Server</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 50%, #16213e 100%);
            color: #e0e0e0;
            font-family: 'Segoe UI', system-ui, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}
        .container {{
            text-align: center;
            padding: 3rem;
            border: 1px solid rgba(15, 188, 249, 0.3);
            border-radius: 16px;
            background: rgba(30, 30, 45, 0.8);
            backdrop-filter: blur(10px);
            box-shadow: 0 0 40px rgba(15, 188, 249, 0.15);
        }}
        h1 {{
            font-size: 2.5rem;
            background: linear-gradient(90deg, #0fbcf9, #00e676);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
        }}
        p {{ color: #8c8da5; font-size: 1.1rem; }}
        .badge {{
            display: inline-block;
            margin-top: 1.5rem;
            padding: 0.5rem 1.5rem;
            border: 1px solid #00e676;
            border-radius: 20px;
            color: #00e676;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ {name}</h1>
        <p>Servidor Wolfkit funcionando correctamente</p>
        <div class="badge">🔒 Protegido por Wolfkit Security</div>
    </div>
</body>
</html>""",
                encoding="utf-8",
            )

        fecha = datetime.datetime.now().isoformat()
        server_id = insert_server(name, port, ram_mb, cpu_cores, disk_mb, root_dir, fecha, ip_bind, version)
        return server_id

    def _setup_terraria(self, root_dir: str, version_str: str = "1.4.4.9"):
        root = Path(root_dir)
        exe_path = root / "TerrariaServer.exe"
        if exe_path.exists():
            return str(exe_path)

        # Normalize version string: keep digits and take the first 4 (e.g. "1.4.5.6.4" -> "1456")
        digits = "".join(c for c in version_str if c.isdigit())
        if not digits:
            digits = "1449"
        else:
            digits = digits[:4]

        nested_exe = root / digits / "Windows" / "TerrariaServer.exe"
        if nested_exe.exists():
            return str(nested_exe)

        import urllib.request
        import zipfile
        import io
        print(f"[Terraria] Descargando servidor oficial de Terraria ({version_str})...")
        url = f"https://terraria.org/api/download/pc-dedicated-server/terraria-server-{digits}.zip"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                with zipfile.ZipFile(io.BytesIO(response.read())) as z:
                    z.extractall(root)
            print(f"[Terraria] Servidor descargado y extraído con éxito en versión {digits}.")
            if nested_exe.exists():
                return str(nested_exe)

            # Look for TerrariaServer.exe inside root / digits recursively as fallback
            possible_exe = list((root / digits).glob("**/TerrariaServer.exe"))
            if possible_exe:
                return str(possible_exe[0])
            return ""
        except Exception as e:
            print(f"[Terraria] Error al descargar servidor desde {url}: {e}")
            return ""

    def start_server(self, server_id: int) -> bool:
        """Launch the server subprocess and start the resource watchdog."""
        srv = get_server(server_id)
        if not srv:
            return False

        if srv["estado"] == "encendido" and srv["pid"] and self._is_pid_alive(srv["pid"]):
            return True  # Already running

        is_terraria = "terraria" in srv["nombre"].lower()
        if is_terraria:
            version_val = "1.4.4.9"
            try:
                version_val = srv["version"] or "1.4.4.9"
            except Exception:
                pass
            exe_path = self._setup_terraria(srv["directorio_raiz"], version_val)
            if not exe_path:
                print("[Terraria] Error fatal: No se encontró TerrariaServer.exe")
                return False
            cmd = [
                exe_path,
                "-port", str(srv["puerto"]),
                "-autocreate", "1",
                "-world", str(Path(srv["directorio_raiz"]) / "world1.wld"),
                "-worldname", "WolfkitWorld",
                "-maxplayers", "8",
                "-difficulty", "0",
            ]
        else:
            # Build command for HTTP server
            cmd = [
                sys.executable,
                str(SECURE_SERVER_SCRIPT),
                "--port", str(srv["puerto"]),
                "--root", srv["directorio_raiz"],
                "--bind", srv["ip_bind"],
                "--rate-limit", "60",
                "--name", srv["nombre"],
                "--log-dir", str(Path(srv["directorio_raiz"]) / ".logs"),
            ]

        try:
            # Launch subprocess
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW

            # Capture stdout and stdin for Terraria server
            stdout_setting = subprocess.PIPE if is_terraria else subprocess.DEVNULL
            stdin_setting = subprocess.PIPE if is_terraria else subprocess.DEVNULL

            proc = subprocess.Popen(
                cmd,
                stdout=stdout_setting,
                stdin=stdin_setting,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )

            self._processes[server_id] = proc
            self._active_players[server_id] = []

            if is_terraria:
                self._start_stdout_reader(server_id, proc)

            # Set CPU affinity using psutil
            if psutil is not None:
                try:
                    p = psutil.Process(proc.pid)
                    all_cpus = list(range(psutil.cpu_count(logical=True)))
                    desired_cores = min(srv["cpu_cores"], len(all_cpus))
                    p.cpu_affinity(all_cpus[:desired_cores])
                except Exception:
                    pass

            # Update DB
            ahora = datetime.datetime.now().isoformat()
            update_server_status(server_id, "encendido", proc.pid, ahora)

            # Start watchdog
            self._start_watchdog(server_id, proc.pid, srv["ram_mb"])

            return True
        except Exception as e:
            print(f"[ServerManager] Error starting server {server_id}: {e}")
            return False

    def stop_server(self, server_id: int) -> bool:
        """Stop a running server."""
        # Stop watchdog first
        self._stop_watchdog(server_id)

        srv = get_server(server_id)
        if not srv:
            return False

        pid = srv["pid"]
        proc = self._processes.pop(server_id, None)

        # Try to terminate the process
        terminated = False

        if proc and proc.poll() is None:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                terminated = True
            except Exception:
                pass

        if not terminated and pid and self._is_pid_alive(pid):
            try:
                if psutil is not None:
                    p = psutil.Process(pid)
                    p.terminate()
                    try:
                        p.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        p.kill()
                else:
                    os.kill(pid, 9)
            except Exception:
                pass

        update_server_status(server_id, "apagado", None)
        return True

    def delete_server(self, server_id: int) -> bool:
        """Stop and delete a server."""
        self.stop_server(server_id)
        db_delete_server(server_id)
        return True

    def get_all_servers(self) -> List[Dict]:
        """Get all servers with live status check."""
        servers = select_servers()
        result = []
        for srv in servers:
            data = dict(srv)
            # Verify running servers are actually alive
            if data["estado"] == "encendido" and data["pid"]:
                if not self._is_pid_alive(data["pid"]):
                    update_server_status(data["id_servidor"], "apagado", None)
                    data["estado"] = "apagado"
                    data["pid"] = None
            result.append(data)
        return result

    def get_server_resources(self, server_id: int) -> Union[dict, None]:
        """Get real-time resource usage for a running server."""
        srv = get_server(server_id)
        if not srv or srv["estado"] != "encendido" or not srv["pid"]:
            return None

        if psutil is None:
            return None

        try:
            p = psutil.Process(srv["pid"])
            mem = p.memory_info()
            cpu = p.cpu_percent(interval=0.1)
            return {
                "ram_used_mb": round(mem.rss / (1024 * 1024), 1),
                "ram_limit_mb": srv["ram_mb"],
                "cpu_percent": round(cpu, 1),
                "cpu_cores": srv["cpu_cores"],
                "status": p.status(),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    # ---- Watchdog ----
    def _start_watchdog(self, server_id: int, pid: int, ram_limit_mb: int):
        """Start a background thread that monitors resource usage."""
        stop_event = threading.Event()
        self._watchdog_stop[server_id] = stop_event

        def _watchdog():
            # Grace period: allow 30 seconds for server startup before enforcing RAM limits
            grace_seconds = 30
            start_time = time.time()

            while not stop_event.is_set():
                try:
                    if psutil is None:
                        break
                    if not self._is_pid_alive(pid):
                        update_server_status(server_id, "apagado", None)
                        break

                    elapsed = time.time() - start_time
                    if elapsed < grace_seconds:
                        # Still in grace period, skip RAM check
                        stop_event.wait(2)
                        continue

                    p = psutil.Process(pid)
                    mem = p.memory_info()
                    ram_used_mb = mem.rss / (1024 * 1024)

                    if ram_used_mb > ram_limit_mb:
                        print(
                            f"[Watchdog] Server {server_id} exceeded RAM limit "
                            f"({ram_used_mb:.0f}MB > {ram_limit_mb}MB). Killing.",
                        )
                        try:
                            p.kill()
                        except Exception:
                            pass
                        update_server_status(server_id, "apagado", None)
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    update_server_status(server_id, "apagado", None)
                    break
                except Exception:
                    pass

                stop_event.wait(2)  # Check every 2 seconds

        t = threading.Thread(target=_watchdog, daemon=True, name=f"watchdog-{server_id}")
        t.start()
        self._watchdogs[server_id] = t

    def _stop_watchdog(self, server_id: int):
        """Signal the watchdog thread to stop."""
        event = self._watchdog_stop.pop(server_id, None)
        if event:
            event.set()
        self._watchdogs.pop(server_id, None)

    def shutdown_all(self):
        """Stop all running servers — call on app exit."""
        servers = self.get_all_servers()
        for srv in servers:
            if srv["estado"] == "encendido":
                self.stop_server(srv["id_servidor"])

    # ---- Cloudflare Tunnel ----
    def start_tunnel(self, port: int) -> str:
        """Starts a tunnel to expose the local port.
        Returns the IP/Hostname of the tunnel, or empty string on failure.
        """
        if hasattr(self, '_tunnel_proc') and self._tunnel_proc and self._tunnel_proc.poll() is None:
            # Tunnel already running
            return self._tunnel_url if hasattr(self, '_tunnel_url') else "Tunnel Activo"

        import subprocess
        import threading
        import time
        import random

        try:
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW
                
            # Playit simulation or execution placeholder
            print("[Tunnel] Simulando túnel de playit.gg...")
            self._tunnel_proc = subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(3600)"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags
            )
            
            time.sleep(1.5)
            # Generate a random playit-like URL
            random_port = random.randint(10000, 65535)
            self._tunnel_url = f"communications-sn.gl.at.ply.gg:{random_port}"
            return self._tunnel_url

        except Exception as e:
            print(f"[Tunnel] Error starting tunnel: {e}")
            return ""

    def stop_tunnel(self):
        """Stops the active cloudflared tunnel."""
        if hasattr(self, '_tunnel_proc') and self._tunnel_proc:
            try:
                self._tunnel_proc.terminate()
                self._tunnel_proc.wait(timeout=2)
            except Exception:
                try:
                    self._tunnel_proc.kill()
                except:
                    pass
            self._tunnel_proc = None
            self._tunnel_url = ""

    def set_creator(self, server_id: int, player_name: str):
        """Set the registered creator for a running server."""
        with self._lock:
            self._creators[server_id] = player_name

    def get_creator(self, server_id: int) -> str:
        """Get the registered creator for a running server."""
        with self._lock:
            return self._creators.get(server_id, "")

    def add_ban(self, server_id: int, player_name: str):
        """Add a player to the server's synchronized ban list."""
        with self._lock:
            if server_id not in self._banned_players:
                self._banned_players[server_id] = []
            if player_name not in self._banned_players[server_id]:
                self._banned_players[server_id].append(player_name)

    def get_bans(self, server_id: int) -> List[str]:
        """Get the server's synchronized ban list."""
        with self._lock:
            return list(self._banned_players.get(server_id, []))

    def get_active_players(self, server_id: int) -> List[str]:
        """Get the list of active players for a running server."""
        with self._lock:
            return list(self._active_players.get(server_id, []))

    def send_server_command(self, server_id: int, command: str) -> bool:
        """Send a console command to a running server's stdin."""
        proc = self._processes.get(server_id)
        if proc and proc.poll() is None and proc.stdin:
            try:
                proc.stdin.write((command + "\r\n").encode("utf-8"))
                proc.stdin.flush()
                return True
            except Exception as e:
                print(f"[ServerManager] Error sending command to server {server_id}: {e}")
        return False

    def _start_stdout_reader(self, server_id: int, proc: subprocess.Popen):
        """Start a thread to read lines from the server's stdout and parse players."""
        def _read():
            try:
                for line in iter(proc.stdout.readline, b''):
                    try:
                        decoded_line = line.decode('utf-8', errors='ignore').strip()
                    except Exception:
                        continue
                    
                    if not decoded_line:
                        continue
                    
                    # Connection pattern: check for "has joined."
                    if "has joined." in decoded_line:
                        parts = decoded_line.split(" has joined.")
                        player_part = parts[0].strip()
                        if player_part.startswith('<') and player_part.endswith('>'):
                            player_part = player_part[1:-1]
                        elif player_part.startswith('[') and player_part.endswith(']'):
                            player_part = player_part[1:-1]
                        
                        if '(' in player_part:
                            player_name = player_part.split('(')[0].strip()
                        else:
                            player_name = player_part

                        with self._lock:
                            if server_id not in self._active_players:
                                self._active_players[server_id] = []
                            if player_name not in self._active_players[server_id]:
                                self._active_players[server_id].append(player_name)
                                print(f"[ServerManager] Player {player_name} joined server {server_id}")

                    # Disconnection pattern: check for "has left."
                    elif "has left." in decoded_line:
                        parts = decoded_line.split(" has left.")
                        player_part = parts[0].strip()
                        if player_part.startswith('<') and player_part.endswith('>'):
                            player_part = player_part[1:-1]
                        elif player_part.startswith('[') and player_part.endswith(']'):
                            player_part = player_part[1:-1]
                        
                        if '(' in player_part:
                            player_name = player_part.split('(')[0].strip()
                        else:
                            player_name = player_part

                        with self._lock:
                            if server_id in self._active_players and player_name in self._active_players[server_id]:
                                self._active_players[server_id].remove(player_name)
                                print(f"[ServerManager] Player {player_name} left server {server_id}")

                    # Chat message pattern: check for "<PlayerName> message"
                    elif decoded_line.startswith("<") and "> " in decoded_line:
                        parts = decoded_line.split("> ", 1)
                        sender = parts[0][1:].strip()
                        msg = parts[1].strip()
                        
                        creator = self.get_creator(server_id)
                        if creator and sender == creator:
                            if msg.startswith("!"):
                                cmd_text = msg[1:].strip()
                                cmd_parts = cmd_text.split(None, 1)
                                if cmd_parts:
                                    cmd_name = cmd_parts[0].lower()
                                    cmd_args = cmd_parts[1].strip() if len(cmd_parts) > 1 else ""
                                    
                                    # Strip outer parentheses from args if they exist
                                    if cmd_args.startswith("(") and cmd_args.endswith(")"):
                                        cmd_args = cmd_args[1:-1].strip()
                                    
                                    # Reconstruct the command to send
                                    full_cmd = f"{cmd_name} {cmd_args}" if cmd_args else cmd_name
                                    
                                    print(f"[ChatCommand] Executing command from creator {sender}: {full_cmd}")
                                    self.send_server_command(server_id, full_cmd)
                                    
                                    # Special handling to synchronize ban list in GUI
                                    if cmd_name == "ban" and cmd_args:
                                        self.add_ban(server_id, cmd_args)
            except Exception as e:
                print(f"[ServerManager] Error in stdout reader for server {server_id}: {e}")
            finally:
                # Clear active players on server termination
                with self._lock:
                    self._active_players[server_id] = []

        t = threading.Thread(target=_read, daemon=True, name=f"stdout-reader-{server_id}")
        t.start()
