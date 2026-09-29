"""Opt-in OSV metadata adapter. Not connected to automatic repository transmission."""

import json
import re
import tomllib
from datetime import UTC, datetime
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field


class Dependency(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    ecosystem: Literal["PyPI", "npm"]
    name: str = Field(pattern=r"^[@A-Za-z0-9][A-Za-z0-9_./@-]{0,159}$")
    version: str = Field(pattern=r"^[0-9][A-Za-z0-9.+_-]{0,79}$")


def from_lockfile(name: str, text: str) -> list[Dependency]:
    if len(text.encode()) > 256 * 1024:
        raise ValueError("LOCKFILE_TOO_LARGE")
    items: list[Dependency] = []
    if name == "uv.lock":
        for package in tomllib.loads(text).get("package", []):
            if package.get("source") != {"registry": "https://pypi.org/simple"}:
                continue
            items.append(
                Dependency(ecosystem="PyPI", name=package["name"], version=package["version"])
            )
    elif name == "package-lock.json":
        lock = json.loads(text)
        if lock.get("lockfileVersion") not in (2, 3):
            raise ValueError("UNSUPPORTED_LOCKFILE")
        for path, package in lock.get("packages", {}).items():
            if (
                not path
                or "node_modules/" not in path
                or package.get("link")
                or not str(package.get("resolved", "")).startswith("https://registry.npmjs.org/")
            ):
                continue
            package_name = path.rsplit("node_modules/", 1)[1]
            items.append(Dependency(ecosystem="npm", name=package_name, version=package["version"]))
    else:
        raise ValueError("UNSUPPORTED_LOCKFILE")
    unique = list(dict.fromkeys(items))
    if len(unique) > 100:
        raise ValueError("DEPENDENCY_LIMIT")
    return unique


async def query_osv(
    dependency: Dependency,
    *,
    approved_metadata_transfer: bool,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, object]:
    if not approved_metadata_transfer:
        raise ValueError("METADATA_CONSENT_REQUIRED")
    async with httpx.AsyncClient(
        transport=transport,
        trust_env=False,
        follow_redirects=False,
        timeout=5,
    ) as http:
        async with http.stream(
            "POST",
            "https://api.osv.dev/v1/query",
            json={
                "package": {"ecosystem": dependency.ecosystem, "name": dependency.name},
                "version": dependency.version,
            },
        ) as response:
            response.raise_for_status()
            raw = bytearray()
            async for chunk in response.aiter_bytes():
                raw.extend(chunk)
                if len(raw) > 256 * 1024:
                    raise ValueError("OSV_RESPONSE_TOO_LARGE")
    data = json.loads(raw)
    vulns = data.get("vulns", [])
    if not isinstance(vulns, list):
        raise ValueError("INVALID_OSV_RESPONSE")
    records = []
    for item in vulns[:100]:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", item["id"])
        ):
            raise ValueError("INVALID_OSV_RESPONSE")
        if not item.get("withdrawn"):
            records.append({"id": item["id"], "modified": str(item.get("modified", ""))[:40]})
    return {
        "dependency": dependency.model_dump(),
        "source": "OSV",
        "checked_at": datetime.now(UTC).isoformat(),
        "records": records,
        "complete": not data.get("next_page_token") and len(vulns) <= 100,
        "reachability": "NOT_CHECKED",
        "match": "PROVIDER_VERSION_MATCH",
    }
