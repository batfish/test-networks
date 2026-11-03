# SPDX-License-Identifier: Apache-2.0
"""Compose copies of a router graph and generate a synthetic eBGP snapshot."""

import argparse
from collections import defaultdict
import hashlib
import ipaddress
import json
from pathlib import Path
import random
import re


def components(nodes, edges):
    adjacency = defaultdict(set)
    for left, right in edges:
        adjacency[left].add(right)
        adjacency[right].add(left)
    unseen = set(nodes)
    count = 0
    while unseen:
        count += 1
        pending = [unseen.pop()]
        while pending:
            for neighbor in adjacency[pending.pop()]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    pending.append(neighbor)
    return count


def validate_base(graph):
    nodes = graph["nodes"]
    if not nodes or len(set(nodes)) != len(nodes):
        raise ValueError("Base graph needs unique node names.")
    if any(re.fullmatch(r"[A-Za-z0-9_-]+", node) is None for node in nodes):
        raise ValueError("Node names may contain letters, digits, underscores, and hyphens.")
    node_set = set(nodes)
    edges = set()
    for left, right in graph["edges"]:
        if left not in node_set or right not in node_set or left == right:
            raise ValueError(f"Invalid base edge {left}, {right}")
        edge = tuple(sorted((left, right)))
        if edge in edges:
            raise ValueError(f"Duplicate base edge {edge}")
        edges.add(edge)
    if components(nodes, edges) != 1:
        raise ValueError("Base graph must be connected.")


def compose(graph, copies, join="random", seed=0, gateway=None):
    validate_base(graph)
    if copies < 1:
        raise ValueError("Copies must be positive.")
    if join not in {"random", "chain", "ring", "disconnected"}:
        raise ValueError(f"Unknown join method {join}")
    original = sorted(graph["nodes"])
    gateway = gateway or original[0]
    if gateway not in original:
        raise ValueError(f"Unknown gateway {gateway}")
    identities = {
        f"c{copy:04d}-{node}": {"copy": copy, "base_node": node}
        for copy in range(copies) for node in original
    }
    edges = {
        tuple(sorted((f"c{copy:04d}-{left}", f"c{copy:04d}-{right}")))
        for copy in range(copies) for left, right in graph["edges"]
    }
    connectors = set()
    rng = random.Random(seed)
    for copy in range(1, copies):
        if join == "random":
            left = f"c{copy:04d}-{rng.choice(original)}"
            previous = rng.randrange(copy)
            right = f"c{previous:04d}-{rng.choice(original)}"
        elif join in {"chain", "ring"}:
            left = f"c{copy:04d}-{gateway}"
            right = f"c{copy-1:04d}-{gateway}"
        else:
            continue
        connectors.add(tuple(sorted((left, right))))
    if join == "ring" and copies > 2:
        connectors.add(tuple(sorted((
            f"c{copies-1:04d}-{gateway}", f"c0000-{gateway}"
        ))))
    edges.update(connectors)
    return {
        "nodes": identities,
        "edges": sorted(edges),
        "connectors": sorted(connectors),
        "parameters": {"copies": copies, "join": join, "seed": seed, "gateway": gateway},
        "components": components(identities, edges),
    }


def allocate(topology, prefixes_per_node=1):
    if prefixes_per_node < 1:
        raise ValueError("Prefixes per node must be positive.")
    if len(topology["nodes"]) > 1048574:
        raise ValueError("Infrastructure address pool exhausted.")
    if len(topology["edges"]) > 65536:
        raise ValueError("Link address pool exhausted.")
    if len(topology["nodes"]) * prefixes_per_node > 16777214:
        raise ValueError("Service address pool exhausted.")
    nodes = {}
    for index, (name, identity) in enumerate(topology["nodes"].items()):
        nodes[name] = {
            **identity,
            "asn": 4200000000 + index,
            "router_id": str(ipaddress.IPv4Address("172.16.0.1") + index),
            "prefixes": [
                f"{ipaddress.IPv4Address('10.0.0.1') + index * prefixes_per_node + offset}/32"
                for offset in range(prefixes_per_node)
            ],
            "interfaces": [],
        }
    links = []
    connectors = set(topology["connectors"])
    for index, (left, right) in enumerate(topology["edges"]):
        address = ipaddress.IPv4Address("198.18.0.0") + 2 * index
        endpoints = []
        for offset, (name, remote) in enumerate(((left, right), (right, left))):
            endpoint = {
                "node": name,
                "interface": f"GigabitEthernet0/{len(nodes[name]['interfaces'])}",
                "address": f"{address + offset}/31",
                "remote": remote,
                "peer_ip": str(address + 1 - offset),
                "remote_as": nodes[remote]["asn"],
            }
            nodes[name]["interfaces"].append(endpoint)
            endpoints.append(endpoint)
        links.append({"endpoints": endpoints, "intercopy": (left, right) in connectors})
    return nodes, links


