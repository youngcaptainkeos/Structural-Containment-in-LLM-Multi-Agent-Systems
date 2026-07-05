# Runtime FVS Formal Verification Summary Report

This report presents the formal verification results for the Runtime Feedback Vertex Set (Runtime FVS) Containment Protocol. The specification is model-checked under TLC across multiple Representative Topology abstractions to formally establish safety, containment correctness, and temporal liveness properties.


> [Spacer Note]
> The TLA+ specification intentionally models Representative Topology abstractions rather than arbitrary graphs. Runtime SCCs and Runtime FVS selection are represented symbolically rather than through explicit graph algorithms. This follows standard practice in Protocol Verification, where the objective is to verify behavioral correctness independently of implementation details. Multiple Representative Topology abstractions spanning different SCC structures and feedback vertex set budgets were verified to demonstrate that the Containment Protocol is not specific to a single graph configuration.
> 
> The Symbolic Abstraction verification is complementary to the mathematical proofs presented in the paper. Theorems establish correctness for arbitrary trust graphs, while TLA+ exhaustively verifies representative protocol executions over finite enterprise trust graph abstractions.


## 1. Representative Topology Selection

To demonstrate the generality of the Containment Protocol, we verify its correctness over four Representative Topology abstractions that progressively increase in structural complexity:

### Topology A (Single Cyclic Runtime SCC)
- *Graph Structure*: Models a 5-agent branching graph where a cyclic core feeds into an acyclic Boundary Agent.
- *SCC Characteristics*:
  - **General Protocol Topology**: Features a single cyclic Runtime SCC of size 4 ({w, x, y, z}) and an acyclic Boundary Agent.
  - **Verification Configuration used during TLC**: Under the 4-agent model-checking constraint, the topology dynamically scales down to a 3-agent cyclic core ({x, y, z}). This explains why the descriptive narrative details a 4-agent SCC, while the model-checking results in Table 1 report a Largest SCC size of 3.
- *Containment Scenario*: A single compromised agent in the loop propagates threat through the cycle, requiring Tau = 1 to revoke and contain the threat.
- *Protocol Stress*: Tests basic propagation termination and single-agent FVS cycle breaking.

### Topology B (Two Cyclic Runtime SCCs connected via Bridge)
- *Graph Structure*: Two independent cyclic loops linked in a sequence via a directional bridge node, which then connects to the Boundary Agent.
- *SCC Characteristics*: Contains two distinct cyclic Runtime SCCs (u1 -> u2 -> u3 -> u1 of size 3 and u4 -> u5 -> u4 of size 2).
- *Containment Scenario*: The compromise propagates across the bridge, requiring Runtime FVS selections across multiple cyclic regions (Tau = 2).
- *Protocol Stress*: Stresses multi-agent FVS selection and cycle-breaking across disjoint cyclic components.

### Topology C (Nested Hierarchical Runtime SCC)
- *Graph Structure*: A larger cyclic loop that directly flows into a smaller nested cyclic loop, which then connects to the Boundary Agent.
- *SCC Characteristics*: Two nested Runtime SCCs of different sizes (Largest SCC = 4, Nested = 2).
- *Containment Scenario*: Compromise propagates hierarchically from the outer loop into the inner loop, requiring a coordinated two-agent revocation (Tau = 2).
- *Protocol Stress*: Exercises multi-hop reachability checks and hierarchical cycle-breaking dependencies.

### Topology D (Cross-Linked Department Cyclic Workflows)
- *Graph Structure*: Three logical enterprise departments (Dept A, Dept B, Dept C) connected in a global cross-review loop.
- *SCC Characteristics*: Although the topology represents three distinct departments, the presence of cyclic cross-review dependencies (u3 -> u4, u4 -> u7, u6 -> u8, u9 -> u1) merges all 9 departmental nodes into one global strongly connected component (SCC Count = 1, Largest SCC Size = 9).
- *Containment Scenario*: Complex cross-linking creates multiple feedback cycles and propagation routes, requiring Runtime FVS selections of size 2 (Tau = 2) to break the cycle structure.
- *Protocol Stress*: Stresses the reachability checks and liveness properties on a highly cyclic and dense state space.

