# ADR-0001: Canonical Repository Tree

## Decision

Use one `src/nexus_cove` package as the sole source of truth. Git provides historical versions.

## Rationale

The supplied archive contained three overlapping source trees and multiple byte-identical files. Duplicate implementations created ambiguity about which code was authoritative.
