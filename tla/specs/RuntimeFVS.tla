----------------------------- MODULE RuntimeFVS -----------------------------

EXTENDS Naturals, FiniteSets, Sequences

CONSTANTS Agents, BoundaryAgents, TopologyType, Tau

VARIABLES
    trustEdges,
    compromised,
    revoked,
    runtimeFVS,
    contained,
    phase,
    runtimeSCCs,
    cyclicSCCs,
    largestSCC

vars ==
    << trustEdges,
       compromised,
       revoked,
       runtimeFVS,
       contained,
       phase,
       runtimeSCCs,
       cyclicSCCs,
       largestSCC >>

\* Symbolic constants for the protocol stages
Build == "BUILD"
Propagate == "PROPAGATE"
Contain == "CONTAIN"
Verify == "VERIFY"
Finished == "FINISHED"

\* Helper sets and node selectors to define topology dynamically
NonBoundary == Agents \ BoundaryAgents

\* Selecting nodes from the constant sets to construct our topology safely
w == IF Cardinality(NonBoundary) >= 4
     THEN CHOOSE a \in NonBoundary : TRUE
     ELSE CHOOSE a \in NonBoundary : TRUE

x == IF Cardinality(NonBoundary) >= 4
     THEN CHOOSE a \in NonBoundary \ {w} : TRUE
     ELSE CHOOSE a \in NonBoundary : TRUE

y == IF Cardinality(NonBoundary) >= 4
     THEN CHOOSE a \in NonBoundary \ {w, x} : TRUE
     ELSE CHOOSE a \in NonBoundary \ {x} : TRUE

z == IF Cardinality(NonBoundary) >= 4
     THEN CHOOSE a \in NonBoundary \ {w, x, y} : TRUE
     ELSE CHOOSE a \in NonBoundary \ {x, y} : TRUE

b == CHOOSE a \in BoundaryAgents : TRUE

\* Graph helper operators
Outgoing(a) == { v \in Agents : <<a, v>> \in trustEdges }
Incoming(a) == { u \in Agents : <<u, a>> \in trustEdges }
Neighbors(a) == Outgoing(a) \cup Incoming(a)

\* OutgoingNeighbors(S) returns all nodes reachable by exactly one outgoing edge from any node in S
OutgoingNeighbors(S) == { v \in Agents : \exists u \in S : <<u, v>> \in trustEdges }

\* PropagationCandidates returns nodes that are one-hop outgoing neighbors of compromised nodes,
\* but are not yet compromised or revoked
PropagationCandidates == OutgoingNeighbors(compromised) \ (compromised \cup revoked)

\* CanPropagate returns TRUE if there are any propagation candidates left
CanPropagate == PropagationCandidates /= {}

\* Helper operators to compute reachability excluding FVS nodes for cycle detection (unrolled to 10 steps using LET-caching)
ReachStep(S, fvs) == { v \in Agents \ fvs : \exists u \in S : <<u, v>> \in trustEdges }
ReachNoSelf1(a, fvs) == ReachStep({a}, fvs)
ReachNoSelf2(a, fvs) == LET r == ReachNoSelf1(a, fvs) IN r \cup ReachStep(r, fvs)
ReachNoSelf3(a, fvs) == LET r == ReachNoSelf2(a, fvs) IN r \cup ReachStep(r, fvs)
ReachNoSelf4(a, fvs) == LET r == ReachNoSelf3(a, fvs) IN r \cup ReachStep(r, fvs)
ReachNoSelf5(a, fvs) == LET r == ReachNoSelf4(a, fvs) IN r \cup ReachStep(r, fvs)
ReachNoSelf6(a, fvs) == LET r == ReachNoSelf5(a, fvs) IN r \cup ReachStep(r, fvs)
ReachNoSelf7(a, fvs) == LET r == ReachNoSelf6(a, fvs) IN r \cup ReachStep(r, fvs)
ReachNoSelf8(a, fvs) == LET r == ReachNoSelf7(a, fvs) IN r \cup ReachStep(r, fvs)
ReachNoSelf9(a, fvs) == LET r == ReachNoSelf8(a, fvs) IN r \cup ReachStep(r, fvs)
ReachNoSelf10(a, fvs) == LET r == ReachNoSelf9(a, fvs) IN r \cup ReachStep(r, fvs)