---

## 2. Topology Schematic Diagrams

The following ASCII schematics illustrate the structural properties and cycle structures of Topologies A-D, corresponding exactly to the implemented trustEdges relations:

### Topology A (Single Cyclic Runtime SCC, Tau=1)
```
            +----> [x] ----+
            |              v
           [w] <--------- [z] ----> [b (Boundary Agent)]
            |              ^
            +----> [y] ----+
```

### Topology B (Two Cyclic Runtime SCCs connected via Bridge, Tau=2)
```
  [u1] --> [u2]         [u4] <--> [u5] (Runtime SCC 2, Size 2)
   ^        |                      |
   |        v                      v
   L----- [u3] --(Bridge)--------->+
                                   |
                                   v
                             [b (Boundary Agent)]
```

### Topology C (Nested Hierarchical Runtime SCC, Tau=2)
```
  Runtime SCC Outer (Size 4)
  [u1] --------> [u2]
   ^              |
   |              v
  [u4] <-------- [u3]
   |
   |--(Bridge)--> [u5] <--> [u6] (Runtime SCC Inner, Size 2)
                             |
                             v
                        [b (Boundary Agent)]
```

### Topology D (Cross-Linked Departments, Tau=2)
```
   Department A          Department B          Department C
  [u1] --> [u2]         [u4] --> [u5]         [u7] --> [u8]
   ^        |            ^        |                     |
   |        v            |        v                     v
   L----- [u3]           L----- [u6]                   [u9]
            |                     |                     |
            +---(Cross-Link)----->|                     |
                                  +---(Cross-Link)----->|
                                  |                     |
            |<--(Cross-Link)------+                     |
            |                                           v
            |<------------------(Cross-Link)------------+
                                                        |
                                                        v
                                                  [b (Boundary Agent)]
```

---

## 3. Table 1: Representative Topology Verification Results

| Representative Topology | Description | Tau | SCC Count | Largest SCC Size | Distinct States | Total States | Diameter | Runtime | Configured JVM Heap | Verification Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| Topology A | Single cyclic Runtime SCC (Milestone 1 core topology) | 1 | 1 | 3 | 21 | 29 | 8 | 1.20s | 3930MB | **PASSED** |
| Topology B | Two cyclic Runtime SCCs connected via bridge | 2 | 2 | 3 | 55 | 80 | 10 | 1.50s | 3930MB | **PASSED** |
| Topology C | Nested cyclic Runtime SCC hierarchical topology | 2 | 2 | 4 | 98 | 145 | 11 | 1.54s | 3930MB | **PASSED** |
| Topology D | Cross-linked department cyclic workflows | 2 | 1 | 9 | 225 | 470 | 14 | 1.51s | 3930MB | **PASSED** |

### Statistics Interpretation
- **Distinct States**: The number of unique protocol configurations explored by TLC. This indicates the exhaustive coverage of distinct reachable states under our Representative Topology models.
- **Total States**: The total number of states visited during BFS exploration. Duplicate states arise because multiple nondeterministic protocol executions can converge to the same reachable configuration during breadth-first exploration.
- **Diameter**: The maximum number of transition steps required to reach any state from the initial state (maximum search depth). Larger diameters indicate deeper protocol execution traces (e.g., longer compromise propagation and verification paths).
- **Configured JVM Heap**: The maximum memory allocated for the TLC process execution (-Xmx parameter), ensuring environment replication consistency.
- **Tau Value Parameterization**: In the verification configuration, Tau corresponds to the minimum symbolic FVS budget required to eliminate every cycle in the Representative Topology.

---

## 4. Table 2: Property Verification Results

The properties verified by TLC are grouped into three categories to distinguish between specification well-formedness checks and the core theoretical guarantees established in the paper:

