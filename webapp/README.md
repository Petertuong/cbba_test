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
- **Rules:** cars drive at 10 m/s in straight lines; a task is worth `value × 0.98^seconds`;
  each car does at most 2 tasks; on equal bids, the lower car number wins.

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
