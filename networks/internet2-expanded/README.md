# Expanded Internet2 graph

The [two-copy snapshot](snapshots/two-copies) contains twenty routers and
39 links, composed from the published Internet2 router graph. Each copy
keeps the original nineteen adjacencies, and one seeded connector joins
the copies. [SOURCES.md](SOURCES.md) records the seed, source method, and
local changes. Repository-authored material uses [Apache-2.0](LICENSE).

The configs use synthetic single-hop eBGP, unique ASNs, and service /32
origins. They replace the original IS-IS, iBGP, prefix policies, and external
advertisements. Parallel logical circuits, bandwidth, and geographical
distance are not modeled.

## Reproduce or enlarge

From the repository root:

```bash
python3 networks/internet2-expanded/generate.py \
  --base networks/internet2/topology.json \
  --copies 2 --join random --seed 0 \
  --output build/internet2-two-copies
```

The helper is local to this network and uses Python's standard library.
The manifest records source and helper hashes, a source-node map, copy
count, seed, connection method, addresses, ASNs, and component count.
`--join chain`, `ring`, and `disconnected` select other compositions.
`--gateway` chooses the connector site for chain and ring.

The [scaling notes](../../docs/scaling.md) explain the published method
and the additional work required to preserve original configuration
policy. [Validation notes](VALIDATION.md) cover the saved example.
