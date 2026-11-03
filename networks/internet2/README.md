# Published Internet2 snapshot

Ten raw Juniper router configs are copied byte-for-byte from the pinned
Expresso artifact. Its README attributes their earlier source to Bagpipe
and describes them as lightly cleaned. [SOURCES.md](SOURCES.md) records
those references and their revisions. The original operator capture date
and byte-level lineage are unknown.

The [snapshot](snapshot) contains only vendor configs. Expresso's
supplemental external-route XML is not injected. External peer state is
therefore incomplete. The local [licenses](licenses) preserve the
immediate upstream and reported earlier source notices.

[Validation notes](VALIDATION.md) describe partial parser compatibility
in the tested Batfish version. The raw files are retained as published.

## Router graph for scaling

[topology.json](topology.json) is derived from the pinned
[inferred interface topology](upstream/topology.txt). The local
[extraction helper](build_graph.py) collapses 108 logical interface
circuits into nineteen router adjacencies. The source has 215 directed
entries; one circuit lacks a reverse entry. The simple graph is undirected.

From the repository root:

```bash
python3 networks/internet2/build_graph.py \
  --input networks/internet2/upstream/topology.txt \
  --output networks/internet2/topology.json
```

The [scaling notes](../../docs/scaling.md) describe this transformation
and the separate topology-derived example. The original configs and
inferred topology remain the source data.