def render(name, node, max_paths=16):
    lines = [
        "version 15.2", f"hostname {name}", "ip routing", "!",
        "interface Loopback0",
        f" ip address {node['router_id']} 255.255.255.255", "!",
    ]
    for index, prefix in enumerate(node["prefixes"], 100):
        lines += [
            f"interface Loopback{index}",
            f" ip address {ipaddress.ip_interface(prefix).ip} 255.255.255.255", "!",
        ]
    for endpoint in node["interfaces"]:
        lines += [
            f"interface {endpoint['interface']}",
            f" description to {endpoint['remote']}",
            " no switchport",
            f" ip address {ipaddress.ip_interface(endpoint['address']).ip} 255.255.255.254",
            " no shutdown", "!",
        ]
    lines += [
        f"router bgp {node['asn']}",
        f" bgp router-id {node['router_id']}",
        " bgp bestpath as-path multipath-relax",
        f" maximum-paths {max_paths}",
    ]
    for prefix in node["prefixes"]:
        lines += [f" network {ipaddress.ip_interface(prefix).ip} mask 255.255.255.255"]
    for endpoint in node["interfaces"]:
        lines += [
            f" neighbor {endpoint['peer_ip']} remote-as {endpoint['remote_as']}",
            f" neighbor {endpoint['peer_ip']} route-map SERVICES in",
            f" neighbor {endpoint['peer_ip']} route-map SERVICES out",
        ]
    lines += [
        "!",
        "ip prefix-list SERVICES seq 10 permit 10.0.0.0/8 ge 32 le 32",
        "route-map SERVICES permit 10",
        " match ip address prefix-list SERVICES",
        "!", "end", "",
    ]
    return "\n".join(lines)


def write_snapshot(directory, topology, base_bytes, prefixes_per_node=1, max_paths=16):
    if max_paths < 1:
        raise ValueError("Maximum paths must be positive.")
    nodes, links = allocate(topology, prefixes_per_node)
    configs = directory / "configs"
    if configs.exists() and any(configs.iterdir()):
        raise ValueError(f"Refusing to overwrite nonempty config directory {configs}")
    configs.mkdir(parents=True, exist_ok=True)
    for name, node in nodes.items():
        (configs / f"{name}.cfg").write_text(render(name, node, max_paths))
    wiring = []
    for link in links:
        left, right = link["endpoints"]
        for first, second in ((left, right), (right, left)):
            wiring.append({
                "node1": {"hostname": first["node"], "interfaceName": first["interface"]},
                "node2": {"hostname": second["node"], "interfaceName": second["interface"]},
            })
    (directory / "batfish").mkdir(exist_ok=True)
    (directory / "batfish/layer1_topology.json").write_text(
        json.dumps({"edges": wiring}, indent=2) + "\n"
    )
    manifest = {
        "kind": "derived-generated-snapshot",
        "base_graph_sha256": hashlib.sha256(base_bytes).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "parameters": {
            **topology["parameters"], "prefixes_per_node": prefixes_per_node, "max_paths": max_paths
        },
        "counts": {
            "nodes": len(nodes), "physical_links": len(links),
            "intercopy_links": len(topology["connectors"]),
            "directed_bgp_sessions": 2 * len(links),
            "originated_prefixes": len(nodes) * prefixes_per_node,
            "components": topology["components"],
        },
        "modeling": {
            "preserved": ["Base graph adjacency inside every copy."],
            "changed": [
                "Add documented inter-copy links.",
                "Assign new node names, ASNs, router IDs, and interface addresses.",
                "Generate fresh single-hop eBGP and synthetic service /32 origins.",
            ],
            "not_preserved": [
                "Original router configuration, IS-IS, iBGP, BGP policies, and external advertisements.",
                "Interface circuit multiplicity, bandwidth, and geographical distances.",
            ],
        },
        "nodes": nodes,
        "links": links,
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--copies", type=int, required=True)
    parser.add_argument("--join", choices=["random", "chain", "ring", "disconnected"], default="random")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--gateway")
    parser.add_argument("--prefixes-per-node", type=int, default=1)
    parser.add_argument("--max-paths", type=int, default=16)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base_bytes = args.base.read_bytes()
    topology = compose(json.loads(base_bytes), args.copies, args.join, args.seed, args.gateway)
    manifest = write_snapshot(
        args.output, topology, base_bytes, args.prefixes_per_node, args.max_paths
    )
    print(json.dumps(manifest["counts"], indent=2))


if __name__ == "__main__":
    main()
