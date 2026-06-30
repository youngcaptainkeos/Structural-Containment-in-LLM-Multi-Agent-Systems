"""Run numbered, deterministic runtime trust-graph experiments."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "langgraph-fvs-matplotlib")
)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

from enterprise_prompts import sample_enterprise_prompts
from enterprise_topology import (
    DEPARTMENTS,
    build_enterprise_runtime_trust_graph,
    build_enterprise_topology,
    route_prompt_departments,
    classify_workflow_family,
    compute_graph_hash,
)
from fvs_analysis import compute_fvs


LAYOUT_SEED = 42
ROOT = Path(__file__).resolve().parent
EXPERIMENTS_DIR = ROOT / "experiments"
ENTERPRISE_GRAPH = build_enterprise_topology(seed=LAYOUT_SEED)

NODES = list(ENTERPRISE_GRAPH.nodes())

PROMPT_SCENARIOS = sample_enterprise_prompts()

PROMPTS = [scenario["prompt"] for scenario in PROMPT_SCENARIOS]

COMPROMISED_NODES = NODES
TOPOLOGIES = ["enterprise_departmental_workflow"]
TOPOLOGY_TRACE_IDS = {"enterprise_departmental_workflow": "A"}
EXPECTED_TOPOLOGY_TAU: dict[str, int] = {}
STATIC_TAU = len(NODES)


def create_experiment_directory() -> tuple[str, Path]:
    """Atomically create and return the next exp_NNN directory."""
    EXPERIMENTS_DIR.mkdir(exist_ok=True)
    number = 1
    while True:
        experiment_id = f"exp_{number:03d}"
        path = EXPERIMENTS_DIR / experiment_id
        try:
            path.mkdir()
            (path / "figures").mkdir()
            (path / "runtime_logs").mkdir()
            (path / "communications").mkdir()
            return experiment_id, path
        except FileExistsError:
            number += 1


def build_graph(edges: list[tuple[str, str]]) -> nx.DiGraph:
    """Build a topology containing the complete configured node set."""
    graph = nx.DiGraph()
    graph.add_nodes_from(NODES)
    graph.add_edges_from(edges)
    return graph


def propagate_compromise(graph: nx.DiGraph, compromised_node: str) -> list[str]:
    """Return reachable downstream nodes in deterministic BFS order."""
    if compromised_node not in graph:
        return []

    visited = {compromised_node}
    infected: list[str] = []
    queue = deque([compromised_node])
    while queue:
        current = queue.popleft()
        for neighbor in graph.successors(current):
            if neighbor not in visited:
                visited.add(neighbor)
                infected.append(neighbor)
                queue.append(neighbor)
    return infected


def propagate_compromise_depth(graph: nx.DiGraph, compromised_node: str) -> tuple[list[str], int]:
    """Return reachable downstream nodes in BFS order and the maximum propagation depth."""
    if compromised_node not in graph:
        return [], 0

    visited = {compromised_node}
    infected: list[str] = []
    distances = {compromised_node: 0}
    queue = deque([compromised_node])
    while queue:
        current = queue.popleft()
        current_dist = distances[current]
        for neighbor in graph.successors(current):
            if neighbor not in visited:
                visited.add(neighbor)
                distances[neighbor] = current_dist + 1
                infected.append(neighbor)
                queue.append(neighbor)
    max_depth = max(distances.values()) if distances else 0
    return infected, max_depth


def generate_agent_output(
    agent: str,
    scenario: dict[str, str],
    compromised_node: str,
) -> str:
    """Generate deterministic role-specific content carrying a poison marker."""
    finding = scenario["finding"]
    estimate = scenario["estimate"]
    category = scenario.get("category", "Enterprise")
    role_outputs = {
        "researcher": f"Researcher: Collected literature regarding {category.lower()} risk and documented evidence. {finding}",
        "writer": f"Writer: Drafted enterprise briefing with evidence, recommendations, and residual risks. {finding}",
        "reviewer": f"Reviewer: Reviewed assumptions, challenged unsupported claims, and requested validation. {finding}",
        "math": f"Finance: Estimated project cost and exposure. {estimate}",
        "auditor": f"Auditor: Policy violation identified and mapped to required remediation evidence. {finding}",
        "planner": f"Planner: Generated implementation roadmap with owners, milestones, and control checkpoints. {estimate}",
        "coder": "Backend Engineer: Implemented authentication service with audit logging, rollback hooks, and service telemetry.",
        "critic": f"Risk Reviewer: Identified unresolved dependency, compliance, and delivery risks. {finding}",
        "verifier": "QA: Detected failing security regression and flagged release readiness for follow-up.",
        "summarizer": f"Executive Communications: Summarized business impact, decision options, and cost exposure. {estimate}",
        "security": "Threat Intelligence: Detected malicious IOC and recommended containment, credential rotation, and monitoring.",
        "database": "Data Platform Engineer: Validated encryption, backup integrity, retention controls, and lineage coverage.",
        "api": "API Engineer: Reviewed authentication, schema validation, idempotency, throttling, and audit requirements.",
        "executor": "Operations Lead: Executed workflow handoff, tracked operational readiness, and recorded rollback conditions.",
        "supervisor": f"Executive Supervisor: Approved escalation path and requested measurable remediation plan. {estimate}",
        "Executive Supervisor": f"Executive Supervisor: Prioritized business risk, funding decision, and accountable owners. {estimate}",
        "Executive Strategy": f"Executive Strategy: Connected the work to enterprise objectives and risk appetite. {finding}",
        "Executive Legal": f"Legal Counsel: Reviewed contractual, privacy, and regulatory exposure. {finding}",
        "Executive Finance": f"Finance: Estimated project cost, business exposure, and funding impact. {estimate}",
        "Executive Communications": "Executive Communications: Prepared stakeholder update with decision context and next steps.",
        "Executive Governance": "Governance Lead: Recorded decision rights, policy exceptions, and escalation requirements.",
        "Research Supervisor": f"Research Supervisor: Scoped evidence collection and review criteria for the task. {finding}",
        "Research Scientist": f"Researcher: Collected literature regarding {category.lower()} migration and risk. {finding}",
        "Research Analyst": f"Research Analyst: Compared evidence, constraints, and likely enterprise impact. {finding}",
        "Research Writer": f"Research Writer: Drafted findings into an executive-ready research report. {finding}",
        "Research Reviewer": "Research Reviewer: Validated citations, challenged assumptions, and requested missing evidence.",
        "Research Data Steward": "Data Steward: Checked data lineage, retention assumptions, and evidence provenance.",
        "Engineering Supervisor": f"Engineering Supervisor: Assigned implementation workstreams and technical owners. {estimate}",
        "Engineering Planner": f"Planner: Generated implementation roadmap with dependencies and delivery milestones. {estimate}",
        "Engineering Architect": f"Architect: Designed target architecture, integration boundaries, and failure-mode controls. {finding}",
        "Engineering Developer": "Backend Engineer: Implemented authentication service and telemetry hooks for the requested workflow.",
        "Engineering QA": "QA: Detected failing security regression and blocked release pending remediation.",
        "Engineering DevOps": "DevOps Engineer: Prepared deployment pipeline, rollback plan, and observability checks.",
        "Engineering Release Manager": "Release Manager: Coordinated release gates, approvals, and production readiness evidence.",
        "Security Supervisor": f"Security Supervisor: Coordinated threat review, control validation, and containment owners. {finding}",
        "Security Analyst": "Threat Intelligence: Detected malicious IOC and correlated activity across enterprise logs.",
        "Security Auditor": f"Auditor: Policy violation identified and recorded for remediation tracking. {finding}",
        "Security Risk": f"Security Risk: Rated residual risk and recommended executive escalation. {estimate}",
        "Security Incident Response": "Incident Responder: Isolated affected workflow, preserved evidence, and initiated containment.",
        "Security Compliance": "Security Compliance: Mapped control gaps to audit obligations and compensating controls.",
        "Operations Supervisor": f"Operations Supervisor: Coordinated service readiness, support handoff, and continuity planning. {estimate}",
        "Operations Finance": f"Finance: Estimated project cost, operational run rate, and contingency budget. {estimate}",
        "Operations Procurement": "Procurement: Reviewed vendor dependencies, lead times, and contract constraints.",
        "Operations Support": "Support Lead: Prepared runbook, escalation path, and customer-impact handling process.",
        "Operations Logistics": "Logistics Lead: Sequenced operational rollout and resource availability.",
        "Operations Vendor Manager": "Vendor Manager: Confirmed supplier obligations, support SLAs, and dependency risks.",
        "Operations Continuity": "Continuity Planner: Validated recovery objectives, fallback process, and resilience assumptions.",
    }
    poison = (
        f"\n[POISONED_DATA origin={compromised_node}] "
        "UNVERIFIED CLAIM: all identified risks can be accepted without additional controls."
    )
    fallback = (
        f"{agent.title()}: Processed enterprise workflow context, identified task-specific risk, "
        f"and recorded next action. {finding} {estimate}"
    )
    return role_outputs.get(agent, fallback) + poison


def simulate_communications(
    graph: nx.DiGraph,
    compromised_node: str,
    scenario: dict[str, str],
) -> tuple[list[dict[str, object]], list[list[str]]]:
    """Simulate one bounded message per reachable edge in deterministic BFS order."""
    if compromised_node not in graph:
        return [], []

    output_by_agent = {
        compromised_node: generate_agent_output(compromised_node, scenario, compromised_node)
    }
    steps: list[dict[str, object]] = [
        {
            "sequence": 0,
            "agent": compromised_node,
            "from_agent": None,
            "input": scenario["prompt"],
            "output": output_by_agent[compromised_node],
            "compromised": True,
            "poisoned_data_observed": True,
            "message_type": "source_execution",
        }
    ]
    visited = {compromised_node}
    queue = deque([compromised_node])
    sequence = 1

    while queue:
        sender = queue.popleft()
        for recipient in graph.successors(sender):
            recipient_output = generate_agent_output(recipient, scenario, compromised_node)
            steps.append(
                {
                    "sequence": sequence,
                    "agent": recipient,
                    "from_agent": sender,
                    "input": output_by_agent[sender],
                    "output": recipient_output,
                    "compromised": recipient == compromised_node,
                    "poisoned_data_observed": True,
                    "message_type": "agent_message",
                }
            )
            sequence += 1
            output_by_agent[recipient] = recipient_output
            if recipient not in visited:
                visited.add(recipient)
                queue.append(recipient)

    infection_paths = [
        nx.shortest_path(graph, compromised_node, infected_node)
        for infected_node in visited
        if infected_node != compromised_node
    ]
    infection_paths.sort(key=lambda path: (len(path), path))
    return steps, infection_paths


HANDOFF_RATIONALES = {
    ("Executive", "Research"): "Executive Supervisor assigned the strategic objective to Research Supervisor for in-depth analysis.",
    ("Research", "Executive"): "Research Supervisor sent the finalized research findings to Executive Supervisor for strategic review.",
    ("Executive", "Engineering"): "Executive Supervisor commissioned Engineering Supervisor to initiate system design and development.",
    ("Engineering", "Executive"): "Engineering Supervisor delivered the release report to Executive Supervisor for review.",
    ("Executive", "Security"): "Executive Supervisor requested Security Supervisor to conduct a compliance and threat audit.",
    ("Security", "Executive"): "Security Risk escalated risk and assessment findings to Executive Supervisor.",
    ("Executive", "Operations"): "Executive Supervisor tasked Operations Supervisor with deployment and procurement coordination.",
    ("Operations", "Executive"): "Operations Supervisor confirmed operational readiness to Executive Supervisor.",
    ("Research", "Engineering"): "Research Writer shared requirements with Engineering Planner to start architecting the solution.",
    ("Research", "Security"): "Research Supervisor consulted Security Supervisor on zero-trust and encryption requirements.",
    ("Engineering", "Research"): "Engineering Supervisor requested Research Supervisor for further feasibility assessment on new tech.",
    ("Engineering", "Security"): "Engineering QA requested Security Auditor to perform a security and vulnerability scan on release.",
    ("Engineering", "Operations"): "Engineering Supervisor coordinated rollout plans with Operations Supervisor.",
    ("Security", "Engineering"): "Security Supervisor advised Engineering Supervisor on containment and patch deployment.",
    ("Security", "Operations"): "Security Supervisor coordinated firewall and access controls with Operations Supervisor.",
    ("Operations", "Security"): "Operations Supervisor requested Security Supervisor to review vendor security compliance.",
    ("Operations", "Research"): "Operations Finance consulted Research Supervisor on research adoption cost estimates.",
}


def generate_execution_narrative(trace: dict[str, object]) -> list[str]:
    """Generate a human-readable case study explanation for the empirical evaluation."""
    route = trace.get("route", [])
    active_nodes = trace.get("active_nodes_list", [])
    compromised = trace.get("compromise_source", "")
    fvs = trace.get("fvs_nodes", [])
    infected_before = trace.get("infected_nodes", [])
    depth_before = trace.get("depth_before", 0)
    depth_after = trace.get("depth_after", 0)
    depts_before = trace.get("affected_depts_before", 0)
    depts_after = trace.get("affected_depts_after", 0)
    efficiency = trace.get("containment_efficiency", 0.0)
    paths = trace.get("infection_paths", [])

    lines = [
        "# Execution Narrative",
        "",
        "### 🏢 Participating Departments",
        " → ".join(route),
        "",
        "### 👥 Specialists Collaborating",
    ]
    
    dept_agents: dict[str, list[str]] = {}
    for node in active_nodes:
        for dept in ["Executive", "Research", "Engineering", "Security", "Operations"]:
            if node.startswith(dept):
                dept_agents.setdefault(dept, []).append(node)
                break
                
    for dept in sorted(dept_agents.keys()):
        agents_str = ", ".join(sorted(dept_agents[dept]))
        lines.append(f"- **{dept}**: {agents_str}")
        
    lines.extend([
        "",
        "### 🔗 Handoff Rationale",
    ])
    for u, v in zip(route, route[1:]):
        if u != v:
            rationale = HANDOFF_RATIONALES.get((u, v), f"Handoff from {u} to {v} for workflow progression.")
            lines.append(f"- **{u} → {v}**: {rationale}")
            
    lines.extend([
        "",
        "### ⚠️ Compromise Propagation Trace",
    ])
    if not infected_before:
        lines.append(f"The compromise remained isolated at the source (**{compromised}**) and did not spread.")
    else:
        lines.append(f"The compromise initiated at **{compromised}** and propagated to the following downstream nodes:")
        for path in paths:
            if len(path) > 1:
                target = path[-1]
                path_str = " → ".join(path)
                lines.append(f"- **{target}** (Path: {path_str})")
                
    lines.extend([
        "",
        "### 🛡️ Feedback Vertex Set (FVS) Containment",
        f"- **FVS Nodes Selected**: {', '.join(fvs) if fvs else 'None (Topology is acyclic)'}",
        f"- **Containment Efficiency**: {efficiency * 100:.1f}%",
        f"- **Propagation Depth**: Reduced from {depth_before} to {depth_after} hops.",
        f"- **Affected Departments**: Reduced from {depts_before} to {depts_after} departments.",
    ])
    if efficiency == 1.0:
        lines.append("Complete containment was achieved. All downstream compromise propagation was blocked.")
    elif efficiency > 0.0:
        lines.append("Partial containment was achieved. Compromise propagation was significantly limited.")
    else:
        lines.append("No active feedback cycles were present, or containment did not change the reachability footprint.")
        
    lines.extend([
        "",
        "---",
        ""
    ])
    return lines


def communication_markdown(trace: dict[str, object]) -> str:
    """Render a communication trace as a reviewer-readable Markdown transcript."""
    lines = generate_execution_narrative(trace)
    
    lines.extend([
        "# Prompt",
        "",
        str(trace["prompt"]),
        "",
        f"**Topology:** {trace['topology']}  ",
        f"**Compromised node:** {trace['compromise_source']}  ",
        f"**Runtime τ_FVS:** {trace['runtime_tau']}  ",
        f"**FVS nodes:** {', '.join(trace['fvs_nodes']) or 'None'}  ",
        f"**Messages before revocation:** {trace['message_count']}  ",
        f"**Messages after revocation:** {trace['message_count_after_revocation']}",
        "",
        "---",
        "",
        "# Communication Before Revocation",
    ])
    for step in trace["steps"]:
        lines.extend(
            [
                "",
                f"## {step['sequence']:02d}. {str(step['agent']).title()}",
                "",
                f"From: {step['from_agent'] or 'User prompt'}",
                "",
                "Input:",
                str(step["input"]),
                "",
                "Output:",
                str(step["output"]),
                "",
                f"Compromised: {step['compromised']}",
                "",
                f"Poisoned Data Observed: {step['poisoned_data_observed']}",
                "",
                "---",
            ]
        )

    lines.extend(["", "# Communication After FVS Revocation"])
    if not trace["post_revocation_steps"]:
        lines.extend(["", "No communication occurred because the compromise source was revoked."])
    else:
        for step in trace["post_revocation_steps"]:
            lines.extend(
                [
                    "",
                    f"## {step['sequence']:02d}. {str(step['agent']).title()}",
                    "",
                    f"From: {step['from_agent'] or 'User prompt'}",
                    "",
                    "Input:",
                    str(step["input"]),
                    "",
                    "Output:",
                    str(step["output"]),
                    "",
                    f"Poisoned Data Observed: {step['poisoned_data_observed']}",
                    "",
                    "---",
                ]
            )
    return "\n".join(lines) + "\n"


def save_communication_trace(
    json_path: Path,
    markdown_path: Path,
    trace: dict[str, object],
) -> None:
    """Store the same communication evidence as structured JSON and Markdown."""
    json_path.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(communication_markdown(trace), encoding="utf-8")


def save_runtime_log(path: Path, edges: list[tuple[str, str]]) -> None:
    """Save a deterministic JSONL edge trace."""
    with path.open("w", encoding="utf-8") as log_file:
        for source, target in edges:
            log_file.write(json.dumps({"source": source, "target": target}) + "\n")


DEPARTMENT_CENTERS = {
    "Research": (0.0, 3.2),
    "Engineering": (-3.3, 0.4),
    "Executive": (3.3, 0.4),
    "Security": (-3.3, -2.8),
    "Operations": (3.3, -2.8),
}

DEPARTMENT_COLORS = {
    "Executive": "#f8e7d0",
    "Research": "#dceefb",
    "Engineering": "#e4f4df",
    "Security": "#fde2e1",
    "Operations": "#eee6fb",
}


def departmental_layout(graph: nx.DiGraph) -> dict[str, tuple[float, float]]:
    """Return deterministic positions using fixed department centers."""
    positions: dict[str, tuple[float, float]] = {}
    for department, center in DEPARTMENT_CENTERS.items():
        department_nodes = [
            node
            for node, attributes in graph.nodes(data=True)
            if attributes.get("department") == department
        ]
        subgraph = graph.subgraph(department_nodes)
        local_positions = nx.spring_layout(subgraph, seed=LAYOUT_SEED, scale=0.95)
        supervisor = DEPARTMENTS[department]["supervisor"]
        for node, (x_position, y_position) in local_positions.items():
            if node == supervisor:
                positions[node] = center
            else:
                positions[node] = (center[0] + float(x_position), center[1] + float(y_position))
    return positions


def draw_department_backgrounds(axis: plt.Axes) -> None:
    """Draw lightly shaded department regions behind the enterprise graph."""
    for department, center in DEPARTMENT_CENTERS.items():
        axis.add_patch(
            Circle(
                center,
                radius=1.85,
                facecolor=DEPARTMENT_COLORS[department],
                edgecolor="#b8b8b8",
                linewidth=1.0,
                alpha=0.65,
                zorder=0,
            )
        )
        axis.text(
            center[0],
            center[1] + 2.05,
            department,
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
            color="#333333",
        )


def save_trace_graph(
    path: Path,
    graph: nx.DiGraph,
    compromised_node: str,
    infected_nodes: list[str],
    fvs_nodes: list[str],
    title: str,
    run_id: str = "N/A",
    topology: str = "N/A",
    tau_runtime: int = 0,
    k_before: int = 0,
    k_after: int = 0,
    containment_efficiency: float = 1.0,
) -> None:
    """Render compromise state and FVS membership for one run with high-quality visual features."""
    path_png = Path(path)
    path_pdf = path_png.with_suffix(".pdf")
    
    display_graph = ENTERPRISE_GRAPH
    positions = departmental_layout(display_graph)
    active_nodes = set(graph.nodes())
    infected = set(infected_nodes)
    fvs = set(fvs_nodes)
    
    colors = [
        "#e74c3c" if node == compromised_node
        else "#f1c40f" if node in infected
        else "#2ecc71" if node in active_nodes
        else "#d9d9d9"
        for node in display_graph.nodes()
    ]
    borders = ["black" if node in fvs else "#666666" for node in display_graph.nodes()]
    widths = [3.2 if node in fvs else 1.0 for node in display_graph.nodes()]

    figure, axis = plt.subplots(figsize=(14, 11))
    draw_department_backgrounds(axis)
    
    inactive_edges = [
        edge for edge in display_graph.edges() if edge[0] not in active_nodes or edge[1] not in active_nodes
    ]
    
    active_edges_list = list(graph.edges())
    active_internal = []
    active_cross = []
    for u, v in active_edges_list:
        dept_u = graph.nodes[u].get("department")
        dept_v = graph.nodes[v].get("department")
        if dept_u == dept_v:
            active_internal.append((u, v))
        else:
            active_cross.append((u, v))
            
    nx.draw_networkx_edges(
        display_graph,
        positions,
        edgelist=inactive_edges,
        ax=axis,
        edge_color="#d0d0d0",
        alpha=0.25,
        arrows=True,
        arrowsize=8,
        width=0.7,
    )
    nx.draw_networkx_edges(
        graph,
        positions,
        edgelist=active_internal,
        ax=axis,
        edge_color="#111111",
        arrows=True,
        arrowsize=14,
        width=1.8,
    )
    nx.draw_networkx_edges(
        graph,
        positions,
        edgelist=active_cross,
        ax=axis,
        edge_color="#333333",
        style="dashed",
        arrows=True,
        arrowsize=14,
        width=1.8,
    )
    nx.draw_networkx_nodes(
        display_graph,
        positions,
        ax=axis,
        node_color=colors,
        edgecolors=borders,
        linewidths=widths,
        node_size=1150,
    )
    
    label_positions = {node: (x, y + 0.15) for node, (x, y) in positions.items()}
    nx.draw_networkx_labels(
        display_graph,
        label_positions,
        ax=axis,
        font_size=7,
        font_family="DejaVu Sans",
        font_weight="bold",
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.7, boxstyle="round,pad=0.2"),
    )
    
    axis.set_title(title, fontsize=12, fontweight="bold")
    axis.axis("off")
    
    axis.legend(
        handles=[
            Line2D([], [], marker="o", linestyle="", color="#e74c3c", label="Compromised"),
            Line2D([], [], marker="o", linestyle="", color="#f1c40f", label="Infected"),
            Line2D([], [], marker="o", linestyle="", color="#2ecc71", label="Active / Safe"),
            Line2D([], [], marker="o", linestyle="", color="#d9d9d9", label="Inactive"),
            Line2D(
                [], [], marker="o", linestyle="", markerfacecolor="white",
                markeredgecolor="black", markeredgewidth=3, label="FVS Node",
            ),
        ],
        loc="lower center",
        ncol=5,
        fontsize=9,
        bbox_to_anchor=(0.5, -0.05)
    )
    
    figure.tight_layout()
    figure.savefig(path_png, dpi=600, bbox_inches="tight")
    figure.savefig(path_pdf, bbox_inches="tight")
    plt.close(figure)


def save_scc_graph(path: Path, graph: nx.DiGraph, title: str) -> None:
    """Render each strongly connected component with a distinct color, highlighting nontrivial SCCs."""
    path_png = Path(path)
    path_pdf = path_png.with_suffix(".pdf")
    
    components = list(nx.strongly_connected_components(graph))
    nontrivial_sccs = [c for c in components if len(c) > 1]
    positions = departmental_layout(ENTERPRISE_GRAPH)
    
    palette = plt.get_cmap("Set2")
    
    colors = []
    borders = []
    widths = []
    for node in ENTERPRISE_GRAPH.nodes():
        in_scc = False
        scc_idx = -1
        for idx, scc in enumerate(nontrivial_sccs):
            if node in scc:
                in_scc = True
                scc_idx = idx
                break
        
        if in_scc:
            colors.append(palette(scc_idx % 8))
            borders.append("#111111")
            widths.append(1.5)
        else:
            colors.append("#e6e6e6")
            borders.append("#cccccc")
            widths.append(1.0)
            
    figure, axis = plt.subplots(figsize=(14, 11))
    draw_department_backgrounds(axis)
    
    active_edges_list = list(graph.edges())
    active_internal = []
    active_cross = []
    for u, v in active_edges_list:
        dept_u = graph.nodes[u].get("department")
        dept_v = graph.nodes[v].get("department")
        if dept_u == dept_v:
            active_internal.append((u, v))
        else:
            active_cross.append((u, v))
            
    nx.draw_networkx_edges(
        graph,
        positions,
        edgelist=active_internal,
        ax=axis,
        edge_color="#333333",
        arrows=True,
        arrowsize=14,
        width=1.5,
    )
    nx.draw_networkx_edges(
        graph,
        positions,
        edgelist=active_cross,
        ax=axis,
        edge_color="#555555",
        style="dashed",
        arrows=True,
        arrowsize=14,
        width=1.5,
    )
    nx.draw_networkx_nodes(
        ENTERPRISE_GRAPH,
        positions,
        ax=axis,
        node_color=colors,
        edgecolors=borders,
        linewidths=widths,
        node_size=1150,
    )
    
    label_positions = {node: (x, y + 0.15) for node, (x, y) in positions.items()}
    nx.draw_networkx_labels(
        ENTERPRISE_GRAPH,
        label_positions,
        ax=axis,
        font_size=7,
        font_family="DejaVu Sans",
        font_weight="bold",
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.7, boxstyle="round,pad=0.2"),
    )
    
    for idx, scc in enumerate(nontrivial_sccs, 1):
        scc_nodes = list(scc)
        scc_subgraph = graph.subgraph(scc_nodes)
        scc_tau, _ = compute_fvs(scc_subgraph)
        
        xs = [positions[node][0] for node in scc_nodes]
        ys = [positions[node][1] for node in scc_nodes]
        centroid_x = sum(xs) / len(scc_nodes)
        centroid_y = sum(ys) / len(scc_nodes)
        
        scc_text = f"SCC {idx}\nNodes: {len(scc_nodes)}\nτ: {scc_tau}"
        axis.text(
            centroid_x, centroid_y + 0.45,
            scc_text,
            fontsize=8,
            fontweight="bold",
            fontfamily="DejaVu Sans",
            ha="center",
            va="center",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="#ffffff",
                edgecolor=palette((idx - 1) % 8),
                alpha=0.95,
                linewidth=1.5,
            ),
            zorder=10
        )
        
    axis.set_title(f"{title} — Strongly Connected Components", fontsize=12, fontweight="bold")
    axis.axis("off")
    figure.tight_layout()
    figure.savefig(path_png, dpi=600, bbox_inches="tight")
    figure.savefig(path_pdf, bbox_inches="tight")
    plt.close(figure)


def save_before_after_comparison(
    path_png: Path,
    path_pdf: Path,
    graph: nx.DiGraph,
    revoked_graph: nx.DiGraph,
    compromised_node: str,
    infected_before: list[str],
    infected_after: list[str],
    fvs_nodes: list[str],
    title: str,
    run_id: str = "N/A",
    topology: str = "N/A",
    tau_runtime: int = 0,
    k_before: int = 0,
    k_after: int = 0,
    containment_efficiency: float = 1.0,
) -> None:
    """Generate a 4-panel figure showing the complete theorem flow from runtime graph to contained state."""
    display_graph = ENTERPRISE_GRAPH
    positions = departmental_layout(display_graph)
    active_nodes = set(graph.nodes())
    fvs = set(fvs_nodes)
    
    active_depts = set(graph.nodes[n].get("department") for n in active_nodes if n in graph)
    
    figure, ((ax_a, ax_b), (ax_c, ax_d)) = plt.subplots(2, 2, figsize=(24, 22))
    
    def draw_backgrounds(ax):
        for dept, center in DEPARTMENT_CENTERS.items():
            is_active = dept in active_depts
            alpha_val = 0.65 if is_active else 0.20
            ax.add_patch(
                Circle(
                    center,
                    radius=1.85,
                    facecolor=DEPARTMENT_COLORS[dept],
                    edgecolor="#b8b8b8",
                    linewidth=1.0,
                    alpha=alpha_val,
                    zorder=0,
                )
            )
            ax.text(
                center[0],
                center[1] + 2.05,
                dept,
                ha="center",
                va="center",
                fontsize=11,
                fontweight="bold",
                color="#333333",
                alpha=1.0 if is_active else 0.4
            )
            
    label_positions = {node: (x, y + 0.15) for node, (x, y) in positions.items()}
    
    def draw_fvs_double_outline(ax, fvs_set, size=950):
        fvs_list = [n for n in display_graph.nodes() if n in fvs_set]
        if fvs_list:
            nx.draw_networkx_nodes(
                display_graph, positions, nodelist=fvs_list, ax=ax,
                node_color="black", node_size=size + 350
            )
            nx.draw_networkx_nodes(
                display_graph, positions, nodelist=fvs_list, ax=ax,
                node_color="white", node_size=size + 150
            )

    # ----------------------------------------------------
    # Panel (a): Runtime Trust Graph
    # ----------------------------------------------------
    draw_backgrounds(ax_a)
    
    colors_a = [
        "#e74c3c" if node == compromised_node
        else "#2ecc71" if node in active_nodes
        else "#d9d9d9"
        for node in display_graph.nodes()
    ]
    borders_a = ["black" if node in fvs else "#666666" for node in display_graph.nodes()]
    widths_a = [1.0 for _ in display_graph.nodes()]
    
    sizes_a = [
        1350 if node == compromised_node
        else 1150 if node in fvs
        else 950
        for node in display_graph.nodes()
    ]
    
    inactive_edges = [
        edge for edge in display_graph.edges() if edge[0] not in active_nodes or edge[1] not in active_nodes
    ]
    active_edges_list = list(graph.edges())
    active_internal = [e for e in active_edges_list if graph.nodes[e[0]].get("department") == graph.nodes[e[1]].get("department")]
    active_cross = [e for e in active_edges_list if graph.nodes[e[0]].get("department") != graph.nodes[e[1]].get("department")]
    
    nx.draw_networkx_edges(
        display_graph, positions, edgelist=inactive_edges, ax=ax_a,
        edge_color="#d0d0d0", alpha=0.25, arrows=True, arrowsize=8, width=0.7
    )
    nx.draw_networkx_edges(
        graph, positions, edgelist=active_internal, ax=ax_a,
        edge_color="#111111", arrows=True, arrowsize=14, width=1.8
    )
    nx.draw_networkx_edges(
        graph, positions, edgelist=active_cross, ax=ax_a,
        edge_color="#333333", style="dashed", arrows=True, arrowsize=18, width=2.0,
        connectionstyle="arc3,rad=0.1"
    )
    
    draw_fvs_double_outline(ax_a, fvs, size=950)
    nx.draw_networkx_nodes(
        display_graph, positions, ax=ax_a,
        node_color=colors_a, edgecolors=borders_a, linewidths=widths_a, node_size=sizes_a
    )
    nx.draw_networkx_labels(
        display_graph, label_positions, ax=ax_a,
        font_size=7, font_family="DejaVu Sans", font_weight="bold",
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.7, boxstyle="round,pad=0.2")
    )
    ax_a.set_title("(a) Runtime Trust Graph", fontsize=14, fontweight="bold", pad=10)
    ax_a.axis("off")
    
    # ----------------------------------------------------
    # Panel (b): Strongly Connected Components (SCC)
    # ----------------------------------------------------
    draw_backgrounds(ax_b)
    components = list(nx.strongly_connected_components(graph))
    nontrivial_sccs = [c for c in components if len(c) > 1]
    
    palette = plt.get_cmap("Set2")
    colors_b = []
    borders_b = []
    sizes_b = []
    for node in display_graph.nodes():
        in_scc = False
        scc_idx = -1
        for idx, scc in enumerate(nontrivial_sccs):
            if node in scc:
                in_scc = True
                scc_idx = idx
                break
        if in_scc:
            colors_b.append(palette(scc_idx % 8))
            borders_b.append("#111111")
            sizes_b.append(1200)
        else:
            colors_b.append("#e6e6e6")
            borders_b.append("#cccccc")
            sizes_b.append(950)
            
    nx.draw_networkx_edges(
        graph, positions, edgelist=active_internal, ax=ax_b,
        edge_color="#333333", arrows=True, arrowsize=14, width=1.5
    )
    nx.draw_networkx_edges(
        graph, positions, edgelist=active_cross, ax=ax_b,
        edge_color="#555555", style="dashed", arrows=True, arrowsize=18, width=1.5,
        connectionstyle="arc3,rad=0.1"
    )
    nx.draw_networkx_nodes(
        display_graph, positions, ax=ax_b,
        node_color=colors_b, edgecolors=borders_b, node_size=sizes_b
    )
    nx.draw_networkx_labels(
        display_graph, label_positions, ax=ax_b,
        font_size=7, font_family="DejaVu Sans", font_weight="bold",
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.7, boxstyle="round,pad=0.2")
    )
    
    for idx, scc in enumerate(nontrivial_sccs, 1):
        scc_nodes = list(scc)
        scc_subgraph = graph.subgraph(scc_nodes)
        scc_tau, _ = compute_fvs(scc_subgraph)
        xs = [positions[node][0] for node in scc_nodes]
        ys = [positions[node][1] for node in scc_nodes]
        centroid_x = sum(xs) / len(scc_nodes)
        centroid_y = sum(ys) / len(scc_nodes)
        
        scc_text = f"SCC {idx}\nNodes: {len(scc_nodes)}\nτ: {scc_tau}"
        ax_b.text(
            centroid_x, centroid_y + 0.45,
            scc_text,
            fontsize=8,
            fontweight="bold",
            fontfamily="DejaVu Sans",
            ha="center",
            va="center",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="#ffffff",
                edgecolor=palette((idx - 1) % 8),
                alpha=0.95,
                linewidth=1.5,
            ),
            zorder=10
        )
    ax_b.set_title("(b) SCC & Feedback Cycles", fontsize=14, fontweight="bold", pad=10)
    ax_b.axis("off")
    
    # ----------------------------------------------------
    # Panel (c): Before FVS Revocation
    # ----------------------------------------------------
    draw_backgrounds(ax_c)
    inf_left = set(infected_before)
    
    colors_c = [
        "#e74c3c" if node == compromised_node
        else "#f1c40f" if node in inf_left
        else "#2ecc71" if node in active_nodes
        else "#d9d9d9"
        for node in display_graph.nodes()
    ]
    borders_c = ["black" if node in fvs else "#666666" for node in display_graph.nodes()]
    
    sizes_c = [
        1350 if node == compromised_node
        else 1200 if node in inf_left
        else 1150 if node in fvs
        else 950
        for node in display_graph.nodes()
    ]
    
    nx.draw_networkx_edges(
        display_graph, positions, edgelist=inactive_edges, ax=ax_c,
        edge_color="#d0d0d0", alpha=0.25, arrows=True, arrowsize=8, width=0.7
    )
    nx.draw_networkx_edges(
        graph, positions, edgelist=active_internal, ax=ax_c,
        edge_color="#111111", arrows=True, arrowsize=14, width=1.8
    )
    nx.draw_networkx_edges(
        graph, positions, edgelist=active_cross, ax=ax_c,
        edge_color="#333333", style="dashed", arrows=True, arrowsize=18, width=2.0,
        connectionstyle="arc3,rad=0.1"
    )
    
    draw_fvs_double_outline(ax_c, fvs, size=950)
    nx.draw_networkx_nodes(
        display_graph, positions, ax=ax_c,
        node_color=colors_c, edgecolors=borders_c, node_size=sizes_c
    )
    nx.draw_networkx_labels(
        display_graph, label_positions, ax=ax_c,
        font_size=7, font_family="DejaVu Sans", font_weight="bold",
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.7, boxstyle="round,pad=0.2")
    )
    ax_c.set_title("(c) Before Containment", fontsize=14, fontweight="bold", pad=10)
    ax_c.axis("off")
    
    # ----------------------------------------------------
    # Panel (d): After FVS-Based Containment
    # ----------------------------------------------------
    draw_backgrounds(ax_d)
    active_right = set(revoked_graph.nodes())
    inf_right = set(infected_after)
    
    colors_d = []
    alphas_d = []
    sizes_d = []
    for node in display_graph.nodes():
        if node == compromised_node:
            colors_d.append("#e74c3c")
            alphas_d.append(1.0)
            sizes_d.append(1350)
        elif node in inf_right:
            colors_d.append("#f1c40f")
            alphas_d.append(1.0)
            sizes_d.append(1200)
        elif node in active_right:
            colors_d.append("#2ecc71")
            alphas_d.append(0.35)
            sizes_d.append(950)
        else:
            colors_d.append("#d9d9d9")
            alphas_d.append(0.20)
            sizes_d.append(950)
            
    borders_d = ["black" if node in fvs else "#666666" for node in display_graph.nodes()]
    
    inactive_right_edges = [
        edge for edge in display_graph.edges() if edge[0] not in active_right or edge[1] not in active_right
    ]
    active_right_edges = list(revoked_graph.edges())
    active_right_internal = [e for e in active_right_edges if revoked_graph.nodes[e[0]].get("department") == revoked_graph.nodes[e[1]].get("department")]
    active_right_cross = [e for e in active_right_edges if revoked_graph.nodes[e[0]].get("department") != revoked_graph.nodes[e[1]].get("department")]
    
    nx.draw_networkx_edges(
        display_graph, positions, edgelist=inactive_right_edges, ax=ax_d,
        edge_color="#d0d0d0", alpha=0.15, arrows=True, arrowsize=8, width=0.7
    )
    nx.draw_networkx_edges(
        revoked_graph, positions, edgelist=active_right_internal, ax=ax_d,
        edge_color="#111111", alpha=0.9, arrows=True, arrowsize=14, width=1.8
    )
    nx.draw_networkx_edges(
        revoked_graph, positions, edgelist=active_right_cross, ax=ax_d,
        edge_color="#333333", style="dashed", alpha=0.9, arrows=True, arrowsize=18, width=2.0,
        connectionstyle="arc3,rad=0.1"
    )
    
    for node_idx, node in enumerate(display_graph.nodes()):
        if node in fvs:
            nx.draw_networkx_nodes(
                display_graph, positions, nodelist=[node], ax=ax_d,
                node_color="black", node_size=sizes_d[node_idx] + 350,
                alpha=alphas_d[node_idx]
            )
            nx.draw_networkx_nodes(
                display_graph, positions, nodelist=[node], ax=ax_d,
                node_color="white", node_size=sizes_d[node_idx] + 150,
                alpha=alphas_d[node_idx]
            )
            
        nx.draw_networkx_nodes(
            display_graph, positions, nodelist=[node], ax=ax_d,
            node_color=[colors_d[node_idx]], edgecolors=[borders_d[node_idx]],
            node_size=[sizes_d[node_idx]], alpha=alphas_d[node_idx]
        )
        
    nx.draw_networkx_labels(
        display_graph, label_positions, ax=ax_d,
        font_size=7, font_family="DejaVu Sans", font_weight="bold",
        bbox=dict(facecolor="white", edgecolor="none", alpha=0.6, boxstyle="round,pad=0.2")
    )
    ax_d.set_title("(d) After FVS Containment", fontsize=14, fontweight="bold", pad=10)
    ax_d.axis("off")
    
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#e74c3c", markersize=10, label="Compromised"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#f1c40f", markersize=10, label="Infected"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="white", markeredgecolor="black", markeredgewidth=3, markersize=10, label="FVS Node (Revocation target)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2ecc71", markersize=10, label="Active / Safe"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#d9d9d9", markersize=10, label="Inactive / Revoked"),
    ]
    figure.legend(handles=legend_elements, loc="lower center", ncol=5, fontsize=12, frameon=True, bbox_to_anchor=(0.5, 0.02))
    
    figure.suptitle(f"FVS Containment Theorem Flow — {run_id} ({topology})", fontsize=18, fontweight="bold", y=0.96)
    
    plt.subplots_adjust(bottom=0.08, top=0.90, wspace=0.15, hspace=0.15)
    figure.savefig(path_png, dpi=600, bbox_inches="tight")
    figure.savefig(path_pdf, bbox_inches="tight")
    plt.close(figure)


def save_run_summary_table(
    path_png: Path,
    path_pdf: Path,
    graph: nx.DiGraph,
    compromised_node: str,
    fvs_nodes: list[str],
    run_id: str,
    topology: str,
    tau_runtime: int,
    scc_count: int,
    components: list[set[str]],
    k_before: int,
    k_after: int,
    containment_efficiency: float,
    depth_before: int,
    depth_after: int,
    graph_hash: str,
) -> None:
    """Render a separate publication-quality summary table figure for a run."""
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.axis("off")
    
    largest_scc = max([len(c) for c in components]) if components else 0
    
    table_data = [
        ["Experiment Metric", "Observed Simulation Value"],
        ["Run ID", run_id],
        ["Workflow", topology],
        ["Compromised Agent", compromised_node],
        ["Runtime τ_FVS", str(tau_runtime)],
        ["FVS Size", str(len(fvs_nodes))],
        ["Active Agents", str(graph.number_of_nodes())],
        ["Active Edges", str(graph.number_of_edges())],
        ["SCC Count", str(scc_count)],
        ["Largest SCC Size", str(largest_scc)],
        ["Infected Before", str(k_before)],
        ["Infected After", str(k_after)],
        ["Containment Efficiency", f"{containment_efficiency * 100:.1f}%"],
        ["Propagation Depth", f"{depth_before} -> {depth_after} (Reduction: {depth_before - depth_after} hops)"],
        ["Graph Hash", graph_hash],
    ]
    
    table = ax.table(
        cellText=table_data[1:],
        colLabels=table_data[0],
        loc="center",
        cellLoc="left",
        colWidths=[0.38, 0.62],
    )
    
    table.auto_set_font_size(False)
    table.set_fontsize(10.5)
    table.scale(1.2, 1.6)
    
    for (row_idx, col_idx), cell in table.get_celld().items():
        if row_idx == 0:
            cell.set_text_props(weight="bold", color="white", fontsize=11)
            cell.set_facecolor("#2c3e50")
            cell.set_edgecolor("#2c3e50")
        else:
            if row_idx % 2 == 0:
                cell.set_facecolor("#f8f9fa")
            else:
                cell.set_facecolor("#ffffff")
            cell.set_edgecolor("#e9ecef")
            
            if table_data[row_idx][0] == "Containment Efficiency":
                cell.set_text_props(weight="bold", color="#27ae60" if k_after == 0 else "#e67e22")
            if table_data[row_idx][0] == "Run ID":
                cell.set_text_props(weight="bold")
                 
    fig.suptitle(f"Containment Simulation Executive Summary — {run_id}", fontsize=14, fontweight="bold", y=0.96)
    
    fig.savefig(path_png, dpi=600, bbox_inches="tight")
    fig.savefig(path_pdf, bbox_inches="tight")
    plt.close(fig)


def save_aggregate_charts(results: pd.DataFrame, figures_dir: Path) -> None:
    """Save τ distribution and compromise propagation comparison charts in PNG (600 DPI) and PDF formats."""
    # 1. runtime_tau_histogram.png & .pdf
    tau_min = int(results["Runtime τ"].min())
    tau_max = int(results["Runtime τ"].max())
    bins = [value - 0.5 for value in range(tau_min, tau_max + 2)]
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.hist(results["Runtime τ"], bins=bins, edgecolor="black", color="#3498db")
    axis.set_xticks(range(tau_min, tau_max + 1))
    axis.set_xlabel("Runtime τ")
    axis.set_ylabel("Run Count")
    axis.set_title("Runtime τ Distribution")
    figure.tight_layout()
    figure.savefig(figures_dir / "runtime_tau_histogram.png", dpi=600)
    figure.savefig(figures_dir / "runtime_tau_histogram.pdf")
    plt.close(figure)

    # 2. containment_efficiency_histogram.png & .pdf
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.hist(results["Containment Efficiency"] * 100, bins=10, edgecolor="black", color="#2ecc71")
    axis.set_xlabel("Containment Efficiency (%)")
    axis.set_ylabel("Run Count")
    axis.set_title("Containment Efficiency Distribution")
    figure.tight_layout()
    figure.savefig(figures_dir / "containment_efficiency_histogram.png", dpi=600)
    figure.savefig(figures_dir / "containment_efficiency_histogram.pdf")
    plt.close(figure)

    # 3. k_before_after_boxplot.png & .pdf
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.boxplot([results["K Before"], results["K After"]])
    axis.set_xticklabels(["K Before", "K After"])
    axis.set_ylabel("Infected Agents Count")
    axis.set_title("Compromise Footprint Before vs After Revocation")
    figure.tight_layout()
    figure.savefig(figures_dir / "k_before_after_boxplot.png", dpi=600)
    figure.savefig(figures_dir / "k_before_after_boxplot.pdf")
    plt.close(figure)

    # 4. runtime_tau_vs_messages.png & .pdf
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.scatter(results["Runtime τ"], results["Messages Before"], alpha=0.6, color="#e74c3c", edgecolor="black")
    axis.set_xlabel("Runtime τ")
    axis.set_ylabel("Messages Before")
    axis.set_title("Runtime τ vs Message Count")
    figure.tight_layout()
    figure.savefig(figures_dir / "runtime_tau_vs_messages.png", dpi=600)
    figure.savefig(figures_dir / "runtime_tau_vs_messages.pdf")
    plt.close(figure)

    # 5. runtime_tau_vs_kbefore.png & .pdf
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.scatter(results["Runtime τ"], results["K Before"], alpha=0.6, color="#9b59b6", edgecolor="black")
    axis.set_xlabel("Runtime τ")
    axis.set_ylabel("K Before (Infected Downstream Agents)")
    axis.set_title("Runtime τ vs Initial Compromise Footprint")
    figure.tight_layout()
    figure.savefig(figures_dir / "runtime_tau_vs_kbefore.png", dpi=600)
    figure.savefig(figures_dir / "runtime_tau_vs_kbefore.pdf")
    plt.close(figure)


def write_prompts(path: Path, prompts: list[str]) -> None:
    """Persist the exact ordered prompt set used by the experiment."""
    path.write_text(
        "\n".join(f"{index}. {prompt}" for index, prompt in enumerate(prompts, 1)) + "\n",
        encoding="utf-8",
    )


def write_metadata(experiment_id: str, path: Path, run_count: int, seed: int = 42) -> None:
    """Persist experiment configuration and reproducibility metadata."""
    import subprocess
    git_commit = "unknown"
    try:
        git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
    except Exception:
        pass
    metadata = {
        "Experiment ID": experiment_id,
        "Date": datetime.now(timezone.utc).isoformat(),
        "Git Commit": git_commit,
        "Seed": seed,
        "Prompt Dataset Version": "1.0",
        "Enterprise Size": len(NODES),
        "Number of Runs": run_count,
        "Workflow Families": 10,
        "Simulator Version": "1.0"
    }
    path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def build_grouped_summaries(results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate run metrics by topology and by observed runtime tau."""
    aggregations = {
        "Runs": ("Run ID", "count"),
        "Mean K Before": ("K Before", "mean"),
        "Mean K After": ("K After", "mean"),
        "Containment Success Rate (%)": ("Containment Success", lambda values: values.mean() * 100),
        "Mean Message Count": ("Message Count", "mean"),
        "Total Message Count": ("Message Count", "sum"),
        "Mean Containment Efficiency": ("containment_efficiency", "mean"),
        "Mean Propagation Depth Before": ("propagation_depth_before", "mean"),
        "Mean Propagation Depth After": ("propagation_depth_after", "mean"),
    }
    by_topology = (
        results.groupby(["Topology", "Runtime τ_FVS"], sort=False)
        .agg(**aggregations)
        .reset_index()
    )
    by_tau = (
        results.groupby("Runtime τ_FVS", sort=True)
        .agg(Topologies=("Topology", "nunique"), **aggregations)
        .reset_index()
    )
    numeric_columns = [
        "Mean K Before",
        "Mean K After",
        "Containment Success Rate (%)",
        "Mean Message Count",
        "Mean Containment Efficiency",
        "Mean Propagation Depth Before",
        "Mean Propagation Depth After",
    ]
    by_topology[numeric_columns] = by_topology[numeric_columns].round(2)
    by_tau[numeric_columns] = by_tau[numeric_columns].round(2)
    return by_topology, by_tau


