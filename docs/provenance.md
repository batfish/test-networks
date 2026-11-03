# Source notes

Each network has a plain-text `SOURCES.md`. Identify the original
publisher, upstream path, and fixed source revision. For a publication,
include its citation and the sections used to construct the model.

Describe whether the files are published router configs, generated
configs, or a derived model. An operator's name or topology does not
establish that generated configs are production configurations.

Record what was preserved, changed, and remains unknown. Include
redactions, input omissions, protocol substitutions, parallel-link
collapse, synthetic advertisements, and address or ASN remapping.
For captured snapshots, record the capture date when known.

Keep upstream license texts in the network directory. Explain which
material each license covers. Reported links in a source chain should be
identified without claiming unverified byte-level history.

`SHA256SUMS` is a plain-text list of file identities. Preserve original
archive bytes when an archive is the referenced source. Reproduction
instructions belong in the network README; generated snapshot manifests
can retain the parameters and source-node mapping needed to use the data.

Validation notes should state the tested simulator version and scope.
Parsing, dataplane completion, structural invariants, reachability, and
policy equivalence are distinct checks. Record compatibility limits
without attaching performance claims to the dataset.
