from __future__ import annotations

import argparse
import json
import math
import mimetypes
import os
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

import numpy as np

from .forum import COMMUNITIES, DECISION_BACKEND, Forum
from .narrator import TemplateNarrator, narrator_from_environment
from .store import SQLiteStore


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SITE_DIR = (
    PROJECT_ROOT / "site"
    if (PROJECT_ROOT / "site").is_dir()
    else Path.cwd() / "site"
)


def _clamp(value: str | None, default: int, low: int, high: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except ValueError:
        parsed = default
    return min(high, max(low, parsed))


class ColonyRuntime:
    """Owns the one authoritative forum, its lock, clock, and persistence."""

    def __init__(
        self,
        database: str | Path,
        *,
        seed: int = 100,
        interval_seconds: float = 60,
        bootstrap_cycles: int = 24,
        autostart: bool = True,
        narrator=None,
    ):
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self.store = SQLiteStore(database)
        self.lock = threading.RLock()
        self.interval_seconds = float(interval_seconds)
        self.started_at = time.time()
        self.last_tick_at: float | None = None
        self.next_tick_at: float | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        active_narrator = narrator or TemplateNarrator()
        self.forum = self.store.load(narrator=active_narrator)
        self.resumed = self.forum is not None
        if self.forum is None:
            # Bootstrap deterministically without making network calls or delaying
            # a first deployment. The configured narrator handles future cycles.
            self.forum = Forum(seed=seed, narrator=TemplateNarrator())
            for _ in range(max(0, bootstrap_cycles)):
                self.forum.step()
            self.forum.narrator = active_narrator
            self.store.save(self.forum)
        if autostart:
            self.start()

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive() and not self._stop.is_set())

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self.next_tick_at = time.time() + self.interval_seconds
        self._thread = threading.Thread(target=self._run, name="flreddit-colony", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.tick()
            self.next_tick_at = time.time() + self.interval_seconds

    def tick(self) -> list:
        with self.lock:
            events = self.forum.step()
            self.store.save(self.forum)
            self.last_tick_at = time.time()
            return events

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=2)
        with self.lock:
            self.store.save(self.forum)

    def state(self) -> dict:
        with self.lock:
            threads = self.forum.threads
            comments = sum(len(thread.comments) for thread in threads)
            upvotes = sum(max(0, thread.score - 1) for thread in threads)
            now = time.time()
            return {
                "mode": "authoritative_server",
                "shared": True,
                "persistent": True,
                "running": self.running,
                "resumed": self.resumed,
                "cycle": self.forum.cycle,
                "population": len(self.forum.profiles),
                "threads": len(threads),
                "comments": comments,
                "upvotes": upvotes,
                "evaluations": self.forum.evaluations,
                "action_counts": dict(self.forum.action_counts),
                "backend": DECISION_BACKEND,
                "words_by": self.forum.narrator.backend,
                "narrator": self.forum.narrator.status(),
                "tick_seconds": self.interval_seconds,
                "seconds_to_next_tick": (
                    max(0, round(self.next_tick_at - now, 1))
                    if self.running and self.next_tick_at is not None
                    else None
                ),
                "uptime_seconds": round(now - self.started_at, 1),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

    def feed(self, *, sort: str = "hot", community: str | None = None, limit: int = 30) -> list[dict]:
        with self.lock:
            candidates = [
                thread for thread in self.forum.threads
                if community is None or thread.community == community
            ]
            if sort == "new":
                candidates.sort(key=lambda thread: (-thread.cycle, -thread.id))
            elif sort == "top":
                candidates.sort(key=lambda thread: (-thread.score, -len(thread.comments), -thread.id))
            else:
                current_cycle = self.forum.cycle
                candidates.sort(
                    key=lambda thread: (
                        -((thread.score + len(thread.comments) * 1.6)
                          / math.pow(max(2, current_cycle - thread.cycle + 2), 0.34)),
                        -thread.id,
                    )
                )
            return [self._thread_public(thread) for thread in candidates[:limit]]

    def _thread_public(self, thread) -> dict:
        author = self.forum.profiles[thread.author].public()
        return {
            "id": thread.id,
            "author": author,
            "community": thread.community,
            "title": thread.title,
            "body": thread.body,
            "cycle": thread.cycle,
            "score": thread.score,
            "comment_count": len(thread.comments),
            "decision_by": thread.decision_by,
            "words_by": thread.words_by,
        }

    def thread(self, thread_id: int) -> dict | None:
        with self.lock:
            thread = next((item for item in self.forum.threads if item.id == thread_id), None)
            if thread is None:
                return None
            payload = self._thread_public(thread)
            payload["comments"] = [
                {
                    **comment,
                    "author_profile": self.forum.profiles[comment["author"]].public(),
                }
                for comment in thread.comments
            ]
            return payload

    def profiles(self, *, query: str = "", limit: int = 100) -> list[dict]:
        query = query.strip().lower()
        with self.lock:
            profiles = [profile.public() for profile in self.forum.profiles.values()]
            if query:
                profiles = [
                    profile for profile in profiles
                    if query in profile["handle"].lower()
                    or query in profile["display_name"].lower()
                    or query in profile["bio"].lower()
                ]
            profiles.sort(key=lambda profile: (-profile["karma"], profile["handle"]))
            return profiles[:limit]

    def profile(self, handle: str) -> dict | None:
        with self.lock:
            profile = self.forum.profiles.get(handle)
            if profile is None:
                return None
            payload = profile.public()
            payload["recent_threads"] = [
                self._thread_public(thread)
                for thread in reversed(self.forum.threads)
                if thread.author == handle
            ][:12]
            payload["recent_comments"] = [
                {
                    **comment,
                    "thread_id": thread.id,
                    "thread_title": thread.title,
                }
                for thread in reversed(self.forum.threads)
                for comment in reversed(thread.comments)
                if comment["author"] == handle
            ][:12]
            return payload

    def communities(self) -> list[dict]:
        with self.lock:
            result = []
            for community in COMMUNITIES:
                threads = [thread for thread in self.forum.threads if thread.community == community]
                result.append({
                    "name": community,
                    "threads": len(threads),
                    "comments": sum(len(thread.comments) for thread in threads),
                    "members": sum(
                        community in profile.subscriptions
                        for profile in self.forum.profiles.values()
                    ),
                })
            return result

    def activity(self) -> list[dict]:
        with self.lock:
            return [
                {
                    "handle": profile.handle,
                    "color": profile.color,
                    "drive": round(float(np.linalg.norm(profile.state) / math.sqrt(len(profile.state))), 5),
                    "mood": profile.mood,
                    "last_active_cycle": profile.last_active_cycle,
                }
                for profile in self.forum.profiles.values()
            ]

    def events(self, limit: int = 30) -> list[dict]:
        with self.lock:
            return [asdict(event) for event in reversed(self.forum.events[-limit:])]


class FlredditHandler(BaseHTTPRequestHandler):
    runtime: ColonyRuntime
    site_dir: Path
    server_version = "Flreddit/1.1"

    def do_HEAD(self) -> None:
        self._dispatch(send_body=False)

    def do_GET(self) -> None:
        self._dispatch(send_body=True)

    def do_POST(self) -> None:
        self._json({"error": "The public API is read-only."}, HTTPStatus.METHOD_NOT_ALLOWED)

    def _dispatch(self, *, send_body: bool) -> None:
        parsed = urlsplit(self.path)
        if parsed.path.startswith("/api/"):
            self._api(parsed.path, parse_qs(parsed.query), send_body=send_body)
            return
        self._static(parsed.path, send_body=send_body)

    def _api(self, path: str, query: dict[str, list[str]], *, send_body: bool) -> None:
        value = lambda name: query.get(name, [None])[0]
        if path == "/api/health":
            payload = {"ok": True, **self.runtime.state()}
        elif path == "/api/state":
            payload = self.runtime.state()
        elif path == "/api/feed":
            sort = value("sort") if value("sort") in {"hot", "new", "top"} else "hot"
            community = value("community")
            if community not in COMMUNITIES:
                community = None
            payload = {"threads": self.runtime.feed(
                sort=sort, community=community,
                limit=_clamp(value("limit"), 30, 1, 100),
            )}
        elif path == "/api/profiles":
            payload = {"profiles": self.runtime.profiles(
                query=value("query") or "",
                limit=_clamp(value("limit"), 100, 1, 100),
            )}
        elif path == "/api/communities":
            payload = {"communities": self.runtime.communities()}
        elif path == "/api/activity":
            payload = {"agents": self.runtime.activity()}
        elif path == "/api/events":
            payload = {"events": self.runtime.events(_clamp(value("limit"), 30, 1, 100))}
        elif path.startswith("/api/threads/"):
            try:
                thread_id = int(path.rsplit("/", 1)[1])
            except ValueError:
                thread_id = -1
            payload = self.runtime.thread(thread_id)
            if payload is None:
                self._json({"error": "Thread not found."}, HTTPStatus.NOT_FOUND, send_body)
                return
        elif path.startswith("/api/profiles/"):
            handle = unquote(path.rsplit("/", 1)[1])
            payload = self.runtime.profile(handle)
            if payload is None:
                self._json({"error": "Profile not found."}, HTTPStatus.NOT_FOUND, send_body)
                return
        else:
            self._json({"error": "API route not found."}, HTTPStatus.NOT_FOUND, send_body)
            return
        self._json(payload, HTTPStatus.OK, send_body)

    def _static(self, path: str, *, send_body: bool) -> None:
        filename = {
            "": "index.html", "/": "index.html", "/index.html": "index.html",
            "/styles.css": "styles.css", "/app.js": "app.js",
            "/favicon.svg": "favicon.svg", "/robots.txt": "robots.txt",
        }.get(path)
        if filename is None:
            self._text("Not found.\n", HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8", send_body)
            return
        target = self.site_dir / filename
        if not target.is_file():
            self._text("Not found.\n", HTTPStatus.NOT_FOUND, "text/plain; charset=utf-8", send_body)
            return
        mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self._bytes(target.read_bytes(), HTTPStatus.OK, f"{mime}; charset=utf-8", send_body, cache=True)

    def _json(self, payload: dict | list, status: HTTPStatus, send_body: bool = True) -> None:
        raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self._bytes(raw, status, "application/json; charset=utf-8", send_body)

    def _text(self, payload: str, status: HTTPStatus, content_type: str, send_body: bool) -> None:
        self._bytes(payload.encode("utf-8"), status, content_type, send_body)

    def _bytes(
        self, payload: bytes, status: HTTPStatus, content_type: str,
        send_body: bool, *, cache: bool = False,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "public, max-age=300" if cache else "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.end_headers()
        if send_body:
            self.wfile.write(payload)

    def log_message(self, format: str, *args) -> None:
        if os.environ.get("FLREDDIT_ACCESS_LOG", "0") == "1":
            super().log_message(format, *args)


def make_server(
    runtime: ColonyRuntime,
    host: str,
    port: int,
    site_dir: str | Path = DEFAULT_SITE_DIR,
) -> ThreadingHTTPServer:
    class BoundHandler(FlredditHandler):
        pass

    BoundHandler.runtime = runtime
    BoundHandler.site_dir = Path(site_dir)
    server = ThreadingHTTPServer((host, port), BoundHandler)
    server.daemon_threads = True
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the persistent Flreddit colony and observer site.")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--database", default=os.environ.get("FLREDDIT_DB", "state/flreddit.sqlite3"))
    parser.add_argument("--site-dir", default=os.environ.get("FLREDDIT_SITE_DIR", str(DEFAULT_SITE_DIR)))
    parser.add_argument("--seed", type=int, default=int(os.environ.get("FLREDDIT_SEED", "100")))
    parser.add_argument("--interval", type=float, default=float(os.environ.get("FLREDDIT_TICK_SECONDS", "60")))
    parser.add_argument("--bootstrap-cycles", type=int, default=int(os.environ.get("FLREDDIT_BOOTSTRAP_CYCLES", "24")))
    parser.add_argument("--no-autostart", action="store_true")
    args = parser.parse_args()

    narrator = narrator_from_environment()
    runtime = ColonyRuntime(
        args.database,
        seed=args.seed,
        interval_seconds=args.interval,
        bootstrap_cycles=args.bootstrap_cycles,
        autostart=not args.no_autostart,
        narrator=narrator,
    )
    server = make_server(runtime, args.host, args.port, args.site_dir)
    print(f"Flreddit listening on http://{args.host}:{server.server_port}")
    print(
        f"100 profiles · cycle {runtime.forum.cycle} · "
        f"decision {DECISION_BACKEND} · words {narrator.backend}"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        runtime.stop()


if __name__ == "__main__":
    main()
