# Contributing

Each network lives in `networks/<name>/` with a README and a plain-text
`SOURCES.md`. Add a link to the root README.

For a published snapshot, identify the publisher, the earliest source
you can establish, the source revision, capture date when known, license,
and any redactions or conversions. Preserve upstream notices. Record
unknown provenance explicitly.

For a generator, cite the topology and routing-policy sources separately.
Describe which choices are modeled: address allocation, ASNs, routing
protocol substitutions, summarization, missing external peers, and failure
scenarios. Include deterministic parameters and reproduction commands.

For a derived network, identify the base artifact and its checksum,
transformation, seed, and parameters. List what is preserved and changed.
A topology-only transformation must say when original policy is replaced.

Keep license texts and checksums with the network. Captured configs must
be authorized for public redistribution and have credentials and private
material removed; document any changes in the source notes.

Keep small snapshots in Git. Larger variants can be reproduced locally
or supplied as versioned archives with their source notes, parameters,
checksums, and license texts. Preserve an original archive's bytes when
it is the referenced source.

Keep reproduction helpers, their dependencies, and tests in the relevant
network directory. Most contributions should consist of data and
explanatory text; reproduction helpers are optional.

Check source notes, local links, and checksums before submitting a pull
request. If a helper transforms network behavior, check the property it
claims to preserve and record the scope of those checks.

Parser warnings and incomplete reference resolution are allowed when
documented for a historical snapshot. Contributions should improve the
record rather than discard unrecognized input without attribution.
