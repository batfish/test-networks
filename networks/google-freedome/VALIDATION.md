# Validation

The small OSPF and BGP snapshots were checked with open-source Batfish
0.36.0 at revision `59abf28a36ee8b8131ff8983c3a918de7f4da72e`.

All files parsed. Parse warnings, conversion warnings, and undefined
references were absent. Configured BGP endpoints and route-reflector
client flags matched the generated manifest. Datacenter edges carried
only /16 cluster aggregates; infrastructure loopbacks did not appear
in the BGP RIB.

Global loop detection and symbolic rack-endpoint reachability passed.
Successful witnesses were required for every source rack. Campus-local
paths avoided the WAN.

Both cluster modes were also checked after one cluster uplink failed,
a Datacenter Freedome block failed, campus 0 lost its WAN uplinks, and
the first cluster lost all external uplinks. Campus isolation preserved
local reachability; cluster isolation withdrew the default while keeping
internal endpoints reachable.

The larger recorded profiles used route-scope checks and representative
traces rather than global symbolic reachability. Validation is against
Batfish's model; live NOS behavior was not tested. The local
[verification helper](verify.py) reproduces these behavioral checks.
