from __future__ import annotations

from io import BytesIO
from typing import Iterable

import streamlit as st


class SessionUploadedFile(BytesIO):
    """UploadedFile-compatible object rebuilt from bytes kept in Session State."""

    def __init__(self, data: bytes, name: str, mime_type: str | None = None):
        super().__init__(data)
        self.name = name
        self.type = mime_type or "application/octet-stream"
        self.size = len(data)


def _to_payload(uploaded) -> dict | None:
    """Convert a Streamlit UploadedFile-like object to a serializable payload."""
    if uploaded is None:
        return None

    try:
        data = uploaded.getvalue()
    except Exception:
        try:
            uploaded.seek(0)
            data = uploaded.read()
        except Exception:
            return None

    return {
        "name": str(getattr(uploaded, "name", "uploaded_file")),
        "type": str(
            getattr(uploaded, "type", "application/octet-stream")
            or "application/octet-stream"
        ),
        "data": bytes(data),
    }


def _restore_payloads(state_key: str) -> list[dict]:
    """Read uploads only from the active Streamlit browser session.

    No disk fallback is used intentionally. This gives the requested behavior:
    - moving between Streamlit pages/rooms keeps the uploaded files;
    - a full browser refresh creates a new session, so the uploads disappear.
    """
    value = st.session_state.get(state_key)

    if isinstance(value, dict) and value.get("data"):
        return [value]

    if isinstance(value, list):
        return [
            payload
            for payload in value
            if isinstance(payload, dict) and payload.get("data")
        ]

    return []


def remember_upload(state_key: str, uploaded) -> None:
    """Keep one uploaded file in Session State only."""
    payload = _to_payload(uploaded)
    if payload is not None:
        st.session_state[state_key] = payload


def restore_upload(state_key: str):
    """Restore one file while the current browser session is alive."""
    payloads = _restore_payloads(state_key)
    if not payloads:
        return None

    payload = payloads[0]
    return SessionUploadedFile(
        payload["data"],
        payload.get("name", "uploaded_file"),
        payload.get("type"),
    )


def remember_uploads(state_key: str, uploaded_files: Iterable | None) -> None:
    """Keep multiple uploaded files in Session State only."""
    if not uploaded_files:
        return

    payloads: list[dict] = []
    for uploaded in uploaded_files:
        payload = _to_payload(uploaded)
        if payload is not None:
            payloads.append(payload)

    if payloads:
        st.session_state[state_key] = payloads


def restore_uploads(state_key: str) -> list[SessionUploadedFile]:
    """Restore multiple files while the current browser session is alive."""
    return [
        SessionUploadedFile(
            payload["data"],
            payload.get("name", "uploaded_file"),
            payload.get("type"),
        )
        for payload in _restore_payloads(state_key)
    ]


def clear_upload_memory(*state_keys: str, clear_persistent: bool = False) -> None:
    """Clear session upload memory.

    clear_persistent is retained only for API compatibility with older versions;
    v5.1.1 does not write or restore uploaded data from disk.
    """
    for key in state_keys:
        st.session_state.pop(key, None)
        st.session_state.pop(f"{key}__persist_ok", None)
        st.session_state.pop(f"{key}__persist_error", None)


def upload_memory_info(state_key: str) -> dict | None:
    payloads = _restore_payloads(state_key)
    if not payloads:
        return None

    payload = payloads[0]
    return {
        "name": str(payload.get("name", "uploaded_file")),
        "type": str(payload.get("type", "application/octet-stream")),
        "size": len(payload.get("data", b"")),
        "persistent": False,
        "session_only": True,
    }


def upload_memories_info(state_key: str) -> list[dict]:
    info: list[dict] = []
    for payload in _restore_payloads(state_key):
        info.append(
            {
                "name": str(payload.get("name", "uploaded_file")),
                "type": str(payload.get("type", "application/octet-stream")),
                "size": len(payload.get("data", b"")),
                "persistent": False,
                "session_only": True,
            }
        )
    return info
