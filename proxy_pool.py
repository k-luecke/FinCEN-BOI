#!/usr/bin/env python3
"""
Dynamic free SOCKS5 proxy pool, built fresh per run.

Free proxy lists churn (most entries are dead within hours), so a
committed static list goes stale fast. Instead this pulls candidates
from a few public aggregators at run time, validates each candidate
against a neutral endpoint before it's ever pointed at a real target
(never burn a request against the target site probing dead proxies),
and hands out validated proxies round-robin with dead ones evicted on
failure.

Uses PySocks directly against urllib rather than `requests`: this
repo's root-level queue.py shadows the stdlib `queue` module for any
code run from the repo root, which breaks urllib3 (a requests
dependency) at import time.
"""

from __future__ import annotations

import random
import re
import socket
import urllib.request
from dataclasses import dataclass, field

import socks  # PySocks

IP_PORT_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3}):(\d{2,5})\b")

# Public free-proxy-list aggregators, plain "ip:port" per line (or
# embedded in a page we regex over). Best-effort and unauthenticated —
# expect most entries to be dead or already blocklisted.
CANDIDATE_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all",
]

# Cheap, neutral liveness check — deliberately never sec.gov, so a
# dead proxy never costs the target site a request.
VALIDATION_URL = "https://api.ipify.org"

_real_socket = socket.socket


def _install_proxy(host: str, port: int) -> None:
    socks.set_default_proxy(socks.SOCKS5, host, port, rdns=True)
    socket.socket = socks.socksocket


def _clear_proxy() -> None:
    socket.socket = _real_socket


def fetch_candidates(timeout: float = 10.0) -> list[str]:
    seen: set[str] = set()
    for url in CANDIDATE_SOURCES:
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(request, timeout=timeout) as resp:
                body = resp.read(1_000_000).decode("utf-8", "ignore")
            for host, port in IP_PORT_RE.findall(body):
                seen.add(f"{host}:{port}")
        except Exception:
            continue
    return list(seen)


def validate(proxy: str, timeout: float = 5.0) -> bool:
    host, _, port = proxy.partition(":")
    try:
        _install_proxy(host, int(port))
        request = urllib.request.Request(
            VALIDATION_URL, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False
    finally:
        _clear_proxy()


@dataclass
class ProxyPool:
    validated: list[str] = field(default_factory=list)
    _index: int = 0

    @classmethod
    def build(
        cls,
        want: int = 8,
        max_candidates: int = 60,
        timeout: float = 5.0,
    ) -> "ProxyPool":
        candidates = fetch_candidates()
        random.shuffle(candidates)

        validated: list[str] = []
        for proxy in candidates[:max_candidates]:
            if validate(proxy, timeout=timeout):
                validated.append(proxy)
                if len(validated) >= want:
                    break

        return cls(validated=validated)

    def __len__(self) -> int:
        return len(self.validated)

    def next(self) -> str | None:
        if not self.validated:
            return None
        proxy = self.validated[self._index % len(self.validated)]
        self._index += 1
        return proxy

    def mark_dead(self, proxy: str) -> None:
        if proxy in self.validated:
            self.validated.remove(proxy)


def install(proxy: str) -> None:
    host, _, port = proxy.partition(":")
    _install_proxy(host, int(port))


def clear() -> None:
    _clear_proxy()
