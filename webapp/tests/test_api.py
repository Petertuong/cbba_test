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
                         'scores', 'winners', 'guess', 'correct'}
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


def test_rejection_says_what_is_wrong():
    r = client.post('/api/games', json=with_(guess=5))
    assert 'guess must be the index of one of the cars (0 to 1)' in r.text


def test_config_matches_the_game_rules():
    cfg = client.get('/api/config').json()
    assert cfg['map_width'] == 1000 and cfg['map_height'] == 600
    assert cfg['cars'] == {'min': 2, 'max': 5}


def test_frontend_is_served():
    r = client.get('/')
    assert r.status_code == 200
    assert 'text/html' in r.headers['content-type']
