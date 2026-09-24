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


class Car(BaseModel):
    x: float = Field(ge=0, le=game.MAP_WIDTH)
    y: float = Field(ge=0, le=game.MAP_HEIGHT)


class TaskIn(BaseModel):
    x: float = Field(ge=0, le=game.MAP_WIDTH)
    y: float = Field(ge=0, le=game.MAP_HEIGHT)
    value: float = Field(ge=1, le=100)


class GameIn(BaseModel):
    cars: list[Car] = Field(min_length=2, max_length=5)
    tasks: list[TaskIn] = Field(min_length=1, max_length=10)
    guess: int

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
            'cars': {'min': 2, 'max': 5}, 'tasks': {'min': 1, 'max': 10},
            'value': {'min': 1, 'max': 100}}


@app.post('/api/games')
def create_game(body: GameIn):
    return game.play([(c.x, c.y) for c in body.cars],
                     [(t.x, t.y, t.value) for t in body.tasks],
                     body.guess)


@app.get('/')
def index():
    return FileResponse(STATIC / 'index.html')


app.mount('/static', StaticFiles(directory=STATIC), name='static')
