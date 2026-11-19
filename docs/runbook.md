# Operations runbook

Each section matches a Prometheus alert. Escalate to the on-call site data engineer if the check fails twice.

## ConnectorDown

**Symptom:** No metrics from a connector for 2 minutes.

1. `docker compose ps` — confirm the container is up.
2. `docker compose logs --tail=100 <service>` — look for auth, broker, or OPC UA endpoint errors.
3. Restart: `docker compose restart mqtt-connector` (or opcua / modbus).
4. If Mosquitto/Redpanda is down, fix the dependency first; connectors will reconnect with backoff.

## IngestStalled

**Symptom:** `minehub_last_message_unixtime` older than 5 minutes for a source.

1. Check the simulator / plant link (OPC UA endpoint, Modbus host, MQTT topic).
2. Verify Redpanda is accepting produce (`redpanda-console` or topic end offsets).
3. Confirm the connector is not stuck validating (spike in `minehub_validation_failures_total`).

## ConsumerLagHigh

**Symptom:** Stream-processor lag > 10,000 messages.

1. Check CPU/memory on `stream-processor`; scale vertically on the site host if saturated.
2. Look for poison messages looping (DLQ growth).
3. Temporarily pause simulators if recovering from an outage backlog.

## DiskFilling

**Symptom:** Root filesystem < 20% free.

1. `df -h` and `docker system df`.
2. Prune old images/volumes carefully; confirm Timescale compression/retention policies are active.
3. Rotate `/var/backups/minehub` with `backup_retain_days`.

## BackupMissed

**Symptom:** No successful backup in 26 h.

1. Inspect `/var/log/minehub-backup.log` and cron for `minehub-backup`.
2. Run `/usr/local/bin/backup.sh` manually; fix Postgres connectivity if dump fails.
3. Confirm `last_success.unixtime` updates under the backup directory.

## DLQGrowing

**Symptom:** Dead-letter rate > 1% of input.

1. Sample DLQ payloads / `ops.quarantine` for the failing source.
2. Fix mapping (vendor JSON, tag quality, Modbus word order) or widen contract ranges if data is legitimate.
3. Replay only after the root cause is fixed.

## TagStale

**Symptom:** Critical plant / OPC UA source quiet for > 10 minutes.

1. Check OPC UA server health and network path from the connector host.
2. Browse tags with the connector browser helper; compare to `config/tags.yaml`.
3. Restart `opcua-connector`; if quality is BAD, escalate to plant control.

## DQFailure

**Symptom:** Critical row in `ops.dq_results` with `passed = false`.

1. Query `ops.dq_results` for `check_name`, `failing_rows`, `details`.
2. For tonnes-balance / time-usage failures, inspect the underlying mart for the shift.
3. Quarantine or correct source data; re-run dbt + DQ via Dagster before publishing the shift report.
