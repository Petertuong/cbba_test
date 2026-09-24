"""simulate(), agent_score() and agent speed."""
import pytest

from cbba.models import Agent, Task
from cbba.scoring import agent_score
from cbba.simulation import simulate
from tests.test_integration import CHAIN, make_world


def test_simulate_reaches_the_known_allocation():
    agents, tasks = make_world()
    result = simulate(agents, tasks, max_bundle=2)

    assert result['converged']
    final = result['rounds'][-1]['agreed']
    assert [a['bundle'] for a in final] == [[0, 4], [2, 1], [3]]
    assert all(a['z'] == [0, 1, 1, 2, 0] for a in final)


def test_round_one_bids_show_the_conflicts():
    agents, tasks = make_world()
    first = simulate(agents, tasks, max_bundle=2)['rounds'][0]['bids']
    # everyone bids blind in round 1: tasks 1 and 2 are each claimed twice
    assert [a['bundle'] for a in first] == [[0, 1], [2, 1], [3, 2]]


def test_multi_hop_network_needs_more_rounds():
    full = simulate(*make_world(), max_bundle=2)
    chain = simulate(*make_world(), max_bundle=2, graph=CHAIN)
    assert chain['converged']
    assert len(chain['rounds']) > len(full['rounds'])


def test_scores_are_what_each_path_earns():
    agents, tasks = make_world()
    result = simulate(agents, tasks, max_bundle=2)
    for i, agent in agents.items():
        assert result['scores'][i] == pytest.approx(agent_score(agent, tasks))
    assert result['scores'][2] > 0


def test_agent_score_uses_speed():
    # one task 10 away, speed 2 -> arrives at t=5, earns 8 * 0.5**5 = 0.25
    agent = Agent(0, (0.0, 0.0), 1, 1, speed=2.0)
    tasks = {0: Task(0, (10.0, 0.0), 8.0, 0.5)}
    agent.path = [0]
    assert agent_score(agent, tasks) == pytest.approx(0.25)


def test_agent_without_tasks_scores_zero():
    agent = Agent(0, (0.0, 0.0), 1, 1)
    assert agent_score(agent, {0: Task(0, (1.0, 0.0), 1.0, 0.9)}) == 0.0
