"""End-to-end: a real browser plays the game against the real server."""
import json
import re

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture
def game(page: Page, base_url):
    # reduced motion: the app skips the animation and shows the result at once
    page.emulate_media(reduced_motion='reduce')
    page.goto(base_url)
    return page


def click_map(page: Page, x, y):
    """Click the map at map coordinates (metres); the map is 1000 x 600."""
    box = page.get_by_test_id('map').bounding_box()
    page.mouse.click(box['x'] + x / 1000 * box['width'], box['y'] + y / 600 * box['height'])


def test_example_layout_loads_and_race_needs_a_guess(game: Page):
    expect(game.get_by_test_id('phase')).to_have_text('3 cars · 5 tasks · pick a car to guess')
    expect(game.get_by_test_id('run')).to_be_disabled()
    expect(game.get_by_test_id('result')).to_be_hidden()
    game.get_by_test_id('guess-1').click()
    expect(game.get_by_test_id('run')).to_be_enabled()


def test_correct_guess_on_the_example(game: Page):
    # on the example layout, Car 3 earns the most (T4 -> T5, 82.46 points)
    game.get_by_test_id('guess-3').click()
    game.get_by_test_id('run').click()
    expect(game.get_by_test_id('verdict')).to_have_text('You called it! Car 3 wins.')
    expect(game.get_by_test_id('score-3')).to_contain_text('T4 → T5')
    expect(game.get_by_test_id('score-3')).to_contain_text('82.46')
    expect(game.get_by_test_id('scoreboard').locator('tr')).to_have_count(3)


def test_wrong_guess_is_announced(game: Page):
    game.get_by_test_id('guess-1').click()
    game.get_by_test_id('run').click()
    expect(game.get_by_test_id('verdict')).to_have_text('Not this time: Car 3 wins.')


def test_player_builds_a_map_from_scratch(game: Page):
    game.get_by_test_id('clear').click()
    expect(game.get_by_test_id('phase')).to_have_text('0 cars · 0 tasks · pick a car to guess')
    click_map(game, 100, 300)                      # car 1
    click_map(game, 900, 300)                      # car 2
    game.get_by_test_id('tool-task').click()
    game.get_by_test_id('task-value').fill('80')
    click_map(game, 150, 300)                      # task next to car 1
    expect(game.get_by_test_id('phase')).to_have_text('2 cars · 1 tasks · pick a car to guess')
    game.get_by_test_id('guess-1').click()
    game.get_by_test_id('run').click()
    expect(game.get_by_test_id('verdict')).to_have_text('You called it! Car 1 wins.')
    expect(game.get_by_test_id('score-2')).to_contain_text('none')


def test_clicking_a_car_removes_it_and_its_guess(game: Page):
    game.get_by_test_id('guess-3').click()
    game.get_by_test_id('car-3').click()
    expect(game.get_by_test_id('guesses').get_by_role('radio')).to_have_count(2)
    expect(game.get_by_test_id('run')).to_be_disabled()


def test_car_limit_is_enforced(game: Page):
    click_map(game, 300, 50)
    click_map(game, 600, 50)                        # 5 cars now
    click_map(game, 800, 50)
    expect(game.get_by_test_id('error')).to_have_text('At most 5 cars.')


def test_invalid_task_value_is_refused(game: Page):
    game.get_by_test_id('tool-task').click()
    game.get_by_test_id('task-value').fill('500')
    click_map(game, 500, 400)
    expect(game.get_by_test_id('error')).to_have_text('Task value must be between 1 and 100.')


def test_server_rejection_is_shown_to_the_player(game: Page):
    # simulate the server refusing the game, to check the error path
    game.route('**/api/games', lambda route: route.fulfill(
        status=422, content_type='application/json',
        body=json.dumps({'detail': [{'msg': 'guess must be the index of one of the cars'}]})))
    game.get_by_test_id('guess-1').click()
    game.get_by_test_id('run').click()
    expect(game.get_by_test_id('error')).to_contain_text('The server rejected this game')


def test_animation_plays_rounds_and_can_be_skipped(page: Page, base_url):
    page.goto(base_url)                              # normal motion this time
    page.get_by_test_id('guess-3').click()
    page.get_by_test_id('run').click()
    expect(page.get_by_test_id('phase')).to_have_text(re.compile(r'Round 1 of \d+'))
    page.get_by_test_id('skip').click()
    expect(page.get_by_test_id('verdict')).to_have_text('You called it! Car 3 wins.')
    expect(page.get_by_test_id('skip')).to_be_hidden()


def test_play_again_keeps_the_layout(game: Page):
    game.get_by_test_id('guess-2').click()
    game.get_by_test_id('run').click()
    expect(game.get_by_test_id('result')).to_be_visible()
    game.get_by_test_id('again').click()
    expect(game.get_by_test_id('result')).to_be_hidden()
    expect(game.get_by_test_id('phase')).to_have_text('3 cars · 5 tasks · you picked Car 2')
