"""Game rules, kept free of any web code so they can be unit tested directly.

A player places cars and tasks on a map, guesses which car will earn the most
points, and CBBA decides who does what. A car earns each task's value,
discounted by how long it took to get there: value * discount ** seconds.
The player can change speed, discount and tasks per car; the constants below
are the defaults.
"""
from cbba.models import Agent, Task
from cbba.simulation import simulate

MAP_WIDTH = 1000.0   # metres
MAP_HEIGHT = 600.0   # metres
CAR_SPEED = 10.0     # metres per second (default)
DISCOUNT = 0.98      # value kept per second of travel (default)
TASKS_PER_CAR = 2    # CBBA bundle limit L_t (default)


def play(cars, tasks, guess, tasks_per_car=TASKS_PER_CAR, speed=CAR_SPEED, discount=DISCOUNT):
    """cars: [(x, y)], tasks: [(x, y, value)], guess: index of a car.
    Inputs are assumed valid (the API layer checks them)."""
    agents = {i: Agent(i, (x, y), len(tasks), len(cars), speed=speed)
              for i, (x, y) in enumerate(cars)}
    task_dict = {j: Task(j, (x, y), value, discount)
                 for j, (x, y, value) in enumerate(tasks)}

    result = simulate(agents, task_dict, tasks_per_car)

    scores = [round(result['scores'][i], 2) for i in range(len(cars))]
    best = max(scores)
    # a tie for first place is possible (e.g. two cars that both earn nothing)
    winners = [i for i, s in enumerate(scores) if s == best]
    paths = [agents[i].path for i in range(len(cars))]
    # where each car waits for the next mission: its last task, or its start if it got none
    end_positions = [list(tasks[path[-1]][:2]) if path else list(cars[i])
                     for i, path in enumerate(paths)]
    return {
        'rounds': [{'bids': strip(r['bids']), 'agreed': strip(r['agreed'])}
                   for r in result['rounds']],
        'converged': result['converged'],
        'paths': paths,
        'end_positions': end_positions,
        'scores': scores,
        'winners': winners,
        'guess': guess,
        'correct': guess in winners,
        # echoed back so the browser animates with exactly the rules the server used
        'settings': {'tasks_per_car': tasks_per_car, 'speed': speed, 'discount': discount},
    }


def strip(snapshots):
    """Per-agent state for the frontend; bids are rounded so the JSON stays small."""
    return [{'bundle': s['bundle'], 'path': s['path'], 'z': s['z'],
             'y': [round(v, 3) for v in s['y']]} for s in snapshots]
