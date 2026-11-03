# Test networks

Network configuration data for Batfish and other network analysis tools.
Each network directory contains its snapshots or archives, a README,
plain-text source notes, checksums, and the relevant license texts.
Some directories include a small helper for reproducing or enlarging
that network.

## Networks

| Network | Data | Source notes |
|---|---|---|
| [Google Jupiter/Freedome](networks/google-freedome/README.md) | OSPF and BGP fabric snapshots; local generator | [Sources](networks/google-freedome/SOURCES.md) |
| [Internet2](networks/internet2/README.md) | Ten published Juniper router configs and inferred topology | [Sources](networks/internet2/SOURCES.md) |
| [Expanded Internet2 graph](networks/internet2-expanded/README.md) | A two-copy example; local reproduction helper | [Sources](networks/internet2-expanded/SOURCES.md) |
| [Archived Batfish fat tree](networks/batfish-fattree20/README.md) | Original 500-router ZIP | [Sources](networks/batfish-fattree20/SOURCES.md) |
| [Archived Batfish ring](networks/batfish-ring200/README.md) | Original 200-router ZIP | [Sources](networks/batfish-ring200/SOURCES.md) |
| [Archived Batfish jellyfish](networks/batfish-jellyfish190/README.md) | Original 190-router ZIP | [Sources](networks/batfish-jellyfish190/SOURCES.md) |
| [Archived Batfish full mesh](networks/batfish-fullmesh100/README.md) | Original 100-router ZIP | [Sources](networks/batfish-fullmesh100/SOURCES.md) |

[Other public resources](docs/other-resources.md) include REAL, S2/ACORN,
and Propane. The [scaling notes](docs/scaling.md) distinguish reuse of a
topology from preservation of its original routing policy.

## Use the data

Batfish accepts a directory or ZIP containing `configs/`. With Pybatfish
installed and a local Batfish service:

```python
from pybatfish.client.session import Session

bf = Session(host="localhost")
bf.set_network("test-networks")
bf.init_snapshot("networks/internet2/snapshot", name="internet2")
bf.generate_dataplane()
```

Network READMEs describe the input layout, transformations, and known
modeling limits. Internet2's historical raw files parse partially in the
tested Batfish version; see its [validation notes](networks/internet2/VALIDATION.md).

## Contribute

Add data and a README under `networks/<name>/`. Record the original source,
version, license, changes, and known limitations in `SOURCES.md`.
Keep any reproduction helpers and dependency files beside that network.
See [CONTRIBUTING.md](CONTRIBUTING.md) and the
[provenance notes](docs/provenance.md).

Repository-authored material uses Apache-2.0. Upstream licenses are kept
with their networks and indexed in [THIRD_PARTY.md](THIRD_PARTY.md).
