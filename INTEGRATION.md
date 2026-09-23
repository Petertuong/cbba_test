# CBBA integration guide (ROS 2 Jazzy + Unity)

This guide is for teammates, and for the AI coding agents that work for them, who need to connect
to the task-allocation part of the project. Read it fully before you change code that touches
the topics below.

- **Owner of this repo / the algorithm:** Petertuong
- **Repo:** https://github.com/Petertuong/cbba_test
- **ROS distro:** ROS 2 Jazzy, Ubuntu 24.04, Python 3.12
- **Status:** assumption A0 works end to end (static agents, static task set, synchronous
  rounds, everyone hears everyone). See "Current assumptions" before relying on anything else.

---

## 1. What this component does

Three (or more) drones decide **among themselves** which drone does which task, with no central
allocator. This uses the Consensus-Based Bundle Algorithm (CBBA; Choi, Brunet & How, 2009).

- **Input:** a list of tasks (position, value), published once by the environment.
- **Output:** for each drone, an ordered list of tasks and their positions (waypoints).
- **In between:** the drones exchange bids every round until they agree. The environment does
  **not** assign tasks. It only announces them.

## 2. Repository layout and ownership

```
cbba/                      the algorithm, pure Python, NO ROS imports (owner: Petertuong)
tests/                     pytest suite for cbba/ (offline, deterministic)
ros2_ws/src/
  cbba_interfaces/msg/     SHARED CONTRACT: Task, TaskArray, CbbaMessage, AgentPlan
  cbba_ros/                ROS 2 nodes (owner: Petertuong)
    cbba -> ../../../cbba    symlink, the nodes import the algorithm directly
    cbba_ros/agent_node.py   one process per drone, runs CBBA
    cbba_ros/task_manager_node.py  stand-in for the environment: publishes tasks from YAML
    cbba_ros/monitor_node.py       debug: global consensus check (logs only)
    cbba_ros/visualizer_node.py    debug: RViz markers on /cbba/markers
    config/*.yaml            scenarios (agents, tasks, round timing, comm range)
    launch/cbba.launch.py    task manager + monitor + one agent per scenario entry
    launch/demo.launch.py    same, plus RViz, with 5 s rounds
```

**Rules for AI agents working in this repo:**
1. Do **not** modify `cbba/` or `tests/`. Open an issue or ask Petertuong instead.
2. Do **not** add ROS imports to `cbba/`. It must stay testable with plain `pytest`.
3. Do **not** change any `.msg` file in `cbba_interfaces/` without agreement from **all**
   teams. Unity generates C# classes from them, and a silent mismatch breaks the connection.
4. Integrate by **publishing and subscribing to the topics in section 4**, not by importing
   Python modules from `cbba_ros`.
5. Before launching anything, check that nothing else is running (section 7). Every ROS
   program on the same machine and the same `ROS_DOMAIN_ID` shares topics.

## 3. Build and run

```bash
cd ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch cbba_ros cbba.launch.py                  # default scenario, 0.5 s rounds
ros2 launch cbba_ros demo.launch.py                  # RViz visualisation, 5 s rounds
ros2 launch cbba_ros cbba.launch.py scenario:=/abs/path/to/your.yaml
```

Offline algorithm tests (no ROS needed): `python3 -m pytest -q tests/test_bundle.py
tests/test_consensus.py tests/test_integration.py tests/test_geometry.py tests/test_tie_break.py`.
(`tests/test_search_algo.py` is known to be out of date.)

**Expected result** of the default scenario: the monitor logs
`CONSENSUS z=[0, 1, 1, 2, 0]  agent 0 path=[0, 4] | agent 1 path=[2, 1] | agent 2 path=[3]`.

## 4. Interface contract (topics)

All positions are `geometry_msgs/Point` in the ROS convention: **x forward/east, y left/north,
z up, right-handed**. The fixed frame is `map`. Units are **metres** (see the known issue in
section 8).

