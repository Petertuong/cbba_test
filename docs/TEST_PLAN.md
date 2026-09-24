# Test plan: CBBA core and CBBA Car Race

## 1. Scope

| Component | What it is | In scope |
|---|---|---|
| `cbba/` | Consensus-Based Bundle Algorithm (task allocation), pure Python | yes |
| `webapp/` | CBBA Car Race: a web game built on the core (FastAPI + browser UI) | yes |

**Out of scope:** performance and load, security testing, browsers other than Chromium, mobile devices.

## 2. Test levels

| Level | What is checked | Where | Tool | Count |
|---|---|---|---|---|
| Unit | bundle building, the consensus decision table, tie-breaking, distance, scoring | `tests/` | pytest | 58 (whole core suite) |
| Integration | several agents running full rounds until agreement; invariants hold at the end | `tests/test_integration.py`, `tests/test_simulation.py` | pytest | included above |
| Component | game rules (who wins, points formula, limits, where cars end) without HTTP | `webapp/tests/test_game.py` | pytest | 10 |
| API | the HTTP contract: valid games, rejected input, error messages, caching headers | `webapp/tests/test_api.py` | pytest + FastAPI TestClient | 27 |
| End-to-end / acceptance | a real browser plays the game against the real server | `webapp/tests/e2e/` | Playwright | 15 |

All levels are run with pytest before every commit (commands in section 8).

## 3. Test design techniques

- **Decision table:** the consensus rules of the paper (what the receiver does, given who the sender and receiver believe won) are one parametrized test with 30 rows (`tests/test_consensus.py`), one row per rule, including the tie rows.
- **Equivalence partitioning and boundary values:** every API limit is tested on both sides of the boundary.
  - 1 car and 6 cars are **rejected**; 2 and 5 are **accepted**.
  - 0 and 11 tasks are rejected; 1 and 10 are accepted.
  - A value of 0 or 101 is rejected; 1 and 100 are accepted.
  - A position of -1 or 1001 m is rejected; the map corners are accepted.
  - A guess of -1 or of a car that doesn't exist is rejected; the last car is accepted.
- **Invariant (property) checks:** after any game, each task has at most one owner, no car exceeds its task limit, and all agents agree.
- **Known-answer (oracle) tests:** hand-computed expected results, e.g. a task worth 100 that is 300 m away earns `100 × 0.98^30`.
- **Fault injection:** the E2E suite fakes a server rejection (`page.route`) to test the error path the player sees.
- **Mutation check:** a fixed defect was re-introduced on purpose to confirm a test fails (see D6).

## 4. Acceptance scenarios

Written from the player's side, each automated in `webapp/tests/e2e/test_ui.py`.

| ID | Scenario | Test |
|---|---|---|
| AC1 | **Given** the page opens, **when** no car is guessed yet, **then** the race cannot start | `test_example_layout_loads_and_race_needs_a_guess` |
| AC2 | **Given** the example map, **when** I guess the car that earns the most and start the race, **then** I am told I called it, and the scoreboard shows each car's tasks and points | `test_correct_guess_on_the_example` |
| AC3 | **Given** a wrong guess, **when** the race ends, **then** I am told which car won instead | `test_wrong_guess_is_announced` |
| AC4 | **Given** an empty map, **when** I place my own cars and a task and start, **then** the game is played on my layout | `test_player_builds_a_map_from_scratch` |
| AC5 | **Given** I picked a car, **when** I remove that car, **then** my guess is cleared and I must pick again | `test_clicking_a_car_removes_it_and_its_guess` |
| AC6 | **Given** 5 cars, **when** I try to add a sixth, **then** I am told the limit | `test_car_limit_is_enforced` |
| AC7 | **Given** a task value outside 1-100, **when** I place a task, **then** it is refused with a reason | `test_invalid_task_value_is_refused` |
| AC8 | **Given** the server rejects a game, **when** I start the race, **then** I see why | `test_server_rejection_is_shown_to_the_player` |
| AC9 | **Given** the race animation is running, **when** I press Skip, **then** I go straight to the result | `test_animation_plays_rounds_and_can_be_skipped` |
| AC10 | **Given** a finished mission, **when** I start the next one, **then** each car waits where it finished and the completed tasks are gone | `test_next_mission_starts_where_the_cars_finished` |
| AC11 | **Given** more tasks than the cars can take, **when** the next mission starts, **then** the unassigned tasks are still on the map | `test_unassigned_tasks_wait_for_the_next_mission` |
| AC12 | **Given** a finished mission, **then** the leaderboard ranks the cars by tasks done, then points, and shows how many of my guesses were right | `test_leaderboard_after_one_mission` |
| AC13 | **Given** several missions, **then** the leaderboard adds them up, and cars with equal tasks are ordered by points | `test_leaderboard_adds_up_over_missions` |
| AC14 | **Given** a game in progress, **when** I try to add or remove a car, **then** I am told the cars stay fixed | `test_cars_are_fixed_during_a_game` |
| AC15 | **Given** a game in progress, **when** I press New game, **then** the map and leaderboard are reset | `test_new_game_resets_everything` |

