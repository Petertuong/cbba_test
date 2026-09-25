"""API tests: the HTTP contract, including every way a request can be rejected."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VALID = {'cars': [{'x': 100, 'y': 100}, {'x': 900, 'y': 500}],
         'tasks': [{'x': 150, 'y': 100, 'value': 50}],
         'guess': 0}


def with_(**changes):
    body = {k: (list(v) if isinstance(v, list) else v) for k, v in VALID.items()}
    body.update(changes)
    return body


def test_valid_game_returns_the_full_result():
    r = client.post('/api/games', json=VALID)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {'rounds', 'converged', 'paths', 'end_positions',
                         'scores', 'winners', 'guess', 'correct', 'settings'}
    assert body['correct'] is True
    assert len(body['scores']) == 2
    assert body['rounds'][0]['bids'][0]['bundle'] == [0]


@pytest.mark.parametrize('name,body', [
    ('one car only', with_(cars=[{'x': 1, 'y': 1}])),
    ('six cars', with_(cars=[{'x': i, 'y': 1} for i in range(6)])),
    ('no tasks', with_(tasks=[])),
    ('eleven tasks', with_(tasks=[{'x': i, 'y': 1, 'value': 5} for i in range(11)])),
    ('car off the map', with_(cars=[{'x': 1001, 'y': 1}, {'x': 1, 'y': 1}])),
    ('negative coordinate', with_(tasks=[{'x': -1, 'y': 1, 'value': 5}])),
    ('task value 0', with_(tasks=[{'x': 1, 'y': 1, 'value': 0}])),
    ('task value 101', with_(tasks=[{'x': 1, 'y': 1, 'value': 101}])),
    ('guess is not a car', with_(guess=2)),
    ('negative guess', with_(guess=-1)),
    ('missing guess', {k: v for k, v in VALID.items() if k != 'guess'}),
    ('text instead of number', with_(cars=[{'x': 'left', 'y': 1}, {'x': 1, 'y': 1}])),
])
def test_invalid_input_is_rejected(name, body):
    r = client.post('/api/games', json=body)
    assert r.status_code == 422, name


@pytest.mark.parametrize('name,body', [
    ('exactly 2 cars', with_(cars=[{'x': 0, 'y': 0}, {'x': 1, 'y': 1}])),
    ('exactly 5 cars', with_(cars=[{'x': 100 * i, 'y': 1} for i in range(5)])),
    ('exactly 1 task', with_(tasks=[{'x': 5, 'y': 5, 'value': 50}])),
    ('exactly 10 tasks', with_(tasks=[{'x': 90 * i, 'y': 300, 'value': 50} for i in range(10)])),
    ('lowest task value', with_(tasks=[{'x': 5, 'y': 5, 'value': 1}])),
    ('highest task value', with_(tasks=[{'x': 5, 'y': 5, 'value': 100}])),
    ('map corners', with_(cars=[{'x': 0, 'y': 0}, {'x': 1000, 'y': 600}],
                          tasks=[{'x': 1000, 'y': 0, 'value': 50}])),
    ('guess the last car', with_(guess=1)),
])
def test_values_on_the_limits_are_accepted(name, body):
    assert client.post('/api/games', json=body).status_code == 200, name


FIVE_TASKS = [{'x': 100 * i, 'y': 100, 'value': 50} for i in range(1, 6)]


def test_settings_default_to_the_original_rules():
    body = client.post('/api/games', json=with_(tasks=FIVE_TASKS)).json()
    assert body['settings'] == {'tasks_per_car': 2, 'speed': 10, 'discount': 0.98}


def test_default_tasks_per_car_shrinks_to_the_number_of_tasks():
    # one task on the map: the default of 2 per car becomes 1 instead of a rejection
    body = client.post('/api/games', json=VALID).json()
    assert body['settings']['tasks_per_car'] == 1


@pytest.mark.parametrize('name,settings', [
    ('0 tasks per car', {'tasks_per_car': 0}),
    ('11 tasks per car', {'tasks_per_car': 11}),
    ('more tasks per car than tasks', {'tasks_per_car': 6}),
    ('speed below 1', {'speed': 0.9}),
    ('speed above 50', {'speed': 51}),
    ('discount below 0.5', {'discount': 0.49}),
    ('discount above 1', {'discount': 1.01}),
])
def test_invalid_settings_are_rejected(name, settings):
    r = client.post('/api/games', json=with_(tasks=FIVE_TASKS, **settings))
    assert r.status_code == 422, name


@pytest.mark.parametrize('name,settings', [
    ('1 task per car', {'tasks_per_car': 1}),
    ('as many per car as there are tasks', {'tasks_per_car': 5}),
    ('slowest speed', {'speed': 1}),
    ('fastest speed', {'speed': 50}),
    ('strongest discount', {'discount': 0.5}),
    ('no discount', {'discount': 1.0}),
])
def test_settings_on_the_limits_are_accepted(name, settings):
    r = client.post('/api/games', json=with_(tasks=FIVE_TASKS, **settings))
    assert r.status_code == 200, name


def test_too_many_tasks_per_car_says_why():
    r = client.post('/api/games', json=with_(tasks=FIVE_TASKS, tasks_per_car=6))
    assert "tasks_per_car can't be more than the number of tasks (5)" in r.text


def test_rejection_says_what_is_wrong():
    r = client.post('/api/games', json=with_(guess=5))
    assert 'guess must be the index of one of the cars (0 to 1)' in r.text


def test_config_matches_the_game_rules():
    cfg = client.get('/api/config').json()
    assert cfg['map_width'] == 1000 and cfg['map_height'] == 600
    assert cfg['cars'] == {'min': 2, 'max': 5}


@pytest.mark.parametrize('path', ['/', '/static/app.js', '/static/style.css'])
def test_browsers_must_check_for_a_new_frontend(path):
    # without this, a browser can mix a cached old app.js with a new page after a deploy
    r = client.get(path)
    assert r.status_code == 200
    assert r.headers.get('cache-control') == 'no-cache'


def test_frontend_is_served():
    r = client.get('/')
    assert r.status_code == 200
    assert 'text/html' in r.headers['content-type']
