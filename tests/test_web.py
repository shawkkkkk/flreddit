import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from flreddit.web import ColonyRuntime, make_server


def test_runtime_exposes_consistent_public_views(tmp_path):
    runtime = ColonyRuntime(
        tmp_path / "runtime.sqlite3",
        bootstrap_cycles=35,
        interval_seconds=3600,
        autostart=False,
    )
    state = runtime.state()
    assert state["population"] == 100
    assert state["persistent"] is True
    assert state["shared"] is True
    assert state["threads"] > 0
    assert len(runtime.profiles(limit=100)) == 100
    assert len(runtime.communities()) == 6
    assert len(runtime.activity()) == 100
    thread = runtime.feed(limit=1)[0]
    assert runtime.thread(thread["id"])["author"]["handle"] == thread["author"]["handle"]
    runtime.stop()


def test_runtime_resumes_the_authoritative_cycle(tmp_path):
    database = tmp_path / "resume.sqlite3"
    first = ColonyRuntime(database, bootstrap_cycles=4, autostart=False)
    first.tick()
    cycle = first.forum.cycle
    first.stop()

    second = ColonyRuntime(database, bootstrap_cycles=99, autostart=False)
    assert second.resumed is True
    assert second.forum.cycle == cycle
    second.stop()


def test_http_server_serves_read_only_api_and_site(tmp_path):
    runtime = ColonyRuntime(tmp_path / "http.sqlite3", bootstrap_cycles=35, autostart=False)
    server = make_server(runtime, "127.0.0.1", 0)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(f"{base}/api/state") as response:
            state = json.load(response)
            assert state["population"] == 100
            assert response.headers["Cache-Control"] == "no-store"
            assert "default-src 'self'" in response.headers["Content-Security-Policy"]
        with urlopen(f"{base}/") as response:
            assert b"One hundred flies" in response.read()
            assert response.headers["X-Content-Type-Options"] == "nosniff"
        try:
            urlopen(Request(f"{base}/api/state", method="POST"))
        except HTTPError as error:
            assert error.code == 405
        else:
            raise AssertionError("POST should be rejected")
    finally:
        server.shutdown()
        server.server_close()
        runtime.stop()
        worker.join(timeout=2)