IsFVS(fvs) ==
    \forall a \in (UNION cyclicSCCs) \ fvs :
        a \notin ReachNoSelf10(a, fvs)

\* Bounded fixed-point reachability operators (unrolled to 10 steps using LET-caching)
Reach1(S) == S \cup { v \in Agents : \exists u \in S : <<u, v>> \in trustEdges }
Reach2(S) == LET r == Reach1(S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in trustEdges }
Reach3(S) == LET r == Reach2(S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in trustEdges }
Reach4(S) == LET r == Reach3(S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in trustEdges }
Reach5(S) == LET r == Reach4(S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in trustEdges }
Reach6(S) == LET r == Reach5(S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in trustEdges }
Reach7(S) == LET r == Reach6(S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in trustEdges }
Reach8(S) == LET r == Reach7(S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in trustEdges }
Reach9(S) == LET r == Reach8(S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in trustEdges }
Reach10(S) == LET r == Reach9(S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in trustEdges }

BoundaryReachable(S) == (Reach10(S) \cap BoundaryAgents) /= {}

\* Bounded reachability operators in active trustEdges (without FVS exclusion) for cycle-breaking invariant (unrolled to 10 steps using LET-caching)
ReachActiveStep(S) == { v \in Agents : \exists u \in S : <<u, v>> \in trustEdges }
ReachActiveNoSelf1(a) == ReachActiveStep({a})
ReachActiveNoSelf2(a) == LET r == ReachActiveNoSelf1(a) IN r \cup ReachActiveStep(r)
ReachActiveNoSelf3(a) == LET r == ReachActiveNoSelf2(a) IN r \cup ReachActiveStep(r)
ReachActiveNoSelf4(a) == LET r == ReachActiveNoSelf3(a) IN r \cup ReachActiveStep(r)
ReachActiveNoSelf5(a) == LET r == ReachActiveNoSelf4(a) IN r \cup ReachActiveStep(r)
ReachActiveNoSelf6(a) == LET r == ReachActiveNoSelf5(a) IN r \cup ReachActiveStep(r)
ReachActiveNoSelf7(a) == LET r == ReachActiveNoSelf6(a) IN r \cup ReachActiveStep(r)
ReachActiveNoSelf8(a) == LET r == ReachActiveNoSelf7(a) IN r \cup ReachActiveStep(r)
ReachActiveNoSelf9(a) == LET r == ReachActiveNoSelf8(a) IN r \cup ReachActiveStep(r)
ReachActiveNoSelf10(a) == LET r == ReachActiveNoSelf9(a) IN r \cup ReachActiveStep(r)

