"""Discrete-event haul fleet simulation publishing vendor MQTT telemetry."""
from __future__ import annotations

import logging
import random
import time
from collections import deque
from datetime import UTC, datetime

from minehub_common.logging import setup_logging
from minehub_common.settings import get_settings
from simulators.fleet.crusher import DumpPoint
from simulators.fleet.dispatcher import assign_dump, assign_shovel, dump_by_id, shovel_by_id
from simulators.fleet.faults import FaultInjector
from simulators.fleet.publisher import FleetPublisher, to_vendor_payload
from simulators.fleet.road_graph import build_road_graph, interpolate_xy, node_xy, shortest_path, travel_time_s
from simulators.fleet.shovel import Shovel
from simulators.fleet.truck import Truck, TruckState

SERVICE = "sim-fleet"
log = logging.getLogger(SERVICE)
TICK_S = 1.0
SPOT_S = 15.0
PUBLISH_EVERY_S = 2.0


def _make_trucks(eq: dict, road) -> list[Truck]:  # noqa: ANN001
    cfg = eq["trucks"]
    start_node = eq["shovels"][0]["location"]
    x, y = node_xy(road, start_node)
    trucks: list[Truck] = []
    for i in range(1, int(cfg["count"]) + 1):
        trucks.append(
            Truck(
                truck_id=f"{cfg['id_prefix']}{i:02d}",
                empty_speed_kmh=float(cfg["empty_speed_kmh"]),
                loaded_speed_kmh=float(cfg["loaded_speed_kmh"]),
                nominal_payload_t=float(cfg["nominal_payload_t"]),
                x=x + (i % 5) * 8,
                y=y + (i // 5) * 8,
                location=start_node,
                fuel_pct=70.0 + (i % 20),
            )
        )
    return trucks


def _begin_travel(truck: Truck, road, dest: str, loaded: bool, now: float) -> None:  # noqa: ANN001
    src = truck.location or dest
    path = shortest_path(road, src, dest)
    speed = truck.loaded_speed_kmh if loaded else truck.empty_speed_kmh
    duration = max(travel_time_s(road, path, speed), 1.0)
    truck.path = path
    truck.path_progress = 0.0
    truck.state_until = now + duration
    truck.speed_kmh = speed
    truck.state = TruckState.HAUL_FULL if loaded else TruckState.HAUL_EMPTY
    truck.travel_start = now  # type: ignore[attr-defined]


def _update_travel(truck: Truck, road, now: float) -> bool:  # noqa: ANN001
    start = float(getattr(truck, "travel_start", now))
    end = float(truck.state_until)
    span = max(end - start, 1e-6)
    progress = min(1.0, max(0.0, (now - start) / span))
    truck.path_progress = progress
    truck.x, truck.y = interpolate_xy(road, truck.path, progress)
    if now >= end:
        truck.location = truck.path[-1] if truck.path else truck.location
        truck.speed_kmh = 0.0
        truck.path_progress = 1.0
        return True
    return False


def _drop_from_queues(truck_id: str, shovels: list[Shovel], dumps: list[DumpPoint]) -> None:
    for shovel in shovels:
        if truck_id in shovel.queue:
            shovel.queue = deque(x for x in shovel.queue if x != truck_id)
    for dump in dumps:
        if truck_id in dump.queue:
            dump.queue = deque(x for x in dump.queue if x != truck_id)


def main() -> None:
    setup_logging(SERVICE)
    s = get_settings()
    rng = random.Random(42)
    faults = FaultInjector(s.fault_rate, rng)
    road = build_road_graph(s.load_yaml("road_network.yaml"))
    eq = s.load_yaml("equipment.yaml")
    shovels = [Shovel.from_cfg(row) for row in eq["shovels"]]
    dumps = [DumpPoint.from_cfg(row) for row in eq["dumps"]]
    trucks = _make_trucks(eq, road)
    truck_map = {t.truck_id: t for t in trucks}

    publisher = FleetPublisher(s.mqtt_host, s.mqtt_port)
    publisher.connect()

    for truck in trucks:
        shovel = assign_shovel(truck, shovels)
        assert shovel is not None
        shovel.enqueue(truck.truck_id)
        truck.state = TruckState.QUEUE
        truck.location = shovel.location
        truck.x, truck.y = node_xy(road, shovel.location)

    sim_t = 0.0
    last_pub = -PUBLISH_EVERY_S
    log.info("fleet sim started", extra={"extra": {"trucks": len(trucks), "fault_rate": s.fault_rate}})

    try:
        while True:
            step = TICK_S / max(s.sim_speed, 0.01)
            wall = time.time()
            now = sim_t

            for shovel in shovels:
                started = shovel.try_start_service(now, rng)
                if started:
                    t = truck_map[started]
                    t.state = TruckState.SPOT
                    t.state_until = now + SPOT_S
                    t.speed_kmh = 0.0
                finished = shovel.finish_if_due(now)
                if finished:
                    t = truck_map[finished]
                    t.payload_t = t.nominal_payload_t * rng.uniform(0.92, 1.05)
                    t.material = shovel.material
                    dump = assign_dump(t, dumps)
                    assert dump is not None
                    _begin_travel(t, road, dump.location, loaded=True, now=now)

            for dump in dumps:
                started = dump.try_start_service(now, rng)
                if started:
                    t = truck_map[started]
                    t.state = TruckState.DUMP
                    t.state_until = dump.busy_until
                    t.speed_kmh = 0.0
                finished = dump.finish_if_due(now)
                if finished:
                    t = truck_map[finished]
                    t.payload_t = 0.0
                    shovel = assign_shovel(t, shovels)
                    assert shovel is not None
                    _begin_travel(t, road, shovel.location, loaded=False, now=now)

            for truck in trucks:
                if truck.state == TruckState.BREAKDOWN:
                    if now >= truck.breakdown_until:
                        truck.state = TruckState.QUEUE
                        truck.engine_on = True
                        shovel = shovel_by_id(shovels, truck.assigned_shovel) or assign_shovel(truck, shovels)
                        if shovel:
                            shovel.enqueue(truck.truck_id)
                            truck.location = shovel.location
                            truck.x, truck.y = node_xy(road, shovel.location)
                    continue

                if truck.state == TruckState.SPOT and now >= truck.state_until:
                    truck.state = TruckState.LOAD
                    shovel = shovel_by_id(shovels, truck.assigned_shovel)
                    if shovel and shovel.serving == truck.truck_id:
                        truck.state_until = shovel.begin_load(now, rng)

                if truck.state in (TruckState.HAUL_FULL, TruckState.HAUL_EMPTY):
                    if _update_travel(truck, road, now):
                        if truck.state == TruckState.HAUL_FULL:
                            dump = dump_by_id(dumps, truck.assigned_dump) or assign_dump(truck, dumps)
                            assert dump is not None
                            dump.enqueue(truck.truck_id)
                            truck.state = TruckState.QUEUE_DUMP
                        else:
                            shovel = shovel_by_id(shovels, truck.assigned_shovel) or assign_shovel(truck, shovels)
                            assert shovel is not None
                            shovel.enqueue(truck.truck_id)
                            truck.state = TruckState.QUEUE

                truck.burn_fuel(TICK_S)

                decision = faults.roll()
                if decision.kind == "breakdown" and truck.state not in (
                    TruckState.BREAKDOWN,
                    TruckState.LOAD,
                    TruckState.DUMP,
                    TruckState.SPOT,
                ):
                    truck.state = TruckState.BREAKDOWN
                    truck.engine_on = False
                    truck.speed_kmh = 0.0
                    truck.breakdown_until = now + decision.breakdown_s
                    _drop_from_queues(truck.truck_id, shovels, dumps)

            if now - last_pub >= PUBLISH_EVERY_S:
                last_pub = now
                wall_ts = datetime.now(UTC)
                for truck in trucks:
                    decision = faults.roll()
                    if decision.kind == "breakdown":
                        decision = type(decision)(kind="none")
                    vendor = to_vendor_payload(truck.telemetry(), wall_ts)
                    for msg in faults.apply_to_payload(vendor, decision, wall_ts):
                        publisher.publish(truck.truck_id or "UNKNOWN", msg)

            sim_t += TICK_S
            time.sleep(max(0.0, step - (time.time() - wall)))
    except KeyboardInterrupt:
        log.info("fleet sim stopping")
    finally:
        publisher.close()


if __name__ == "__main__":
    main()
