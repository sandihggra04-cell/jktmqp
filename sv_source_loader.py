from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlparse, urlunparse
from functools import lru_cache
from base64 import urlsafe_b64encode
import os
import re
import time

import pandas as pd
import requests


EXCEL_MIME_MARKERS = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/octet-stream",
)

GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]
_GRAPH_TOKEN_CACHE: dict[tuple[str, str], tuple[str, float]] = {}


def normalize_source_url(value: str) -> str:
    """Normalize a pasted source URL.

    Supports a plain URL and Markdown-style copied links such as:
        [https://...](https://...\&file=...)
    """
    value = str(value or "").strip().strip('"').strip("'")
    if not value:
        return ""

    md_match = re.search(r"\[[^\]]*\]\((https?://[^)]+)\)", value, flags=re.IGNORECASE)
    if md_match:
        value = md_match.group(1)

    if not re.match(r"^https?://", value, flags=re.IGNORECASE):
        url_match = re.search(r"https?://[^\s<>\"]+", value, flags=re.IGNORECASE)
        if url_match:
            value = url_match.group(0)

    value = value.strip().strip("<>").strip()
    value = value.replace(r"\&", "&").replace(r"\_", "_")
    return value


def source_kind(url: str) -> str:
    """Classify a user-entered data source URL.

    Microsoft Lists sharing links use the ``/:l:/`` short-link marker. They
    must be detected before generic SharePoint URLs because a List is not an
    Excel file and needs a different reader. Canonical ``/Lists/...`` URLs are
    also accepted.
    """
    text = normalize_source_url(url)
    low = text.lower()
    if re.search(r"docs\.google\.com/spreadsheets/d/", low):
        return "google"
    if "sharepoint.com" in low and ("/:l:/" in low or re.search(r"/lists/[^/?#]+", low)):
        return "microsoft_list"
    if "sharepoint.com" in low or "onedrive.live.com" in low or "1drv.ms" in low:
        return "sharepoint"
    if re.match(r"^https?://", low) and re.search(r"\.(xlsx?|csv|json)(?:[?#]|$)", low):
        return "file_url"
    # Power Automate / Logic Apps / simple API endpoints often have no file extension.
    # Treat an otherwise-unclassified http(s) URL as a generic remote data endpoint;
    # the response parser will still reject HTML/login pages.
    if re.match(r"^https?://", low):
        return "remote_data"
    if low.startswith("file://") or (not re.match(r"^https?://", low) and re.search(r"\.(xlsx?|csv)$", low)):
        return "local_file"
    return "unknown"


def is_supported_source_url(url: str) -> bool:
    return source_kind(url) != "unknown"


