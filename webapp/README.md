# CBBA Car Race

**Play it online: https://cbba-test.onrender.com/** (the first load after a quiet period can take up to a minute).

A web game built on the CBBA core in `../cbba/`. Place 2-5 cars and 1-10 tasks on a
1000 × 600 m map, guess which car will earn the most points, and watch the cars split
the tasks among themselves with the Consensus-Based Bundle Algorithm.

- **Backend** (`app/`): FastAPI. `game.py` holds the rules and calls `cbba.simulation.simulate()`;
  `main.py` validates requests and serves the page. `POST /api/games` returns every round,
  the final routes, the points and the winner.
- **Frontend** (`static/`): plain HTML, CSS and JavaScript. It only replays what the server
  returns; the server alone decides the winner.
- **Rules:** cars drive in straight lines; a task is worth `value × discount^seconds`;
  each task goes to one car; on equal bids, the lower car number wins.
- **Settings** (per race): tasks per car (1 up to the tasks on the map, default 2), value
  lost per second (0-50 %, default 2 %, i.e. discount 0.98) and car speed (1-50 m/s,
  default 10). The API accepts them as `tasks_per_car`, `discount` and `speed`.
- **Missions:** after a race, each car waits where it finished; completed tasks disappear and
  unassigned ones stay. Add new tasks and race again: a leaderboard adds up tasks done, points
  and wins per car over the whole game.

## Run it

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/pip install -e . -r webapp/requirements-dev.txt   # server + test tools
cd webapp && env -u PYTHONPATH ../.venv/bin/uvicorn app.main:app --reload
```

Open http://localhost:8000. (`env -u PYTHONPATH` keeps ROS 2's Python packages out of the
app, if your shell sources ROS.)

## Test it

```bash
../.venv/bin/playwright install chromium                          # once
env -u PYTHONPATH ../.venv/bin/python -m pytest tests             # game rules, API, end-to-end
```

See [`../docs/TEST_PLAN.md`](../docs/TEST_PLAN.md) for the test levels, techniques and
acceptance scenarios.
