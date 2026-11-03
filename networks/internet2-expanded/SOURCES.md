# Sources and provenance

Seeded connected copies of the published router graph, with explicitly synthetic eBGP policies and service origins.

## Sources

### Internet2 topology seed

Repository: [https://github.com/XJTU-NetVerify/Expresso](https://github.com/XJTU-NetVerify/Expresso).
Revision: `e21604f39b5e3ec2d75634ce39a73a6aeab9be65`.
Upstream path: [networks/internet2/topology.txt](https://github.com/XJTU-NetVerify/Expresso/blob/e21604f39b5e3ec2d75634ce39a73a6aeab9be65/networks/internet2/topology.txt).

### REAL graph duplication method

Repository: [https://github.com/XJTU-NetVerify/REAL-artifact-evaluation](https://github.com/XJTU-NetVerify/REAL-artifact-evaluation).
Revision: `9186ddee0f2746cf6e4496416b0d13921be6f627`.
Upstream path: [batfish/scripts/config/confgen.py](https://github.com/XJTU-NetVerify/REAL-artifact-evaluation/blob/9186ddee0f2746cf6e4496416b0d13921be6f627/batfish/scripts/config/confgen.py).
generate_blueprint_dupzoo and generate_blueprint_from_graph. Method reference only; no upstream code is bundled.

### Repository-authored WAN composition generator

Implementation: [generate.py](generate.py).

### Internet2 router graph extraction

Implementation: [../internet2/build_graph.py](../internet2/build_graph.py).

## Licenses

[Apache-2.0](LICENSE): Repository-authored composition implementation and newly generated configs.

## Preserved

- Nineteen router adjacencies inside each ten-router copy.
- Base node names remain traceable through the generated copy map.

## Changes

- Add one seeded random connector from each new copy to an earlier copy, or choose explicit chain, ring, or disconnected composition.
- Replace original policies with fresh single-hop eBGP, new ASNs and addresses, and synthetic service /32 origins.

## Unknowns

- Equivalence to original Internet2 routing policy; this workflow makes no such claim.

## Verification

Clean parsing, dataplane completion, 78/78 established BGP endpoints, global loop freedom, and symbolic service reachability from all 20 routers in the two-copy example.

File identities are recorded in [SHA256SUMS](SHA256SUMS).
