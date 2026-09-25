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
| Component | game rules (who wins, points formula, limits, where cars end, player settings) without HTTP | `webapp/tests/test_game.py` | pytest | 15 |
| API | the HTTP contract: valid games, rejected input and settings, error messages, caching headers | `webapp/tests/test_api.py` | pytest + FastAPI TestClient | 43 |
| End-to-end / acceptance | a real browser plays the game against the real server | `webapp/tests/e2e/` | Playwright | 26 |

All levels are run with pytest before every commit (commands in section 8).

## 3. Test design techniques

- **Decision table:** the consensus rules of the paper (what the receiver does, given who the sender and receiver believe won) are one parametrized test with 30 rows (`tests/test_consensus.py`), one row per rule, including the tie rows.
- **Equivalence partitioning and boundary values:** every API limit is tested on both sides of the boundary.
  - 1 car and 6 cars are **rejected**; 2 and 5 are **accepted**.
  - 0 and 11 tasks are rejected; 1 and 10 are accepted.
  - A value of 0 or 101 is rejected; 1 and 100 are accepted.
  - A position of -1 or 1001 m is rejected; the map corners are accepted.
  - A guess of -1 or of a car that doesn't exist is rejected; the last car is accepted.
  - Tasks per car: 0, 11, and more than the tasks sent are rejected; 1 and exactly the number of tasks are accepted.
  - Speed: 0.9 and 51 m/s are rejected; 1 and 50 are accepted. Discount: 0.49 and 1.01 are rejected; 0.5 and 1.0 are accepted.
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
| AC16 | **Given** I change the settings, **then** the rules on the page show the new values | `test_settings_update_the_rules_text` |
| AC17 | **Given** a faster car speed, **when** the race ends, **then** the points follow the new travel time | `test_speed_changes_the_points` |
| AC18 | **Given** no value lost per second, **then** a car earns the task's full value | `test_no_value_lost_gives_full_points` |
| AC19 | **Given** 1 task per car, **then** no car does more than one task and the rest wait for the next mission | `test_one_task_per_car_leaves_tasks_for_later` |
| AC20 | **Given** fewer tasks on the map than my tasks-per-car choice, **then** it is lowered to the number of tasks, a too-high value is explained while I type and set to the maximum when I leave the box, and adding tasks brings my choice back | `test_tasks_per_car_cannot_exceed_the_tasks_on_the_map`, `test_too_many_tasks_per_car_is_set_to_the_maximum`, `test_adding_tasks_brings_back_the_chosen_tasks_per_car` |
| AC21 | **Given** a speed outside 1-50 m/s, **then** I am told the limits and the race cannot start | `test_speed_outside_the_limits_is_refused` |
| AC22 | **Given** I change speed and value lost, **when** I start the race, **then** exactly those values are sent to the server | `test_speed_and_loss_reach_the_server` |
| AC23 | **Given** one setting box holds an invalid value, **when** I change another setting, **then** that change still applies | `test_one_bad_setting_does_not_freeze_the_others` |
| AC24 | **Given** a speed above 50 m/s, **when** I leave the box, **then** it is set to 50 and I am told why | `test_out_of_range_speed_is_corrected_when_leaving_the_box` |

## 5. Traceability: requirement → tests

| Requirement | Tests |
|---|---|
| R1 Each task is done by at most one car | `test_every_task_is_assigned_at_most_once`, `test_convergence_invariants` |
| R2 A car does at most the chosen number of tasks (default 2) | `test_a_car_never_takes_more_than_the_limit`, `test_tasks_per_car_is_respected`, AC19 |
| R3 Points = value × discount^seconds; seconds = distance / speed (defaults 0.98 and 10 m/s) | `test_points_follow_the_published_formula`, `test_agent_score_uses_speed`, `test_faster_cars_lose_less_value`, `test_discount_sets_the_value_kept_per_second`, AC17, AC18 |
| R4 Equal bids go to the lower car number | `test_equal_bids_go_to_the_lower_car_id`, the `tie_*` rows, `test_tie_break.py` |
| R5 Input limits (2-5 cars, 1-10 tasks, values 1-100, on the map) | `test_invalid_input_is_rejected`, `test_values_on_the_limits_are_accepted`, AC6, AC7 |
| R6 The player learns whether the guess was right | `test_wrong_guess_is_reported`, AC2, AC3 |
| R7 Agents converge on the known allocation | `test_simulate_reaches_the_known_allocation`, `test_convergence_invariants` |
| R8 Information crosses at most one hop per round | `test_one_hop_per_round`, `test_multi_hop_network_needs_more_rounds` |
| R9 After a mission, a car waits at its last task (or where it started if it got none) | `test_cars_end_at_their_last_task_or_stay_put`, `test_end_position_follows_the_route_order`, AC10 |
| R10 The leaderboard adds up tasks, points and wins over all missions of a game | AC12, AC13 |
| R11 The player can set tasks per car (1 up to the tasks on the map, max 10), value lost per second (0-50 %) and car speed (1-50 m/s) | `test_invalid_settings_are_rejected`, `test_settings_on_the_limits_are_accepted`, AC16, AC20, AC21 |
| R12 Without settings, a game plays with the defaults; tasks per car never exceeds the tasks sent | `test_settings_default_to_the_original_rules`, `test_default_tasks_per_car_shrinks_to_the_number_of_tasks` |

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
| D11 | A game with 1 task was rejected once tasks per car was validated (default 2 > 1 task) | 10 existing API tests failed after the change | the default adapts to the number of tasks; only an explicit choice is refused; `test_default_tasks_per_car_shrinks_to_the_number_of_tasks` |
| D12 | Building a map from scratch locked tasks per car at 1: it was lowered for the first task and never raised again | `test_unassigned_tasks_wait_for_the_next_mission` failed (3 tasks left instead of 1) | the player's choice is remembered and re-applied as tasks are added; `test_adding_tasks_brings_back_the_chosen_tasks_per_car` |
| D13 | A too-high tasks-per-car value stayed in the box while the game kept using the old one (box "6", game 2); the rules text disagreed with the box | reported by a user on the live site | out-of-range values are corrected when leaving the box, with a note; `test_too_many_tasks_per_car_is_set_to_the_maximum` |
| D14 | One invalid setting silently blocked changes to the others (speed typed as 25, game still used 10 m/s) | same user report, reproduced with real typing | each setting is checked and stored on its own; `test_one_bad_setting_does_not_freeze_the_others` |
| D15 | The first click on a guess after editing a setting was lost: leaving the box refreshed the page and rebuilt the button being clicked | 4 existing browser tests failed after the D13 fix | guess buttons are updated in place; covered by AC17-AC19, AC22 |

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
