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

ReachStep(edges, S, fvs) == { v \in Agents \ fvs : \exists u \in S : <<u, v>> \in edges }
ReachNoSelf1(edges, a, fvs) == ReachStep(edges, {a}, fvs)
ReachNoSelf2(edges, a, fvs) == LET r == ReachNoSelf1(edges, a, fvs) IN r \cup ReachStep(edges, r, fvs)
ReachNoSelf3(edges, a, fvs) == LET r == ReachNoSelf2(edges, a, fvs) IN r \cup ReachStep(edges, r, fvs)
ReachNoSelf4(edges, a, fvs) == LET r == ReachNoSelf3(edges, a, fvs) IN r \cup ReachStep(edges, r, fvs)
ReachNoSelf5(edges, a, fvs) == LET r == ReachNoSelf4(edges, a, fvs) IN r \cup ReachStep(edges, r, fvs)
ReachNoSelf6(edges, a, fvs) == LET r == ReachNoSelf5(edges, a, fvs) IN r \cup ReachStep(edges, r, fvs)
ReachNoSelf7(edges, a, fvs) == LET r == ReachNoSelf6(edges, a, fvs) IN r \cup ReachStep(edges, r, fvs)
ReachNoSelf8(edges, a, fvs) == LET r == ReachNoSelf7(edges, a, fvs) IN r \cup ReachStep(edges, r, fvs)
ReachNoSelf9(edges, a, fvs) == LET r == ReachNoSelf8(edges, a, fvs) IN r \cup ReachStep(edges, r, fvs)
ReachNoSelf10(edges, a, fvs) == LET r == ReachNoSelf9(edges, a, fvs) IN r \cup ReachStep(edges, r, fvs)

ValidFeedbackVertexSet(edges, fvs) ==
    \forall a \in (UNION cyclicSCCs) \ fvs :
        a \notin ReachNoSelf10(edges, a, fvs)

\* Bounded fixed-point reachability operators (unrolled to 10 steps using LET-caching)
Reach1(edges, S) == S \cup { v \in Agents : \exists u \in S : <<u, v>> \in edges }
Reach2(edges, S) == LET r == Reach1(edges, S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in edges }
Reach3(edges, S) == LET r == Reach2(edges, S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in edges }
Reach4(edges, S) == LET r == Reach3(edges, S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in edges }
Reach5(edges, S) == LET r == Reach4(edges, S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in edges }
Reach6(edges, S) == LET r == Reach5(edges, S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in edges }
Reach7(edges, S) == LET r == Reach6(edges, S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in edges }
Reach8(edges, S) == LET r == Reach7(edges, S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in edges }
Reach9(edges, S) == LET r == Reach8(edges, S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in edges }
Reach10(edges, S) == LET r == Reach9(edges, S) IN r \cup { v \in Agents : \exists u \in r : <<u, v>> \in edges }

BoundaryReachable(edges, S) == (Reach10(edges, S) \cap BoundaryAgents) /= {}

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
            /\ LET updatedEdges == { edge \in trustEdges :
                                       /\ edge[1] \notin fvs
                                       /\ edge[2] \notin fvs }
               IN
                   /\ ValidFeedbackVertexSet(updatedEdges, fvs)
                   /\ trustEdges' = updatedEdges
            /\ Cardinality(fvs) <= Tau
            /\ runtimeFVS' = fvs
            /\ revoked' = revoked \cup fvs
            /\ compromised' = compromised \ fvs
            /\ phase' = Verify
            /\ UNCHANGED
                 << contained,
                    runtimeSCCs,
                    cyclicSCCs,
                    largestSCC >>

    \/ /\ phase = Verify
       /\ phase' = Finished
       /\ contained' = ~BoundaryReachable(trustEdges, compromised)
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
ContainedImpliesNoBoundaryReachability == contained => ~BoundaryReachable(trustEdges, compromised)
RuntimeFVSSubsetCyclicSCCs == runtimeFVS \subseteq (UNION cyclicSCCs)
BoundaryNeverCompromisedWhenContained == contained => compromised \cap BoundaryAgents = {}

CyclesBrokenAfterContainment ==
    (phase = Finished) =>
        \forall a \in Agents \ BoundaryAgents :
            a \notin ReachActiveNoSelf10(a)

SymbolicCycleBreaking == CyclesBrokenAfterContainment

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
EventualContainment ==
    \A ba \in BoundaryAgents :
        ([] ~(ba \in compromised)) => <> contained
Termination == <>(phase = Finished)

=============================================================================
