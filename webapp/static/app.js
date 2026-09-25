// CBBA Car Race: frontend.
// The server decides everything (allocation, points, winner); this file only
// lets the player place things, sends the game to the API and replays the result.
// Players see 1-based numbers ("Car 1"); the API uses 0-based indexes.

const SVGNS = 'http://www.w3.org/2000/svg';
const COLOR_VARS = ['--c0', '--c1', '--c2', '--c3', '--c4'];
const LIMITS = { cars: 5, tasks: 10 };

// example layout so the page is playable straight away
const example = () => ({
  cars: [{ x: 120, y: 480 }, { x: 520, y: 110 }, { x: 880, y: 470 }],
  tasks: [
    { x: 250, y: 340, value: 40 }, { x: 430, y: 290, value: 90 }, { x: 700, y: 200, value: 30 },
    { x: 820, y: 330, value: 60 }, { x: 560, y: 520, value: 100 },
  ],
});

const state = {
  ...example(),
  guess: null,
  // campaign: several missions with the same cars; the leaderboard adds them up
  mission: 1,
  board: null,     // per car {tasks, points, wins}; null until the first mission ends
  guesses: { right: 0, total: 0 },
  tool: 'car',
  // race settings chosen by the player (the server checks them again)
  settings: { tasksPerCar: 2, lossPct: 2, speed: 10 },
  wantedTasksPerCar: 2,   // what the player chose; the map may only allow fewer
  result: null,
  runId: 0,        // bumped to cancel a running animation
};

const $ = id => document.getElementById(id);
const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const carColor = i => css(COLOR_VARS[i % COLOR_VARS.length]);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function el(tag, attrs, parent) {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}

// ------------------------------------------------------------------ drawing
// view = { snap?: per-car {bundle, path}, carPos?: [{x,y}], done?: task set, trail?: bool }

function draw(view = {}) {
  const svg = $('map');
  svg.textContent = '';
  for (let x = 100; x < 1000; x += 100) el('line', { x1: x, y1: 0, x2: x, y2: 600, stroke: css('--grid'), 'stroke-width': 1 }, svg);
  for (let y = 100; y < 600; y += 100) el('line', { x1: 0, y1: y, x2: 1000, y2: y, stroke: css('--grid'), 'stroke-width': 1 }, svg);
  const scale = el('text', { x: 992, y: 590, 'text-anchor': 'end', fill: css('--muted'), 'font-size': 13, 'font-family': 'JetBrains Mono, monospace' }, svg);
  scale.textContent = 'grid = 100 m';

  const snap = view.snap;
  // planned routes
  if (snap) snap.forEach((car, i) => {
    if (!car.path.length) return;
    const pts = [state.cars[i]].concat(car.path.map(t => state.tasks[t]));
    el('polyline', { points: pts.map(p => `${p.x},${p.y}`).join(' '), fill: 'none', stroke: carColor(i), 'stroke-width': 4, 'stroke-linejoin': 'round', 'stroke-linecap': 'round', 'stroke-opacity': view.carPos ? 0.35 : 0.8 }, svg);
  });

  // tasks: white = unclaimed, car colour = claimed, red = claimed by several cars
  state.tasks.forEach((t, j) => {
    const owners = snap ? snap.map((c, i) => c.bundle.includes(j) ? i : -1).filter(i => i >= 0) : [];
    const conflict = owners.length > 1;
    const fill = conflict ? css('--conflict') : owners.length ? carColor(owners[0]) : css('--free');
    const g = el('g', { 'data-kind': 'task', 'data-index': j, 'data-testid': `task-${j + 1}`, style: 'cursor:pointer' }, svg);
    if (conflict) el('circle', { cx: t.x, cy: t.y, r: 25, fill: 'none', stroke: css('--conflict'), 'stroke-width': 3, 'stroke-dasharray': '5 4' }, g);
    const doneTask = view.done && view.done.has(j);
    el('circle', { cx: t.x, cy: t.y, r: 18, fill, 'fill-opacity': doneTask ? 0.35 : 1, stroke: owners.length ? fill : css('--muted'), 'stroke-width': 2 }, g);
    const v = el('text', { x: t.x, y: t.y + 5, 'text-anchor': 'middle', 'font-size': 14, 'font-weight': 700, 'font-family': 'Figtree, sans-serif', fill: owners.length && !doneTask ? '#fff' : css('--ink') }, g);
    v.textContent = doneTask ? '✓' : Math.round(t.value);
    const lab = el('text', { x: t.x, y: t.y - 25, 'text-anchor': 'middle', 'font-size': 12, 'font-weight': 600, fill: conflict ? css('--conflict') : css('--muted'), 'font-family': 'Figtree, sans-serif' }, g);
    lab.textContent = conflict ? `T${j + 1} conflict` : `T${j + 1}`;
  });

  // cars
  state.cars.forEach((c, i) => {
    const p = view.carPos ? view.carPos[i] : c;
    const g = el('g', { 'data-kind': 'car', 'data-index': i, 'data-testid': `car-${i + 1}`, style: 'cursor:pointer' }, svg);
    el('rect', { x: p.x - 20, y: p.y - 13, width: 40, height: 26, rx: 8, fill: carColor(i), stroke: css('--surface'), 'stroke-width': 2.5 }, g);
    const n = el('text', { x: p.x, y: p.y + 5, 'text-anchor': 'middle', 'font-size': 14, 'font-weight': 700, fill: '#fff', 'font-family': 'Figtree, sans-serif' }, g);
    n.textContent = i + 1;
  });
}

