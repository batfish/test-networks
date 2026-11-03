import ipaddress
from pathlib import Path
import sys
import unittest

network = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(network))
sys.path.insert(0, str(network.parent / "internet2"))
from generate import allocate, compose, render
from build_graph import collapse


class WanExpansionTest(unittest.TestCase):
    def setUp(self):
        self.base = {"nodes": ["a", "b", "c"], "edges": [["a", "b"], ["b", "c"], ["a", "c"]]}

    def test_seeded_join_connects_every_copy(self):
        result = compose(self.base, 5, "random", seed=7)
        self.assertEqual(len(result["nodes"]), 15)
        self.assertEqual(len(result["edges"]), 3 * 5 + 4)
        self.assertEqual(result["components"], 1)
        self.assertTrue(all(
            result["nodes"][left]["copy"] != result["nodes"][right]["copy"]
            for left, right in result["connectors"]
        ))

    def test_disconnected_copies_keep_routes_in_separate_components(self):
        result = compose(self.base, 4, "disconnected")
        self.assertEqual(result["components"], 4)
        self.assertEqual(len(result["edges"]), 12)

    def test_ring_join_has_no_duplicate_edges_for_two_copies(self):
        self.assertEqual(len(compose(self.base, 2, "ring")["connectors"]), 1)
        result = compose(self.base, 4, "ring")
        self.assertEqual(len(result["connectors"]), 4)
        self.assertEqual(result["components"], 1)

    def test_seed_is_reproducible_and_changes_connectors(self):
        self.assertEqual(compose(self.base, 8, seed=3), compose(self.base, 8, seed=3))
        self.assertNotEqual(
            compose(self.base, 8, seed=3)["connectors"],
            compose(self.base, 8, seed=19)["connectors"],
        )

    def test_address_and_asn_allocation_is_unique_and_reciprocal(self):
        nodes, links = allocate(compose(self.base, 5), prefixes_per_node=3)
        addresses = [node["router_id"] for node in nodes.values()]
        addresses += [
            str(ipaddress.ip_interface(prefix).ip)
            for node in nodes.values() for prefix in node["prefixes"]
        ]
        for link in links:
            left, right = link["endpoints"]
            addresses.extend(str(ipaddress.ip_interface(end["address"]).ip) for end in (left,right))
            self.assertEqual(left["peer_ip"], str(ipaddress.ip_interface(right["address"]).ip))
            self.assertEqual(right["peer_ip"], str(ipaddress.ip_interface(left["address"]).ip))
            self.assertEqual(left["remote_as"], nodes[right["node"]]["asn"])
        self.assertEqual(len(addresses), len(set(addresses)))
        self.assertEqual(len({node["asn"] for node in nodes.values()}), len(nodes))

    def test_infrastructure_is_not_a_bgp_origin(self):
        nodes, _ = allocate(compose(self.base, 2))
        for name, node in nodes.items():
            config = render(name, node)
            self.assertNotIn(f" network {node['router_id']} ", config)
            self.assertIn(
                f" network {ipaddress.ip_interface(node['prefixes'][0]).ip} mask 255.255.255.255",
                config,
            )

    def test_parallel_interface_circuits_collapse_with_recorded_counts(self):
        graph = collapse("a if0 b if0\nb if0 a if0\na if1 b if1\nb if1 a if1\n")
        self.assertEqual(graph["edges"], [["a", "b"]])
        self.assertEqual(graph["derivation"]["interface_circuits"], 2)
        self.assertEqual(graph["derivation"]["router_edges"], 1)
        self.assertEqual(graph["derivation"]["circuits_missing_reverse_entry"], 0)

    def test_invalid_base_graph_is_rejected(self):
        for graph in (
            {"nodes": ["a","b"], "edges": []},
            {"nodes": ["a"], "edges": [["a","a"]]},
            {"nodes": ["a","b"], "edges": [["a","b"],["b","a"]]},
        ):
            with self.subTest(graph=graph):
                with self.assertRaises(ValueError):
                    compose(graph, 2)


if __name__ == "__main__":
    unittest.main()
