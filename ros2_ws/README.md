# CBBA on ROS 2 Jazzy

The algorithm in `../cbba/` stays **ROS-free**: it is plain Python with plain
pytest tests. This workspace is a thin wrapper around it:

```
ros2_ws/src/
  cbba_interfaces/      .msg definitions (the contract with the other teams)
  cbba_ros/
    cbba -> ../../../cbba   symlink: the nodes import your library directly
    cbba_ros/agent_node.py         one CBBA agent (one process per agent)
    cbba_ros/task_manager_node.py  stand-in for the environment: publishes tasks
    cbba_ros/monitor_node.py       global observer, checks consensus (debug only)
    config/scenario.yaml           3 agents, 5 tasks, full connectivity
    config/chain.yaml              same world, comm_range=500 -> chain 0-1-2
    launch/cbba.launch.py          task manager + monitor + one agent per scenario entry
```

## Build and run

```bash
cd ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch cbba_ros cbba.launch.py
ros2 launch cbba_ros cbba.launch.py scenario:=$PWD/src/cbba_ros/config/chain.yaml
ros2 launch cbba_ros demo.launch.py     # RViz view, 5 s rounds
```

Before launching, check nothing is still running (`ros2 node list --no-daemon`
must be empty): every ROS program on the machine shares topics. To run a test
next to another system, isolate it with `export ROS_DOMAIN_ID=42`.

Thanks to `--symlink-install`, edits to `cbba/*.py` and to the nodes are picked up
on the next launch without rebuilding. Rebuild only when you change a `.msg`
file, `setup.py`, or add a new config or launch file.

Useful while it runs:

```bash
ros2 topic echo /cbba/plans
ros2 topic echo /cbba/messages --field winning_agents
ros2 node list
ros2 param get /agent_0/cbba_agent comm_range
```

## How one round maps onto ROS

The library is a lock-step simulator (`cbba/main.py`): all agents build,
then all send, then all receive. On ROS each agent is its own process and
a round is one `round_period` of the shared clock:

```
on /cbba/messages   -> append to inbox (drop own messages and out-of-range senders)
each new round      -> consume_message(msgs from earlier rounds) ; release() ; build_bundle() ;
                       produce_message(now) -> publish /cbba/messages ; publish /cbba/plans
```

* **Synchronous rounds.** Round `r` starts at the same wall-clock instant for
  every agent (`r = clock time // round_period`), and a message sent in round
  `r` is only consumed in round `r+1`, even if it arrives earlier. Timestamps
  `s_i` are round numbers, as in the offline simulator. Agents therefore need a
  shared clock: automatic on one machine; across machines use NTP/chrony.
* **Communication range:** DDS delivers every message to every subscriber,
  however far apart they are. A limited range is simulated in the receiver
  (`comm_range` parameter, using `sender_position` in the message).
* **Sanity check:** `scenario.yaml` is the same world as
  `tests/test_integration.py::make_world`. The ROS run must end in the same
  state as `python3 tests/test_integration.py`
  (`z=[0, 1, 1, 2, 0]`, paths `[0,4] / [2,1] / [3]`). Whenever you change the
  algorithm, compare the ROS result with the offline result first.

## Interface contract (for the other teams)

| Topic | Type | Who publishes | Who uses it |
|---|---|---|---|
| `/cbba/tasks` | `cbba_interfaces/TaskArray` (reliable, transient_local) | environment (Unity); `task_manager` for now | agents |
| `/cbba/messages` | `cbba_interfaces/CbbaMessage` | each agent | other agents, monitor |
| `/cbba/plans` | `cbba_interfaces/AgentPlan` (path + waypoints) | each agent | navigation/control, monitor |

Unity side (see Unity-Robotics-Hub): the `ROS-TCP-Endpoint` package runs in
this workspace, and Unity uses `ROS-TCP-Connector`. Unity has to generate C#
classes from `src/cbba_interfaces/msg` (*Robotics → Generate ROS Messages*),
so treat those files as a shared API: change them only after agreeing with
the other teams. `ROS-TCP-Endpoint`'s ROS 2 branch was written for older
distros. Build it from source in this workspace and check it on Jazzy early.

## Workflow: one assumption at a time

For every step:

1. **Write the assumption down** here (below) and in `scenario.yaml`.
2. **Reproduce it offline first**: add a pytest in `tests/` that sets up the
   situation with the lock-step simulator. It is deterministic and fast to
   debug, whereas ROS is not.
3. **Change `cbba/`** until the test passes; keep the existing tests green.
4. **Run it on ROS** with a scenario file for that assumption; watch the
   monitor output and compare it with the offline result.
5. Commit, then relax the next assumption.

### Assumption ladder (suggested order)

| # | Assumption | Status | What changes when it is relaxed |
|---|---|---|---|
| A0 | static agents, static task set, everyone hears everyone, reliable messages, no failures | **works** | - |
| A1 | limited but **static** comm range (multi-hop) | works (`chain.yaml`) | try a disconnected graph: expect each component to converge on its own, so tasks can be assigned twice across components |
| A2 | rounds are **not synchronised**, messages can be **lost or delayed** | todo | CBBA's convergence proof assumes synchronous rounds. Try BEST_EFFORT QoS or random drops in `on_message`, then look at Asynchronous CBBA (Johnson, Ponda, Choi & How, 2010) |
| A3 | agents **move** (position from odometry) | todo | positions come from a subscription instead of a parameter; the topology changes over time; decide when to re-plan |
| A4 | tasks **appear / get completed** | todo | `z`/`y` are lists indexed by task id and sized once, so they must become dicts; the environment needs to say when a task is done |
| A5 | an agent **dies** | todo | its tasks stay claimed forever (nothing resets `z`). You need a liveness timeout on `s_ik` and a way to release those tasks |

## Known issues in `cbba/`

Confirmed by running them:

* **The score uses distance as time.** `0.95 ** distance` is about 4e-112 at
  5 km and exactly `0.0` beyond about 14 km, so the agent never bids. Decide on
  units with the Unity team (metres?) and use `tau = distance / speed`.
* **`cbba/main.py` crashes on import.** Its module-level code uses the
  undefined names `tasks_dict` and `N_u`, calls `main(graph, D)` with too few
  arguments, and passes `Records(...)`. The ROS nodes do not import it.
* **`tests/test_search_algo.py` is out of date.** Five tests still call
  `bfs(agents, comm_range=...)` and fail, but `bfs` now takes `(N_u, graph)`.
Not reproduced yet, only a risk:

* **The convergence check can stop too early.** `main.py` stops after a single
  unchanged round and compares only `bundle` and `z` (not `y`, and not
  agreement between agents). With multi-hop topologies, information can still
  be in flight at that point. Consider "unchanged for D rounds".
