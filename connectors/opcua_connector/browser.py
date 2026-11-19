"""Browse the OPC UA address space and verify nodes listed in tags.yaml."""
from __future__ import annotations

import logging
from typing import Any

from asyncua import Client, ua

log = logging.getLogger("opcua-browser")


def _node_id_str(node_id: str) -> str:
    return node_id.strip()


async def verify_tags(client: Client, tags: list[dict[str, Any]]) -> list[str]:
    """Return list of missing node ids from tags.yaml opcua.tags."""
    missing: list[str] = []
    for tag in tags:
        node_id = _node_id_str(tag["node"])
        try:
            node = client.get_node(node_id)
            await node.read_browse_name()
        except (ua.UaError, OSError, TimeoutError) as exc:
            log.warning("tag missing", extra={"extra": {"node": node_id, "error": str(exc)}})
            missing.append(node_id)
    return missing


async def browse_tree(client: Client, root: Any | None = None, depth: int = 3) -> list[str]:
    """Return browse paths (display names) up to depth for diagnostics."""
    paths: list[str] = []

    async def _walk(node: Any, prefix: str, remaining: int) -> None:
        try:
            name = (await node.read_browse_name()).Name
        except Exception:  # noqa: BLE001
            name = "?"
        path = f"{prefix}/{name}" if prefix else name
        paths.append(path)
        if remaining <= 0:
            return
        try:
            children = await node.get_children()
        except Exception:  # noqa: BLE001
            return
        for child in children:
            await _walk(child, path, remaining - 1)

    start = root or client.nodes.objects
    await _walk(start, "", depth)
    return paths
