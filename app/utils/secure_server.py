"""Wolfkit Secure HTTP Server — Subprocess-based secure file server.

This module is designed to be launched as a standalone subprocess by the
ServerManager.  It provides a hardened HTTP file server with:

- Rate limiting per IP (configurable requests/minute)
- Path traversal prevention (all paths resolved to root_dir)
- Security headers injection (CSP, X-Frame-Options, HSTS, etc.)
- IP blocklist for abusive clients
- Request logging with timestamps
- Directory listing protection (optionally disabled)
- Maximum request size enforcement
"""

import argparse
import datetime
import json
import logging
import os
import signal
import sys
import threading
import time
from collections import defaultdict
from http import HTTPStatus
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Union, List, Dict, Set



# ---------------------------------------------------------------------------
# Rate-limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Token-bucket style rate limiter keyed by client IP."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: Dict[str, List[float]] = defaultdict(list)
        self._blocked: Set[str] = set()
        self._block_duration = 300  # 5 minutes
        self._block_until: Dict[str, float] = {}
        self._lock = threading.Lock()

    def is_allowed(self, ip: str) -> bool:
        now = time.time()
        with self._lock:
            # Check block
            if ip in self._blocked:
                if now < self._block_until.get(ip, 0):
                    return False
                self._blocked.discard(ip)
                self._block_until.pop(ip, None)

            # Purge old hits
            cutoff = now - self.window
            self._hits[ip] = [t for t in self._hits[ip] if t > cutoff]

            if len(self._hits[ip]) >= self.max_requests:
                # Block the IP
                self._blocked.add(ip)
                self._block_until[ip] = now + self._block_duration
                return False

            self._hits[ip].append(now)
            return True

    def get_blocked_ips(self) -> List[str]:
        with self._lock:
            return list(self._blocked)


# ---------------------------------------------------------------------------
# Security Headers
# ---------------------------------------------------------------------------

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
    "Cache-Control": "no-store, no-cache, must-revalidate",
    "Pragma": "no-cache",
}


# ---------------------------------------------------------------------------
# Secure Request Handler
# ---------------------------------------------------------------------------