## 5. Traceability: requirement → tests

| Requirement | Tests |
|---|---|
| R1 Each task is done by at most one car | `test_every_task_is_assigned_at_most_once`, `test_convergence_invariants` |
| R2 A car does at most 2 tasks | `test_a_car_never_takes_more_than_the_limit` |
| R3 Points = value × 0.98^seconds, at 10 m/s | `test_points_follow_the_published_formula`, `test_agent_score_uses_speed` |
| R4 Equal bids go to the lower car number | `test_equal_bids_go_to_the_lower_car_id`, the `tie_*` rows, `test_tie_break.py` |
| R5 Input limits (2-5 cars, 1-10 tasks, values 1-100, on the map) | `test_invalid_input_is_rejected`, `test_values_on_the_limits_are_accepted`, AC6, AC7 |
| R6 The player learns whether the guess was right | `test_wrong_guess_is_reported`, AC2, AC3 |
| R7 Agents converge on the known allocation | `test_simulate_reaches_the_known_allocation`, `test_convergence_invariants` |
| R8 Information crosses at most one hop per round | `test_one_hop_per_round`, `test_multi_hop_network_needs_more_rounds` |
| R9 After a mission, a car waits at its last task (or where it started if it got none) | `test_cars_end_at_their_last_task_or_stay_put`, `test_end_position_follows_the_route_order`, AC10 |
| R10 The leaderboard adds up tasks, points and wins over all missions of a game | AC12, AC13 |

## 6. Defects found

| ID | Defect | How it was found | Fix and regression test |
|---|---|---|---|
| D1 | A message carried its sender's timestamp one round out of date | reasoning about a redundant field; confirmed by `test_one_hop_per_round` failing after the change | stamp before copying in `produce_message` |
| D2 | Two agents with exactly equal bids both kept the task forever | code review against the paper; reproduced with two agents at the same spot | lower id wins; `test_tie_break.py`, 4 decision-table rows |
| D3 | Distance ignored the z coordinate | new requirement (3D); failing test first | `math.dist`; `test_geometry.py` |
| D4 | 5 graph-search tests out of date after an API change | full test run | tests updated to the new signature |
| D5 | Importing `cbba/main.py` crashed (experiment code at module level) | import check | code moved under `if __name__ == "__main__"` |
| D6 | The empty result card showed before any game (a CSS `display` rule overrode the `hidden` attribute) | manual exploratory test in the browser | global `[hidden]` rule; AC1 now asserts the card is hidden. Re-introducing the bug makes AC1 fail |
| D7 | "Skip animation" was unreachable: it sat inside the card hidden during the animation | code review | button moved next to the round status; AC9 |
| D8 | Tests fail in shells that source ROS 2 (ROS's pytest plugin needs `yaml`) | local run | run with `env -u PYTHONPATH` |
| D9 | After a deploy, a browser could combine a cached old `app.js` with the new page: no leaderboard, and "Next mission" did nothing | reported by a user on the live site right after a release; the server sent no caching instructions | server sends `Cache-Control: no-cache` for the page and its files; `test_browsers_must_check_for_a_new_frontend` |
| D10 | When every task was done, the next mission looked frozen (empty map, disabled button, no hint) | same user report | the status line tells the player to place new tasks; AC10 asserts the message |

## 7. Entry and exit criteria

- **Entry:** the code builds, and the test environment installs from `webapp/requirements-dev.txt` (the server alone needs only `webapp/requirements.txt`).
- **Exit (per change):** every test level green, no open defect of high severity, and core coverage not lower than before (currently 81% core, 100% web backend).

## 8. How to run

```bash
python3 -m venv .venv && .venv/bin/pip install -e . -r webapp/requirements-dev.txt
.venv/bin/playwright install chromium
env -u PYTHONPATH .venv/bin/python -m pytest tests                       # core
cd webapp && env -u PYTHONPATH ../.venv/bin/python -m pytest tests       # game, API, end-to-end
```
