import pytest

from cbba import Agent, Task
from cbba.bundle import build_bundle
from cbba.consensus import resolve_tasks

# Mirrors the scenario in cbba/main.py: agents 0 and 2 are not neighbors,
# so any consensus between them must propagate through agent 1.
AGENT_TOPOLOGY = [
    [1, 1, 0],
    [1, 1, 1],
    [0, 1, 1],
]

L_T = 2
D = 2


@pytest.fixture
def scenario():
    tasks_dict = {
        0: Task(0, (2, 3), static_score=10, discount_factor=0.95),
        1: Task(1, (8, 1), static_score=25, discount_factor=0.95),
        2: Task(2, (5, 7), static_score=15, discount_factor=0.95),
        3: Task(3, (1, 9), static_score=20, discount_factor=0.95),
        4: Task(4, (9, 8), static_score=12, discount_factor=0.95),
    }
    agent_dict = {
        0: Agent(0, (0, 0), num_tasks=5, num_agents=3),
        1: Agent(1, (5, 0), num_tasks=5, num_agents=3),
        2: Agent(2, (10, 0), num_tasks=5, num_agents=3),
    }
    return tasks_dict, agent_dict


def run_to_convergence(tasks_dict, agent_dict):
    iteration = min(len(tasks_dict), len(agent_dict) * L_T) * D
    current_round = 0
    while current_round <= iteration:
        current_round += 1

        for i in agent_dict:
            build_bundle(i, agent_dict, tasks_dict, L_T)

        for i in agent_dict:
            for k in agent_dict:
                if i != k and AGENT_TOPOLOGY[i][k] == 1:
                    resolve_tasks(i, k, agent_dict, tasks_dict, current_round)


def test_converges_to_conflict_free_consensus(scenario):
    tasks_dict, agent_dict = scenario

    run_to_convergence(tasks_dict, agent_dict)

    claimed = {}
    for i in agent_dict:
        for task in agent_dict[i].bundle:
            assert task not in claimed, f"task {task} claimed by both {claimed.get(task)} and {i}"
            claimed[task] = i

    ids = list(agent_dict)
    reference = agent_dict[ids[0]].winning_agent_list
    for i in ids:
        assert agent_dict[i].winning_agent_list == reference

    for i in agent_dict:
        assert len(agent_dict[i].bundle) <= L_T


def test_nonneighboring_agents_agree_via_relay(scenario):
    """Agents 0 and 2 aren't directly connected; they must still agree
    after running through agent 1, exercising the timestamp vector."""
    tasks_dict, agent_dict = scenario

    run_to_convergence(tasks_dict, agent_dict)

    assert agent_dict[0].winning_agent_list == agent_dict[2].winning_agent_list