// ---------------------------------------------------------------- settings

const SETTING_LIMITS = { tasksPerCar: [1, LIMITS.tasks], lossPct: [0, 50], speed: [1, 50] };

// never more than the tasks on the map; with an empty map, only the overall limit applies
function maxTasksPerCar() { return state.tasks.length ? Math.min(LIMITS.tasks, state.tasks.length) : LIMITS.tasks; }

// read the three inputs. Each valid value is stored on its own, so one bad box
// never blocks the others. Returns the first problem, or '' when all are valid.
function readSettings() {
  const perCar = Number($('setting-tasks-per-car').value);
  const loss = Number($('setting-loss').value);
  const speed = Number($('setting-speed').value);
  const problems = [];
  if (Number.isInteger(perCar) && perCar >= 1 && perCar <= maxTasksPerCar()) state.settings.tasksPerCar = perCar;
  else problems.push(`Tasks per car must be a whole number from 1 to ${maxTasksPerCar()} (the tasks on the map).`);
  if (Number.isFinite(loss) && loss >= SETTING_LIMITS.lossPct[0] && loss <= SETTING_LIMITS.lossPct[1]) state.settings.lossPct = loss;
  else problems.push('Value lost per second must be between 0 and 50 %.');
  if (Number.isFinite(speed) && speed >= SETTING_LIMITS.speed[0] && speed <= SETTING_LIMITS.speed[1]) state.settings.speed = speed;
  else problems.push('Car speed must be between 1 and 50 m/s.');
  return problems[0] || '';
}

// when the player leaves a box (Tab, Enter, click elsewhere): move an out-of-range
// value to the nearest allowed one and say so, so the box always shows what is used
const SETTING_BOXES = {
  'setting-tasks-per-car': { name: 'Tasks per car', unit: '', whole: true,
    range: () => [1, maxTasksPerCar()], why: max => state.tasks.length ? ` (the tasks on the map)` : '' },
  'setting-loss': { name: 'Value lost per second', unit: ' %', range: () => SETTING_LIMITS.lossPct, why: () => '' },
  'setting-speed': { name: 'Car speed', unit: ' m/s', range: () => SETTING_LIMITS.speed, why: () => '' },
};

function onSettingCommit(evt) {
  const box = SETTING_BOXES[evt.target.id], input = evt.target;
  const [min, max] = box.range();
  let v = Number(input.value), note = '';
  if (input.value.trim() === '' || !Number.isFinite(v)) {
    v = min; note = `${box.name} needs a number, so it was set to ${min}.`;
  } else if (v > max) {
    note = `${box.name} can be at most ${max}${box.unit}${box.why(max)}, so it was set to ${max}.`; v = max;
  } else if (v < min) {
    note = `${box.name} must be at least ${min}${box.unit}, so it was set to ${min}.`; v = min;
  } else if (box.whole && !Number.isInteger(v)) {
    v = Math.round(v); note = `${box.name} must be a whole number, so it was set to ${v}.`;
  }
  input.value = v;
  if (evt.target.id === 'setting-tasks-per-car') state.wantedTasksPerCar = v;
  $('settings-note').textContent = note;
  $('settings-note').hidden = !note;
  onSettingChange(evt);
}

// keep "tasks per car" within the tasks on the map, and the rules text in step
function syncSettings() {
  const max = maxTasksPerCar(), input = $('setting-tasks-per-car');
  input.max = max;
  $('tasks-per-car-max').textContent = `max ${max}`;
  ['setting-tasks-per-car', 'setting-loss', 'setting-speed'].forEach(id => { $(id).disabled = !editing(); });
  const { tasksPerCar, lossPct, speed } = state.settings;
  $('rule-loss').textContent = `${lossPct}% per second`;
  $('rule-speed').textContent = `${speed} m/s`;
  $('rule-per-car').textContent = `${tasksPerCar} task${tasksPerCar === 1 ? '' : 's'}`;
}

