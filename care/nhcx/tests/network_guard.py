"""L7.1 network guard for the NHCX tests.

Every NHCX test must run against fakes: no call may reach NHCX, the registry,
ABDM or a payer service. Installed when ``care.nhcx.tests`` is imported, the
guard wraps ``socket.getaddrinfo`` and ``socket.socket.connect``/``connect_ex``
and refuses any destination that is not loopback, a Unix socket, or a host of
the test infrastructure itself (the database, cache and broker named in
settings, and their resolved addresses). It only acts when a frame of the calling stack belongs to a file
under ``care/nhcx/tests``, so the rest of the CARE suite is unaffected.

``NetworkBlockedError`` derives from ``BaseException`` so a broad ``except
Exception`` in requests or the gateway cannot swallow it; the test errors.
"""

from __future__ import annotations

import ipaddress
import socket
import sys
from pathlib import Path
from urllib.parse import urlsplit

TESTS_DIR = str(Path(__file__).resolve().parent) + "/"
LOOPBACK_NAMES = {"localhost", "localhost.localdomain", "ip6-localhost", ""}

_installed = False
_original = {}
_infra_hosts: set[str] | None = None


class NetworkBlockedError(BaseException):
    """A care.nhcx test tried to reach a non-loopback host."""


def _host_of(url) -> str:
    if not url:
        return ""
    text = str(url)
    if "://" not in text:
        text = "//" + text
    try:
        return (urlsplit(text).hostname or "").lower()
    except ValueError:
        return ""


def infra_hosts() -> set[str]:
    """Hosts of the services the test run itself needs (db, cache, broker)."""
    global _infra_hosts  # noqa: PLW0603
    if _infra_hosts is not None:
        return _infra_hosts
    hosts: set[str] = set()
    try:
        from django.conf import settings

        for db in getattr(settings, "DATABASES", {}).values():
            if db.get("HOST"):
                hosts.add(str(db["HOST"]).lower())
        for cache in getattr(settings, "CACHES", {}).values():
            loc = cache.get("LOCATION")
            for item in loc if isinstance(loc, list | tuple) else [loc]:
                if host := _host_of(item):
                    hosts.add(host)
        for name in ("CELERY_BROKER_URL", "CELERY_RESULT_BACKEND", "REDIS_URL"):
            if host := _host_of(getattr(settings, name, "")):
                hosts.add(host)
    except Exception:
        return hosts
    resolve = _original.get("getaddrinfo", socket.getaddrinfo)
    for host in list(hosts):
        try:
            hosts.update(str(info[4][0]).lower() for info in resolve(host, None))
        except OSError:
            continue
    _infra_hosts = hosts
    return hosts


def _is_loopback(host) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "ignore")
    name = str(host).strip("[]").lower()
    if name in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(name.split("%")[0]).is_loopback
    except ValueError:
        return False


def allowed(host) -> bool:
    if _is_loopback(host):
        return True
    name = (host.decode() if isinstance(host, bytes) else str(host)).lower()
    return name in infra_hosts()


def _from_nhcx_test() -> bool:
    frame = sys._getframe(2)  # noqa: SLF001
    while frame is not None:
        if frame.f_code.co_filename.startswith(TESTS_DIR):
            return True
        frame = frame.f_back
    return False


def _refuse(host, port):
    msg = f"care.nhcx tests may not reach {host}:{port}; use a fake transport"
    raise NetworkBlockedError(msg)


def _guarded_getaddrinfo(host, port, *args, **kwargs):
    if not allowed(host) and _from_nhcx_test():
        _refuse(host, port)
    return _original["getaddrinfo"](host, port, *args, **kwargs)


def _target(sock, address):
    if sock.family == getattr(socket, "AF_UNIX", None):
        return None, None
    if isinstance(address, tuple) and address:
        return address[0], address[1] if len(address) > 1 else None
    return None, None


def _guarded_connect(self, address):
    host, port = _target(self, address)
    if not allowed(host) and _from_nhcx_test():
        _refuse(host, port)
    return _original["connect"](self, address)


def _guarded_connect_ex(self, address):
    host, port = _target(self, address)
    if not allowed(host) and _from_nhcx_test():
        _refuse(host, port)
    return _original["connect_ex"](self, address)


def install() -> None:
    global _installed  # noqa: PLW0603
    if _installed:
        return
    _original["getaddrinfo"] = socket.getaddrinfo
    _original["connect"] = socket.socket.connect
    _original["connect_ex"] = socket.socket.connect_ex
    socket.getaddrinfo = _guarded_getaddrinfo
    socket.socket.connect = _guarded_connect
    socket.socket.connect_ex = _guarded_connect_ex
    _installed = True


def installed() -> bool:
    return _installed
