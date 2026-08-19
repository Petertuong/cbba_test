"""
Regression + structural tests for the message-object refactor.

Nothing here knows anything about the scoring function on purpose --
these tests must stay valid when the reward model changes.
"""

from cbba.models import Agent, Task, Message
from cbba.bundle import build_bundle
from cbba.consensus import produce_message, consume_message, release
from cbba.transport import deliver_message


# ---------------------------------------------------------------- fixtures

def make_world():
    """3 agents, 5 tasks, fixed positions. No RNG anywhere."""
    agents = {
        0: Agent(0, (0.0, 0.0), 5, 3),
        1: Agent(1, (500.0, 0.0), 5, 3),
        2: Agent(2, (1000.0, 0.0), 5, 3),
    }
    tasks = {
        0: Task(0, (100.0, 100.0), 1.0, 0.95),
        1: Task(1, (400.0, 200.0), 1.0, 0.95),
        2: Task(2, (600.0, 100.0), 1.0, 0.95),
        3: Task(3, (900.0, 300.0), 1.0, 0.95),
        4: Task(4, (200.0, 800.0), 1.0, 0.95),
    }
    return agents, tasks


CHAIN = [[1, 1, 0],
         [1, 1, 1],
         [0, 1, 1]]

COMPLETE = [[1, 1, 1],
            [1, 1, 1],
            [1, 1, 1]]


def one_round(agents, tasks, graph, L_t, rnd):
    outgoing = [None] * len(agents)
    for a in agents.values():
        build_bundle(a, tasks, L_t)
        outgoing[a.id] = produce_message(a, rnd)

    inboxes = deliver_message(outgoing, graph)

    for aid, msgs in inboxes.items():
        for m in msgs:
            consume_message(agents[aid], m)
        release(agents[aid])


# ---------------------------------------------------- TEST 1: one hop/round

def test_one_hop_per_round():
    """
    Chain 0-1-2. After ONE round, agent 2 must know nothing that
    originated at agent 0. If it does, produce and consume are
    interleaved and information crossed two hops in one round.
    """
    agents, tasks = make_world()
    one_round(agents, tasks, CHAIN, L_t=2, rnd=1)

    a0, a2 = agents[0], agents[2]

    assert a2.timestamp_list[0] == -1, (
        "agent 2 has a timestamp for agent 0 after one round -- "
        "two hops travelled in one round"
    )
    assert a0.timestamp_list[2] == -1, "same failure, other direction"

    for j in tasks:
        assert a2.winning_agent_list[j] != 0, (
            "agent 2 believes agent 0 won task %d after one round" % j
        )

    # and the positive half: one hop DID happen
    assert a2.timestamp_list[1] == 1, "agent 2 never heard from its neighbour"


# ------------------------------------------- TEST 2: invariants at fixpoint

def run_to_fixpoint(agents, tasks, graph, L_t, cap=200):
    rnd = 0
    while rnd < cap:
        rnd += 1
        before = {a.id: (list(a.bundle), list(a.winning_agent_list))
                  for a in agents.values()}
        one_round(agents, tasks, graph, L_t, rnd)
        after = {a.id: (list(a.bundle), list(a.winning_agent_list))
                 for a in agents.values()}
        if before == after:
            return rnd
    raise AssertionError("hit round cap %d without a fixpoint" % cap)


def test_convergence_invariants():
    agents, tasks = make_world()
    L_t = 2
    run_to_fixpoint(agents, tasks, COMPLETE, L_t)

    ids = sorted(agents)
    ref = agents[ids[0]]

    # (a) consensus: every agent holds the same z and y
    for i in ids[1:]:
        assert agents[i].winning_agent_list == ref.winning_agent_list, \
            "agents disagree on z"
        assert agents[i].winning_bid_list == ref.winning_bid_list, \
            "agents disagree on y"

    # (b) capacity
    for a in agents.values():
        assert len(a.bundle) <= L_t, "agent %d over capacity" % a.id

    # (c) conflict-free: each task claimed by at most one agent,
    #     and a claim in z must match the claimer's bundle
    for j in tasks:
        owner = ref.winning_agent_list[j]
        claimers = [a.id for a in agents.values() if j in a.bundle]
        assert len(claimers) <= 1, "task %d claimed by %s" % (j, claimers)
        if owner != -1:
            assert claimers == [owner], \
                "z says %d owns task %d but bundles say %s" % (owner, j, claimers)

    # (d) bundle/z consistency, both directions
    for a in agents.values():
        from_z = {j for j in tasks if a.winning_agent_list[j] == a.id}
        assert from_z == set(a.bundle), \
            "agent %d: bundle %s vs z-claims %s" % (a.id, a.bundle, sorted(from_z))

    # (e) eq. (9): within a bundle, bids are non-increasing
    for a in agents.values():
        bids = [a.winning_bid_list[t] for t in a.bundle]
        for n in range(len(bids) - 1):
            assert bids[n] >= bids[n + 1], \
                "agent %d bundle bids not monotone: %s" % (a.id, bids)


# --------------------------------------------------- regression state dump

def dump(agents):
    """Canonical string. Diff this against a pre-refactor run."""
    out = []
    for i in sorted(agents):
        a = agents[i]
        out.append("agent %d" % i)
        out.append("  bundle %s" % a.bundle)
        out.append("  path   %s" % a.path)
        out.append("  z      %s" % a.winning_agent_list)
        out.append("  y      %s" % ["%.6f" % v for v in a.winning_bid_list])
        out.append("  s      %s" % a.timestamp_list)
    return "\n".join(out)


if __name__ == "__main__":
    test_one_hop_per_round()
    print("one-hop test passed")

    agents, tasks = make_world()
    r = run_to_fixpoint(agents, tasks, COMPLETE, L_t=2)
    print("converged in %d rounds\n" % r)
    print(dump(agents))

    test_convergence_invariants()
    print("\ninvariants passed")