def write_validation_report(
    results: pd.DataFrame,
    by_topology: pd.DataFrame,
    by_tau: pd.DataFrame,
    path: Path,
) -> None:
    """Generate a conclusion from observed values without assuming success."""
    observed = sorted(int(value) for value in results["Runtime τ_FVS"].unique())
    maximum = int(results["Runtime τ_FVS"].max())
    minimum = int(results["Runtime τ_FVS"].min())
    containment_rate = float(results["Containment Success"].mean() * 100)
    average_before = float(results["K Before"].mean())
    average_after = float(results["K After"].mean())
    average_messages = float(results["Message Count"].mean())
    total_messages = int(results["Message Count"].sum())
    bound_holds = maximum <= STATIC_TAU
    
    unique_hashes = results["Graph Hash"].nunique()
    
    avg_efficiency = float(results["containment_efficiency"].mean() * 100)
    avg_prop_depth_before = float(results["propagation_depth_before"].mean())
    avg_prop_depth_after = float(results["propagation_depth_after"].mean())
    avg_prop_depth_reduction = float(results["propagation_depth_reduction"].mean())
    avg_depts_before = float(results["affected_departments_before"].mean())
    avg_depts_after = float(results["affected_departments_after"].mean())
    avg_depts_reduction = float(results["affected_departments_reduction"].mean())
    avg_msg_reduction = float(results["message_reduction"].mean())

    violating_topologies = sorted(
        results.loc[results["Runtime τ_FVS"] > STATIC_TAU, "Topology"].unique()
    )
    lines = [
        "Runtime τ_FVS Validation Report",
        "================================",
        "",
        f"Unique Runtime Graphs: {unique_hashes}/{len(results)}",
        f"Observed τ values: {set(observed)}",
        f"Maximum runtime τ: {maximum}",
        f"Minimum runtime τ: {minimum}",
        f"Containment Success Rate: {containment_rate:.1f}%",
        f"Average Containment Efficiency: {avg_efficiency:.1f}%",
        f"Average K Before: {average_before:.2f}",
        f"Average K After: {average_after:.2f}",
        f"Average Message Count: {average_messages:.2f}",
        f"Total Agent-to-Agent Messages: {total_messages}",
        f"Average Propagation Depth Before: {avg_prop_depth_before:.2f}",
        f"Average Propagation Depth After: {avg_prop_depth_after:.2f}",
        f"Average Propagation Depth Reduction: {avg_prop_depth_reduction:.2f}",
        f"Average Affected Departments Before: {avg_depts_before:.2f}",
        f"Average Affected Departments After: {avg_depts_after:.2f}",
        f"Average Affected Departments Reduction: {avg_depts_reduction:.2f}",
        f"Average Message Reduction: {avg_msg_reduction:.2f}",
        f"Static τ_FVS: {STATIC_TAU}",
        "",
        "Static upper-bound validation: " + ("PASS" if bound_holds else "FAIL"),
    ]
    if bound_holds:
        lines.append("All observed runtime τ values were less than or equal to the static upper bound.")
    else:
        lines.append(
            "The configured static upper bound was exceeded by: "
            + ", ".join(violating_topologies)
            + "."
        )
        
    lines.extend([
        "",
        "Workflow Family Validation Summary:",
        "-----------------------------------"
    ])
    family_groups = results.groupby("workflow_family")
    for name, group in family_groups:
        family_taus = sorted([int(x) for x in group["Runtime τ_FVS"].unique()])
        family_depts = sorted(group["activated_departments"].unique())
        lines.append(f"Family: {name}")
        lines.append(f"  Observed τ values: {family_taus}")
        lines.append(f"  Unique department routes activated: {len(family_depts)}")

    lines.extend(
        [
            "",
            "Summary by topology:",
            by_topology.to_string(index=False),
            "",
            "Summary by runtime τ value:",
            by_tau.to_string(index=False),
            "",
            "Interpretation:",
            "FVS revocation guarantees removal of directed cycles. It does not, by itself, "
            "guarantee zero downstream reachability from every compromised node.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_enterprise_prompts(path: Path) -> pd.DataFrame:
    """Robust custom parser for the unquoted enterprise_prompts.csv file."""
    rows = []
    valid_depts = {"Research", "Engineering", "Security", "Operations", "Executive"}
    
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    for line_idx, line in enumerate(lines[1:], 1):
        line = line.strip()
        if not line:
            continue
            
        parts = line.split(",")
        if len(parts) < 9:
            continue
            
        prompt_id = parts[0]
        workflow_family = parts[1]
        difficulty = parts[2]
        domain = parts[3]
        
        idx = 4
        expected_depts = []
        while idx < len(parts) and parts[idx] in valid_depts:
            expected_depts.append(parts[idx])
            idx += 1
            
        count_idx = -1
        for i in range(idx, len(parts) - 1):
            if parts[i].isdigit() and parts[i+1] in {"Short", "Medium", "Long"}:
                count_idx = i
                break
                
        if count_idx == -1:
            # Fallback search from right
            for i in range(len(parts) - 2, idx - 1, -1):
                if parts[i] in {"Short", "Medium", "Long"} and parts[i-1].isdigit():
                    count_idx = i - 1
                    break
                    
        if count_idx == -1:
            # Absolute fallback
            count_idx = len(parts) - 3
            
        expected_roles = parts[idx:count_idx]
        dept_count = int(parts[count_idx]) if parts[count_idx].isdigit() else len(expected_depts)
        workflow_depth = parts[count_idx+1]
        prompt = ",".join(parts[count_idx+2:])
        
        rows.append({
            "Prompt_ID": prompt_id,
            "Workflow_Family": workflow_family,
            "Difficulty": difficulty,
            "Enterprise_Domain": domain,
            "Expected_Departments": ",".join(expected_depts),
            "Expected_Critical_Roles": ",".join(expected_roles),
            "Estimated_Department_Count": dept_count,
            "Estimated_Workflow_Depth": workflow_depth,
            "Prompt": prompt
        })
        
    return pd.DataFrame(rows)


def run_experiment() -> tuple[str, Path, pd.DataFrame]:
    """Execute enterprise workflows from datasets/enterprise_prompts.csv according to experiment_config.json."""
    import time
    import subprocess
    
    experiment_id, experiment_dir = create_experiment_directory()
    figures_dir = experiment_dir / "figures"
    logs_dir = experiment_dir / "runtime_logs"
    communications_dir = experiment_dir / "communications"
    
    # 1. Read configuration
    config_path = ROOT / "experiment_config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {
            "runs": 100,
            "enterprise_sizes": [32],
            "workflow_families": 10,
            "prompts_per_family": 10,
            "compromise_rotation": true,
            "seed": 42
        }
    
    runs = config.get("runs", 100)
    seed = config.get("seed", 42)
    compromise_rotation = config.get("compromise_rotation", True)
    
    # 2. Read prompt dataset
    prompts_path = ROOT / "datasets" / "enterprise_prompts.csv"
    if not prompts_path.exists():
        raise FileNotFoundError(f"Prompts dataset not found at: {prompts_path}")
    prompts_df = load_enterprise_prompts(prompts_path)
    num_prompts = len(prompts_df)
    
    write_prompts(experiment_dir / "prompts.txt", prompts_df["Prompt"].tolist())

    records = []
    for run_idx in range(runs):
        prompt_number = (run_idx % num_prompts) + 1
        row = prompts_df.iloc[prompt_number - 1]
        prompt = row["Prompt"]
        prompt_id = row["Prompt_ID"]
        workflow_family = row["Workflow_Family"].lower()
        
        scenario = {
            "prompt_id": prompt_id,
            "prompt": prompt,
            "workflow_family": workflow_family,
            "difficulty": row["Difficulty"],
            "category": row["Enterprise_Domain"],
            "finding": f"identified risk in {row['Enterprise_Domain'].lower()}",
            "estimate": f"exposure estimated at ${1.5 + (run_idx % 5) * 0.5:.1f}M",
        }
        
        start_time = time.perf_counter()
        
        graph = build_enterprise_runtime_trust_graph(prompt, seed=seed)
        route = route_prompt_departments(prompt)
        topology = "workflow_" + "_to_".join(route).lower()
        trace_id = TOPOLOGY_TRACE_IDS["enterprise_departmental_workflow"]
        cycles = list(nx.simple_cycles(graph))
        tau_runtime, fvs_nodes = compute_fvs(graph)
        scc_count = nx.number_strongly_connected_components(graph)
        active_nodes = sorted(graph.nodes())
        
        if compromise_rotation:
            compromised = active_nodes[(run_idx // num_prompts) % len(active_nodes)]
        else:
            compromised = active_nodes[0]
            
        run_id = f"run_{run_idx + 1:03d}"
        
        # Linear-time BFS depth compromise propagation
        infected_before, depth_before = propagate_compromise_depth(graph, compromised)
        revoked_graph = graph.copy()
        revoked_graph.remove_nodes_from(fvs_nodes)
        infected_after, depth_after = propagate_compromise_depth(revoked_graph, compromised)
        
        containment_success = len(infected_before) > 0 and len(infected_after) == 0
        steps_before, infection_paths = simulate_communications(
            graph, compromised, scenario
        )
        steps_after, infection_paths_after = simulate_communications(
            revoked_graph, compromised, scenario
        )
        message_count = max(0, len(steps_before) - 1)
        message_count_after = max(0, len(steps_after) - 1)

        # Calculate semantic and comparative metrics:
        internal_messages = sum(
            1 for u, v in graph.edges()
            if graph.nodes[u].get("department") == graph.nodes[v].get("department")
        )
        department_handoffs = sum(
            1 for u, v in graph.edges()
            if graph.nodes[u].get("department") != graph.nodes[v].get("department")
        )
        
        active_agents = [n for n in graph if graph.nodes[n].get("role") == "agent"]
        active_specialists_count = len(active_agents)
        collaboration_depth = active_specialists_count
        review_cycles = len(cycles)
        
        active_depts = set(route)
        average_department_size = graph.number_of_nodes() / len(active_depts) if active_depts else 0.0
        
        max_dept_depth = 0
        for d in active_depts:
            dept_agents = [n for n in graph if graph.nodes[n].get("department") == d and graph.nodes[n].get("role") == "agent"]
            max_dept_depth = max(max_dept_depth, len(dept_agents))
            
        propagation_depth_before = depth_before
        propagation_depth_after = depth_after
        propagation_depth_reduction = depth_before - depth_after
        
        visited_before_nodes = set(infected_before) | ({compromised} if compromised in graph else set())
        visited_after_nodes = set(infected_after) | ({compromised} if compromised in revoked_graph else set())
        
        affected_depts_before = len(set(graph.nodes[n]["department"] for n in visited_before_nodes if n in graph))
        affected_depts_after = len(set(revoked_graph.nodes[n]["department"] for n in visited_after_nodes if n in revoked_graph))
        affected_depts_reduction = affected_depts_before - affected_depts_after
        
        message_reduction = message_count - message_count_after
        
        k_before = len(infected_before)
        k_after = len(infected_after)
        if k_before > 0:
            containment_efficiency = (k_before - k_after) / k_before
        else:
            containment_efficiency = 1.0 if k_after == 0 else 0.0

        execution_time = time.perf_counter() - start_time

        communication_stem = f"trace_{trace_id}_prompt_{prompt_number:02d}"
        communication_json = f"communications/{communication_stem}.json"
        communication_markdown_path = f"communications/{communication_stem}.md"
        
        communication_trace = {
            "experiment": experiment_id,
            "run_id": run_id,
            "prompt": prompt,
            "topology": topology,
            "runtime_tau": tau_runtime,
            "compromise_source": compromised,
            "fvs_nodes": fvs_nodes,
            "k_before": k_before,
            "k_after": k_after,
            "message_count": message_count,
            "message_count_after_revocation": message_count_after,
            "infected_nodes": infected_before,
            "infected_nodes_after_revocation": infected_after,
            "infection_paths": infection_paths,
            "infection_paths_after_revocation": infection_paths_after,
            "steps": steps_before,
            "post_revocation_steps": steps_after,
            "trace_semantics": (
                "Deterministic simulation; each reachable directed edge transmits "
                "at most once, preventing infinite replay through cycles."
            ),
            # Narrative fields:
            "route": route,
            "active_nodes_list": list(active_nodes),
            "depth_before": depth_before,
            "depth_after": depth_after,
            "affected_depts_before": affected_depts_before,
            "affected_depts_after": affected_depts_after,
            "containment_efficiency": containment_efficiency,
        }
        
        save_communication_trace(
            experiment_dir / communication_json,
            experiment_dir / communication_markdown_path,
            communication_trace,
        )
        save_runtime_log(logs_dir / f"{run_id}.jsonl", list(graph.edges()))

        # Calculate fingerprint metrics:
        graph_hash = compute_graph_hash(graph)
        activated_departments = "|".join(sorted(list(set(route))))
        activated_roles = "|".join(sorted([node for node in graph.nodes() if graph.nodes[node].get("role") == "agent"]))

        # Save individual network visualizations only for the first 20 runs
        if run_idx < 20:
            title = f"{run_id}: {' → '.join(route)} | compromised={compromised}"
            save_trace_graph(
                figures_dir / f"{run_id}_trace_graph.png",
                graph,
                compromised,
                infected_before,
                fvs_nodes,
                title,
                run_id=run_id,
                topology=topology,
                tau_runtime=tau_runtime,
                k_before=k_before,
                k_after=k_after,
                containment_efficiency=containment_efficiency,
            )
            save_scc_graph(figures_dir / f"{run_id}_scc.png", graph, title)
            save_before_after_comparison(
                figures_dir / f"{run_id}_before_after.png",
                figures_dir / f"{run_id}_before_after.pdf",
                graph,
                revoked_graph,
                compromised,
                infected_before,
                infected_after,
                fvs_nodes,
                title,
                run_id=run_id,
                topology=topology,
                tau_runtime=tau_runtime,
                k_before=k_before,
                k_after=k_after,
                containment_efficiency=containment_efficiency,
            )
            
            # Generate standalone executive summary table figure
            components = list(nx.strongly_connected_components(graph))
            save_run_summary_table(
                path_png=figures_dir / f"{run_id}_summary.png",
                path_pdf=figures_dir / f"{run_id}_summary.pdf",
                graph=graph,
                compromised_node=compromised,
                fvs_nodes=fvs_nodes,
                run_id=run_id,
                topology=topology,
                tau_runtime=tau_runtime,
                scc_count=scc_count,
                components=components,
                k_before=k_before,
                k_after=k_after,
                containment_efficiency=containment_efficiency,
                depth_before=depth_before,
                depth_after=depth_after,
                graph_hash=graph_hash,
            )

        records.append(
            {
                "Run ID": run_id,
                "Prompt ID": prompt_id,
                "Workflow Family": row["Workflow_Family"],
                "Enterprise Size": len(NODES),
                "Runtime τ": tau_runtime,
                "Runtime SCC": scc_count,
                "FVS Size": len(fvs_nodes),
                "Graph Hash": graph_hash,
                "Compromised Node": compromised,
                "K Before": k_before,
                "K After": k_after,
                "Containment Efficiency": containment_efficiency,
                "Propagation Depth Before": propagation_depth_before,
                "Propagation Depth After": propagation_depth_after,
                "Propagation Depth Reduction": propagation_depth_reduction,
                "Affected Departments Before": affected_depts_before,
                "Affected Departments After": affected_depts_after,
                "Affected Departments Reduction": affected_depts_reduction,
                "Messages Before": message_count,
                "Messages After": message_count_after,
                "Execution Time": execution_time,
                "Seed": seed,
                # Compatibility columns:
                "Experiment ID": experiment_id,
                "Prompt": prompt,
                "Topology": topology,
                "Nodes": graph.number_of_nodes(),
                "Edges": graph.number_of_edges(),
                "Cycle Count": len(cycles),
                "SCC Count": scc_count,
                "Runtime τ_FVS": tau_runtime,
                "FVS Nodes": "|".join(fvs_nodes),
                "Containment Success": containment_success,
                "Message Count": message_count,
                "Messages After Revocation": message_count_after,
                "Infection Path Count": len(infection_paths),
                "workflow_family": workflow_family,
                "activated_departments": activated_departments,
                "activated_roles": activated_roles,
                "active_node_count": graph.number_of_nodes(),
                "active_edge_count": graph.number_of_edges(),
                "containment_efficiency": containment_efficiency,
                "propagation_depth_before": propagation_depth_before,
                "propagation_depth_after": propagation_depth_after,
                "propagation_depth_reduction": propagation_depth_reduction,
                "affected_departments_before": affected_depts_before,
                "affected_departments_after": affected_depts_after,
                "affected_departments_reduction": affected_depts_reduction,
                "message_reduction": message_reduction,
            }
        )

    results = pd.DataFrame.from_records(records)
    results.to_csv(experiment_dir / "results.csv", index=False)
    
    # Generate summaries
    summary_cols = [
        "Nodes", "Edges", "Cycle Count", "SCC Count", "Runtime τ",
        "K Before", "K After", "Messages Before", "Messages After",
        "Containment Efficiency", "Propagation Depth Before", "Propagation Depth After",
        "Propagation Depth Reduction", "Affected Departments Before", "Affected Departments After",
        "Affected Departments Reduction", "Execution Time"
    ]
    summary_cols = [c for c in summary_cols if c in results.columns]
    stats_list = []
    for col in summary_cols:
        stats_list.append({
            "Metric": col,
            "Mean": results[col].mean(),
            "Std": results[col].std(),
            "Min": results[col].min(),
            "Max": results[col].max(),
            "Median": results[col].median()
        })
    stats_df = pd.DataFrame(stats_list)
    stats_df.to_csv(experiment_dir / "summary_statistics.csv", index=False)

    tau_counts = results["Runtime τ"].value_counts().sort_index()
    tau_total = len(results)
    tau_dist_list = []
    for tau, count in tau_counts.items():
        percentage = (count / tau_total) * 100
        tau_dist_list.append({
            "τ": tau,
            "Count": count,
            "Percentage": f"{percentage:.1f}%"
        })
    tau_dist_df = pd.DataFrame(tau_dist_list)
    tau_dist_df.to_csv(experiment_dir / "runtime_tau_distribution.csv", index=False)

    wf_df = results.groupby("Workflow Family").agg(
        Mean_tau=("Runtime τ", "mean"),
        Mean_K_Before=("K Before", "mean"),
        Mean_K_After=("K After", "mean"),
        Mean_Containment_Efficiency=("Containment Efficiency", "mean")
    ).reset_index()
    wf_df.rename(columns={
        "Workflow Family": "Workflow",
        "Mean_tau": "Mean τ",
        "Mean_K_Before": "Mean K Before",
        "Mean_K_After": "Mean K After",
        "Mean_Containment_Efficiency": "Mean Containment Efficiency"
    }, inplace=True)
    wf_df.to_csv(experiment_dir / "summary_by_workflow.csv", index=False)

    comp_df = results.groupby("Compromised Node").agg(
        Avg_K_Before=("K Before", "mean"),
        Avg_K_After=("K After", "mean"),
        Avg_Efficiency=("Containment Efficiency", "mean")
    ).reset_index()
    comp_df.rename(columns={
        "Compromised Node": "Compromised Role",
        "Avg_K_Before": "Avg K Before",
        "Avg_K_After": "Avg K After",
        "Avg_Efficiency": "Avg Efficiency"
    }, inplace=True)
    comp_df.to_csv(experiment_dir / "summary_by_compromise.csv", index=False)

    size_df = results.groupby("Enterprise Size").agg(
        Mean_tau=("Runtime τ", "mean"),
        Mean_K_Before=("K Before", "mean"),
        Mean_K_After=("K After", "mean"),
        Mean_Containment_Efficiency=("Containment Efficiency", "mean")
    ).reset_index()
    size_df.rename(columns={
        "Mean_tau": "Mean τ",
        "Mean_K_Before": "Mean K Before",
        "Mean_K_After": "Mean K After",
        "Mean_Containment_Efficiency": "Mean Containment Efficiency"
    }, inplace=True)
    size_df.to_csv(experiment_dir / "summary_by_size.csv", index=False)

    by_topology, by_tau = build_grouped_summaries(results)
    by_topology.to_csv(experiment_dir / "summary_by_topology.csv", index=False)
    by_tau.to_csv(experiment_dir / "summary_by_tau.csv", index=False)
    
    save_aggregate_charts(results, figures_dir)
    write_validation_report(
        results,
        by_topology,
        by_tau,
        experiment_dir / "validation_report.txt",
    )
    write_metadata(experiment_id, experiment_dir / "metadata.json", len(results), seed=seed)
    return experiment_id, experiment_dir, results


def print_summary(experiment_id: str, experiment_dir: Path, results: pd.DataFrame) -> None:
    """Print the experiment location and aggregate observations."""
    observed = set(int(value) for value in results["Runtime τ"].unique())
    successes = int(results["Containment Success"].sum())
    unique_hashes = results["Graph Hash"].nunique()
    print(f"Experiment: {experiment_id}")
    print(f"Output: {experiment_dir}")
    print(f"Runs: {len(results)}")
    print(f"Unique runtime graphs: {unique_hashes}/{len(results)}")
    print(f"Observed runtime τ values: {observed}")
    print(f"Maximum runtime τ: {int(results['Runtime τ'].max())}")
    print(f"Minimum runtime τ: {int(results['Runtime τ'].min())}")
    print(f"Containment success rate: {successes}/{len(results)}")
    print(f"Average containment efficiency: {results['Containment Efficiency'].mean() * 100:.1f}%")
    print(f"Average K Before: {results['K Before'].mean():.2f}")
    print(f"Average K After: {results['K After'].mean():.2f}")
    print(f"Average message count: {results['Messages Before'].mean():.2f}")
    print(f"Total agent-to-agent messages: {int(results['Messages Before'].sum())}")
    print(f"Average propagation depth before: {results['Propagation Depth Before'].mean():.2f}")
    print(f"Average propagation depth after: {results['Propagation Depth After'].mean():.2f}")
    print(f"Average propagation depth reduction: {results['Propagation Depth Reduction'].mean():.2f}")
    print(f"Average affected departments before: {results['Affected Departments Before'].mean():.2f}")
    print(f"Average affected departments after: {results['Affected Departments After'].mean():.2f}")
    print(f"Average affected departments reduction: {results['Affected Departments Reduction'].mean():.2f}")
    print(f"Average message reduction: {results['message_reduction'].mean():.2f}")
    
    print("\nWorkflow Family Diversity Summary:")
    print("----------------------------------")
    family_groups = results.groupby("workflow_family")
    for name, group in family_groups:
        family_taus = sorted([int(x) for x in group["Runtime τ"].unique()])
        family_depts = sorted(group["activated_departments"].unique())
        print(f"Family: {name}")
        print(f"  Observed τ values: {family_taus}")
        print(f"  Unique department routes activated: {len(family_depts)}")


if __name__ == "__main__":
    current_id, current_dir, experiment_results = run_experiment()
    print_summary(current_id, current_dir, experiment_results)
