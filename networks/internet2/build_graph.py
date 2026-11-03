# SPDX-License-Identifier: Apache-2.0
"""Derive a simple router graph from the pinned Internet2 interface topology."""

import argparse
import hashlib
import json
from pathlib import Path


def collapse(text):
    nodes = set()
    edges = set()
    circuits = set()
    directed = set()
    rows = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        left, left_interface, right, right_interface = line.split()
        if left == right:
            raise ValueError(f"Self-loop at {left}")
        rows += 1
        nodes.update((left, right))
        edges.add(tuple(sorted((left, right))))
        circuit = ((left, left_interface), (right, right_interface))
        directed.add(circuit)
        circuits.add(tuple(sorted(circuit)))
    return {
        "nodes": sorted(nodes),
        "edges": [list(edge) for edge in sorted(edges)],
        "derivation": {
            "source_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "source_rows": rows,
            "interface_circuits": len(circuits),
            "circuits_missing_reverse_entry": sum(
                (right, left) not in directed for left, right in directed
            ),
            "router_edges": len(edges),
            "changes": [
                "Collapse parallel interface circuits between the same routers.",
                "Discard interface names; do not infer bandwidth or routing policy.",
            ],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.input.read_bytes()
    graph = collapse(source.decode())
    graph["derivation"]["source_sha256"] = hashlib.sha256(source).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(graph, indent=2) + "\n")
    print(f"{len(graph['nodes'])} routers, {len(graph['edges'])} router edges")


if __name__ == "__main__":
    main()