def _with_download_flag(url: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.pop("web", None)
    query["download"] = "1"
    return urlunparse(parsed._replace(query=urlencode(query)))


def _sharepoint_doc_link_info(url: str) -> dict[str, str] | None:
    """Parse an Office-generated SharePoint Doc.aspx workbook URL."""
    normalized = normalize_source_url(url)
    parsed = urlparse(normalized)
    host = (parsed.hostname or "").strip()
    if "sharepoint.com" not in host.lower():
        return None

    path = unquote(parsed.path or "")
    path = re.sub(r"^/:[a-zA-Z]:/(?:r|s)/", "/", path)
    match = re.search(
        r"(?P<site>/(?:sites|teams)/[^/]+)/_layouts/15/doc\.aspx$",
        path,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    source_doc = unquote(str(query.get("sourcedoc") or "")).strip().strip("{}")
    filename = unquote(str(query.get("file") or "")).strip()

    return {
        "host": host,
        "site_path": match.group("site"),
        "source_doc": source_doc,
        "filename": filename,
        "url": normalized,
    }


def sharepoint_download_candidates(url: str):
    """Generate best-effort anonymous download forms for SharePoint/OneDrive links."""
    text = normalize_source_url(url)
    candidates: list[tuple[str, str]] = []
    if not text:
        return candidates

    parsed = urlparse(text)
    original_query = dict(parse_qsl(parsed.query, keep_blank_values=True))

    # Office Doc.aspx links often download directly with action=download.
    q_action = dict(original_query)
    q_action["action"] = "download"
    q_action.pop("web", None)
    action_url = urlunparse(parsed._replace(query=urlencode(q_action)))
    candidates.append(("SharePoint action=download", action_url))

    # Generic download=1 form.
    q_download = dict(original_query)
    q_download.pop("action", None)
    q_download.pop("web", None)
    q_download["download"] = "1"
    download_url = urlunparse(parsed._replace(query=urlencode(q_download)))
    if download_url not in [u for _, u in candidates]:
        candidates.append(("SharePoint download=1", download_url))

    # GUID-based download endpoint used by some SharePoint tenants.
    info = _sharepoint_doc_link_info(text)
    if info and info.get("source_doc"):
        unique_url = (
            f"https://{info['host']}{info['site_path']}/_layouts/15/download.aspx?"
            + urlencode({"UniqueId": "{" + info["source_doc"] + "}"})
        )
        if unique_url not in [u for _, u in candidates]:
            candidates.append(("SharePoint document GUID download", unique_url))

    if text not in [u for _, u in candidates]:
        candidates.append(("SharePoint original", text))
    return candidates


def _looks_like_login_html(response: requests.Response) -> bool:
    ctype = (response.headers.get("Content-Type") or "").lower()
    sample = (response.content[:6000] or b"").lower()
    final_url = (response.url or "").lower()
    login_markers = [
        b"login.microsoftonline.com",
        b"microsoft sign in",
        b"sign in to your account",
        b"sharepoint login",
        b"aadcdn",
        b"oauth2/authorize",
    ]
    if "login.microsoftonline.com" in final_url:
        return True
    if "text/html" in ctype and any(m in sample for m in login_markers):
        return True
    if sample.lstrip().startswith((b"<!doctype html", b"<html")) and any(m in sample for m in login_markers):
        return True
    return False


def _sharepoint_settings() -> dict[str, str]:
    """Load Microsoft Graph app credentials from Streamlit secrets or environment.

    Preferred Streamlit secrets format::

        [sharepoint]
        tenant_id = "..."
        client_id = "..."
        client_secret = "..."

    Environment-variable fallback is useful for Docker/servers:
    SP_TENANT_ID, SP_CLIENT_ID, SP_CLIENT_SECRET.
    """
    settings = {
        "tenant_id": os.getenv("SP_TENANT_ID", "").strip(),
        "client_id": os.getenv("SP_CLIENT_ID", "").strip(),
        "client_secret": os.getenv("SP_CLIENT_SECRET", "").strip(),
    }

    try:
        import streamlit as st

        section = st.secrets.get("sharepoint", {})
        for key in settings:
            value = section.get(key, "") if hasattr(section, "get") else ""
            if str(value or "").strip():
                settings[key] = str(value).strip()
    except Exception:
        # No secrets file is a normal state: anonymous SharePoint links still work.
        pass

    return settings



def configured_source_url(name: str, fallback: str = "") -> str:
    """Read an optional default source from Streamlit secrets or environment.

    Supported names: ``apu_shop_visit`` and ``engine_shop_visit``.
    Environment variables are APU_SHOP_VISIT_SOURCE and ENGINE_SHOP_VISIT_SOURCE.
    """
    env_map = {
        "apu_shop_visit": "APU_SHOP_VISIT_SOURCE",
        "engine_shop_visit": "ENGINE_SHOP_VISIT_SOURCE",
        "apu_shop_visit_bridge": "APU_SHOP_VISIT_BRIDGE",
        "engine_shop_visit_bridge": "ENGINE_SHOP_VISIT_BRIDGE",
    }
    value = os.getenv(env_map.get(name, ""), "").strip() if env_map.get(name) else ""
    try:
        import streamlit as st

        section = st.secrets.get("sources", {})
        secret_value = section.get(name, "") if hasattr(section, "get") else ""
        if str(secret_value or "").strip():
            value = str(secret_value).strip()
    except Exception:
        pass
    return value or str(fallback or "").strip()

def sharepoint_graph_status() -> tuple[bool, str]:
    """Return whether private SharePoint access through Microsoft Graph is configured."""
    cfg = _sharepoint_settings()
    missing = [k for k in ("tenant_id", "client_id", "client_secret") if not cfg.get(k)]
    if not missing:
        return True, "Microsoft Graph configured"
    readable = {"tenant_id": "tenant_id", "client_id": "client_id", "client_secret": "client_secret"}
    return False, "Microsoft Graph not configured: missing " + ", ".join(readable[k] for k in missing)


def _get_graph_token(force_refresh: bool = False) -> str:
    cfg = _sharepoint_settings()
    missing = [k for k in ("tenant_id", "client_id", "client_secret") if not cfg.get(k)]
    if missing:
        raise RuntimeError(
            "Private SharePoint membutuhkan Microsoft Graph credentials. "
            "Isi [sharepoint] tenant_id, client_id, dan client_secret pada .streamlit/secrets.toml "
            "atau SP_TENANT_ID/SP_CLIENT_ID/SP_CLIENT_SECRET pada environment."
        )

    cache_key = (cfg["tenant_id"], cfg["client_id"])
    cached = _GRAPH_TOKEN_CACHE.get(cache_key)
    if cached and not force_refresh and cached[1] > time.time() + 120:
        return cached[0]

    try:
        import msal
    except ImportError as exc:
        raise RuntimeError(
            "Package 'msal' belum terpasang. Jalankan: python -m pip install -r requirements.txt"
        ) from exc

    authority = f"https://login.microsoftonline.com/{cfg['tenant_id']}"
    app = msal.ConfidentialClientApplication(
        client_id=cfg["client_id"],
        authority=authority,
        client_credential=cfg["client_secret"],
    )
    result = app.acquire_token_for_client(scopes=GRAPH_SCOPE)
    token = result.get("access_token")
    if not token:
        detail = result.get("error_description") or result.get("error") or "unknown authentication error"
        raise PermissionError(f"Microsoft Graph authentication gagal: {detail}")

    expires_in = int(result.get("expires_in", 3600) or 3600)
    _GRAPH_TOKEN_CACHE[cache_key] = (token, time.time() + max(expires_in, 300))
    return token


def _graph_response(url: str, *, timeout: int = 45, accept: str | None = None) -> requests.Response:
    """GET a Graph endpoint and retry once if the cached token is rejected."""
    last = None
    for force in (False, True):
        token = _get_graph_token(force_refresh=force)
        headers = {"Authorization": f"Bearer {token}"}
        if accept:
            headers["Accept"] = accept
        r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        last = r
        if r.status_code != 401:
            return r
    return last


def _graph_error(response: requests.Response) -> str:
    try:
        payload = response.json()
        err = payload.get("error", {})
        code = err.get("code") or response.status_code
        message = err.get("message") or response.text[:300]
        return f"{code}: {message}"
    except Exception:
        return f"HTTP {response.status_code}: {(response.text or '')[:300]}"


def _graph_share_id(url: str) -> str:
    encoded = urlsafe_b64encode(str(url).encode("utf-8")).decode("ascii").rstrip("=")
    return "u!" + encoded


def _download_graph_drive_item(drive_id: str, item_id: str, timeout: int) -> bytes:
    endpoint = f"https://graph.microsoft.com/v1.0/drives/{quote(drive_id, safe='')}/items/{quote(item_id, safe='')}/content"
    r = _graph_response(endpoint, timeout=timeout, accept="*/*")
    if r.status_code >= 400:
        raise PermissionError("Microsoft Graph download gagal: " + _graph_error(r))
    if _looks_like_login_html(r):
        raise PermissionError("Microsoft Graph unexpectedly returned a Microsoft sign-in page.")
    if not r.content:
        raise ValueError("Microsoft Graph mengembalikan file kosong.")
    return r.content


def _download_sharepoint_graph_via_share_url(url: str, timeout: int) -> tuple[bytes, str]:
    """Download the pasted sharing URL directly through Graph /shares/.../driveItem/content."""
    share_id = _graph_share_id(url)
    endpoint = f"https://graph.microsoft.com/v1.0/shares/{share_id}/driveItem/content"
    r = _graph_response(endpoint, timeout=timeout, accept="*/*")
    if r.status_code >= 400:
        raise LookupError(_graph_error(r))
    if _looks_like_login_html(r):
        raise PermissionError("Microsoft Graph returned a sign-in page instead of file content.")
    if not r.content:
        raise ValueError("Microsoft Graph mengembalikan file kosong.")
    return r.content, "SharePoint file"


def _normalize_guid(value: str) -> str:
    return re.sub(r"[^0-9a-f]", "", str(value or "").lower())


def _download_sharepoint_graph_via_doc_link(url: str, timeout: int) -> tuple[bytes, str]:
    """Resolve a private Doc.aspx link through Microsoft Graph.

    Doc.aspx contains a site path, document GUID, and workbook filename but
    not the real document-library-relative path. We therefore:
      1. resolve the SharePoint site,
      2. enumerate document libraries,
      3. search for the exact workbook name,
      4. prefer a matching SharePoint unique ID when Graph exposes it,
      5. download the matching drive item.
    """
    info = _sharepoint_doc_link_info(url)
    if not info:
        raise ValueError("URL bukan SharePoint Doc.aspx link.")

    filename = str(info.get("filename") or "").strip()
    expected_guid = _normalize_guid(info.get("source_doc") or "")
    if not filename:
        raise ValueError("SharePoint Doc.aspx link tidak memiliki parameter file=.")

    site_endpoint = (
        f"https://graph.microsoft.com/v1.0/sites/{info['host']}:"
        f"{quote(info['site_path'], safe='/')}?$select=id,webUrl"
    )
    site_r = _graph_response(site_endpoint, timeout=timeout, accept="application/json")
    if site_r.status_code >= 400:
        raise PermissionError("Tidak dapat resolve SharePoint site: " + _graph_error(site_r))

    site_id = str(site_r.json().get("id") or "").strip()
    if not site_id:
        raise ValueError("Microsoft Graph tidak mengembalikan site id.")

    drives_url = (
        f"https://graph.microsoft.com/v1.0/sites/{quote(site_id, safe=',')}/drives"
        "?$select=id,name,webUrl,driveType&$top=999"
    )
    drives_r = _graph_response(drives_url, timeout=timeout, accept="application/json")
    if drives_r.status_code >= 400:
        raise PermissionError("Tidak dapat membaca SharePoint document libraries: " + _graph_error(drives_r))

    drives = drives_r.json().get("value", []) or []
    if not drives:
        raise ValueError("Tidak ada document library yang dapat diakses pada SharePoint site tersebut.")

    exact: list[tuple[str, str, str, str, bool]] = []
    errors: list[str] = []
    q_text = quote(filename, safe="")

    for drive in drives:
        drive_id = str(drive.get("id") or "").strip()
        drive_name = str(drive.get("name") or "Documents").strip()
        if not drive_id:
            continue

        search_url = (
            f"https://graph.microsoft.com/v1.0/drives/{quote(drive_id, safe='')}"
            f"/root/search(q='{q_text}')"
            "?$select=id,name,webUrl,file,parentReference,sharepointIds&$top=200"
        )
        sr = _graph_response(search_url, timeout=timeout, accept="application/json")
        if sr.status_code >= 400:
            errors.append(f"{drive_name}: {_graph_error(sr)}")
            continue

        for item in sr.json().get("value", []) or []:
            if not isinstance(item, dict) or not item.get("file"):
                continue
            item_name = str(item.get("name") or "").strip()
            item_id = str(item.get("id") or "").strip()
            if not item_id or item_name.casefold() != filename.casefold():
                continue

            sp_ids = item.get("sharepointIds") or {}
            item_guid = _normalize_guid(sp_ids.get("listItemUniqueId") or "")
            guid_match = bool(expected_guid and item_guid and item_guid == expected_guid)
            exact.append((drive_id, item_id, item_name, drive_name, guid_match))

    if not exact:
        detail = " | ".join(errors[-4:])
        raise FileNotFoundError(
            f"Workbook '{filename}' tidak ditemukan pada SharePoint site {info['site_path']}. {detail}"
        )

    # GUID match first, then standard Documents library, then any exact filename match.
    exact.sort(
        key=lambda row: (
            1 if row[4] else 0,
            1 if row[3].strip().lower() in ("documents", "shared documents") else 0,
        ),
        reverse=True,
    )

    download_errors: list[str] = []
    for drive_id, item_id, item_name, drive_name, _guid_match in exact:
        try:
            return _download_graph_drive_item(drive_id, item_id, timeout), item_name
        except Exception as exc:
            download_errors.append(f"{drive_name}/{item_name}: {type(exc).__name__}: {exc}")

    raise FileNotFoundError(
        "Workbook ditemukan tetapi tidak dapat diunduh melalui Microsoft Graph. "
        + " | ".join(download_errors[-4:])
    )


def _sharepoint_path_parts(url: str) -> tuple[str, str, str]:
    """Extract hostname, site path, and document-library-relative path from common SharePoint URLs."""
    parsed = urlparse(normalize_source_url(url))
    host = (parsed.hostname or "").strip()
    path = unquote(parsed.path or "")

    # Office-generated links often start with /:x:/r/ or /:x:/s/.
    path = re.sub(r"^/:[a-zA-Z]:/(?:r|s)/", "/", path)
    match = re.search(r"(?P<site>/(?:sites|teams)/[^/]+)(?P<rest>/.*)?$", path, flags=re.IGNORECASE)
    if not host or not match:
        raise ValueError("SharePoint URL path tidak dapat dipetakan ke site/document library.")
    site_path = match.group("site")
    rest = (match.group("rest") or "").strip("/")
    if not rest:
        raise ValueError("SharePoint URL tidak memuat path file yang dapat dikenali.")
    return host, site_path, rest


def _download_sharepoint_graph_via_path(url: str, timeout: int) -> tuple[bytes, str]:
    """Fallback for ordinary SharePoint file URLs that /shares cannot resolve."""
    host, site_path, rest = _sharepoint_path_parts(url)
    site_endpoint = f"https://graph.microsoft.com/v1.0/sites/{host}:{quote(site_path, safe='/')}?$select=id"
    site_r = _graph_response(site_endpoint, timeout=timeout, accept="application/json")
    if site_r.status_code >= 400:
        raise PermissionError("Tidak dapat resolve SharePoint site: " + _graph_error(site_r))
    site_id = site_r.json().get("id")
    if not site_id:
        raise ValueError("Microsoft Graph tidak mengembalikan site id.")

    drives_endpoint = f"https://graph.microsoft.com/v1.0/sites/{quote(site_id, safe=',')}/drives?$select=id,name,webUrl,driveType"
    drives_r = _graph_response(drives_endpoint, timeout=timeout, accept="application/json")
    if drives_r.status_code >= 400:
        raise PermissionError("Tidak dapat membaca document libraries: " + _graph_error(drives_r))
    drives = drives_r.json().get("value", []) or []
    if not drives:
        raise ValueError("Tidak ada document library yang dapat diakses pada SharePoint site tersebut.")

    pieces = [p for p in rest.split("/") if p]
    first = pieces[0] if pieces else ""
    attempts: list[tuple[str, str, str]] = []

    # Prefer a drive whose name matches the first URL segment.
    for drive in drives:
        drive_id = str(drive.get("id") or "")
        drive_name = str(drive.get("name") or "")
        if not drive_id:
            continue
        drive_name_norm = re.sub(r"\s+", " ", drive_name).strip().lower()
        first_norm = re.sub(r"\s+", " ", first).strip().lower()
        if first_norm and (first_norm == drive_name_norm or (first_norm == "shared documents" and drive_name_norm == "documents")):
            rel = "/".join(pieces[1:])
            if rel:
                attempts.append((drive_id, rel, drive_name))

    # Default Documents library usually has the URL segment "Shared Documents".
    for drive in drives:
        drive_id = str(drive.get("id") or "")
        drive_name = str(drive.get("name") or "")
        if not drive_id:
            continue
        if drive_name.strip().lower() in ("documents", "shared documents"):
            rel = "/".join(pieces[1:]) if first.lower() in ("shared documents", "documents") else rest
            if rel:
                attempts.append((drive_id, rel, drive_name))

    # Last resort: try each drive with the full relative path.
    for drive in drives:
        drive_id = str(drive.get("id") or "")
        drive_name = str(drive.get("name") or "")
        if drive_id:
            attempts.append((drive_id, rest, drive_name))

    seen = set()
    errors = []
    for drive_id, rel_path, drive_name in attempts:
        key = (drive_id, rel_path)
        if key in seen:
            continue
        seen.add(key)
        endpoint = (
            f"https://graph.microsoft.com/v1.0/drives/{quote(drive_id, safe='')}/root:/"
            f"{quote(rel_path, safe='/')}:/content"
        )
        r = _graph_response(endpoint, timeout=timeout, accept="*/*")
        if r.status_code < 400 and r.content and not _looks_like_login_html(r):
            return r.content, rel_path.rsplit("/", 1)[-1]
        errors.append(f"{drive_name or 'drive'}: {_graph_error(r)}")

    raise FileNotFoundError("File tidak ditemukan melalui Microsoft Graph. " + " | ".join(errors[-3:]))


def download_sharepoint_file_graph(url: str, timeout: int = 45):
    """Download a private SharePoint/OneDrive Excel file through Microsoft Graph.

    Supports:
    - ordinary SharePoint/OneDrive links,
    - sharing links,
    - Office-generated Doc.aspx links containing sourcedoc + file.
    """
    url = normalize_source_url(url)
    errors: list[str] = []

    if _sharepoint_doc_link_info(url):
        try:
            data, filename = _download_sharepoint_graph_via_doc_link(url, timeout)
            return data, _detect_format(data, filename, ""), "SharePoint Doc.aspx · Microsoft Graph"
        except Exception as exc:
            errors.append(f"Doc.aspx: {type(exc).__name__}: {exc}")

    try:
        data, filename = _download_sharepoint_graph_via_share_url(url, timeout)
        return data, _detect_format(data, filename, ""), "SharePoint · Microsoft Graph"
    except Exception as exc:
        errors.append(f"sharing URL: {type(exc).__name__}: {exc}")

    # Real path resolution is useful for ordinary SharePoint file URLs. A
    # Doc.aspx URL points to /_layouts/... rather than the actual library path.
    if not _sharepoint_doc_link_info(url):
        try:
            data, filename = _download_sharepoint_graph_via_path(url, timeout)
            return data, _detect_format(data, filename, ""), "SharePoint · Microsoft Graph"
        except Exception as exc:
            errors.append(f"site/path: {type(exc).__name__}: {exc}")

    raise PermissionError(
        "Microsoft Graph tidak dapat membaca SharePoint workbook. Pastikan App Registration "
        "memiliki izin baca ke site/file tersebut dan admin consent sudah diberikan. "
        + " | ".join(errors[-3:])
    )




def _json_find_key(value, key: str):
    """Return the first matching key from a nested JSON structure."""
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for child in value.values():
            found = _json_find_key(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _json_find_key(child, key)
            if found is not None:
                return found
    return None


def _microsoft_list_site_parts(url: str) -> tuple[str, str, str | None]:
    """Infer SharePoint hostname/site path and an optional list-name hint.

    Supports the Microsoft Lists short sharing form used by ``My Lists``::

        https://tenant-my.sharepoint.com/:l:/g/personal/user_tenant_com/<token>

    and canonical list URLs such as ``/sites/X/Lists/MyList/AllItems.aspx``.
    The short link does not contain a list title, so the Graph fallback later
    enumerates lists on the inferred site and lets the dashboard schema choose
    the matching list automatically.
    """
    parsed = urlparse(str(url or "").strip())
    host = (parsed.hostname or "").strip()
    path = unquote(parsed.path or "")
    if not host or "sharepoint.com" not in host.lower():
        raise ValueError("Microsoft List URL bukan URL SharePoint yang valid.")

    # Short Lists share link, e.g. /:l:/g/personal/user_domain_com/<token>
    m = re.match(r"^/:l:/[^/]+(?P<site>/(?:personal|sites|teams)/[^/]+)(?:/.*)?$", path, flags=re.IGNORECASE)
    if m:
        return host, m.group("site"), None

    # Canonical list URL, e.g. /sites/team/Lists/Engine%20SV/AllItems.aspx
    m = re.search(r"(?P<site>/(?:personal|sites|teams)/[^/]+)/Lists/(?P<list>[^/]+)", path, flags=re.IGNORECASE)
    if m:
        return host, m.group("site"), unquote(m.group("list"))

    # A list URL can occasionally be rooted directly under a personal site.
    m = re.search(r"(?P<site>/personal/[^/]+)", path, flags=re.IGNORECASE)
    if m:
        return host, m.group("site"), None

    raise ValueError(
        "Microsoft List link tidak dapat dipetakan ke SharePoint site. Gunakan link dari Share > Copy link "
        "atau URL List yang mengandung /Lists/."
    )


def _microsoft_list_remote_api_url(share_url: str, specific_api: str) -> str:
    """Build Microsoft's documented SP.RemoteWeb short-link compatibility URL.

    Microsoft documents this as a compatibility workaround for APIs that need
    to operate on a user-supplied SharePoint short sharing URL. It is attempted
    only for an Anyone link; Graph remains the supported fallback.
    """
    parsed = urlparse(str(share_url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Microsoft List sharing URL tidak valid.")
    base = f"{parsed.scheme}://{parsed.netloc}"
    encoded = quote(str(share_url), safe="")
    sep = "&" if "?" in specific_api else "?"
    return f"{base}/_api/SP.RemoteWeb(@a)/web/{specific_api}{sep}@a='{encoded}'"


def _anonymous_list_link_info(share_url: str, timeout: int = 30) -> dict:
    """Resolve a Microsoft List Anyone link with SharePoint's RemoteWeb API."""
    endpoint = _microsoft_list_remote_api_url(share_url, "GetSharingLinkData(@a)")
    r = requests.get(
        endpoint,
        headers={"Accept": "application/json;odata=nometadata", "User-Agent": "Mozilla/5.0 Powerplant-Engineering-Control-Center/4.7.3"},
        timeout=timeout,
        allow_redirects=True,
    )
    if r.status_code in (401, 403) or _looks_like_login_html(r):
        raise PermissionError("Microsoft List Anyone link meminta autentikasi pada REST endpoint.")
    r.raise_for_status()
    try:
        payload = r.json()
    except Exception as exc:
        raise ValueError("SharePoint tidak mengembalikan metadata JSON untuk Microsoft List link.") from exc

    object_id = _json_find_key(payload, "ObjectUniqueId")
    object_type = _json_find_key(payload, "ObjectType")
    is_anonymous = _json_find_key(payload, "IsAnonymous")
    is_sharing = _json_find_key(payload, "IsSharingLink")
    if not object_id:
        raise ValueError("Sharing link berhasil dibuka tetapi List ID tidak ditemukan.")
    return {
        "object_id": str(object_id).strip("{}"),
        "object_type": object_type,
        "is_anonymous": is_anonymous,
        "is_sharing_link": is_sharing,
    }


def _extract_sp_rest_rows(payload) -> list[dict]:
    """Normalize classic/modern SharePoint REST collection responses."""
    if isinstance(payload, dict):
        if isinstance(payload.get("value"), list):
            return payload["value"]
        d = payload.get("d")
        if isinstance(d, dict):
            results = d.get("results")
            if isinstance(results, list):
                return results
            # Some endpoints wrap the collection one level deeper.
            for v in d.values():
                if isinstance(v, dict) and isinstance(v.get("results"), list):
                    return v["results"]
    return []


def _microsoft_list_anonymous_frames(url: str, timeout: int = 35):
    """Best-effort read of an Anyone Microsoft List sharing link without login.

    The Microsoft Lists UI can be anonymous while the REST surface is still
    restricted by tenant policy. In that case this function intentionally
    fails and the supported Microsoft Graph fallback is used.
    """
    info = _anonymous_list_link_info(url, timeout=timeout)
    list_id = info["object_id"]

    # Read field metadata so internal SharePoint names can be restored to the
    # display names expected by the dashboard (e.g. "Scope of Work").
    fields_api = (
        f"lists(guid'{list_id}')/fields"
        "?$select=InternalName,Title,Hidden,ReadOnlyField"
    )
    fields_url = _microsoft_list_remote_api_url(url, fields_api)
    fr = requests.get(
        fields_url,
        headers={"Accept": "application/json;odata=nometadata", "User-Agent": "Mozilla/5.0 Powerplant-Engineering-Control-Center/4.7.3"},
        timeout=timeout,
        allow_redirects=True,
    )
    if fr.status_code in (401, 403) or _looks_like_login_html(fr):
        raise PermissionError("Microsoft List field metadata membutuhkan sign-in.")
    fr.raise_for_status()
    fields = _extract_sp_rest_rows(fr.json())
    rename = {}
    for field in fields:
        internal = str(field.get("InternalName") or "").strip()
        title = str(field.get("Title") or "").strip()
        if internal and title:
            rename[internal] = title

    items_api = f"lists(guid'{list_id}')/items?$top=5000"
    next_url = _microsoft_list_remote_api_url(url, items_api)
    rows: list[dict] = []
    while next_url:
        rr = requests.get(
            next_url,
            headers={"Accept": "application/json;odata=nometadata", "User-Agent": "Mozilla/5.0 Powerplant-Engineering-Control-Center/4.7.3"},
            timeout=timeout,
            allow_redirects=True,
        )
        if rr.status_code in (401, 403) or _looks_like_login_html(rr):
            raise PermissionError("Microsoft List items membutuhkan sign-in.")
        rr.raise_for_status()
        payload = rr.json()
        rows.extend(_extract_sp_rest_rows(payload))
        next_url = payload.get("@odata.nextLink") or payload.get("odata.nextLink")
        if not next_url and isinstance(payload.get("d"), dict):
            next_url = payload["d"].get("__next")

    if not rows:
        return [("Microsoft List · Anyone link", pd.DataFrame())]
    df = pd.DataFrame(rows)
    # Remove metadata/technical fields but retain user columns. Renaming can
    # create duplicates, so coalesce duplicate display names afterwards.
    technical = {"__metadata", "FileSystemObjectType", "ContentTypeId", "OData__UIVersionString", "Attachments", "GUID"}
    keep = [c for c in df.columns if c not in technical]
    df = df[keep].rename(columns=rename)
    if df.columns.duplicated().any():
        merged = {}
        for col in dict.fromkeys(df.columns):
            block = df.loc[:, df.columns == col]
            merged[col] = block.bfill(axis=1).iloc[:, 0]
        df = pd.DataFrame(merged)
    return [("Microsoft List · Anyone link", df)]


def _graph_json(url: str, timeout: int = 45) -> dict:
    r = _graph_response(url, timeout=timeout, accept="application/json")
    if r.status_code >= 400:
        raise PermissionError("Microsoft Graph request gagal: " + _graph_error(r))
    try:
        return r.json()
    except Exception as exc:
        raise ValueError("Microsoft Graph tidak mengembalikan JSON yang valid.") from exc


def _graph_all_values(url: str, timeout: int = 45) -> list[dict]:
    values: list[dict] = []
    next_url = url
    while next_url:
        payload = _graph_json(next_url, timeout=timeout)
        batch = payload.get("value", [])
        if isinstance(batch, list):
            values.extend(batch)
        next_url = payload.get("@odata.nextLink")
    return values


def _microsoft_list_graph_frames(url: str, timeout: int = 45):
    """Read Microsoft Lists through Graph using app credentials.

    For a ``/:l:/`` sharing link the site path is inferred from the URL. The
    link token itself does not expose the List ID, so the code enumerates Lists
    on that site. The APU/Engine page then chooses the List whose schema matches
    its expected columns. Canonical ``/Lists/<name>/`` URLs are narrowed to the
    named List when possible.
    """
    host, site_path, list_hint = _microsoft_list_site_parts(url)
    site_endpoint = f"https://graph.microsoft.com/v1.0/sites/{host}:{quote(site_path, safe='/')}?$select=id,webUrl,displayName"
    site = _graph_json(site_endpoint, timeout=timeout)
    site_id = site.get("id")
    if not site_id:
        raise ValueError("Microsoft Graph tidak mengembalikan site id untuk Microsoft List.")

    lists_url = (
        f"https://graph.microsoft.com/v1.0/sites/{quote(str(site_id), safe=',')}/lists"
        "?$select=id,name,displayName,webUrl,list&$top=999"
    )
    lists = _graph_all_values(lists_url, timeout=timeout)
    if list_hint:
        hint_norm = re.sub(r"[^a-z0-9]+", "", list_hint.lower())
        narrowed = [
            item for item in lists
            if re.sub(r"[^a-z0-9]+", "", str(item.get("displayName") or item.get("name") or "").lower()) == hint_norm
        ]
        if narrowed:
            lists = narrowed

    frames = []
    errors = []
    for lst in lists:
        list_id = str(lst.get("id") or "").strip()
        title = str(lst.get("displayName") or lst.get("name") or list_id).strip()
        if not list_id:
            continue
        # Skip obvious system/catalog lists when Graph exposes their template.
        template = str((lst.get("list") or {}).get("template") or "").lower()
        if template and template not in {"genericlist", "issue", "tasks", "survey", "contacts", "events", "customgrid"}:
            continue
        try:
            cols_url = (
                f"https://graph.microsoft.com/v1.0/sites/{quote(str(site_id), safe=',')}/lists/{quote(list_id, safe='')}/columns"
                "?$select=name,displayName,hidden,readOnly&$top=999"
            )
            columns = _graph_all_values(cols_url, timeout=timeout)
            rename = {
                str(c.get("name")): str(c.get("displayName") or c.get("name"))
                for c in columns if c.get("name")
            }
            items_url = (
                f"https://graph.microsoft.com/v1.0/sites/{quote(str(site_id), safe=',')}/lists/{quote(list_id, safe='')}/items"
                "?$expand=fields&$top=999"
            )
            items = _graph_all_values(items_url, timeout=timeout)
            rows = []
            for item in items:
                fields = item.get("fields") if isinstance(item, dict) else None
                if isinstance(fields, dict):
                    rows.append(dict(fields))
            df = pd.DataFrame(rows)
            if len(df.columns):
                df = df.rename(columns=rename)
                if df.columns.duplicated().any():
                    merged = {}
                    for col in dict.fromkeys(df.columns):
                        block = df.loc[:, df.columns == col]
                        merged[col] = block.bfill(axis=1).iloc[:, 0]
                    df = pd.DataFrame(merged)
            frames.append((f"Microsoft List · {title}", df))
        except Exception as exc:
            errors.append(f"{title}: {type(exc).__name__}: {exc}")

    if not frames:
        detail = " | ".join(errors[-3:])
        raise ValueError("Tidak ada Microsoft List yang dapat dibaca pada site tersebut. " + detail)
    return frames


def dataframes_from_microsoft_list(url: str):
    """Read a Microsoft List share/canonical URL.

    1. For an ``Anyone`` sharing link, first try an anonymous SharePoint
       compatibility endpoint so the user can paste the link directly.
    2. If that REST surface is blocked (common on corporate tenants), fall back
       to Microsoft Graph when app credentials are configured.
    """
    errors = []
    if "/:l:/" in str(url).lower():
        try:
            return _microsoft_list_anonymous_frames(url)
        except Exception as exc:
            errors.append(f"Anyone link: {type(exc).__name__}: {exc}")

    graph_ready, graph_status = sharepoint_graph_status()
    if graph_ready:
        try:
            return _microsoft_list_graph_frames(url)
        except Exception as exc:
            errors.append(f"Microsoft Graph: {type(exc).__name__}: {exc}")
    else:
        errors.append(graph_status)

    raise PermissionError(
        "Microsoft List UI dapat terbuka dari link sharing, tetapi endpoint data List masih meminta autentikasi. "
        "Ini bukan masalah format kolom. Cara paling sederhana tanpa App Registration adalah membuat Power Automate "
        "CSV/JSON bridge lalu paste link bridge ke field 'Microsoft List bridge URL'. Alternatifnya configure Microsoft Graph. "
        + " | ".join(errors[-3:])
    )

def _detect_format(data: bytes, url_or_name: str = "", content_type: str = "") -> str:
    if data.startswith(b"PK\x03\x04"):
        return "xlsx"
    if data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "xls"
    low = str(url_or_name or "").lower()
    ctype = str(content_type or "").lower()
    if "text/csv" in ctype or re.search(r"\.csv(?:[?#]|$)", low):
        return "csv"
    if any(m in ctype for m in EXCEL_MIME_MARKERS):
        try:
            pd.ExcelFile(BytesIO(data))
            return "xlsx"
        except Exception:
            pass
    if not data.lstrip().lower().startswith((b"<!doctype html", b"<html")):
        try:
            pd.read_csv(BytesIO(data), nrows=5)
            return "csv"
        except Exception:
            pass
    raise ValueError("Response bukan file Excel/CSV yang dapat dibaca.")


def download_sharepoint_file(url: str, timeout: int = 45):
    """Download SharePoint/OneDrive spreadsheet.

    Order of operations:
    1) Try anonymous/direct SharePoint forms (works for Anyone links).
    2) If Microsoft Graph credentials are configured, automatically retry through Graph
       (works for private corporate SharePoint according to the app's permissions).
    """
    url = normalize_source_url(url)
    errors = []
    headers = {
        "User-Agent": "Mozilla/5.0 Powerplant-Engineering-Control-Center/5.1.5",
        "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,text/csv,*/*",
    }
    for label, candidate in sharepoint_download_candidates(url):
        try:
            r = requests.get(candidate, headers=headers, timeout=timeout, allow_redirects=True)
            if r.status_code in (401, 403):
                errors.append(f"{label}: HTTP {r.status_code} (authentication required)")
                continue
            r.raise_for_status()
            if _looks_like_login_html(r):
                errors.append(f"{label}: Microsoft sign-in page returned")
                continue
            if not r.content:
                errors.append(f"{label}: empty response")
                continue
            try:
                fmt = _detect_format(r.content, r.url or candidate, r.headers.get("Content-Type") or "")
                return r.content, fmt, label
            except Exception as exc:
                errors.append(f"{label}: {exc}")
        except Exception as exc:
            errors.append(f"{label}: {type(exc).__name__}: {exc}")

    graph_ready, graph_status = sharepoint_graph_status()
    if graph_ready:
        try:
            return download_sharepoint_file_graph(url, timeout=timeout)
        except Exception as exc:
            errors.append(f"Microsoft Graph: {type(exc).__name__}: {exc}")
    else:
        errors.append(graph_status)

    detail = " | ".join(errors[-4:])
    raise PermissionError(
        "SharePoint/OneDrive file tidak dapat dibaca. Anonymous download gagal. "
        "Untuk private corporate SharePoint, configure Microsoft Graph pada .streamlit/secrets.toml; "
        "alternatifnya gunakan Anyone-with-link atau Upload Excel/CSV. " + detail
    )



def _local_file_path(text: str) -> Path:
    raw = str(text or "").strip().strip('"')
    if raw.lower().startswith("file://"):
        parsed = urlparse(raw)
        raw = unquote(parsed.path or "")
        if os.name == "nt" and re.match(r"^/[A-Za-z]:/", raw):
            raw = raw[1:]
    return Path(raw).expanduser()


def _read_local_file(path_text: str):
    path = _local_file_path(path_text)
    if not path.exists():
        raise FileNotFoundError(f"Local Excel/CSV file tidak ditemukan: {path}")
    if not path.is_file():
        raise ValueError(f"Local source bukan file: {path}")
    data = path.read_bytes()
    fmt = _detect_format(data, path.name, "text/csv" if path.suffix.lower() == ".csv" else "")
    return data, fmt, f"Local file · {path.name}"

def _json_rows_to_frame(payload) -> pd.DataFrame:
    """Normalize common Power Automate / API JSON shapes to a flat dataframe."""
    data = payload
    # Unwrap common envelopes produced by Power Automate, Graph, and simple APIs.
    for _ in range(4):
        if isinstance(data, dict):
            found = None
            for key in ("value", "items", "rows", "data", "body"):
                if isinstance(data.get(key), list):
                    found = data[key]
                    break
                if isinstance(data.get(key), dict):
                    found = data[key]
                    break
            if found is None:
                # A single object is still a valid one-row dataset.
                return pd.json_normalize([data], sep=".")
            data = found
            continue
        break
    if isinstance(data, list):
        if not data:
            return pd.DataFrame()
        return pd.json_normalize(data, sep=".")
    if isinstance(data, dict):
        return pd.json_normalize([data], sep=".")
    raise ValueError("JSON endpoint tidak mengembalikan array/object tabular yang dapat dibaca.")


def _read_generic_remote_data(url: str, timeout: int = 45):
    """Read a public CSV/Excel/JSON endpoint, including Power Automate bridge URLs."""
    r = requests.get(
        url,
        timeout=timeout,
        allow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 Powerplant-Engineering-Control-Center/4.7.3",
            "Accept": "application/json,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*",
        },
    )
    if r.status_code in (401, 403) or _looks_like_login_html(r):
        raise PermissionError("Remote data endpoint meminta autentikasi.")
    r.raise_for_status()
    ctype = (r.headers.get("Content-Type") or "").lower()
    body = r.content or b""
    stripped = body.lstrip()
    if "application/json" in ctype or stripped.startswith((b"{", b"[")):
        try:
            return [("Remote JSON bridge", _json_rows_to_frame(r.json()))]
        except Exception as exc:
            raise ValueError(f"JSON bridge tidak dapat dibaca: {exc}") from exc
    fmt = _detect_format(body, r.url or url, ctype)
    if fmt == "csv":
        return [("Remote CSV bridge", pd.read_csv(BytesIO(body)))]
    book = pd.ExcelFile(BytesIO(body))
    frames = []
    for tab in book.sheet_names:
        try:
            frames.append((f"Remote Excel bridge · {tab}", pd.read_excel(book, sheet_name=tab)))
        except Exception:
            pass
    if not frames:
        raise ValueError("Remote Excel berhasil diunduh tetapi worksheet tidak dapat dibaca.")
    return frames


def dataframes_from_remote_file(url: str):
    """Return [(label, dataframe), ...] for supported remote/local data sources."""
    url = normalize_source_url(url)
    kind = source_kind(url)
    if kind == "microsoft_list":
        return dataframes_from_microsoft_list(url)
    if kind == "sharepoint":
        data, fmt, label = download_sharepoint_file(url)
    elif kind == "file_url":
        # File URLs may also return JSON when used as a Power Automate/API bridge.
        return _read_generic_remote_data(url)
    elif kind == "remote_data":
        return _read_generic_remote_data(url)
    elif kind == "local_file":
        data, fmt, label = _read_local_file(url)
    else:
        raise ValueError("Bukan Google/Microsoft List/SharePoint/direct/local Excel/CSV/JSON source yang didukung.")

    if fmt == "csv":
        return [(label + " · CSV", pd.read_csv(BytesIO(data)))]

    book = pd.ExcelFile(BytesIO(data))
    frames = []
    for tab in book.sheet_names:
        try:
            df = pd.read_excel(book, sheet_name=tab)
        except Exception:
            continue
        frames.append((f"{label} · {tab}", df))
    if not frames:
        raise ValueError("Workbook berhasil diunduh tetapi tidak ada worksheet yang dapat dibaca.")
    return frames


def dataframes_from_uploaded_file(uploaded):
    """Read Streamlit UploadedFile (Excel or CSV) into labeled dataframes."""
    if uploaded is None:
        return []
    name = (getattr(uploaded, "name", "uploaded") or "uploaded").lower()
    data = uploaded.getvalue()
    if name.endswith(".csv"):
        return [(f"Uploaded file · {getattr(uploaded, 'name', 'CSV')}", pd.read_csv(BytesIO(data)))]
    book = pd.ExcelFile(BytesIO(data))
    frames = []
    for tab in book.sheet_names:
        try:
            frames.append((f"Uploaded file · {tab}", pd.read_excel(book, sheet_name=tab)))
        except Exception:
            pass
    return frames
