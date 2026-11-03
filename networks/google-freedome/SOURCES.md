# Sources and provenance

Hierarchical cluster, building, campus, and WAN model with OSPF or eBGP replacing Firepath and /16 cluster exports.

## Sources

### Jupiter Rising

[Singh et al. Jupiter Rising: A Decade of Clos Topologies and Centralized Control in Google's Datacenter Network. SIGCOMM 2015.](https://research.google/pubs/jupiter-rising-a-decade-of-clos-topologies-and-centralized-control-in-googles-datacenter-network/)
Relevant sections: 4.1, 4.2, 5.2.5.

### Use of BGP for Routing in Large-Scale Data Centers

[Lapukhov, Premji, and Mitchell. RFC 7938. August 2016.](https://www.rfc-editor.org/rfc/rfc7938)
Relevant sections: 4.2, 5.

### Repository-authored Freedome generator

Implementation: [generate.py](generate.py).

## Licenses

[Apache-2.0](LICENSE): Repository-authored generator, snapshots, and notes. Papers are referenced, not redistributed.

## Preserved

- Published routing hierarchy; independent Freedome blocks; eBGP outside blocks and iBGP route reflectors inside blocks.
- Cluster /16 aggregation and scoped infrastructure addressing.

## Changes

- Idealized cluster Clos with parameterized sizes.
- OSPF or single-hop eBGP substitutes for Firepath.
- Synthetic address pools, ASNs, WAN core, and rack endpoints.
- Conditional OSPF default readiness and import filter are modeling choices.

## Unknowns

- Exact production port map, Firepath implementation, overlay, and live NOS behavior.

## Verification

Small OSPF and BGP models: symbolic endpoint reachability and loop checks, including four failure scenarios. Large models: routing invariants and representative traces.

File identities are recorded in [SHA256SUMS](SHA256SUMS).
