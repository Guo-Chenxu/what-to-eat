from types import SimpleNamespace


def test_main_starts_uvicorn_with_host_and_port_from_config(monkeypatch):
    import backend.run as run

    captured = {}

    def fake_uvicorn_run(app_path: str, **kwargs):
        captured["app_path"] = app_path
        captured.update(kwargs)

    monkeypatch.setattr(run.uvicorn, "run", fake_uvicorn_run)
    monkeypatch.setattr(
        run,
        "settings",
        SimpleNamespace(app=SimpleNamespace(host="192.0.2.10", port=8765)),
    )

    run.main()

    assert captured == {
        "app_path": "backend.main:app",
        "host": "192.0.2.10",
        "port": 8765,
        "reload": True,
    }