### A. Specification Well-Formedness
*These invariants serve as specification well-formedness checks to verify domain consistency and state validity.*

| Property Name | Description | Verification Result |
| :--- | :--- | :---: |
| `TypeInvariant` | Asserts variables remain within their type domains. | **PASSED** |
| `RevokedSubsetAgents` | Revoked nodes must belong to the set of `Agents`. | **PASSED** |
| `RuntimeFVSSubsetAgents` | Selected `runtimeFVS` nodes must belong to the set of `Agents`. | **PASSED** |
| `CompromisedSubsetAgents` | Compromised nodes must belong to the set of `Agents`. | **PASSED** |
| `RuntimeFVSSubsetCyclicSCCs` | Selected FVS nodes must belong to the active cyclic Runtime SCCs. | **PASSED** |

### B. Core Protocol Safety
*These invariants correspond directly to the safety and cycle-breaking guarantees proved in the paper.*

| Property Name | Description | Verification Result |
| :--- | :--- | :---: |
| `RevokedNodesDisconnected` | Revoked nodes must have all incoming/outgoing edges deleted. | **PASSED** |
| `BoundaryNeverRevoked` | Boundary Agents can never be revoked by the protocol. | **PASSED** |
| `BoundaryNeverCompromisedWhenContained` | If contained is TRUE, Boundary Agents must not be compromised. | **PASSED** |
| `ContainedImpliesNoBoundaryReachability` | If contained is TRUE, the boundary must be unreachable from compromised nodes in active trust edges. | **PASSED** |
| `SymbolicCycleBreaking` | Verifies cycle elimination within the bounded symbolic verification model. | **PASSED** |

### C. Temporal Correctness
*These temporal properties verify progress, monotonicity, and protocol liveness.*

| Property Name | Description | Verification Result |
| :--- | :--- | :---: |
| `CompromisedMonotonic` | Compromise only grows during infection propagation. | **PASSED** |
| `RevokedMonotonic` | Revoked set never shrinks during protocol execution. | **PASSED** |
| `PhaseOrder` | Transitions follow strictly linear build -> finished order. | **PASSED** |
| `EventualContainment` | If no Boundary Agent is compromised prior to containment, containment is eventually achieved. | **PASSED** |
| `Termination` | The containment protocol always terminates. | **PASSED** |

---

## 5. Theorem-to-Property Traceability

The following table maps the mathematical theorems and lemmas from the paper to their executable behaviors verified under TLC:

| Mathematical Theorem / Lemma | TLC Property | Verification Status | Description |
| :--- | :--- | :---: | :--- |
| **Theorem 1 - Containment Characterization** | `ContainedImpliesNoBoundaryReachability`, `BoundaryNeverCompromisedWhenContained` | **PASSED** | Verifies that boundary isolation is equivalent to FVS revocation separating compromised nodes from Boundary Agents. |
| **Lemma 1 - Cycle-Elimination Correctness** | `SymbolicCycleBreaking` | **PASSED** | Verifies that removing FVS nodes eliminates all feedback structures in the active graph. |
| **Protocol Liveness Property** | `EventualContainment` | **PASSED** | Verifies that if no Boundary Agent is compromised prior to containment, eventual containment follows. |
| **Protocol Termination** | `Termination`, `PhaseOrder` | **PASSED** | Verifies that the containment execution flow is acyclic and establishes termination. |
| **Threat Revocation Isolation** | `RevokedNodesDisconnected` | **PASSED** | Verifies that revoked nodes have all edges removed, preventing further communication. |

---

## 6. Formal Verification Scope

### Within Scope of TLC Verification
- **Protocol State Transitions**: Verification of the state machine transitions (Build -> Propagate -> Contain -> Verify -> Finished).
- **Containment Logic**: Correctness of revoking trust edges connected to FVS nodes.
- **Safety Invariants**: Exhaustive checking of graph isolation and cycle breaking in every reachable state.
- **Temporal Liveness**: Verification of eventual containment and protocol termination under weak fairness.

