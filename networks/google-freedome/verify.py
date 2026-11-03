# SPDX-License-Identifier: Apache-2.0
"""Check generated routing invariants against a local open-source Batfish service."""

import argparse
from collections import Counter, defaultdict
import ipaddress
import json
from pathlib import Path
import re

from pybatfish.client.session import Session
from pybatfish.datamodel import HeaderConstraints, PathConstraints


def expected_sessions(manifest):
    failed = {tuple(item) for item in manifest["failed_interfaces"]}
    adjacency = defaultdict(set)
    for link in manifest["links"]:
        left, right = link["left"], link["right"]
        if link["ospf"] and not any(
            (end["node"], end["interface"]) in failed for end in [left, right]
        ):
            adjacency[left["node"]].add(right["node"])
            adjacency[right["node"]].add(left["node"])
    peers = {
        (peer["local"], peer["local_ip"], peer["peer_ip"]): peer
        for peer in manifest["bgp_peers"]
    }
    expected = {}
    for peer in manifest["bgp_peers"]:
        if peer["type"] == "EBGP_SINGLEHOP":
            reverse = peers[peer["remote"], peer["peer_ip"], peer["local_ip"]]
            established = (
                (peer["local"], peer["interface"]) not in failed
                and (reverse["local"], reverse["interface"]) not in failed
            )
        else:
            visited = {peer["local"]}
            pending = [peer["local"]]
            while pending:
                for neighbor in adjacency[pending.pop()]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        pending.append(neighbor)
            established = peer["remote"] in visited
        expected[peer["local"], peer["peer_ip"]] = established
    return expected