| Topic | Type | QoS | Publisher | Subscribers |
|---|---|---|---|---|
| `/cbba/tasks` | `cbba_interfaces/TaskArray` | RELIABLE, **TRANSIENT_LOCAL**, depth 1 | environment (today: `task_manager`) | agents, visualizer |
| `/cbba/messages` | `cbba_interfaces/CbbaMessage` | RELIABLE, VOLATILE, depth 50 | each agent | agents, monitor, visualizer |
| `/cbba/plans` | `cbba_interfaces/AgentPlan` | RELIABLE, VOLATILE, depth 10 | each agent, **every round** | navigation / Unity, monitor, visualizer |
| `/cbba/markers` | `visualization_msgs/MarkerArray` | default | visualizer (debug only) | RViz |

**Which topics you use depends on your role:**
- **Environment / Unity:** publish the tasks (section 5). Do not touch `/cbba/messages`.
- **Navigation / control / Unity drones:** subscribe to `/cbba/plans` only.
- `/cbba/messages` is **internal** to the algorithm. Its format may change without notice.

### Message definitions (`ros2_ws/src/cbba_interfaces/msg/`)

```
# Task.msg
int32 id                        # MUST be 0..N-1, contiguous (the algorithm indexes lists by id)
geometry_msgs/Point position
float64 static_score            # value of the task
float64 discount_factor         # 0 < lambda < 1, value decays with travel distance

# TaskArray.msg
Task[] tasks                    # the complete task list, sent as ONE message

# AgentPlan.msg  (output)
int32 agent_id
int32[] bundle                  # task ids in the order they were won
int32[] path                    # task ids in the order to FLY them
geometry_msgs/Point[] waypoints # positions of `path`, same order, ready to fly
int32 stable_rounds             # rounds in a row with no change in this agent's view
```

Inspect them with `ros2 interface show cbba_interfaces/msg/AgentPlan`.

### Semantics you must respect

- **Tasks are sent once, as one complete `TaskArray`.** Agents start CBBA when it arrives.
  Re-sending the identical list is harmless. A **different** list is **ignored** for now
  (static task set, assumption A0).
- **Task ids** must be exactly `0..N-1`. Ids like `1..5` or `3, 7, 9` are rejected.
- **Agent ids** are `0..num_agents-1`. `num_agents` must be the same for every agent.
- **Plans are published every round**, even when they don't change. **No agent can know that
  global consensus is reached**. Use `stable_rounds` as the signal: e.g. only start flying when
  `stable_rounds >= 3`. Plans can still change in the first rounds, so don't fly the first plan
  you receive.

## 5. Unity integration (Unity-Robotics-Hub: ROS-TCP-Endpoint + ROS-TCP-Connector)

1. **ROS side:** clone `ROS-TCP-Endpoint` (branch `main-ros2`) into `ros2_ws/src/`, build it with
   `colcon build`, and run its endpoint node. It was written for older ROS 2 distros and is
   **not yet tested on Jazzy**, so do this first and report problems early.
2. **Unity side:** add the `ROS-TCP-Connector` package, then generate C# messages with
   *Robotics → Generate ROS Messages…* pointed at `ros2_ws/src/cbba_interfaces/msg/`. Regenerate
   whenever a `.msg` file changes.
3. **Coordinates:** Unity is left-handed and y-up; ROS is right-handed and z-up. Always convert
   with the connector's `ROSGeometry` helpers (e.g. `To<FLU>()` / `From<FLU>()`). Never copy
   x/y/z across directly.
4. **Receiving plans (works today):** subscribe to `/cbba/plans` (`AgentPlan`). Each message has
   `agent_id`; keep the latest plan per agent. Fly `waypoints` in order.
5. **Publishing tasks: the one known pitfall.** ROS-TCP-Endpoint creates its ROS publishers
   with **default QoS (VOLATILE)**; latching is still a TODO in its source. The agents subscribe
   to `/cbba/tasks` with **TRANSIENT_LOCAL**, and ROS **rejects** that combination: the agents
   only log
   `offering incompatible QoS. No messages will be received from it. Last incompatible policy: DURABILITY`
   and never start (verified on Jazzy). **Therefore Unity must NOT publish on `/cbba/tasks`
   directly.** Agreed approach:
   - Unity publishes the `TaskArray` on **`/env/tasks`** (volatile is fine there).
   - A small relay on the CBBA side (owner: Petertuong, **not implemented yet**) subscribes to
     `/env/tasks` and republishes it latched on `/cbba/tasks`.
   - Until the relay exists, tasks come from `task_manager` and the scenario YAML.