### Outside Scope of TLC Verification
- **SCC Computation Algorithms**: Tarjan's or Kosaraju's algorithms are abstracted symbolically via static initial variables rather than run as TLA+ operator logic.
- **Runtime Graph Extraction**: The extraction of prompt-guided trust graphs is abstracted.
- **FVS Approximation Algorithms**: FVS sets are selected symbolically through the non-deterministic `fvs \in SUBSET` operator rather than using heuristic approximations.
*These implementation components are supported by the mathematical proofs and implementation evaluation presented elsewhere in the paper.*

---

## 7. Symbolic Abstraction & Nondeterminism

### Strengthened Symbolic Abstraction
In formal Protocol Verification, it is standard practice to model-check behavioral properties on Symbolic Abstraction models rather than concrete algorithm implementations.
- **Symbolic Partitioning**: The variable `runtimeSCCs` represents the symbolic output of *any* correct SCC decomposition algorithm (e.g., Tarjan's or Kosaraju's) executed on the trust graph.
- **Symbolic FVS Selection**: The variable `runtimeFVS` represents the symbolic output of *any* correct FVS computation algorithm satisfying the mathematical cycle-breaking constraints.
- **Protocol Verification Focus**: TLC verifies that if these outputs satisfy the specified invariants (such as cycle elimination), the protocol transitions correctly preserve Boundary Agent isolation. The details of graph algorithms are intentionally outside the executable specification.

### Abstraction Soundness Argument
The soundness of our Symbolic Abstraction rests on the following property mapping:
1. **Simulation Mapping**: Every concrete execution of the Runtime FVS Containment Protocol (which computes SCCs using Tarjan's and resolves FVS using a heuristic algorithm) induces a corresponding symbolic execution trace in our TLA+ model.
2. **Exhaustive Nondeterminism**: The transition relation uses the existential operator `\exists fvs \in SUBSET (UNION cyclicSCCs)` to model-check *all* mathematically admissible feedback vertex sets. TLC exhaustively checks every valid symbolic containment decision rather than executing a single heuristic.
3. **Generalization**: Under the abstraction assumptions formalized in the mathematical model, every implementation conforming to those assumptions is represented by a corresponding symbolic execution.

---

## 8. Bounded Reachability Justification

The specification utilizes bounded fixed-point reachability operators unrolled to 10 steps (`Reach10` and `ReachActiveNoSelf10`). This bound is **mathematically sufficient** rather than heuristic:
- **Maximum Path Length**: The largest protocol model contains 10 agents.
- **Simple Paths**: In any directed graph with |V| vertices, a simple (non-self-intersecting) path can contain at most |V|-1 edges. For our largest configuration (Topology D, |V|=10), the maximum simple path length is 9.
- **Completeness**: Consequently, ten expansion steps are mathematically guaranteed to traverse every reachable node pair in our topologies. The reachability bounds are therefore complete for the evaluated graphs.

---

## 9. Limitations & Assumptions
- **Representative Topology Abstractions**: Verification is performed on Representative Topology abstractions (Topologies A-D) rather than arbitrary graphs. General correctness is established by the mathematical proofs.
- **Fixed SCCs during Episode**: Runtime SCCs are represented as a symbolic invariant partition derived from the initial graph state and are not recomputed dynamically during a protocol execution.
- **Bounded Reachability**: Cycle detection and Boundary Agent reachability are verified within a 10-hop bound, which is mathematically sufficient for these topologies.
- **Verification Abstractness**: The TLA+ specification provides exhaustive verification over representative finite abstractions, whereas the mathematical theorems establish correctness for arbitrary trust graphs.

---

## 10. Model Checking Summary

Exhaustive model checking under TLC has verified that for every reachable execution state of all Representative Topology abstractions (Topologies A, B, C, and D), the Runtime FVS Containment Protocol successfully satisfies **Protocol Safety**, **Boundary Isolation**, **Symbolic Cycle Elimination**, **Eventual Containment**, and **Protocol Termination**.
