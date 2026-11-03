# SPDX-License-Identifier: Apache-2.0
"""Generate a Jupiter/Freedome-inspired network for open-source Batfish."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass, field
import ipaddress
import json
from pathlib import Path


@dataclass(frozen=True)
class Parameters:
    campuses: int = 2
    buildings: int = 2
    clusters: int = 1
    racks: int = 4
    aggregation: int = 2
    spines: int = 2
    cbrs: int = 2
    blocks: int = 4
    edges: int = 2
    borders: int = 2
    wan: int = 2
    prefixes_per_rack: int = 1
    max_paths: int = 16
    cluster_protocol: str = "ospf"

    def validate(self):
        if self.cluster_protocol not in {"ospf", "bgp"}:
            raise ValueError("Cluster protocol must be ospf or bgp.")
        if any(value < 1 for value in asdict(self).values() if isinstance(value, int)):
            raise ValueError("All topology parameters must be positive.")
        if self.campuses * self.buildings * self.clusters > 256:
            raise ValueError("The 10.0.0.0/8 pool supports at most 256 cluster /16s.")
        if self.racks * self.prefixes_per_rack > 256:
            raise ValueError("Each cluster /16 supports at most 256 rack /24s.")
        if self.wan > 254:
            raise ValueError("The WAN endpoint pool supports at most 254 routers.")


@dataclass
class Node:
    name: str
    role: str
    domain: str
    loopback: str
    campus: int | None = None
    building: int | None = None
    cluster: int | None = None
    asn: int | None = None
    cluster_prefix: str | None = None
    rack_prefixes: list[str] = field(default_factory=list)
    endpoint: str | None = None


@dataclass(frozen=True)
class End:
    node: str
    interface: str
    address: str


@dataclass(frozen=True)
class Link:
    left: End
    right: End
    kind: str
    ospf: bool


@dataclass(frozen=True)
class InternalPeer:
    left: str
    right: str
    left_reflects: bool = False
    right_reflects: bool = False


@dataclass
class Network:
    parameters: Parameters
    nodes: dict[str, Node] = field(default_factory=dict)
    links: list[Link] = field(default_factory=list)
    internal_peers: list[InternalPeer] = field(default_factory=list)
    cluster_records: list[dict] = field(default_factory=list)
    _interface_counts: dict[str, int] = field(default_factory=dict)
    _links_by_node: dict[str, list[Link]] = field(default_factory=dict)

    def node(self, name, role, domain, **kwargs):
        address = int(ipaddress.IPv4Address("172.16.0.0")) + len(self.nodes) + 1
        if address >= int(ipaddress.IPv4Address("172.32.0.0")):
            raise ValueError("Infrastructure loopback address pool exhausted.")
        node = Node(name, role, domain, str(ipaddress.IPv4Address(address)), **kwargs)
        if node.cluster is not None and self.parameters.cluster_protocol == "bgp":
            node.asn = 4240000000 + len(self.nodes)
        if name in self.nodes:
            raise ValueError(f"Duplicate node {name}")
        self.nodes[name] = node
        self._interface_counts[name] = 0
        self._links_by_node[name] = []
        return node

    def connect(self, left: Node, right: Node, kind, ospf):
        address = int(ipaddress.IPv4Address("198.18.0.0")) + 2 * len(self.links)
        if address + 1 > int(ipaddress.IPv4Address("198.19.255.255")):
            raise ValueError("Point-to-point link address pool exhausted.")
        ends = []
        for node, offset in [(left, 0), (right, 1)]:
            index = self._interface_counts[node.name]
            self._interface_counts[node.name] += 1
            ends.append(
                End(
                    node.name,
                    f"GigabitEthernet0/{index}",
                    f"{ipaddress.IPv4Address(address + offset)}/31",
                )
            )
        link = Link(ends[0], ends[1], kind, ospf)
        self.links.append(link)
        self._links_by_node[left.name].append(link)
        self._links_by_node[right.name].append(link)

    def peers(self, name):
        result = []
        node = self.nodes[name]
        for link in self._links_by_node[name]:
            if link.ospf:
                continue
            if link.left.node == name:
                local, remote = link.left, link.right
            elif link.right.node == name:
                local, remote = link.right, link.left
            else:
                continue
            result.append(
                {
                    "local": name,
                    "remote": remote.node,
                    "local_ip": str(ipaddress.ip_interface(local.address).ip),
                    "peer_ip": str(ipaddress.ip_interface(remote.address).ip),
                    "interface": local.interface,
                    "remote_as": self.nodes[remote.node].asn,
                    "type": "EBGP_SINGLEHOP",
                    "reflector_client": False,
                }
            )
        for peer in self.internal_peers:
            if peer.left == name:
                remote, reflects = peer.right, peer.left_reflects
            elif peer.right == name:
                remote, reflects = peer.left, peer.right_reflects
            else:
                continue
            result.append(
                {
                    "local": name,
                    "remote": remote,
                    "local_ip": node.loopback,
                    "peer_ip": self.nodes[remote].loopback,
                    "interface": "Loopback0",
                    "remote_as": self.nodes[remote].asn,
                    "type": "IBGP",
                    "reflector_client": reflects,
                }
            )
        return sorted(result, key=lambda item: (item["remote"], item["peer_ip"]))

    def failed_interfaces(self, scenario):
        if scenario == "baseline":
            return set()
        if scenario == "cluster-link":
            selected = [next(link for link in self.links if link.kind == "cluster-egress")]
        elif scenario == "cluster-isolated":
            domain = self.cluster_records[0]["name"]
            selected = [
                link
                for link in self.links
                if link.kind == "cluster-egress"
                and any(
                    self.nodes[end.node].domain == domain
                    for end in [link.left, link.right]
                )
            ]
        elif scenario == "dc-block":
            domain = "c0-b0-dc-f0"
            selected = [
                link
                for link in self.links
                if any(
                    self.nodes[end.node].domain == domain
                    for end in [link.left, link.right]
                )
            ]
        elif scenario == "campus-wan":
            selected = [
                link
                for link in self.links
                if link.kind == "wan-uplink"
                and any(
                    self.nodes[end.node].campus == 0
                    for end in [link.left, link.right]
                )
            ]
        else:
            raise ValueError(f"Unknown failure scenario {scenario}")
        return {
            (end.node, end.interface)
            for link in selected
            for end in [link.left, link.right]
        }

    def render(self, name, failed=frozenset()):
        node = self.nodes[name]
        p = self.parameters
        uses_ospf = node.cluster is None or p.cluster_protocol == "ospf"
        lines = ["version 15.2", f"hostname {name}", "ip routing", "!"]
        lines += [
            "interface Loopback0",
            f" ip address {node.loopback} 255.255.255.255",
        ]
        if uses_ospf:
            lines += [" ip ospf 1 area 0"]
        lines += ["!"]
        for index, prefix in enumerate(node.rack_prefixes, 100):
            network = ipaddress.ip_network(prefix)
            lines += [
                f"interface Loopback{index}",
                f" ip address {network.network_address + 1} {network.netmask}",
            ]
            if uses_ospf:
                lines += [" ip ospf network point-to-point", " ip ospf 1 area 0"]
            lines += ["!"]
        if node.endpoint:
            lines += [
                "interface Loopback99",
                f" ip address {node.endpoint} 255.255.255.255",
                "!",
                "ip route 0.0.0.0 0.0.0.0 Null0",
                "!",
            ]
        active_ospf = []
        for link in self._links_by_node[name]:
            if link.left.node == name:
                end, remote = link.left, link.right
            elif link.right.node == name:
                end, remote = link.right, link.left
            else:
                continue
            address = ipaddress.ip_interface(end.address)
            lines += [
                f"interface {end.interface}",
                f" description {link.kind} to {remote.node}",
                " no switchport",
                f" ip address {address.ip} {address.netmask}",
            ]
            if link.ospf:
                lines += [" ip ospf 1 area 0", " ip ospf network point-to-point", " ip ospf cost 1"]
                active_ospf.append(end.interface)
            lines += [" shutdown" if (name, end.interface) in failed else " no shutdown", "!"]
        if uses_ospf:
            lines += [
                "router ospf 1",
                f" router-id {node.loopback}",
                " passive-interface default",
            ]
            lines += [f" no passive-interface {interface}" for interface in active_ospf]
            if node.role == "cbr":
                lines += [
                    " distribute-list prefix OSPF_IMPORT in",
                    " default-information originate metric 10 metric-type 1 route-map HAS_EXTERNAL",
                ]
            lines += ["!"]
        if node.asn is not None:
            lines += [
                f"router bgp {node.asn}",
                f" bgp router-id {node.loopback}",
                " bgp log-neighbor-changes",
                " bgp bestpath as-path multipath-relax",
                f" maximum-paths {self.parameters.max_paths}",
                f" maximum-paths ibgp {self.parameters.max_paths}",
            ]
            if node.role == "cbr":
                prefix = ipaddress.ip_network(node.cluster_prefix)
                if uses_ospf:
                    lines += [" redistribute ospf 1 route-map RACK_ONLY"]
                suffix = " summary-only" if uses_ospf else ""
                lines += [
                    f" aggregate-address {prefix.network_address} {prefix.netmask}{suffix}"
                ]
            for prefix in node.rack_prefixes:
                subnet = ipaddress.ip_network(prefix)
                lines += [f" network {subnet.network_address} mask {subnet.netmask}"]
            if node.role == "wan":
                lines += [
                    " network 0.0.0.0 mask 0.0.0.0",
                    f" network {node.endpoint} mask 255.255.255.255",
                ]
            for peer in self.peers(name):
                address = peer["peer_ip"]
                internal_fabric = (
                    not uses_ospf
                    and self.nodes[peer["remote"]].domain == node.domain
                )
                inbound = "FABRIC_ROUTES" if internal_fabric else "PUBLIC_ROUTES"
                outbound = (
                    "RACK_ONLY" if internal_fabric and node.role == "rack"
                    else "FABRIC_ROUTES" if internal_fabric
                    else "CLUSTER_ONLY" if node.role == "cbr"
                    else "PUBLIC_ROUTES"
                )
                lines += [f" neighbor {address} remote-as {peer['remote_as']}"]
                if peer["type"] == "IBGP":
                    lines += [
                        f" neighbor {address} update-source Loopback0",
                        f" neighbor {address} next-hop-self",
                    ]
                    if peer["reflector_client"]:
                        lines += [f" neighbor {address} route-reflector-client"]
                lines += [
                    f" neighbor {address} send-community both",
                    f" neighbor {address} route-map {inbound} in",
                    f" neighbor {address} route-map {outbound} out",
                ]
            lines += [
                "!",
                "ip prefix-list PUBLIC seq 10 permit 0.0.0.0/0",
                "ip prefix-list PUBLIC seq 20 permit 10.0.0.0/8 ge 16 le 16",
                "ip prefix-list PUBLIC seq 30 permit 192.0.2.0/24 ge 32 le 32",
                "route-map PUBLIC_ROUTES permit 10",
                " match ip address prefix-list PUBLIC",
                "!",
            ]
            if not uses_ospf:
                lines += [
                    f"ip prefix-list LOCAL_RACKS seq 10 permit {node.cluster_prefix} ge 24 le 24",
                    "route-map FABRIC_ROUTES permit 10",
                    " match ip address prefix-list PUBLIC",
                    "route-map FABRIC_ROUTES permit 20",
                    " match ip address prefix-list LOCAL_RACKS",
                    "!",
                ]
                if node.role == "rack":
                    for index, prefix in enumerate(node.rack_prefixes, 1):
                        lines += [f"ip prefix-list OWN_RACKS seq {index * 10} permit {prefix}"]
                    lines += [
                        "route-map RACK_ONLY permit 10",
                        " match ip address prefix-list OWN_RACKS",
                        "!",
                    ]
        if node.role == "cbr":
            prefix = node.cluster_prefix
            lines += [
                f"ip prefix-list CLUSTER seq 10 permit {prefix}",
                "route-map CLUSTER_ONLY permit 10",
                " match ip address prefix-list CLUSTER",
                "!",
            ]
            if uses_ospf:
                lines += [
                    f"ip prefix-list RACKS seq 10 permit {prefix} ge 24 le 32",
                    "ip prefix-list DEFAULT_ONLY seq 10 permit 0.0.0.0/0",
                    f"ip prefix-list OTHER_CLUSTERS seq 10 deny {prefix} le 32",
                    "ip prefix-list OTHER_CLUSTERS seq 20 permit 10.0.0.0/8 ge 16 le 24",
                    "ip prefix-list OSPF_IMPORT seq 10 deny 0.0.0.0/0",
                    "ip prefix-list OSPF_IMPORT seq 20 permit 0.0.0.0/0 le 32",
                    "route-map RACK_ONLY permit 10",
                    " match ip address prefix-list RACKS",
                    "!",
                    "route-map HAS_EXTERNAL permit 10",
                    " match ip address prefix-list DEFAULT_ONLY",
                    "route-map HAS_EXTERNAL permit 20",
                    " match ip address prefix-list OTHER_CLUSTERS",
                    "!",
                ]
        lines += ["end", ""]
        return "\n".join(lines)

    def manifest(self, scenario="baseline"):
        peers = [peer for node in self.nodes for peer in self.peers(node)]
        failed = self.failed_interfaces(scenario)
        return {
            "design": (
                "Google Jupiter/Freedome-inspired; OSPF substitutes for Firepath"
                if self.parameters.cluster_protocol == "ospf"
                else "Google Jupiter/Freedome-inspired; eBGP substitutes for Firepath"
            ),
            "parameters": asdict(self.parameters),
            "scenario": scenario,
            "counts": {
                "nodes": len(self.nodes),
                "physical_links": len(self.links),
                "directed_bgp_sessions": len(peers),
                "rack_prefixes": sum(len(node.rack_prefixes) for node in self.nodes.values()),
                "roles": dict(sorted(Counter(node.role for node in self.nodes.values()).items())),
            },
            "nodes": {name: asdict(node) for name, node in self.nodes.items()},
            "links": [asdict(link) for link in self.links],
            "bgp_peers": peers,
            "clusters": self.cluster_records,
            "failed_interfaces": [list(pair) for pair in sorted(failed)],
            "sources": [
                "https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/43837.pdf",
                "https://www.rfc-editor.org/rfc/rfc7938",
            ],
        }

    def write(self, directory: Path, scenario="baseline"):
        configs = directory / "configs"
        if configs.exists() and any(configs.iterdir()):
            raise ValueError(f"Refusing to overwrite nonempty config directory {configs}")
        configs.mkdir(parents=True, exist_ok=True)
        failed = self.failed_interfaces(scenario)
        for name in self.nodes:
            (configs / f"{name}.cfg").write_text(self.render(name, failed))
        edges = []
        for link in self.links:
            for left, right in [(link.left, link.right), (link.right, link.left)]:
                edges.append(
                    {
                        "node1": {"hostname": left.node, "interfaceName": left.interface},
                        "node2": {"hostname": right.node, "interfaceName": right.interface},
                    }
                )
        (directory / "batfish").mkdir(exist_ok=True)
        (directory / "batfish/layer1_topology.json").write_text(
            json.dumps({"edges": edges}, indent=2) + "\n"
        )
        (directory / "manifest.json").write_text(
            json.dumps(self.manifest(scenario), indent=2) + "\n"
        )


def build_topology(parameters: Parameters):
    parameters.validate()
    network = Network(parameters)
    p = parameters
    campus_blocks = {}
    dc_blocks = {}

    def block(prefix, role, asn, campus, building=None):
        domain = prefix
        edges = [
            network.node(
                f"{prefix}-edge-{index}", f"{role}-edge", domain,
                campus=campus, building=building, asn=asn,
            )
            for index in range(p.edges)
        ]
        borders = [
            network.node(
                f"{prefix}-border-{index}", f"{role}-border", domain,
                campus=campus, building=building, asn=asn,
            )
            for index in range(p.borders)
        ]
        for edge in edges:
            for border in borders:
                network.connect(edge, border, "block-internal", ospf=True)
                network.internal_peers.append(
                    InternalPeer(border.name, edge.name, left_reflects=True)
                )
        for i, first in enumerate(borders):
            for second in borders[i + 1:]:
                network.internal_peers.append(InternalPeer(first.name, second.name))
        return edges, borders

    for campus in range(p.campuses):
        campus_blocks[campus] = [
            block(
                f"c{campus}-campus-f{f}", "campus", 4220000000 + campus * p.blocks + f,
                campus,
            )
            for f in range(p.blocks)
        ]
        for building in range(p.buildings):
            dc_blocks[campus, building] = [
                block(
                    f"c{campus}-b{building}-dc-f{f}", "dc",
                    4210000000 + (campus * p.buildings + building) * p.blocks + f,
                    campus, building,
                )
                for f in range(p.blocks)
            ]
            for _, borders in dc_blocks[campus, building]:
                for border in borders:
                    for edges, _ in campus_blocks[campus]:
                        for edge in edges:
                            network.connect(border, edge, "campus-uplink", ospf=False)

    for campus in range(p.campuses):
        for building in range(p.buildings):
            for cluster in range(p.clusters):
                index = (campus * p.buildings + building) * p.clusters + cluster
                prefix = f"10.{index}.0.0/16"
                name = f"c{campus}-b{building}-k{cluster}"
                kwargs = dict(
                    campus=campus, building=building, cluster=cluster,
                    cluster_prefix=prefix,
                )
                racks = []
                for rack in range(p.racks):
                    prefixes = [
                        f"10.{index}.{rack * p.prefixes_per_rack + number}.0/24"
                        for number in range(p.prefixes_per_rack)
                    ]
                    racks.append(
                        network.node(
                            f"{name}-tor-{rack}", "rack", name,
                            rack_prefixes=prefixes, **kwargs,
                        )
                    )
                aggregation = [
                    network.node(f"{name}-agg-{i}", "aggregation", name, **kwargs)
                    for i in range(p.aggregation)
                ]
                spines = [
                    network.node(f"{name}-spine-{i}", "spine", name, **kwargs)
                    for i in range(p.spines)
                ]
                cbrs = [
                    network.node(
                        f"{name}-cbr-{i}", "cbr", name, asn=4200000000 + index, **kwargs
                    )
                    for i in range(p.cbrs)
                ]
                for lefts, rights in [(racks, aggregation), (aggregation, spines), (spines, cbrs)]:
                    for left in lefts:
                        for right in rights:
                            network.connect(
                                left, right, "cluster-internal",
                                ospf=p.cluster_protocol == "ospf",
                            )
                for cbr in cbrs:
                    for edges, _ in dc_blocks[campus, building]:
                        for edge in edges:
                            network.connect(cbr, edge, "cluster-egress", ospf=False)
                network.cluster_records.append(
                    {
                        "name": name,
                        "campus": campus,
                        "building": building,
                        "prefix": prefix,
                        "racks": [rack.name for rack in racks],
                        "cbrs": [cbr.name for cbr in cbrs],
                        "representative_ip": str(
                            ipaddress.ip_network(racks[0].rack_prefixes[0]).network_address + 1
                        ),
                    }
                )

    wan = [
        network.node(
            f"wan-{index}", "wan", "wan", asn=4230000000,
            endpoint=f"192.0.2.{index + 1}",
        )
        for index in range(p.wan)
    ]
    for i, first in enumerate(wan):
        for second in wan[i + 1:]:
            network.connect(first, second, "wan-internal", ospf=True)
            network.internal_peers.append(InternalPeer(first.name, second.name))
    for blocks in campus_blocks.values():
        for _, borders in blocks:
            for border in borders:
                for wan_router in wan:
                    network.connect(border, wan_router, "wan-uplink", ospf=False)
    return network


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--scenario",
        choices=["baseline", "cluster-link", "cluster-isolated", "dc-block", "campus-wan"],
        default="baseline",
    )
    defaults = Parameters()
    descriptions = {
        "cluster_protocol": "Cluster routing protocol used in place of Firepath (default: ospf).",
    }
    for field_name, default in asdict(defaults).items():
        choices = (
            ["ospf", "bgp"] if field_name == "cluster_protocol"
            else None
        )
        parser.add_argument(
            "--" + field_name.replace("_", "-"),
            type=type(default), default=default, choices=choices,
            help=descriptions.get(field_name),
        )
    arguments = vars(parser.parse_args())
    output = arguments.pop("output")
    scenario = arguments.pop("scenario")
    network = build_topology(Parameters(**arguments))
    network.write(output, scenario)
    print(json.dumps(network.manifest(scenario)["counts"], indent=2))


if __name__ == "__main__":
    main()
