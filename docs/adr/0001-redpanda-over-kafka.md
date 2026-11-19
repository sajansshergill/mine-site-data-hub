# ADR 0001: Redpanda over Apache Kafka

## Status

Accepted

## Context

The site host is a single on-prem Linux box. We need Kafka-compatible topics, a schema registry, and low operational overhead for a small ops team.

## Decision

Use **Redpanda** (Kafka API) instead of Apache Kafka + ZooKeeper/KRaft.

## Consequences

- Same `confluent-kafka` client code and Avro registry workflow.
- Simpler single-process deployment in Docker Compose.
- Fewer knobs for partitioning and ISR tuning — acceptable for one-site volume.
- If the company later centralizes on a managed Kafka cluster, producers/consumers can point at new brokers with minimal code change.