6. **Drone start positions:** agents currently take their start position from the scenario YAML
   (`agents: - {id, position: [x, y, z]}`), not from Unity. The Unity scene must place drone `i`
   at the same position (converted to Unity coordinates), or the plans won't match the scene.
   (This changes with assumption A3; see section 6.)
7. **Clock:** rounds are aligned to the **wall clock** of the machine the agents run on. Do not
   set `use_sim_time` on the agents unless every agent uses the same `/clock`.

## 6. Current assumptions and upcoming changes

Development relaxes **one assumption at a time**. For each step: write the assumption down,
reproduce it in an offline pytest first, change `cbba/`, run it on ROS, compare with the
offline result, commit.

| # | Assumption | Status | What will change for integrators |
|---|---|---|---|
| A0 | static agents, static task set, synchronous rounds, reliable messages, no failures | **done** | - |
| A1 | limited but static comm range (multi-hop) | works (`config/chain.yaml`) | none |
| - | **task batches**: a new task list after all agents have finished the previous one | **next** | `TaskArray` (and `CbbaMessage`) get a `batch_id` field: **contract change**, regenerate the C# messages. Agents re-plan from their current position |
| A2 | rounds not synchronised; messages lost or delayed | planned | none expected |
| A3 | agents move; position from the simulator | planned | Unity will need to publish each drone's pose (proposal: `/agent_<i>/pose`, `geometry_msgs/PoseStamped`, frame `map`) |
| A4 | tasks appear / are completed during the mission | planned | environment reports task completion (message to be agreed) |
| A5 | an agent fails | planned | none expected |

Anything marked "proposal" or "not implemented yet" will be agreed with the affected team first.

## 7. Operational rules (these caused real problems)

- **Only one system at a time.** Before launching, this must print nothing:
  `ps -eo pid,etime,args | grep -E "cbba_ros|rviz2" | grep -v grep`.
  Stop everything with `pkill -INT -f "ros2 launch cbba_ros"`. A forgotten launch in another
  terminal feeds its old results to the new agents.
- `ros2 node list` can show stopped nodes for a few seconds after shutdown. Trust `ps`.
- **To test next to a running system, isolate it:** `export ROS_DOMAIN_ID=42` (any unused
  number) in that terminal. Unity's endpoint must use the same domain as the agents.
- After changing a `.msg` file: `colcon build`, re-source `install/setup.bash`, and regenerate
  the Unity C# messages. Python-only changes need a relaunch, not a rebuild.

## 8. Known issues

- **Bids use distance as time**: `bid = static_score * discount_factor ** distance`. With
  metres and `0.95`, bids are tiny (~1.5e-18 at 800 m) and become exactly 0 beyond ~14 km,
  which means no bid. Keep scenario distances in the hundreds of metres until this is fixed.
- ROS-TCP-Endpoint on Jazzy: untested (section 5).
- `tests/test_search_algo.py` is out of date (5 failures, unrelated to the ROS side).

## 9. Checklist for integrators

- [ ] `colcon build` succeeds and `ros2 launch cbba_ros cbba.launch.py` prints the expected CONSENSUS line.
- [ ] `ros2 topic echo /cbba/plans` shows one plan per agent, every round.
- [ ] Unity: C# messages generated from `cbba_interfaces/msg/`; coordinates converted with `ROSGeometry`.
- [ ] Unity drone start positions match the scenario YAML.
- [ ] Unity publishes tasks on `/env/tasks`, **not** `/cbba/tasks` (until the relay exists, use the YAML).
- [ ] Nothing waits for "global consensus"; flying starts on `stable_rounds`.
