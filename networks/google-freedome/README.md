# Google Jupiter/Freedome-inspired fabric

The data includes two small snapshots with the same physical topology:
[OSPF](snapshots/small-ospf) and [BGP](snapshots/small-bgp). Each has 138
routers and 513 physical links. Cluster borders export /16 aggregates;
rack /24s remain inside their cluster.

[Source notes](SOURCES.md) identify the published design and modeled
choices. [Construction notes](CONSTRUCTION.md) explain how the generator
was written. [Validation notes](VALIDATION.md) describe the checks applied
to the data. Repository-authored material uses [Apache-2.0](LICENSE).

```text
rack -> aggregation -> spine -> cluster border router
     -> Datacenter Freedome -> Campus Freedome -> WAN
```

## Reproduce the data

From the repository root:

```bash
python3 networks/google-freedome/generate.py \
  --cluster-protocol ospf --output build/freedome-ospf
python3 networks/google-freedome/generate.py \
  --cluster-protocol bgp --output build/freedome-bgp
```

OSPF is the default. Generation uses Python's standard library and refuses
to overwrite a nonempty config directory. Each output contains configs,
explicit layer-1 wiring, and a manifest of parameters, node roles,
addresses, peers, and failed interfaces.

## Larger examples

These are topology dimensions. Each can use either cluster protocol.

| Example | Campuses | Buildings per campus | Clusters per building | Racks per cluster | Aggregation | Spines | Prefixes per rack | Routers |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Small | 2 | 2 | 1 | 4 | 2 | 2 | 1 | 138 |
| Medium | 2 | 3 | 8 | 64 | 4 | 8 | 4 | 3,874 |
| Large | 2 | 4 | 10 | 64 | 4 | 8 | 4 | 6,402 |

For example:

```bash
python3 networks/google-freedome/generate.py \
  --cluster-protocol bgp --campuses 2 --buildings 3 --clusters 8 \
  --racks 64 --aggregation 4 --spines 8 --prefixes-per-rack 4 \
  --output build/freedome-medium-bgp
```

## Optional behavioral checks

With Pybatfish installed and a local Batfish service:

```bash
python3 networks/google-freedome/verify.py \
  --path build/freedome-bgp --snapshot freedome-bgp \
  --upload --compute --report working/freedome-bgp-validation.md
```

The network-local [dependency file](requirements.txt) contains Pybatfish.
The helper checks this model's routing invariants, loop freedom, and
endpoint reachability. `--quick` uses representative traces in place of
full symbolic checks. Failure scenarios are `cluster-link`, `dc-block`,
`campus-wan`, and `cluster-isolated`.
