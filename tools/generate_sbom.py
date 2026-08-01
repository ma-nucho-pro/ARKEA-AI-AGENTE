"""Generate the distributable CycloneDX inventory from both lock files."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote
import uuid


ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "arkea_ai_desktop_odysseus_overlay"
PYTHON_LOCK = OVERLAY / "requirements-lock.txt"
NPM_LOCK = OVERLAY / "desktop" / "package-lock.json"
OUTPUT = ROOT / "SBOM-ARKEA-OMNIAGENT.json"


def purl_name(value: str) -> str:
    return quote(value, safe="@/")


def component_key(component: dict) -> tuple[str, str, str]:
    return (
        component.get("purl", "").split(":", 1)[0],
        component.get("name", "").lower(),
        component.get("version", ""),
    )


def python_components() -> list[dict]:
    result = []
    pattern = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s;]+)")
    for raw in PYTHON_LOCK.read_text(encoding="utf-8").splitlines():
        match = pattern.match(raw.strip())
        if not match:
            continue
        name, version = match.groups()
        normalized = name.lower().replace("_", "-")
        result.append(
            {
                "type": "library",
                "name": name,
                "version": version,
                "purl": f"pkg:pypi/{purl_name(normalized)}@{version}",
                "properties": [{"name": "arkea:ecosystem", "value": "python"}],
            }
        )
    return result


def npm_components() -> list[dict]:
    lock = json.loads(NPM_LOCK.read_text(encoding="utf-8"))
    result = []
    for package_path, package in lock.get("packages", {}).items():
        if not package_path or "node_modules/" not in package_path:
            continue
        name = package_path.rsplit("node_modules/", 1)[1]
        version = str(package.get("version") or "").strip()
        if not name or not version:
            continue
        item = {
            "type": "library",
            "name": name,
            "version": version,
            "purl": f"pkg:npm/{purl_name(name)}@{version}",
            "scope": "optional" if package.get("optional") else "required",
            "properties": [
                {"name": "arkea:ecosystem", "value": "npm"},
                {
                    "name": "arkea:developmentDependency",
                    "value": str(bool(package.get("dev"))).lower(),
                },
            ],
        }
        license_id = str(package.get("license") or "").strip()
        if license_id:
            item["licenses"] = [{"license": {"id": license_id}}]
        integrity = str(package.get("integrity") or "")
        if integrity.startswith("sha512-"):
            item["properties"].append(
                {"name": "arkea:npmIntegrity", "value": integrity}
            )
        result.append(item)
    return result


def main() -> None:
    lock_digest = hashlib.sha256(
        PYTHON_LOCK.read_bytes() + b"\0" + NPM_LOCK.read_bytes()
    ).hexdigest()
    components = [
        {
            "type": "application",
            "name": "Odysseus",
            "version": "source-snapshot-2026-07-29",
            "licenses": [{"license": {"id": "AGPL-3.0-or-later"}}],
            "externalReferences": [
                {
                    "type": "vcs",
                    "url": "https://github.com/pewdiepie-archdaemon/odysseus",
                }
            ],
        },
        {
            "type": "application",
            "name": "OmniRoute",
            "version": "3.8.48",
            "licenses": [{"license": {"id": "MIT"}}],
            "hashes": [
                {
                    "alg": "SHA-256",
                    "content": "d3295cded2cc6782afaddfef8ff4d4501d09ffc3a7d2ff2acb7955f7884b1806",
                }
            ],
            "externalReferences": [
                {
                    "type": "distribution",
                    "url": "https://github.com/diegosouzapw/OmniRoute/releases/download/v3.8.48/OmniRoute.Setup.3.8.48.exe",
                }
            ],
        },
        {
            "type": "application",
            "name": "Ollama",
            "version": "0.32.5",
            "licenses": [{"license": {"id": "MIT"}}],
            "hashes": [
                {
                    "alg": "SHA-256",
                    "content": "b7eeef038ddcbd09ac665b11872baff1bc9b42794be41b5ef187b2f4b16a4498",
                }
            ],
            "externalReferences": [
                {
                    "type": "distribution",
                    "url": "https://github.com/ollama/ollama/releases/download/v0.32.5/OllamaSetup.exe",
                }
            ],
        },
    ]
    components.extend(python_components())
    components.extend(npm_components())
    deduplicated = {
        component_key(component): component for component in components
    }
    ordered = sorted(
        deduplicated.values(),
        key=lambda item: (
            item.get("properties", [{}])[0].get("value", ""),
            item["name"].lower(),
            item["version"],
        ),
    )
    document = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, lock_digest)}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "ARKEA lockfile SBOM generator",
                        "version": "1",
                    }
                ]
            },
            "component": {
                "type": "application",
                "name": "ARKEA AI OmniAgent",
                "version": "0.1.0",
                "licenses": [{"license": {"id": "AGPL-3.0-or-later"}}],
            },
            "properties": [
                {"name": "arkea:lockDigestSha256", "value": lock_digest},
                {"name": "arkea:inventoryScope", "value": "python-and-npm-lockfiles-plus-sidecars"},
            ],
        },
        "components": ordered,
    }
    OUTPUT.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"{OUTPUT}: {len(ordered)} components")


if __name__ == "__main__":
    main()