def verify(bf, manifest, quick=False):
    checks = []

    def check(name, passed, detail):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})
        print(f"{'PASS' if passed else 'FAIL'} {name}: {detail}", flush=True)

    parsed = bf.q.fileParseStatus().answer().frame()
    check(
        "all_files_parsed",
        len(parsed) == manifest["counts"]["nodes"] and set(parsed["Status"]) == {"PASSED"},
        dict(Counter(parsed["Status"])),
    )
    for question in ["parseWarning", "viConversionWarning", "undefinedReferences"]:
        frame = getattr(bf.q, question)().answer().frame()
        check(question, len(frame) == 0, len(frame))
    sessions = bf.q.bgpSessionStatus().answer().frame()
    actual = {
        (row["Node"], str(row["Remote_IP"])): row["Established_Status"] == "ESTABLISHED"
        for _, row in sessions.iterrows()
    }
    expected = expected_sessions(manifest)
    mismatches = [
        {"peer": list(peer), "expected": value, "actual": actual.get(peer)}
        for peer, value in expected.items()
        if actual.get(peer) != value
    ]
    check(
        "bgp_sessions_match_physical_and_ospf_connectivity",
        actual == expected,
        {
            "configured": len(expected),
            "established": sum(actual.values()),
            "mismatches": mismatches[:10],
            "status_counts": dict(Counter(sessions["Established_Status"])),
        },
    )
    configured = bf.q.bgpPeerConfiguration(
        properties="Route_Reflector_Client"
    ).answer().frame()
    actual_reflection = {
        (row["Node"], str(row["Remote_IP"])): bool(row["Route_Reflector_Client"])
        for _, row in configured.iterrows()
    }
    expected_reflection = {
        (peer["local"], peer["peer_ip"]): peer["reflector_client"]
        for peer in manifest["bgp_peers"]
    }
    check(
        "route_reflector_clients_match_block_design",
        actual_reflection == expected_reflection,
        {"reflector_client_sessions": sum(actual_reflection.values())},
    )
    infra = bf.q.routes(
        rib="bgp", network="172.16.0.0/12", prefixMatchType="LONGER_PREFIXES"
    ).answer().frame()
    check("infrastructure_not_exported_into_bgp", len(infra) == 0, len(infra))
    exported = bf.q.routes(
        nodes="/.*-dc-.*-edge-.*/", protocols="bgp,ibgp",
        network="10.0.0.0/8", prefixMatchType="LONGER_PREFIXES",
    ).answer().frame()
    observed_prefixes = sorted(set(exported["Network"]))
    check(
        "cluster_boundaries_carry_only_aggregates",
        len(exported) > 0 and all(
            ipaddress.ip_network(prefix).prefixlen == 16
            for prefix in observed_prefixes
        ),
        {
            "routes": len(exported),
            "prefix_count": len(observed_prefixes),
            "prefix_sample": observed_prefixes[:20],
        },
    )
    racks = [node for node in manifest["nodes"].values() if node["role"] == "rack"]
    clusters = manifest["clusters"]
    scenario = manifest["scenario"]
    if manifest["parameters"].get("cluster_protocol", "ospf") == "bgp":
        ospf = bf.q.ospfProcessConfiguration(nodes="/.*-k[0-9]+-.*/").answer().frame()
        check("no_ospf_processes_inside_clusters", len(ospf) == 0, len(ospf))
        cluster = clusters[0]
        local_prefixes = {
            prefix
            for node in racks if node["domain"] == cluster["name"]
            for prefix in node["rack_prefixes"]
        }
        local = bf.q.routes(
            nodes=cluster["name"] + "-agg-0",
            protocols="bgp",
            network=cluster["prefix"],
            prefixMatchType="LONGER_PREFIXES",
        ).answer().frame()
        local_bgp = {
            prefix for prefix in local["Network"]
            if ipaddress.ip_network(prefix).prefixlen == 24
        }
        check(
            "local_rack_specifics_learned_via_bgp",
            local_bgp == local_prefixes,
            {"expected": len(local_prefixes), "observed": len(local_bgp)},
        )

    def addresses(nodes):
        return [
            str(ipaddress.ip_network(prefix).network_address + 1)
            for node in nodes for prefix in node["rack_prefixes"]
        ]

    def reach(name, starts, destinations, actions="failure", transit=None):
        result = bf.q.reachability(
            headers=HeaderConstraints(dstIps=",".join(destinations)),
            pathConstraints=PathConstraints(startLocation=starts, transitLocations=transit),
            actions=actions,
            maxTraces=2,
        ).answer().frame()
        check(name, len(result) == 0, {"counterexamples": len(result), "actions": actions})
        if actions == "failure" and transit is None:
            witnesses = bf.q.reachability(
                headers=HeaderConstraints(dstIps=",".join(destinations)),
                pathConstraints=PathConstraints(startLocation=starts),
                actions="success",
                maxTraces=1,
            ).answer().frame()
            wanted = {
                node["name"] for node in racks if re.fullmatch(starts[1:-1], node["name"])
            }
            observed = {flow.ingressNode for flow in witnesses["Flow"]}
            check(
                name + "_has_witnesses_for_every_source",
                observed == wanted,
                {"sources": len(wanted), "witnessed": len(observed)},
            )

    if not quick:
        loops = bf.q.detectLoops(maxTraces=2).answer().frame()
        check("no_forwarding_loops", len(loops) == 0, len(loops))
        if scenario == "campus-wan":
            for campus in range(manifest["parameters"]["campuses"]):
                own = [node for node in racks if node["campus"] == campus]
                if own:
                    reach(
                        f"campus_{campus}_internal_reachability",
                        f"/c{campus}-.*-tor-.*/", addresses(own),
                    )
            if manifest["parameters"]["campuses"] > 1:
                remote = [node for node in racks if node["campus"] != 0]
                reach(
                    "isolated_campus_cannot_reach_remote_campuses",
                    "/c0-.*-tor-.*/", addresses(remote), actions="success",
                )
                local = [node for node in racks if node["campus"] == 0]
                reach(
                    "remote_campuses_cannot_reach_isolated_campus",
                    "/c[1-9].*-tor-.*/", addresses(local), actions="success",
                )
            reach(
                "isolated_campus_cannot_reach_wan",
                "/c0-.*-tor-.*/", ["192.0.2.1"], actions="success",
            )
        elif scenario == "cluster-isolated":
            cluster = clusters[0]
            own = [node for node in racks if node["domain"] == cluster["name"]]
            reach(
                "isolated_cluster_internal_reachability",
                "/" + cluster["name"] + "-tor-.*/", addresses(own),
            )
            defaults = bf.q.routes(
                nodes="/" + cluster["name"] + "-tor-.*/", network="0.0.0.0/0"
            ).answer().frame()
            check("isolated_cluster_default_withdrawn", len(defaults) == 0, len(defaults))
            reach(
                "isolated_cluster_cannot_reach_wan",
                "/" + cluster["name"] + "-tor-.*/", ["192.0.2.1"], actions="success",
            )
        else:
            reach("all_rack_endpoints_reachable", "/.*-tor-.*/", addresses(racks))
            reach("all_racks_reach_wan_endpoint", "/.*-tor-.*/", ["192.0.2.1"])
        if scenario != "cluster-isolated":
            for campus in range(manifest["parameters"]["campuses"]):
                own = [node for node in racks if node["campus"] == campus]
                for node in manifest["nodes"].values():
                    if node["role"] == "wan":
                        reach(
                            f"campus_{campus}_local_flows_avoid_{node['name']}",
                            f"/c{campus}-.*-tor-.*/",
                            addresses(own),
                            actions="success",
                            transit=node["name"],
                        )

    samples = []
    source = clusters[0]
    targets = [clusters[-1], next(
        (item for item in clusters if item["campus"] == source["campus"]
         and item["building"] != source["building"]), source
    )]
    same_building = next(
        (item for item in clusters if item["campus"] == source["campus"]
         and item["building"] == source["building"] and item["name"] != source["name"]),
        None,
    )
    if same_building is not None:
        targets.append(same_building)
    for target in targets:
        result = bf.q.traceroute(
            startLocation=source["racks"][0],
            headers=HeaderConstraints(
                srcIps=source["representative_ip"], dstIps=target["representative_ip"]
            ),
            maxTraces=2,
        ).answer().frame()
        for _, row in result.iterrows():
            expected_success = not (
                scenario == "cluster-isolated" and target["name"] != source["name"]
                or scenario == "campus-wan" and target["campus"] != source["campus"]
            )
            dispositions = {trace.disposition for trace in row["Traces"]}
            check(
                f"sample_to_{target['name']}",
                dispositions == {"ACCEPTED"} if expected_success else dispositions == {"NO_ROUTE"},
                sorted(dispositions),
            )
            if expected_success and target["campus"] == source["campus"]:
                check(
                    f"local_path_to_{target['name']}_avoids_wan",
                    all(
                        not hop.node.startswith("wan-")
                        for trace in row["Traces"] for hop in trace.hops
                    ),
                    "campus-local path",
                )
                if target["building"] == source["building"]:
                    check(
                        f"building_local_path_to_{target['name']}_stays_at_edge_layer",
                        all(
                            "-border-" not in hop.node and "-campus-" not in hop.node
                            for trace in row["Traces"] for hop in trace.hops
                        ),
                        "building-local path",
                    )
            samples.append(
                {
                    "source": source["racks"][0],
                    "destination": target["representative_ip"],
                    "trace_count": int(row["TraceCount"]),
                    "traces": [
                        {"disposition": trace.disposition, "nodes": [hop.node for hop in trace.hops]}
                        for trace in row["Traces"]
                    ],
                }
            )
    return checks, samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--network", default="google-freedome")
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--compute", action="store_true")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.path / "manifest.json").read_text())
    bf = Session(host=args.host)
    bf.set_network(args.network)
    if args.upload:
        print(f"Initializing {args.snapshot}", flush=True)
        bf.init_snapshot(str(args.path), name=args.snapshot)
    bf.set_snapshot(args.snapshot)
    if args.compute:
        print(f"Computing dataplane for {args.snapshot}", flush=True)
        status = bf.generate_dataplane()
        if status != "TERMINATEDNORMALLY":
            raise RuntimeError(status)
    checks, samples = verify(bf, manifest, args.quick)
    passed = all(check["passed"] for check in checks)
    coverage = (
        "Routing invariants and representative traceroutes."
        if args.quick
        else "Routing invariants, global loop detection, and symbolic endpoint reachability."
    )
    lines = [
        "# Validation",
        "",
        f"Snapshot: `{args.snapshot}`. Scenario: `{manifest['scenario']}`.",
        f"Cluster protocol: `{manifest['parameters'].get('cluster_protocol', 'ospf')}`.",
        "",
        coverage,
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    lines += [
        f"| `{check['check']}` | {'PASS' if check['passed'] else 'FAIL'} |"
        for check in checks
    ]
    lines += ["", "## Sample traces", ""]
    for sample in samples:
        lines += [f"From `{sample['source']}` to `{sample['destination']}`:", ""]
        for trace in sample["traces"]:
            lines += [
                f"Disposition: `{trace['disposition']}`.",
                "",
                "```text",
                " -> ".join(trace["nodes"]),
                "```",
                "",
            ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n")
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