\* Initial State
Init ==
    /\ revoked = {}
    /\ runtimeFVS = {}
    /\ contained = FALSE
    /\ phase = Build
    /\ \exists initialNode \in NonBoundary :
         /\ initialNode \notin revoked
         /\ compromised = {initialNode}
    /\ IF TopologyType = "A" THEN
         IF Cardinality(NonBoundary) >= 4 THEN
             LET w_node == CHOOSE a \in NonBoundary : TRUE
                 x_node == CHOOSE a \in NonBoundary \ {w_node} : TRUE
                 y_node == CHOOSE a \in NonBoundary \ {w_node, x_node} : TRUE
                 z_node == CHOOSE a \in NonBoundary \ {w_node, x_node, y_node} : TRUE
             IN
                 /\ trustEdges = {
                      <<w_node, x_node>>,
                      <<w_node, y_node>>,
                      <<x_node, z_node>>,
                      <<y_node, z_node>>,
                      <<z_node, w_node>>,
                      <<z_node, b>>
                    }
                 /\ runtimeSCCs = {{w_node, x_node, y_node, z_node}, {b}}
                 /\ cyclicSCCs = {{w_node, x_node, y_node, z_node}}
                 /\ largestSCC = {w_node, x_node, y_node, z_node}
         ELSE
             LET x_node == CHOOSE a \in NonBoundary : TRUE
                 y_node == CHOOSE a \in NonBoundary \ {x_node} : TRUE
                 z_node == CHOOSE a \in NonBoundary \ {x_node, y_node} : TRUE
             IN
                 /\ trustEdges = {
                      <<x_node, y_node>>,
                      <<y_node, z_node>>,
                      <<z_node, x_node>>,
                      <<z_node, b>>
                    }
                 /\ runtimeSCCs = {{x_node, y_node, z_node}, {b}}
                 /\ cyclicSCCs = {{x_node, y_node, z_node}}
                 /\ largestSCC = {x_node, y_node, z_node}
       ELSE IF TopologyType = "B" THEN
         LET u1 == CHOOSE a \in NonBoundary : TRUE
             u2 == CHOOSE a \in NonBoundary \ {u1} : TRUE
             u3 == CHOOSE a \in NonBoundary \ {u1, u2} : TRUE
             u4 == CHOOSE a \in NonBoundary \ {u1, u2, u3} : TRUE
             u5 == CHOOSE a \in NonBoundary \ {u1, u2, u3, u4} : TRUE
         IN
             /\ trustEdges = {
                  <<u1, u2>>, <<u2, u3>>, <<u3, u1>>,
                  <<u3, u4>>,
                  <<u4, u5>>, <<u5, u4>>,
                  <<u5, b>>
                }
             /\ runtimeSCCs = {{u1, u2, u3}, {u4, u5}, {b}}
             /\ cyclicSCCs = {{u1, u2, u3}, {u4, u5}}
             /\ largestSCC = {u1, u2, u3}
       ELSE IF TopologyType = "C" THEN
         LET u1 == CHOOSE a \in NonBoundary : TRUE
             u2 == CHOOSE a \in NonBoundary \ {u1} : TRUE
             u3 == CHOOSE a \in NonBoundary \ {u1, u2} : TRUE
             u4 == CHOOSE a \in NonBoundary \ {u1, u2, u3} : TRUE
             u5 == CHOOSE a \in NonBoundary \ {u1, u2, u3, u4} : TRUE
             u6 == CHOOSE a \in NonBoundary \ {u1, u2, u3, u4, u5} : TRUE
         IN
             /\ trustEdges = {
                  <<u1, u2>>, <<u2, u3>>, <<u3, u4>>, <<u4, u1>>,
                  <<u4, u5>>,
                  <<u5, u6>>, <<u6, u5>>,
                  <<u6, b>>
                }
             /\ runtimeSCCs = {{u1, u2, u3, u4}, {u5, u6}, {b}}
             /\ cyclicSCCs = {{u1, u2, u3, u4}, {u5, u6}}
             /\ largestSCC = {u1, u2, u3, u4}
       ELSE \* Topology D
         LET u1 == CHOOSE a \in NonBoundary : TRUE
             u2 == CHOOSE a \in NonBoundary \ {u1} : TRUE
             u3 == CHOOSE a \in NonBoundary \ {u1, u2} : TRUE
             u4 == CHOOSE a \in NonBoundary \ {u1, u2, u3} : TRUE
             u5 == CHOOSE a \in NonBoundary \ {u1, u2, u3, u4} : TRUE
             u6 == CHOOSE a \in NonBoundary \ {u1, u2, u3, u4, u5} : TRUE
             u7 == CHOOSE a \in NonBoundary \ {u1, u2, u3, u4, u5, u6} : TRUE
             u8 == CHOOSE a \in NonBoundary \ {u1, u2, u3, u4, u5, u6, u7} : TRUE
             u9 == CHOOSE a \in NonBoundary \ {u1, u2, u3, u4, u5, u6, u7, u8} : TRUE
         IN
             /\ trustEdges = {
                  <<u1, u2>>, <<u2, u3>>, <<u3, u1>>,
                  <<u4, u5>>, <<u5, u6>>, <<u6, u4>>,
                  <<u7, u8>>, <<u8, u9>>,
                  <<u3, u4>>, <<u4, u7>>, <<u6, u8>>, <<u9, u1>>,
                  <<u9, b>>
                }
             /\ runtimeSCCs = {{u1, u2, u3, u4, u5, u6, u7, u8, u9}, {b}}
             /\ cyclicSCCs = {{u1, u2, u3, u4, u5, u6, u7, u8, u9}}
             /\ largestSCC = {u1, u2, u3, u4, u5, u6, u7, u8, u9}

