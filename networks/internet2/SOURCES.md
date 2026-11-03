# Sources and provenance

Ten raw Juniper configurations distributed by Expresso, whose README attributes the source to Bagpipe.

## Sources

### Expresso Internet2 dataset

Repository: [https://github.com/XJTU-NetVerify/Expresso](https://github.com/XJTU-NetVerify/Expresso).
Revision: `e21604f39b5e3ec2d75634ce39a73a6aeab9be65`.
Upstream path: [networks/internet2](https://github.com/XJTU-NetVerify/Expresso/blob/e21604f39b5e3ec2d75634ce39a73a6aeab9be65/networks/internet2).
Raw configs copied byte-for-byte from this revision. The upstream calls them lightly cleaned.

### Bagpipe, reported earlier source

Repository: [https://github.com/konne88/bagpipe](https://github.com/konne88/bagpipe).
Revision: `9338220fe1fec2e7196e1143c92065ce5d5a7b46`.
Lineage is asserted by the Expresso README; byte-level history back to the operator capture is not established.

### Collapse interface topology to router adjacency

Implementation: [build_graph.py](build_graph.py).

## Licenses

[Apache-2.0](licenses/expresso-Apache-2.0.txt): Immediate upstream repository license, including its published dataset.

[MIT](licenses/bagpipe-MIT.txt): Earlier source repository license and attribution. Original capture history remains unverified.

## Preserved

- All ten raw configuration files, including their original policy text, are copied byte-for-byte.
- Upstream inferred topology.txt is copied byte-for-byte.

## Changes

- Package raw-configs as a Batfish configs directory.
- Derive a separate simple graph with ten routers and nineteen adjacencies by collapsing parallel logical circuits.
- Do not inject Expresso supplemental external-route XML into the Batfish snapshot.

## Unknowns

- Operator capture date, complete operator-to-artifact lineage, and completeness of external peer state.

## Verification

Partial parser compatibility and dataplane completion; ten modeled routers; no policy equivalence verdict.

File identities are recorded in [SHA256SUMS](SHA256SUMS).
