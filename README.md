# CBBA — Consensus-Based Bundle Algorithm

**Live demo: [CBBA Car Race](https://cbba-test.onrender.com/)**. Place cars and tasks on a
map, guess which car earns the most, and watch the cars split the tasks with this
algorithm. (Free hosting: the first load after a quiet period can take up to a minute.)

A from-scratch Python implementation of the Consensus-Based Bundle Algorithm
(CBBA) from:

> Choi, H.-L., Brunet, L., & How, J. P. (2009). _Consensus-Based Decentralized
> Auctions for Robust Task Allocation._ IEEE Transactions on Robotics, 25(4).

**Purpose:** this is a learning project — the goal was to work through the
paper closely enough to reimplement its two phases (greedy bundle
construction and consensus-based conflict resolution) from first principles
and convince myself the algorithm actually converges the way the paper
claims.

## Structure

```
cbba/
  models.py       Agent / Task data classes
  geometry.py     distance helper (2D or 3D)
  scoring.py      path insertion cost, discounted reward, marginal score, points per agent
  bundle.py       phase 1: greedy bundle construction (per agent)
  consensus.py    phase 2: consensus / conflict resolution (per agent pair)
  simulation.py   lock-step rounds until agreement, with a per-round history
  transport.py    message delivery over a communication graph
  search_algo.py  communication graph and network depth (BFS)
  main.py         experiment: convergence for several communication ranges
tests/
  test_bundle.py       phase 1 unit tests
  test_consensus.py    phase 2 decision-table coverage
  test_integration.py  full multi-agent convergence
  test_simulation.py   simulate(), points, agent speed
  test_tie_break.py    equal bids go to the lower agent id
  test_geometry.py     2D / 3D distance
  test_search_algo.py  communication graph and BFS
webapp/              CBBA Car Race: a web game built on the core (see webapp/README.md)
docs/TEST_PLAN.md    test levels, techniques, acceptance scenarios, defects found
```

# CBBA — Consensus-Based Bundle Algorithm

Suppose we have multiple agents, in particular here are drones. We want to figure out a way for drones to communicate with each other, choose tasks that they have to do without a central server allocate for them, under some assumptions.

CBBA is basically the consensus algorithm. Utilizing auction and only rely on local situational awareness.

## Situational Awareness

**Situational awareness** is the knowledge of the drone. And here, we only want it to rely on this knowledge to choose tasks to perform, that still can guarantee 50% optimality of SGA.

Those following knowledges are essential:

- **Bundle `b_i`** — containing tasks it has to perform (in order of arrival time).
- **Path `p_i`** — containing the optimized path of which the drone has to move to solve the tasks.
  > Note that the optimization is not about the shortest path, but about prioritizing tasks that reward more score (more urgent). Although Discounted factor can steer the drone to choose the short path.
- **`z_i`** — list of agent that won the bid of the task. Here I store it in the form of list, thus index is the task ID and the value is the agent ID that won that task.
- **`y_i`** — list of highest bid made for that task. Here I store it in the form of list, thus index is the task ID and the value is the highest bid made for that task.
- **`s_i`** — timestamp list. It stores the knowledge of the agent about the current round of other agents. Here index is the agent ID and value is the `current_round` of that agent.

## Choosing a Task

Choosing a task has to go through three stages:

1. **Constructing the bundle of task** — which mean we find the task that the agent can win the bid, and with highest possible reward, and construct the path that optimize the reward. The reward is calculated through scoring scheme.
2. **Scoring scheme** — we calculate the reward based on time a drone has to take to travel to that task. However, it still doesn't mean the final result is the shortest path.
3. **Consensus** — an agent can naively bid for a task and think it win the task. But if another agent found out that the task is already been claimed, this phase will help resolving the conflict. We follow the table in the paper and construct that table accordingly.

## Messages

Then we started to define message, an essential part of communication.

The CBBA guarantees that there are only three factors that should impact the decisions of an agent and optimality of the algorithm: `y_k`, `z_k`, `s_k` where `k` is the sender (producer of the message).

A message is delivered through transport protocol, by checking if two agent have connection to each other and if they do, it will put the message in the receiver's inbox. The receiver will `consume_message` as define the program, mainly to resolve the conflict and update the `timestamp_list`.

## Network Topology

The transportation cannot happen without us finding out the topology of the network. Note that each agent has no knowledge of the topology.

The topology here is calculated based on the distance between two agents, without weight, and the number of hops `k` between two agents is the multiplication factor `k` of `k * comm_range`.

## Convergence

The algorithm in combination, will run at most `D * N_min` time. And the paper guarantee convergence within that bound if we assume static topology. However, most of the case, convergence is reached a lot earlier.
