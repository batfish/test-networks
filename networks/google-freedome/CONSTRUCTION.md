# How the fabric was constructed

The generator is new Python code written from public design descriptions.
It does not copy Google router configs or implement Firepath. The source
material specifies a routing hierarchy and several policies; the code
supplies a concrete, parameterized graph and Cisco-style configs for that
model. The [source notes](SOURCES.md) identify the references.

## Published design and modeling decisions

| Reference | Mechanism used here | Choices made in the model |
|---|---|---|
| Jupiter Rising, section 4.1 | Cluster border routers connect the cluster fabric to external eBGP peers | A separate border tier attached to the spines |
| Section 4.2 | Datacenter and Campus Freedomes, normally four independent blocks; edges face downward and borders face upward | Configurable numbers of edges and borders; complete bipartite internal wiring |
| Section 4.2 | eBGP outside a block; iBGP inside it with border route reflectors | OSPF supplies block-local loopback reachability |
| Section 5.2.5 | Export a cluster aggregate and provide an inward default | One /16 per cluster; explicit prefix filters; conditional OSPF default readiness |
| RFC 7938 | Single-hop eBGP in a Clos fabric | Optional eBGP cluster mode with a distinct ASN per device |

The cluster Clos is idealized. The generator does not reproduce chassis,
ASIC port maps, link bandwidth ratios, LAGs, or a production WAN. Rack
subnets use loopback interfaces as test endpoints rather than server
nodes. Addresses and ASNs are synthetic.

## Build the graph before rendering configs

[generate.py](generate.py) separates topology construction from rendering.
`Parameters` holds the dimensions and rejects values that exceed the
address pools. `Node`, `Link`, and `InternalPeer` hold the resulting
network, physical wiring, and loopback-based iBGP relationships.

`build_topology` creates campus blocks, datacenter blocks, cluster tiers,
and the WAN core. Within each cluster it connects every rack to every
aggregation router, every aggregation router to every spine, and every
spine to every cluster border. Cluster borders connect to all edge
routers in their building's Datacenter Freedome. Datacenter borders
connect to Campus Freedome edges; campus borders connect to WAN routers.

Each Freedome block connects its edges to its borders. The same borders
are route reflectors for the edges and peer with one another. The graph
keeps an adjacency list per node for config generation. Node creation
order, link order, and peer sorting are deterministic.

For C campuses, B buildings per campus, K clusters per building, and
cluster tiers R racks, A aggregation routers, S spines, and G borders:

```text
cluster devices = C*B*K*(R+A+S+G)
Freedome devices = C*(B+1)*F*(E+H)
total devices = cluster devices + Freedome devices + W
```

F is blocks per Freedome, E edges per block, H borders per block, and W
WAN routers. The default dimensions produce the saved 138-router data.

## Allocate identities and addresses

Each cluster receives a /16 from `10.0.0.0/8`. Rack /24s are allocated
within it using rack index and prefixes-per-rack. Infrastructure
loopbacks are unique /32s from `172.16.0.0/12`; physical links receive
unique /31s from `198.18.0.0/15`. WAN test endpoints use `192.0.2.0/24`.
Interface names are assigned independently on each node.

Four-octet private ASN ranges distinguish clusters, Datacenter Freedome
blocks, Campus Freedome blocks, and the WAN. OSPF cluster mode puts BGP
only on the cluster borders. In BGP cluster mode, every cluster device
receives a distinct ASN. This lets adjacent tiers peer over their link
addresses without AS reuse or an interior reachability protocol.

## Render the routing model

OSPF mode places a single area inside each cluster. Rack subnet loopbacks
use point-to-point OSPF network type so their whole /24 is advertised.
Cluster borders redistribute only local rack prefixes into BGP and create
a /16 aggregate with `summary-only`.

BGP mode originates each rack's connected /24s with `network` statements.
Rack exports contain only its own prefixes. Intermediate cluster tiers
carry local specifics, remote aggregates, and defaults. Cluster borders
create the same /16 aggregate without suppressing local specifics inside
the fabric; the external export map permits only that aggregate.

Block-local iBGP uses loopback addresses, border route-reflector client
flags, and next-hop-self. Block OSPF carries infrastructure reachability.
Inter-block links use directly connected eBGP. Export and import filters
permit cluster /16s, the default, and WAN test endpoints. Infrastructure
loopbacks and link subnets are not advertised into BGP.

The small WAN core originates a default backed by a Null0 route and its
test endpoints. Those are test-model choices.

## Default readiness and the Batfish iteration

Jupiter's abstraction assumes all cluster borders are viable for external
traffic. This model represents partial isolation explicitly. An OSPF
border injects a default while it has an external default or another
cluster's aggregate. It rejects OSPF-learned defaults from neighboring
borders, so those defaults cannot satisfy their own readiness condition.

An initial draft used IOS `match source-protocol bgp`; Batfish did not
model that predicate. The renderer instead uses address scope and OSPF
import filtering. This is an implementation choice for the simulator,
not a published Google policy.

The implementation was checked first on the small topology. The verifier
compares expected physical and loopback peer connectivity with Batfish's
session results, then checks reflector roles, route scope, loop freedom,
and reachability. Link, block, campus-uplink, and complete cluster-egress
failures exercise the same model. Larger instances retain representative
path and route-scope checks. The [validation notes](VALIDATION.md) state
the coverage without treating it as live NOS validation.

The writer emits every physical link in both directions in
`batfish/layer1_topology.json`. The snapshot manifest preserves dimensions,
identities, node roles, and failure selections alongside the configs.
