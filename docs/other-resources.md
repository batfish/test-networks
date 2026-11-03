# Other public resources

These references are candidates for additional source records. Their
implementations are not bundled.

| Resource | Inputs or output | Source version | Observed repository license |
|---|---|---|---|
| [REAL artifact](https://github.com/XJTU-NetVerify/REAL-artifact-evaluation) | FRR fat trees, Topology Zoo WANs, and connected copies | `9186ddee0f2746cf6e4496416b0d13921be6f627` | No repository license advertised |
| [S2 benchmark](https://github.com/XJTU-NetVerify/s2-benchmark) | BGP/OSPF fat-tree config generator | `66d1725df14ee222a45dae245f3659f5c1550620` | No repository license advertised |
| [ACORN benchmarks](https://github.com/divya-urs/ACORN_benchmarks) | Original benchmark family referenced by S2 | Consult upstream | Not evaluated for bundling |
| [Propane](https://github.com/rabeckett/propane) | Topology/policy constructors and Quagga output | `3a7bc9b2da0da0c3a3d3ea10db6c8d9bdef25d86` | MIT |

REAL's
[Batfish generator](https://github.com/XJTU-NetVerify/REAL-artifact-evaluation/blob/9186ddee0f2746cf6e4496416b0d13921be6f627/batfish/scripts/config/confgen.py)
supports `fattree`, `topozoo`, and `dupzoo`. The
[scaling guide](scaling.md) describes its duplication method.

S2 adapts the ACORN family and offers shortest-path and valley-free
routing profiles. Record the selected profile's originated-prefix
scope when importing a variant.

Propane provides topology and policy inputs for configuration synthesis.
A contribution should preserve its MIT notice and identify those inputs.

For referenced code whose redistribution terms are not established,
retain the upstream link and source revision until a contributor supplies
the relevant license or permission record.
