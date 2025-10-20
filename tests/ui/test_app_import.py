"""Ensure the Streamlit UI module imports with stubbed dependencies."""

from __future__ import annotations

import importlib
import sys
import types

import pytest


class StopExecution(RuntimeError):
    """Signal that the mocked Streamlit stop() was invoked."""


def _build_streamlit_stub() -> types.SimpleNamespace:
    stub = types.SimpleNamespace()

    def cache_data(**_kwargs):
        def decorator(func):
            return func

        return decorator

    stub.cache_data = cache_data
    stub.set_page_config = lambda **kwargs: None
    stub.title = lambda *args, **kwargs: None
    stub.markdown = lambda *args, **kwargs: None
    stub.header = lambda *args, **kwargs: None
    stub.radio = lambda *args, **kwargs: "Local"
    stub.text_input = lambda *args, **kwargs: ""
    stub.info = lambda *args, **kwargs: None
    stub.error = lambda *args, **kwargs: None
    stub.warning = lambda *args, **kwargs: None
    stub.caption = lambda *args, **kwargs: None
    stub.file_uploader = lambda *args, **kwargs: None
    stub.toggle = lambda *args, **kwargs: False
    stub.selectbox = lambda *args, **kwargs: ""
    stub.button = lambda *args, **kwargs: False
    stub.json = lambda *args, **kwargs: None
    stub.text = lambda *args, **kwargs: None

    class Sidebar:
        def __enter__(self) -> types.SimpleNamespace:
            return stub

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    stub.sidebar = Sidebar()

    def stop() -> None:
        raise StopExecution()

    stub.stop = stop
    stub.columns = lambda *args, **kwargs: [types.SimpleNamespace(metric=lambda *a, **k: None)] * 5
    stub.tabs = lambda labels: tuple(
        types.SimpleNamespace(
            __enter__=lambda self=..., *a, **k: None,
            __exit__=lambda self, exc_type, exc, tb: None,
            dataframe=lambda *a, **k: None,
            download_button=lambda *a, **k: None,
        )
        for _ in labels
    )
    stub.dataframe = lambda *args, **kwargs: None
    stub.download_button = lambda *args, **kwargs: None

    return stub


@pytest.fixture(autouse=True)
def _patch_streamlit(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_streamlit = _build_streamlit_stub()
    monkeypatch.setitem(sys.modules, "streamlit", stub_streamlit)
    monkeypatch.setitem(
        sys.modules,
        "pandas",
        types.SimpleNamespace(
            Timestamp=lambda value: value,
            Timedelta=lambda **kwargs: None,
            DataFrame=lambda data: data,
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "requests",
        types.SimpleNamespace(
            post=lambda *args, **kwargs: types.SimpleNamespace(
                json=lambda: {}, text="", raise_for_status=lambda: None
            )
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "boto3",
        types.SimpleNamespace(
            client=lambda *args, **kwargs: types.SimpleNamespace(
                generate_presigned_url=lambda *a, **k: ""
            )
        ),
    )


def test_app_import_triggers_stop() -> None:
    with pytest.raises(StopExecution):
        importlib.reload(importlib.import_module("ui.app"))
