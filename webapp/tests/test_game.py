"""Unit tests for the game rules (no HTTP)."""
import pytest

from app import game


def test_closest_car_wins_a_single_task():
    result = game.play(cars=[(100, 100), (900, 500)], tasks=[(150, 100, 50)], guess=0)
    assert result['winners'] == [0]
    assert result['correct'] is True
    assert result['paths'] == [[0], []]


def test_wrong_guess_is_reported():
    result = game.play(cars=[(100, 100), (900, 500)], tasks=[(150, 100, 50)], guess=1)
    assert result['correct'] is False


def test_points_follow_the_published_formula():
    # one car, 300 m from a task worth 100: 30 s at 10 m/s -> 100 * 0.98**30
    result = game.play(cars=[(0, 0), (1000, 600)], tasks=[(300, 0, 100)], guess=0)
    assert result['scores'][0] == pytest.approx(100 * game.DISCOUNT ** 30, abs=0.01)


def test_a_valuable_task_can_beat_a_closer_cheap_one():
    # car 0 sits next to a cheap task; car 1 is farther from a valuable one.
    # CBBA gives each car the task it values most, and car 1 earns more.
    result = game.play(cars=[(100, 300), (500, 300)],
                       tasks=[(120, 300, 5), (700, 300, 100)], guess=1)
    assert result['winners'] == [1]
    assert result['scores'][1] > result['scores'][0]


def test_equal_bids_go_to_the_lower_car_id():
    # two cars on the same spot bid exactly the same for the only task
    result = game.play(cars=[(200, 200), (200, 200)], tasks=[(300, 200, 40)], guess=0)
    assert result['paths'] == [[0], []]
    assert result['winners'] == [0]


def test_every_task_is_assigned_at_most_once():
    result = game.play(cars=[(0, 0), (500, 300), (1000, 600)],
                       tasks=[(100, 100, 10), (450, 250, 60), (900, 500, 30), (600, 100, 80)],
                       guess=0)
    assigned = [t for path in result['paths'] for t in path]
    assert len(assigned) == len(set(assigned))
    assert result['converged']


def test_a_car_never_takes_more_than_the_limit():
    result = game.play(cars=[(0, 0), (1000, 600)],
                       tasks=[(10 * i, 0, 50) for i in range(1, 7)], guess=0)
    assert all(len(p) <= game.TASKS_PER_CAR for p in result['paths'])


def test_tasks_per_car_is_respected():
    tasks = [(10 * i, 0, 50) for i in range(1, 7)]
    for limit in (1, 3):
        result = game.play(cars=[(0, 0), (1000, 600)], tasks=tasks, guess=0, tasks_per_car=limit)
        assert max(len(p) for p in result['paths']) == limit


def test_faster_cars_lose_less_value():
    # 300 m at 20 m/s = 15 s -> 100 * 0.98**15
    result = game.play(cars=[(0, 0), (1000, 600)], tasks=[(300, 0, 100)], guess=0, speed=20)
    assert result['scores'][0] == pytest.approx(100 * 0.98 ** 15, abs=0.01)


def test_discount_sets_the_value_kept_per_second():
    # 300 m at 10 m/s = 30 s -> 100 * 0.9**30
    result = game.play(cars=[(0, 0), (1000, 600)], tasks=[(300, 0, 100)], guess=0, discount=0.9)
    assert result['scores'][0] == pytest.approx(100 * 0.9 ** 30, abs=0.01)


def test_no_discount_means_full_value():
    result = game.play(cars=[(0, 0), (1000, 600)], tasks=[(300, 0, 100)], guess=0, discount=1.0)
    assert result['scores'][0] == 100


def test_result_reports_the_settings_used():
    result = game.play(cars=[(0, 0), (1000, 600)], tasks=[(300, 0, 100)], guess=0,
                       tasks_per_car=1, speed=25, discount=0.95)
    assert result['settings'] == {'tasks_per_car': 1, 'speed': 25, 'discount': 0.95}


def test_cars_end_at_their_last_task_or_stay_put():
    # car 0 takes the nearby task and ends there; car 1 gets nothing and doesn't move
    result = game.play(cars=[(100, 100), (900, 500)], tasks=[(150, 100, 50)], guess=0)
    assert result['end_positions'] == [[150, 100], [900, 500]]


def test_end_position_follows_the_route_order():
    # the last task in the PATH (visit order) is where the car stops
    result = game.play(cars=[(0, 300), (1000, 0)],
                       tasks=[(100, 300, 50), (200, 300, 50)], guess=0)
    assert result['paths'][0] == [0, 1]
    assert result['end_positions'][0] == [200, 300]


def test_round_one_can_show_conflicts_that_later_resolve():
    # both cars want the valuable middle task at first
    result = game.play(cars=[(400, 300), (600, 300)],
                       tasks=[(500, 300, 100), (100, 300, 10), (900, 300, 10)], guess=0)
    first_bids = result['rounds'][0]['bids']
    claimed = [t for car in first_bids for t in car['bundle']]
    assert claimed.count(0) == 2          # conflict in round 1
    final = [t for p in result['paths'] for t in p]
    assert final.count(0) == 1            # resolved at the end