\* Transition Relation
Next ==
    \/ /\ phase = Build
       /\ phase' = Propagate
       /\ UNCHANGED
            << trustEdges,
               compromised,
               revoked,
               runtimeFVS,
               contained,
               runtimeSCCs,
               cyclicSCCs,
               largestSCC >>

    \/ /\ phase = Propagate
       /\ CanPropagate
       /\ \exists n \in PropagationCandidates :
            /\ compromised' = compromised \cup {n}
            /\ phase' = Propagate
            /\ UNCHANGED
                 << trustEdges,
                    revoked,
                    runtimeFVS,
                    contained,
                    runtimeSCCs,
                    cyclicSCCs,
                    largestSCC >>

    \/ /\ phase = Propagate
       /\ ~CanPropagate
       /\ phase' = Contain
       /\ UNCHANGED
            << trustEdges,
               compromised,
               revoked,
               runtimeFVS,
               contained,
               runtimeSCCs,
               cyclicSCCs,
               largestSCC >>

    \/ /\ phase = Contain
       /\ \exists fvs \in SUBSET (UNION cyclicSCCs) :
            /\ fvs \cap BoundaryAgents = {}
            /\ cyclicSCCs /= {} => fvs /= {}
            /\ IsFVS(fvs)
            /\ Cardinality(fvs) <= Tau
            /\ runtimeFVS' = fvs
            /\ revoked' = revoked \cup fvs
            /\ compromised' = compromised \ fvs
            /\ trustEdges' = { edge \in trustEdges :
                                 /\ edge[1] \notin fvs
                                 /\ edge[2] \notin fvs }
            /\ phase' = Verify
            /\ UNCHANGED
                 << contained,
                    runtimeSCCs,
                    cyclicSCCs,
                    largestSCC >>

    \/ /\ phase = Verify
       /\ phase' = Finished
       /\ contained' = ~BoundaryReachable(compromised)
       /\ UNCHANGED
            << trustEdges,
               compromised,
               revoked,
               runtimeFVS,
               runtimeSCCs,
               cyclicSCCs,
               largestSCC >>

    \/ /\ phase = Finished
       /\ UNCHANGED vars

\* Specification definition
Spec ==
    Init /\ [][Next]_vars /\ WF_vars(Next)

\* Strengthened TypeInvariant
TypeInvariant ==
    /\ trustEdges \subseteq (Agents \times Agents)
    /\ compromised \subseteq Agents
    /\ compromised \cap revoked = {}
    /\ revoked \subseteq Agents
    /\ runtimeFVS \subseteq Agents
    /\ contained \in BOOLEAN
    /\ phase \in { Build, Propagate, Contain, Verify, Finished }
    /\ runtimeSCCs \subseteq SUBSET Agents
    /\ cyclicSCCs \subseteq SUBSET Agents
    /\ largestSCC \subseteq Agents

\* Safety Invariants
RevokedSubsetAgents == revoked \subseteq Agents
RuntimeFVSSubsetAgents == runtimeFVS \subseteq Agents
CompromisedSubsetAgents == compromised \subseteq Agents
RevokedNodesDisconnected == \forall e \in trustEdges : e[1] \notin revoked /\ e[2] \notin revoked
BoundaryNeverRevoked == revoked \cap BoundaryAgents = {}
ContainedImpliesNoBoundaryReachability == contained => ~BoundaryReachable(compromised)
RuntimeFVSSubsetCyclicSCCs == runtimeFVS \subseteq (UNION cyclicSCCs)
BoundaryNeverCompromisedWhenContained == contained => compromised \cap BoundaryAgents = {}
SymbolicCycleBreaking == (phase = Finished) => ~(\exists a \in Agents \ BoundaryAgents : a \in ReachActiveNoSelf10(a))

\* Monotonicity & Temporal Properties
CompromisedMonotonic == [][(phase = Build \/ phase = Propagate) => compromised \subseteq compromised']_vars
RevokedMonotonic == [][revoked \subseteq revoked']_vars
PhaseOrder == [][
  \/ (phase = Build) /\ (phase' \in {Build, Propagate})
  \/ (phase = Propagate) /\ (phase' \in {Propagate, Contain})
  \/ (phase = Contain) /\ (phase' \in {Contain, Verify})
  \/ (phase = Verify) /\ (phase' \in {Verify, Finished})
  \/ (phase = Finished) /\ (phase' \in {Finished})
]_vars
EventualContainment == (\forall b_node \in BoundaryAgents : []~(b_node \in compromised)) => <>(contained)
Termination == <>(phase = Finished)

=============================================================================
