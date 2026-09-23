"""Equal bids must be broken by agent id (lower id wins), otherwise two
agents can both keep the same task forever."""
from cbba.bundle import bundle_construction
from cbba.models import Agent, Task
from tests.test_integration import one_round

COMPLETE = [[1, 1],
            [1, 1]]


def make_twins():
    """Two agents at the SAME position and one task: their bids are identical."""
    agents = {0: Agent(0, (0.0, 0.0), 1, 2),
              1: Agent(1, (0.0, 0.0), 1, 2)}
    tasks = {0: Task(0, (10.0, 0.0), 1.0, 0.95)}
    return agents, tasks


def test_equal_bids_only_lower_id_keeps_the_task():
    agents, tasks = make_twins()
    for rnd in range(1, 6):
        one_round(agents, tasks, COMPLETE, L_t=1, rnd=rnd)

    claimers = [a.id for a in agents.values() if 0 in a.bundle]
    assert claimers == [0], "task 0 claimed by %s" % claimers
    for a in agents.values():
        assert a.winning_agent_list == [0], "agent %d thinks z=%s" % (a.id, a.winning_agent_list)


def test_bundle_lower_id_may_take_a_tied_task():
    # agent 1 already holds the task with exactly the bid agent 0 would make
    agents, tasks = make_twins()
    agents[0].set_winner(0, 1, 0.95 ** 10)
    assert bundle_construction(agents[0], tasks) is True
    assert agents[0].bundle == [0]


def test_bundle_higher_id_may_not_take_a_tied_task():
    agents, tasks = make_twins()
    agents[1].set_winner(0, 0, 0.95 ** 10)
    assert bundle_construction(agents[1], tasks) is False
    assert agents[1].bundle == []