// after the number of tasks changes: use the player's choice, or fewer if the map
// has fewer tasks (adding tasks again brings the choice back)
function fitTasksPerCar() {
  const input = $('setting-tasks-per-car');
  input.value = state.tasks.length ? Math.min(state.wantedTasksPerCar, maxTasksPerCar()) : state.wantedTasksPerCar;
}

function onSettingChange(evt) {
  if (evt.type === 'input') $('settings-note').hidden = true;   // an old correction note is stale
  if (evt.target.id === 'setting-tasks-per-car') {
    const v = Number(evt.target.value);
    if (Number.isInteger(v) && v >= 1 && v <= LIMITS.tasks) state.wantedTasksPerCar = v;
  }
  const problem = readSettings();
  showError(problem);
  syncSettings();
  refresh();
}

// ----------------------------------------------------------------- editing

function editing() { return state.result === null; }
function campaignStarted() { return state.board !== null; }
const CARS_FIXED = 'The cars stay the same for the whole game, so the leaderboard is fair. Press New game to change them.';

function setTool(tool) {
  state.tool = tool;
  $('tool-car').setAttribute('aria-pressed', tool === 'car');
  $('tool-task').setAttribute('aria-pressed', tool === 'task');
  $('hint').textContent = tool === 'car'
    ? 'Click the map to place a car. Click a car or task to remove it.'
    : 'Click the map to place a task with the value set above. Click a car or task to remove it.';
}

function toMap(evt) {
  const svg = $('map'), pt = svg.createSVGPoint();
  pt.x = evt.clientX; pt.y = evt.clientY;
  const p = pt.matrixTransform(svg.getScreenCTM().inverse());
  return { x: Math.round(Math.min(1000, Math.max(0, p.x))), y: Math.round(Math.min(600, Math.max(0, p.y))) };
}

function onMapClick(evt) {
  if (!editing()) return;
  showError('');
  const hit = evt.target.closest('[data-kind]');
  if (hit) return removeItem(hit.dataset.kind, +hit.dataset.index);
  const p = toMap(evt);
  if (state.tool === 'car') {
    if (campaignStarted()) return showError(CARS_FIXED);
    if (state.cars.length >= LIMITS.cars) return showError(`At most ${LIMITS.cars} cars.`);
    state.cars.push(p);
  } else {
    const value = Number($('task-value').value);
    if (!Number.isFinite(value) || value < 1 || value > 100) return showError('Task value must be between 1 and 100.');
    if (state.tasks.length >= LIMITS.tasks) return showError(`At most ${LIMITS.tasks} tasks.`);
    state.tasks.push({ ...p, value });
    fitTasksPerCar();
  }
  refresh();
}

function removeItem(kind, i) {
  if (kind === 'car') {
    if (campaignStarted()) return showError(CARS_FIXED);
    state.cars.splice(i, 1);
    // keep the guess pointing at the same car
    if (state.guess === i) state.guess = null;
    else if (state.guess > i) state.guess -= 1;
  } else {
    state.tasks.splice(i, 1);
    fitTasksPerCar();
  }
  refresh();
}

function renderGuesses() {
  const box = $('guesses');
  box.setAttribute('role', 'radiogroup');
  box.setAttribute('aria-label', 'Car you think will win');
  if (!state.cars.length) { box.innerHTML = '<span class="empty">Place at least two cars.</span>'; return; }
  // same cars as before: update the buttons in place. Rebuilding them would swallow a
  // click that is in progress (leaving a settings box refreshes the page mid-click).
  const buttons = box.querySelectorAll('[data-car]');
  if (buttons.length === state.cars.length) {
    buttons.forEach((b, i) => { b.setAttribute('aria-checked', state.guess === i); b.disabled = !editing(); });
    return;
  }
  box.innerHTML = state.cars.map((_, i) =>
    `<button type="button" class="guess" role="radio" aria-checked="${state.guess === i}" data-car="${i}" data-testid="guess-${i + 1}" ${editing() ? '' : 'disabled'}>
       <i style="background:${carColor(i)}"></i>Car ${i + 1}</button>`).join('');
}

