import pytest

from cbba.models import Agent
from cbba.search_algo import bfs, build_graph


def make_agents(positions):
    return {i: Agent(i, pos, 1, len(positions)) for i, pos in enumerate(positions)}


# ------------------------------------------------------------- build_graph

def test_build_graph_connects_within_range():
    agents = make_agents([(0.0, 0.0), (5.0, 0.0)])
    graph = build_graph(agents, comm_range=5.0)

    assert graph == [[0, 1], [1, 0]]


def test_build_graph_leaves_out_of_range_disconnected():
    agents = make_agents([(0.0, 0.0), (5.1, 0.0)])
    graph = build_graph(agents, comm_range=5.0)

    assert graph == [[0, 0], [0, 0]]


def test_build_graph_is_symmetric():
    agents = make_agents([(0.0, 0.0), (3.0, 0.0), (100.0, 0.0)])
    graph = build_graph(agents, comm_range=4.0)

    for i in range(len(agents)):
        for j in range(len(agents)):
            assert graph[i][j] == graph[j][i]


def test_build_graph_no_self_loops():
    agents = make_agents([(0.0, 0.0), (1.0, 0.0)])
    graph = build_graph(agents, comm_range=1000.0)

    for i in range(len(agents)):
        assert graph[i][i] == 0


def test_build_graph_rows_are_independent():
    """Regression: graph used to be [[0]*N]*N, N aliased copies of one row --
    writing to graph[i][j] would leak into every other row."""
    agents = make_agents([(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)])
    graph = build_graph(agents, comm_range=1000.0)

    graph[0][1] = 9
    assert graph[1][1] == 0
    assert graph[2][1] == 1  # untouched by the mutation above


# -------------------------------------------------------------------- bfs

def test_bfs_single_agent_has_zero_depth():
    agents = make_agents([(0.0, 0.0)])
    assert bfs(agents, comm_range=10.0) == 0


def test_bfs_chain_depth_is_hop_count():
    # 0 - 1 - 2 - 3, evenly spaced 10 apart, comm_range covers one hop
    agents = make_agents([(0.0, 0.0), (10.0, 0.0), (20.0, 0.0), (30.0, 0.0)])
    assert bfs(agents, comm_range=10.0) == 3


def test_bfs_star_depth_is_two_hops_leaf_to_leaf():
    # center at origin, three leaves in range of the center only
    agents = make_agents([(0.0, 0.0), (5.0, 0.0), (0.0, 5.0), (-5.0, 0.0)])
    assert bfs(agents, comm_range=5.0) == 2


def test_bfs_fully_connected_depth_is_one():
    agents = make_agents([(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)])
    assert bfs(agents, comm_range=10.0) == 1


def test_bfs_disconnected_components_stay_bounded_by_reachable_set():
    # two isolated pairs, far enough apart that they never see each other
    agents = make_agents([(0.0, 0.0), (1.0, 0.0), (1000.0, 0.0), (1001.0, 0.0)])
    assert bfs(agents, comm_range=1.0) == 1
