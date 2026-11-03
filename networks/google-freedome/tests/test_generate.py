import ipaddress
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import generate


class TopologyTest(unittest.TestCase):
    def test_node_count_matches_independent_hierarchy_formula(self):
        p = generate.Parameters(campuses=2, buildings=2, clusters=2, racks=3)
        network = generate.build_topology(p)
        clusters = p.campuses * p.buildings * p.clusters
        cluster_nodes = p.racks + p.aggregation + p.spines + p.cbrs
        block_nodes = p.edges + p.borders
        blocks = p.campuses * (p.buildings + 1) * p.blocks
        self.assertEqual(
            len(network.nodes), clusters * cluster_nodes + blocks * block_nodes + p.wan
        )

    def test_addresses_and_interface_names_are_unique(self):
        network = generate.build_topology(generate.Parameters())
        addresses = [node.loopback for node in network.nodes.values()]
        interfaces = []
        for link in network.links:
            for end in [link.left, link.right]:
                addresses.append(str(ipaddress.ip_interface(end.address).ip))
                interfaces.append((end.node, end.interface))
            self.assertEqual(
                ipaddress.ip_interface(link.left.address).network,
                ipaddress.ip_interface(link.right.address).network,
            )
        self.assertEqual(len(addresses), len(set(addresses)))
        self.assertEqual(len(interfaces), len(set(interfaces)))

    def test_block_members_share_asn_and_other_blocks_do_not(self):
        network = generate.build_topology(generate.Parameters())
        group_asns = {}
        for node in network.nodes.values():
            if node.asn is not None:
                self.assertGreaterEqual(node.asn, 4200000000)
                self.assertLessEqual(node.asn, 4294967294)
                group_asns.setdefault(node.domain, set()).add(node.asn)
        self.assertTrue(all(len(asns) == 1 for asns in group_asns.values()))
        asns = [next(iter(group)) for group in group_asns.values()]
        self.assertEqual(len(asns), len(set(asns)))

    def test_each_cluster_gateway_connects_to_every_local_edge(self):
        p = generate.Parameters()
        network = generate.build_topology(p)
        for node in network.nodes.values():
            if node.role == "cbr":
                edges = [
                    link
                    for link in network.links
                    if link.kind == "cluster-egress"
                    and node.name in [link.left.node, link.right.node]
                ]
                self.assertEqual(len(edges), p.blocks * p.edges)

    def test_ospf_links_do_not_cross_control_plane_domains(self):
        network = generate.build_topology(generate.Parameters())
        for link in network.links:
            left = network.nodes[link.left.node]
            right = network.nodes[link.right.node]
            if link.ospf:
                self.assertEqual(left.domain, right.domain)
            else:
                self.assertNotEqual(left.domain, right.domain)

    def test_build_is_deterministic(self):
        p = generate.Parameters()
        first = generate.build_topology(p)
        second = generate.build_topology(p)
        self.assertEqual(first.manifest(), second.manifest())
        for name in first.nodes:
            self.assertEqual(first.render(name), second.render(name))

    def test_failure_disables_both_ends_of_selected_links(self):
        network = generate.build_topology(generate.Parameters())
        selected = network.failed_interfaces("cluster-link")
        self.assertEqual(len(selected), 2)
        for node, interface in selected:
            config = network.render(node, selected)
            section = config.split(f"interface {interface}\n", 1)[1].split("!\n", 1)[0]
            self.assertIn(" shutdown\n", section)

    def test_address_capacity_fails_before_writing_partial_snapshot(self):
        with self.assertRaises(ValueError):
            generate.build_topology(
                generate.Parameters(campuses=20, buildings=20, clusters=2)
            )
        with self.assertRaises(ValueError):
            generate.build_topology(generate.Parameters(racks=64, prefixes_per_rack=8))
        with self.assertRaises(ValueError):
            generate.build_topology(generate.Parameters(blocks=0))

    def test_bgp_fabric_has_distinct_asns_on_every_internal_link(self):
        network = generate.build_topology(generate.Parameters(cluster_protocol="bgp"))
        for link in network.links:
            if link.kind == "cluster-internal":
                self.assertFalse(link.ospf)
                self.assertIsNotNone(network.nodes[link.left.node].asn)
                self.assertIsNotNone(network.nodes[link.right.node].asn)
                self.assertNotEqual(
                    network.nodes[link.left.node].asn,
                    network.nodes[link.right.node].asn,
                )

    def test_bgp_fabric_originates_rack_networks_without_ospf(self):
        network = generate.build_topology(generate.Parameters(
            cluster_protocol="bgp", prefixes_per_rack=2
        ))
        for node in network.nodes.values():
            if node.cluster is not None:
                self.assertNotIn("ospf", network.render(node.name))
            if node.role == "rack":
                config = network.render(node.name)
                for prefix in node.rack_prefixes:
                    subnet = ipaddress.ip_network(prefix)
                    self.assertIn(
                        f" network {subnet.network_address} mask {subnet.netmask}\n",
                        config,
                    )

    def test_bgp_aggregation_preserves_local_specifics(self):
        network = generate.build_topology(generate.Parameters(cluster_protocol="bgp"))
        node = next(node for node in network.nodes.values() if node.role == "cbr")
        config = network.render(node.name)
        self.assertIn(" aggregate-address 10.0.0.0 255.255.0.0\n", config)
        self.assertNotIn("summary-only", config)
        self.assertIn("route-map CLUSTER_ONLY out", config)
        self.assertIn("route-map FABRIC_ROUTES out", config)

    def test_both_modes_export_only_cluster_aggregates(self):
        for protocol in ("ospf", "bgp"):
            with self.subTest(protocol=protocol):
                network = generate.build_topology(
                    generate.Parameters(cluster_protocol=protocol)
                )
                for node in network.nodes.values():
                    if node.role == "cbr":
                        config = network.render(node.name)
                        self.assertIn(" aggregate-address ", config)
                        self.assertIn(
                            f"ip prefix-list CLUSTER seq 10 permit {node.cluster_prefix}\n",
                            config,
                        )
                        self.assertIn(
                            "ip prefix-list PUBLIC seq 20 permit 10.0.0.0/8 ge 16 le 16\n",
                            config,
                        )

    def test_unknown_protocol_fails_validation(self):
        with self.assertRaises(ValueError):
            generate.build_topology(generate.Parameters(cluster_protocol="unknown"))


if __name__ == "__main__":
    unittest.main()
