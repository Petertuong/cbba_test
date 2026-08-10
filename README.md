# CBBA — Consensus-Based Bundle Algorithm

A from-scratch Python implementation of the Consensus-Based Bundle Algorithm
(CBBA) from:

> Choi, H.-L., Brunet, L., & How, J. P. (2009). *Consensus-Based Decentralized
> Auctions for Robust Task Allocation.* IEEE Transactions on Robotics, 25(4).

**Purpose:** this is a learning project — the goal was to work through the
paper closely enough to reimplement its two phases (greedy bundle
construction and consensus-based conflict resolution) from first principles
and convince myself the algorithm actually converges the way the paper
claims.

**Next step:** port this simulation (agents sharing one in-process dict) onto
an actual distributed agent system, where each agent is its own process/node
and the consensus messages travel over a real network transport instead of
being direct Python calls.

## Structure

```
cbba/
  models.py     Agent / Task data classes
  geometry.py   distance helper
  scoring.py    path insertion cost, discounted reward, marginal score
  bundle.py     phase 1: greedy bundle construction (per agent)
  consensus.py  phase 2: consensus / conflict resolution (per agent pair)
  main.py       example 3-agent, 5-task scenario
tests/
  test_bundle.py       phase 1 unit tests
  test_consensus.py    phase 2 decision-table coverage
  test_integration.py  full multi-agent convergence
```

### Phase 1 — bundle construction ([bundle.py](cbba/bundle.py))

Each agent greedily inserts whichever unclaimed task gives it the best
marginal score into its path, up to a capacity `L_t`, bidding its own
discounted-reward score for that task.

### Phase 2 — consensus ([consensus.py](cbba/consensus.py))

When agent `i` receives agent `k`'s winner/bid lists, `resolve_task`
implements the paper's action table (`update` / `reset` / leave alone)
based on who each agent currently believes holds task `j`. Agents that
aren't direct neighbors still converge because each agent also carries a
timestamp vector `s`, gossiped alongside the bids, that says how recently
it heard from every other agent — so stale claims get overruled even when
they arrive secondhand through a relay agent.

## Running the tests

```
pip install pytest
pytest tests/ -v
```

### How the tests were passed

`pytest` isn't installable in the sandbox this was authored in (no network
access, no writable venv), so the suite was verified in-session against the
real source files using a small harness that reproduces pytest's
`fixture` / `parametrize` / `approx` semantics well enough to execute the
actual assertions. Final result: **32/32 passed**.

| File | Cases | What it checks |
|---|---|---|
| `test_bundle.py` | 4 | single-agent greedy insertion into an empty/partial path, including reward values, over 4 rounds until the bundle is full |
| `test_consensus.py` | 26 | every branch of the phase-2 decision table (all 17 rows of the paper's table, with extra cases where a row's condition can go either way — e.g. fresher timestamp alone vs. fresher timestamp *and* higher bid) |
| `test_integration.py` | 2 | a 3-agent / 5-task scenario run to convergence: bundles end up conflict-free, all agents agree on every winner, and no agent exceeds its capacity `L_t` — including the case where agents 0 and 2 aren't direct neighbors and must reach agreement only through agent 1 as a relay |

Anyone cloning this repo should just run `pytest tests/ -v` directly —
that's the real, unmodified pytest run; the in-session harness was only a
workaround for not having pytest available while writing the tests.

## Example scenario

[main.py](cbba/main.py) sets up 3 agents and 5 tasks with a topology where
agent 1 sits between agents 0 and 2 (0 and 2 are not directly connected).
`tests/test_integration.py` runs this exact scenario to convergence and
asserts the result is conflict-free and consistent across all three agents.
