import ipaddress
import socket
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin, urlsplit


MAX_JSON_RESPONSE = 10 * 1024 * 1024
MAX_BINARY_RESPONSE = 25 * 1024 * 1024
LOCAL_SERVICE_PORTS = {11434, 20128, 8188, 7860, 9000, 9222}


def safe_path(root: str | Path, relative: str | Path) -> Path:
    root_path = Path(root).expanduser().resolve()
    relative_path = Path(relative)
    if relative_path.is_absolute():
        raise ValueError("La ruta debe ser relativa al workspace")
    target = (root_path / relative_path).resolve()
    try:
        target.relative_to(root_path)
    except ValueError as exc:
        raise ValueError("Ruta fuera del workspace permitido") from exc
    return target


def is_sensitive_command(cmd: str) -> bool:
    blocked = ["rm -rf", "format ", "del /s", "shutdown", "reboot", "mkfs", ":(){ :|:& };:"]
    low = cmd.lower()
    return any(x in low for x in blocked)


def sanitize_svg(svg: str) -> str:
    if "<!DOCTYPE" in svg.upper() or "<!ENTITY" in svg.upper():
        raise ValueError("SVG no seguro")
    root = ET.fromstring(svg)
    blocked = {"script", "style", "foreignObject", "iframe", "object", "embed", "audio", "video"}
    safe_embedded_images = ("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/gif;base64,", "data:image/webp;base64,")
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag.split("}")[-1] in blocked:
                parent.remove(child)
        for key in list(parent.attrib):
            local_key = key.split("}")[-1].lower()
            value = parent.attrib[key].strip().lower()
            unsafe_link = local_key in {"href", "src"} and not (value.startswith("#") or value.startswith(safe_embedded_images))
            unsafe_style = local_key == "style" and "url(" in value
            if local_key.startswith("on") or unsafe_link or unsafe_style:
                del parent.attrib[key]
    return ET.tostring(root, encoding="unicode")


async def read_upload_limited(upload, max_bytes: int) -> bytes:
    chunks = []
    total = 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValueError(f"El archivo supera el límite de {max_bytes // (1024 * 1024)} MB")
        chunks.append(chunk)
    return b"".join(chunks)


def _resolved_ips(hostname: str):
    try:
        return {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(hostname, None)}
    except (socket.gaierror, ValueError) as exc:
        raise ValueError("No se pudo resolver el host remoto") from exc


def validate_outbound_url(url: str, *, allow_local: bool = False) -> str:
    parsed = urlsplit(str(url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Solo se permiten URL HTTP/HTTPS")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("URL remota no válida")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    addresses = _resolved_ips(parsed.hostname)
    for address in addresses:
        local = (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        )
        if local and not (allow_local and address.is_loopback and port in LOCAL_SERVICE_PORTS):
            raise ValueError("La URL apunta a una red local o reservada no permitida")
    return parsed.geturl()


def guarded_request(method: str, url: str, *, allow_local: bool = False,
                    max_response_bytes: int = MAX_JSON_RESPONSE, max_redirects: int = 3, **kwargs):
    import requests

    current = validate_outbound_url(url, allow_local=allow_local)
    kwargs.pop("allow_redirects", None)
    kwargs.pop("stream", None)
    for redirect_count in range(max_redirects + 1):
        response = requests.request(method, current, allow_redirects=False, stream=True, **kwargs)
        if response.is_redirect or response.is_permanent_redirect:
            if redirect_count >= max_redirects:
                response.close()
                raise ValueError("Demasiadas redirecciones")
            location = response.headers.get("location", "")
            response.close()
            current = validate_outbound_url(urljoin(current, location), allow_local=allow_local)
            continue

        declared = response.headers.get("content-length")
        if declared:
            try:
                if int(declared) > max_response_bytes:
                    response.close()
                    raise ValueError("La respuesta remota supera el tamaño permitido")
            except ValueError as exc:
                if "supera" in str(exc):
                    raise

        body = bytearray()
        for chunk in response.iter_content(64 * 1024):
            body.extend(chunk)
            if len(body) > max_response_bytes:
                response.close()
                raise ValueError("La respuesta remota supera el tamaño permitido")
        response._content = bytes(body)
        response._content_consumed = True
        return response
    raise ValueError("No se pudo completar la solicitud remota")
