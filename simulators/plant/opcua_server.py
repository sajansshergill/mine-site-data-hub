"""Plant OPC UA server exposing crusher/mill tags with drift and noise."""
from __future__ import annotations

import asyncio
import logging
import math
import random
from datetime import UTC, datetime

from asyncua import Server, ua

from minehub_common.logging import setup_logging
from minehub_common.settings import get_settings

SERVICE = "sim-plant-opcua"
log = logging.getLogger(SERVICE)

# baseline engineering values; drift + noise applied each tick
BASELINES: dict[str, float] = {
    "Crusher.Throughput": 1800.0,
    "Crusher.Power": 4200.0,
    "Crusher.Running": 1.0,
    "Mill.Feed": 1650.0,
    "Mill.Power": 9800.0,
    "Mill.BearingTemp": 62.0,
}


def _parse_browse_name(node_id: str) -> str:
    # "ns=2;s=Crusher.Throughput" -> Crusher.Throughput
    if ";s=" in node_id:
        return node_id.split(";s=", 1)[1]
    return node_id


async def main() -> None:
    setup_logging(SERVICE)
    s = get_settings()
    cfg = s.load_yaml("tags.yaml")["opcua"]
    rng = random.Random(7)

    server = Server()
    await server.init()
    server.set_endpoint(s.opcua_endpoint)
    server.set_server_name("MineHub Plant Simulator")

    uri = cfg.get("namespace_uri", "urn:minehub:plant")
    idx = await server.register_namespace(uri)

    objects = server.nodes.objects
    folders: dict[str, ua.Node] = {}
    variables: dict[str, ua.Node] = {}

    for tag in cfg["tags"]:
        browse = _parse_browse_name(tag["node"])
        group, _, leaf = browse.partition(".")
        if group not in folders:
            folders[group] = await objects.add_folder(idx, group)
        parent = folders[group]
        base = BASELINES.get(browse, 0.0)
        var = await parent.add_variable(idx, leaf, float(base))
        await var.set_writable()
        # Keep NodeId string form aligned with tags.yaml where possible
        variables[browse] = var

    log.info("opcua server starting", extra={"extra": {"endpoint": s.opcua_endpoint, "tags": len(variables)}})

    async with server:
        tick = 0
        while True:
            tick += 1
            t = tick / 10.0
            for browse, var in variables.items():
                base = BASELINES.get(browse, 0.0)
                if browse.endswith("Running"):
                    # occasional short stoppages
                    value = 0.0 if (tick % 600) < 20 else 1.0
                elif "BearingTemp" in browse:
                    drift = 0.01 * math.sin(t / 40.0)
                    value = base + drift * 10 + rng.gauss(0, 0.15)
                else:
                    drift = 0.02 * math.sin(t / 25.0 + hash(browse) % 7)
                    noise = rng.gauss(0, base * 0.005 if base else 0.1)
                    value = max(0.0, base * (1.0 + drift) + noise)
                    if browse.startswith("Crusher.") and browse != "Crusher.Running":
                        running_node = variables.get("Crusher.Running")
                        if running_node is not None and float(await running_node.read_value()) < 0.5:
                            value = max(0.0, value * 0.05)
                await var.write_value(float(value))
            if tick % 30 == 0:
                log.debug("opcua tick", extra={"extra": {"ts": datetime.now(UTC).isoformat(), "tick": tick}})
            await asyncio.sleep(1.0 / max(s.sim_speed, 0.01))


if __name__ == "__main__":
    asyncio.run(main())
