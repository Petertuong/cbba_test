"""HTTP layer: validates input, calls the game rules, serves the frontend.

Run:  uvicorn app.main:app --reload    (from the webapp/ folder)
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from . import game

STATIC = Path(__file__).resolve().parent.parent / 'static'

app = FastAPI(title='CBBA Car Race')


@app.middleware('http')
async def always_check_for_new_frontend(request, call_next):
    """Without caching instructions a browser may reuse an old app.js with a new
    index.html after a deploy (a page with buttons its script doesn't know).
    'no-cache' makes the browser ask every time; unchanged files still come back
    as a cheap '304 Not Modified'."""
    response = await call_next(request)
    if not request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-cache'
    return response


class Car(BaseModel):
    x: float = Field(ge=0, le=game.MAP_WIDTH)
    y: float = Field(ge=0, le=game.MAP_HEIGHT)


class TaskIn(BaseModel):
    x: float = Field(ge=0, le=game.MAP_WIDTH)
    y: float = Field(ge=0, le=game.MAP_HEIGHT)
    value: float = Field(ge=1, le=100)


MAX_TASKS = 10


class GameIn(BaseModel):
    cars: list[Car] = Field(min_length=2, max_length=5)
    tasks: list[TaskIn] = Field(min_length=1, max_length=MAX_TASKS)
    guess: int
    # optional settings; leaving them out plays with the default rules
    tasks_per_car: int | None = Field(None, ge=1, le=MAX_TASKS)  # default: see below
    speed: float = Field(game.CAR_SPEED, ge=1, le=50)           # m/s
    discount: float = Field(game.DISCOUNT, ge=0.5, le=1.0)      # value kept per second

    @model_validator(mode='after')
    def tasks_per_car_fits_the_map(self):
        if self.tasks_per_car is None:
            # not chosen by the player: the default, but never more than there are tasks
            self.tasks_per_car = min(game.TASKS_PER_CAR, len(self.tasks))
        elif self.tasks_per_car > len(self.tasks):
            raise ValueError("tasks_per_car can't be more than the number of tasks (%d)"
                             % len(self.tasks))
        return self

    @model_validator(mode='after')
    def guess_is_a_car(self):
        if not 0 <= self.guess < len(self.cars):
            raise ValueError('guess must be the index of one of the cars (0 to %d)'
                             % (len(self.cars) - 1))
        return self


@app.get('/api/config')
def config():
    """Rules the frontend needs to draw the map and explain the scoring."""
    return {'map_width': game.MAP_WIDTH, 'map_height': game.MAP_HEIGHT,
            'car_speed': game.CAR_SPEED, 'discount': game.DISCOUNT,
            'tasks_per_car': game.TASKS_PER_CAR,
            'cars': {'min': 2, 'max': 5}, 'tasks': {'min': 1, 'max': MAX_TASKS},
            'value': {'min': 1, 'max': 100},
            'limits': {'tasks_per_car': {'min': 1, 'max': MAX_TASKS},
                       'speed': {'min': 1, 'max': 50},
                       'discount': {'min': 0.5, 'max': 1.0}}}


@app.post('/api/games')
def create_game(body: GameIn):
    return game.play([(c.x, c.y) for c in body.cars],
                     [(t.x, t.y, t.value) for t in body.tasks],
                     body.guess,
                     tasks_per_car=body.tasks_per_car, speed=body.speed, discount=body.discount)


@app.get('/')
def index():
    return FileResponse(STATIC / 'index.html')


app.mount('/static', StaticFiles(directory=STATIC), name='static')
