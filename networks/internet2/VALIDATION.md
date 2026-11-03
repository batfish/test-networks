# Validation

Open-source Batfish 0.36.0 at revision
`59abf28a36ee8b8131ff8983c3a918de7f4da72e` modeled all ten routers.
All raw files had `PARTIALLY_UNRECOGNIZED` parsing status. Dataplane
computation completed.

The diagnostics contained 1,100 parse-warning rows, 151 conversion-warning
rows, and 397 undefined-reference rows. For example, `set chassis
dump-on-panic` was unrecognized, `MISSION-SEGP` was an empty prefix list,
and an IPv6 loopback firewall filter was referenced without a definition.
These include configuration features outside the modeled forwarding
scope as well as incomplete references.

This result does not establish complete routing-policy modeling or
policy equivalence. The source configs have not been altered to remove
those diagnostics. Expresso's supplemental external route input is not
part of the bundled Batfish snapshot.