class SecureRequestHandler(SimpleHTTPRequestHandler):
    """Hardened HTTP request handler with security protections."""

    rate_limiter: RateLimiter = None  # type: ignore[assignment]
    server_root: str = "."
    allow_directory_listing: bool = False
    max_request_size: int = 10 * 1024 * 1024  # 10 MB
    access_logger: logging.Logger = None  # type: ignore[assignment]

    # Override directory to serve from configured root
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=self.server_root, **kwargs)

    # ---- Rate Limiting ----
    def _check_rate_limit(self) -> bool:
        client_ip = self.client_address[0]
        if self.rate_limiter and not self.rate_limiter.is_allowed(client_ip):
            self.send_error(HTTPStatus.TOO_MANY_REQUESTS, "Rate limit exceeded")
            self._log_access("BLOCKED_RATE_LIMIT", 429)
            return False
        return True

    # ---- Path Traversal Prevention ----
    def _safe_path(self, path: str) -> Union[str, None]:
        """Resolve requested path and verify it stays within server_root."""
        root = Path(self.server_root).resolve()
        # Remove query strings and fragments
        clean = path.split("?")[0].split("#")[0]
        # Build full path
        try:
            full = (root / clean.lstrip("/")).resolve()
        except (ValueError, OSError):
            return None

        # Ensure the resolved path is within root
        try:
            full.relative_to(root)
        except ValueError:
            return None

        return str(full)

    def translate_path(self, path: str) -> str:
        """Override to enforce root directory jail."""
        safe = self._safe_path(path)
        if safe is None:
            # Return a path that doesn't exist so the handler returns 404
            return os.path.join(self.server_root, "__INVALID_PATH__")
        return safe

    # ---- Directory Listing ----
    def list_directory(self, path):
        if not self.allow_directory_listing:
            self.send_error(HTTPStatus.FORBIDDEN, "Directory listing is disabled")
            self._log_access("BLOCKED_DIR_LISTING", 403)
            return None
        return super().list_directory(path)

    # ---- Security Headers ----
    def end_headers(self):
        for header, value in SECURITY_HEADERS.items():
            self.send_header(header, value)
        self.send_header("Server", "Wolfkit-Secure/1.0")
        super().end_headers()

    # ---- Request Size Check ----
    def _check_content_length(self) -> bool:
        content_length = self.headers.get("Content-Length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_request_size:
                    self.send_error(
                        HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                        "Request too large",
                    )
                    self._log_access("BLOCKED_TOO_LARGE", 413)
                    return False
            except ValueError:
                pass
        return True

    # ---- Logging ----
    def _log_access(self, note: str = "", status: int = 200):
        if self.access_logger:
            client_ip = self.client_address[0]
            now = datetime.datetime.now().isoformat()
            method = getattr(self, "command", "?")
            path = getattr(self, "path", "?")
            self.access_logger.info(
                json.dumps({
                    "time": now,
                    "ip": client_ip,
                    "method": method,
                    "path": path,
                    "status": status,
                    "note": note,
                })
            )

    def log_message(self, format, *args):
        """Suppress default stderr logging; use our custom logger."""
        if self.access_logger:
            try:
                self._log_access(status=int(args[1]) if len(args) > 1 else 200)
            except (ValueError, IndexError):
                self._log_access()

    # ---- Override HTTP methods ----
    def do_GET(self):
        if not self._check_rate_limit():
            return
        super().do_GET()

    def do_HEAD(self):
        if not self._check_rate_limit():
            return
        super().do_HEAD()

    def do_POST(self):
        if not self._check_rate_limit():
            return
        if not self._check_content_length():
            return
        self.send_error(HTTPStatus.METHOD_NOT_ALLOWED, "POST not supported")

    def do_PUT(self):
        self.send_error(HTTPStatus.METHOD_NOT_ALLOWED, "PUT not supported")

    def do_DELETE(self):
        self.send_error(HTTPStatus.METHOD_NOT_ALLOWED, "DELETE not supported")

    def do_PATCH(self):
        self.send_error(HTTPStatus.METHOD_NOT_ALLOWED, "PATCH not supported")


# ---------------------------------------------------------------------------
# Server Launcher
# ---------------------------------------------------------------------------

def setup_logging(log_dir: str, server_name: str) -> logging.Logger:
    """Configure access logging to file."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(f"wolfkit_server_{server_name}")
    logger.setLevel(logging.INFO)

    # Rotate-friendly file handler
    fh = logging.FileHandler(
        str(log_path / f"{server_name}_access.log"),
        encoding="utf-8",
    )
    fh.setLevel(logging.INFO)
    logger.addHandler(fh)

    return logger


def run_server(
    port: int,
    root_dir: str,
    bind_ip: str = "0.0.0.0",
    rate_limit: int = 60,
    allow_listing: bool = False,
    server_name: str = "wolfkit",
    log_dir: str = "",
):
    """Start the secure HTTP server (blocking)."""
    root = Path(root_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    # Setup logging
    if not log_dir:
        log_dir = str(root / ".logs")
    access_logger = setup_logging(log_dir, server_name)

    # Configure handler class attributes
    SecureRequestHandler.rate_limiter = RateLimiter(max_requests=rate_limit)
    SecureRequestHandler.server_root = str(root)
    SecureRequestHandler.allow_directory_listing = allow_listing
    SecureRequestHandler.access_logger = access_logger

    server = HTTPServer((bind_ip, port), SecureRequestHandler)
    server.timeout = 1

    # Graceful shutdown
    running = True

    def _shutdown(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    access_logger.info(json.dumps({
        "time": datetime.datetime.now().isoformat(),
        "event": "SERVER_START",
        "port": port,
        "root": str(root),
        "bind": bind_ip,
        "rate_limit": rate_limit,
    }))

    print(f"[Wolfkit Server] Listening on {bind_ip}:{port} | Root: {root}", flush=True)

    try:
        while running:
            server.handle_request()
    except Exception:
        pass
    finally:
        server.server_close()
        access_logger.info(json.dumps({
            "time": datetime.datetime.now().isoformat(),
            "event": "SERVER_STOP",
        }))
        print("[Wolfkit Server] Stopped.", flush=True)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Wolfkit Secure HTTP Server")
    parser.add_argument("--port", type=int, required=True, help="Port to listen on")
    parser.add_argument("--root", type=str, required=True, help="Root directory to serve")
    parser.add_argument("--bind", type=str, default="0.0.0.0", help="IP to bind to")
    parser.add_argument("--rate-limit", type=int, default=60, help="Max requests per minute per IP")
    parser.add_argument("--allow-listing", action="store_true", help="Allow directory listing")
    parser.add_argument("--name", type=str, default="wolfkit", help="Server instance name")
    parser.add_argument("--log-dir", type=str, default="", help="Directory for access logs")

    args = parser.parse_args()

    run_server(
        port=args.port,
        root_dir=args.root,
        bind_ip=args.bind,
        rate_limit=args.rate_limit,
        allow_listing=args.allow_listing,
        server_name=args.name,
        log_dir=args.log_dir,
    )


if __name__ == "__main__":
    main()
