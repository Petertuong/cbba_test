import pytest

from cbba import Agent, Task, bundle_construction


@pytest.fixture
def scenario():
    # Agent at origin, tasks on a line: A(1,0), C(10,0), B(5,0)
    tasks_dict = {
        0: Task(task_id=0, position=(1, 0), static_score=10, discount_factor=0.9),   # A
        1: Task(task_id=1, position=(10, 0), static_score=30, discount_factor=0.9),  # C
        2: Task(task_id=2, position=(5, 0), static_score=10, discount_factor=0.9),   # B
    }
    agent_dict = {
        0: Agent(agent_id=0, position=(0, 0), num_tasks=3, num_agents=1),
    }
    return tasks_dict, agent_dict


def test_round_1_claims_highest_value_task(scenario):
    tasks_dict, agent_dict = scenario

    added = bundle_construction(0, agent_dict, tasks_dict)

    assert added is True
    assert agent_dict[0].bundle == [1]
    assert agent_dict[0].path == [1]
    assert agent_dict[0].winning_bid_list == pytest.approx([0.0, 10.460, 0.0], abs=1e-3)


def test_round_2_inserts_task_before_existing_path(scenario):
    tasks_dict, agent_dict = scenario
    bundle_construction(0, agent_dict, tasks_dict)

    bundle_construction(0, agent_dict, tasks_dict)

    assert agent_dict[0].bundle == [1, 0]
    assert agent_dict[0].path == [0, 1]
    assert agent_dict[0].winning_bid_list == pytest.approx([9.000, 10.460, 0.0], abs=1e-3)


def test_round_3_inserts_task_between_existing_path(scenario):
    tasks_dict, agent_dict = scenario
    bundle_construction(0, agent_dict, tasks_dict)
    bundle_construction(0, agent_dict, tasks_dict)

    bundle_construction(0, agent_dict, tasks_dict)

    assert agent_dict[0].bundle == [1, 0, 2]
    assert agent_dict[0].path == [0, 2, 1]
    assert agent_dict[0].winning_bid_list == pytest.approx([9.000, 10.460, 5.905], abs=1e-3)
    assert agent_dict[0].winning_agent_list == [0, 0, 0]


def test_round_4_no_tasks_left_to_add(scenario):
    tasks_dict, agent_dict = scenario
    bundle_construction(0, agent_dict, tasks_dict)
    bundle_construction(0, agent_dict, tasks_dict)
    bundle_construction(0, agent_dict, tasks_dict)

    added = bundle_construction(0, agent_dict, tasks_dict)

    assert added is False