function refresh() {
  renderGuesses();
  syncSettings();
  const settingsProblem = readSettings();
  if (settingsProblem) showError(settingsProblem);   // keep explaining why the race can't start
  const ready = state.cars.length >= 2 && state.tasks.length >= 1 && state.guess !== null && !settingsProblem;
  $('run').disabled = !ready || !editing();
  $('map').classList.toggle('locked', !editing());
  if (editing()) {
    // a new mission with every task done looks frozen, so say what to do next
    const waiting = campaignStarted() && state.tasks.length === 0;
    $('phase').textContent = waiting
      ? `Mission ${state.mission} · the cars are waiting where they finished: click the map to place new tasks`
      : `Mission ${state.mission} · ${state.cars.length} cars · ${state.tasks.length} tasks` +
        (state.guess === null ? ' · pick a car to guess' : ` · you picked Car ${state.guess + 1}`);
    draw();
  }
}

function showError(msg) { $('error').textContent = msg; $('error').hidden = !msg; }

// -------------------------------------------------------------------- race

async function run() {
  showError('');
  const body = {
    cars: state.cars.map(({ x, y }) => ({ x, y })),
    tasks: state.tasks.map(({ x, y, value }) => ({ x, y, value })),
    guess: state.guess,
    tasks_per_car: state.settings.tasksPerCar,
    speed: state.settings.speed,
    discount: Number((1 - state.settings.lossPct / 100).toFixed(4)),   // 2 % lost -> 0.98 kept
  };
  let res;
  try {
    res = await fetch('/api/games', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  } catch (e) {
    return showError('Could not reach the game server. Is it running?');
  }
  const data = await res.json();
  if (!res.ok) {
    const detail = Array.isArray(data.detail) ? data.detail.map(d => d.msg).join('; ') : data.detail;
    return showError(`The server rejected this game: ${detail}`);
  }
  state.result = data;
  refresh();
  play(data);
}

async function play(result) {
  const id = ++state.runId;
  const alive = () => id === state.runId;
  $('result').hidden = true;
  $('skip').hidden = false;
  if (reducedMotion()) return finish(result);

  const n = result.rounds.length;
  for (let r = 0; r < n && alive(); r++) {
    $('phase').textContent = `Round ${r + 1} of ${n}: every car bids for the tasks it values most`;
    draw({ snap: result.rounds[r].bids });
    await sleep(1300);
    if (!alive()) return;
    $('phase').textContent = `Round ${r + 1} of ${n}: cars swap bids, the highest bid keeps each task`;
    draw({ snap: result.rounds[r].agreed });
    await sleep(1300);
  }
  if (!alive()) return;
  await drive(result, alive);
  if (alive()) finish(result);
}

// cars follow their final paths; points are counted as each task is reached
function drive(result, alive) {
  const speed = result.settings.speed, disc = result.settings.discount;
  const legs = result.paths.map((path, i) => {
    let t = 0, from = state.cars[i];
    return path.map(j => {
      const to = state.tasks[j], dt = Math.hypot(to.x - from.x, to.y - from.y) / speed;
      const leg = { from, to, j, start: t, end: t + dt };
      t += dt; from = to;
      return leg;
    });
  });
  const total = Math.max(1, ...legs.flat().map(l => l.end));
  const duration = Math.min(6000, Math.max(1800, total * 40));
  const snap = result.paths.map(p => ({ bundle: p, path: p }));

  return new Promise(resolve => {
    const t0 = performance.now();
    function frame(now) {
      if (!alive()) return resolve();
      const t = Math.min(1, (now - t0) / duration) * total;
      const done = new Set(), points = result.paths.map(() => 0);
      const carPos = state.cars.map((c, i) => {
        let pos = c;
        for (const l of legs[i]) {
          if (t >= l.end) { done.add(l.j); points[i] += state.tasks[l.j].value * disc ** l.end; pos = l.to; }
          else if (t > l.start) { const f = (t - l.start) / (l.end - l.start); pos = { x: l.from.x + f * (l.to.x - l.from.x), y: l.from.y + f * (l.to.y - l.from.y) }; break; }
          else break;
        }
        return pos;
      });
      $('phase').textContent = `Driving · ${Math.round(t)} s · ` + points.map((p, i) => `Car ${i + 1}: ${p.toFixed(1)}`).join(' · ');
      draw({ snap, carPos, done });
      if (t < total) requestAnimationFrame(frame); else resolve();
    }
    requestAnimationFrame(frame);
  });
}

function finish(result) {
  state.runId++;  // stop any animation still running
  if (!result.recorded) { result.recorded = true; recordMission(result); }
  draw({ snap: result.paths.map(p => ({ bundle: p, path: p })) });
  const names = result.winners.map(i => `Car ${i + 1}`);
  const winnerText = names.length > 1 ? `${names.join(' and ')} tie for first` : `${names[0]} wins`;
  const verdict = $('verdict');
  verdict.textContent = result.correct ? `You called it! ${winnerText}.` : `Not this time: ${winnerText}.`;
  verdict.className = result.correct ? 'win' : 'lose';
  $('phase').textContent = result.converged
    ? `The cars agreed after ${result.rounds.length} rounds.`
    : `The cars had not fully agreed after ${result.rounds.length} rounds.`;
  $('scoreboard').innerHTML = result.scores.map((s, i) => `
    <tr class="${result.winners.includes(i) ? 'best' : ''}" data-testid="score-${i + 1}">
      <td><i style="background:${carColor(i)}"></i>Car ${i + 1}${i === result.guess ? ' (your pick)' : ''}</td>
      <td>${result.paths[i].length ? result.paths[i].map(j => 'T' + (j + 1)).join(' → ') : 'none'}</td>
      <td class="num">${s.toFixed(2)}</td>
    </tr>`).join('');
  $('skip').hidden = true;
  $('result').hidden = false;
}

// -------------------------------------------------------------- campaign

function recordMission(result) {
  if (!state.board) state.board = state.cars.map(() => ({ tasks: 0, points: 0, wins: 0 }));
  result.paths.forEach((path, i) => {
    state.board[i].tasks += path.length;
    state.board[i].points += result.scores[i];
    if (result.winners.includes(i)) state.board[i].wins += 1;
  });
  state.guesses.total += 1;
  if (result.correct) state.guesses.right += 1;
  renderBoard();
}

// most tasks first; points, then car number, break ties
function renderBoard() {
  const box = $('leaderboard');
  if (!state.board) { box.hidden = true; return; }
  const order = state.board.map((b, i) => ({ ...b, car: i }))
    .sort((a, b) => b.tasks - a.tasks || b.points - a.points || a.car - b.car);
  $('board').innerHTML = order.map((b, rank) => `
    <tr data-testid="board-row-${rank + 1}">
      <td>${rank + 1}</td>
      <td><i style="background:${carColor(b.car)}"></i>Car ${b.car + 1}</td>
      <td class="num">${b.tasks}</td><td class="num">${b.points.toFixed(2)}</td><td class="num">${b.wins}</td>
    </tr>`).join('');
  const missions = state.guesses.total;
  $('board-summary').textContent = `${missions} mission${missions === 1 ? '' : 's'} played · your guesses: ${state.guesses.right} of ${missions} right`;
  box.hidden = false;
}

// cars wait where they finished; completed tasks go, unassigned ones stay
function nextMission() {
  const r = state.result, done = new Set(r.paths.flat());
  state.runId++;
  state.cars = r.end_positions.map(([x, y]) => ({ x, y }));
  state.tasks = state.tasks.filter((_, j) => !done.has(j));
  fitTasksPerCar();
  state.mission += 1;
  state.guess = null; state.result = null;
  $('result').hidden = true; showError('');
  setTool('task');
  refresh();
}

function newGame() {
  state.runId++;
  Object.assign(state, example(), { guess: null, result: null, mission: 1, board: null, guesses: { right: 0, total: 0 } });
  fitTasksPerCar();
  $('result').hidden = true; showError('');
  setTool('car');
  renderBoard();
  refresh();
}

// ------------------------------------------------------------------ wiring

$('map').addEventListener('click', onMapClick);
$('tool-car').addEventListener('click', () => setTool('car'));
$('tool-task').addEventListener('click', () => setTool('task'));
$('clear').addEventListener('click', () => {
  if (!editing()) return;
  // during a campaign the cars are fixed, so only the tasks are cleared
  if (!campaignStarted()) { state.cars = []; state.guess = null; }
  state.tasks = []; fitTasksPerCar(); showError(''); refresh();
});
$('guesses').addEventListener('click', e => {
  const b = e.target.closest('[data-car]');
  if (!b || !editing()) return;
  state.guess = +b.dataset.car; refresh();
});
$('run').addEventListener('click', run);
$('skip').addEventListener('click', () => state.result && finish(state.result));
$('next-mission').addEventListener('click', nextMission);
$('new-game').addEventListener('click', newGame);
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => state.result ? finish(state.result) : refresh());

['setting-tasks-per-car', 'setting-loss', 'setting-speed'].forEach(id => {
  $(id).addEventListener('input', onSettingChange);      // while typing: check, don't correct
  $(id).addEventListener('change', onSettingCommit);     // when leaving the box: correct if needed
});
fitTasksPerCar();
refresh();
