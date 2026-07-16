# -*- coding: utf-8 -*-
"""Интеграционный тест физики игрока: без окна, с фиксированным dt.

Запуск:  .venv/bin/python tests/test_physics.py
"""
import sys
import time as _time
from math import floor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ursina import Ursina, Vec3, held_keys, mouse  # noqa: E402

from player import Player  # noqa: E402
from world import World  # noqa: E402

app = Ursina(window_type='none')

# без окна mouse.locked недоступен — подменяем свойство заглушкой
type(mouse).locked = property(lambda s: getattr(s, '_locked_flag', False),
                              lambda s, v: setattr(s, '_locked_flag', v))

world = World(seed=123)
spawn = world.find_spawn()
world.pregenerate(spawn)

player = Player(world, position=spawn + Vec3(0, 10, 0))
falls = []
player.on_hard_land = falls.append


def steps(n, dt=1 / 60):
    """Детерминированная прокрутка физики с фиксированным dt."""
    for _ in range(n):
        _time.dt = dt
        player.update()


# --- 1. Падение с высоты: игрок приземляется на поверхность и не проваливается ---
ground_h = world.height_at(floor(spawn.x), floor(spawn.z))
steps(400)
assert player.grounded, f'не приземлился: y={player.y}, vy={player.velocity_y}'
assert abs(player.y - (ground_h + 1)) < 0.05, \
    f'высота приземления {player.y}, ожидалась {ground_h + 1}'
assert falls and falls[0] > 8, f'урон от падения не сработал: {falls}'
print(f'OK падение: y={player.y:.3f}, высота падения={falls[0]:.1f}')

# --- 2. Ходьба вперёд (с прыжками через препятствия): не проваливается ---
start = Vec3(player.position)
held_keys['w'] = 1
held_keys['space'] = 1  # автопрыжки, чтобы забираться на холмы
steps(600)
held_keys['w'] = 0
held_keys['space'] = 0
moved = (player.position - start).length()
assert moved > 5, f'игрок не сдвинулся: {moved}, pos={player.position}'
col = (floor(player.x), floor(player.z))
h = world.height_at(*col)
assert player.y > h - 0.5, f'провалился сквозь землю: y={player.y}, поверхность={h + 1}'
print(f'OK ходьба: прошёл {moved:.1f} блоков, y={player.y:.2f} при поверхности {h + 1}')

# --- 3. Прыжок: взлетает и приземляется обратно ---
steps(100)
y0 = player.y
held_keys['space'] = 1
steps(10)
held_keys['space'] = 0
peak = player.y
steps(300)
assert peak > y0 + 0.5, f'прыжок не поднял игрока: {y0} -> {peak}'
assert player.grounded, 'не приземлился после прыжка'
print(f'OK прыжок: {y0:.2f} -> пик {peak:.2f} -> приземлился {player.y:.2f}')

# --- 4. Полёт (креатив): подъём работает ---
player.can_fly = True
player.flying = True
player.velocity_y = 0
y0 = player.y
held_keys['space'] = 1
steps(60)
held_keys['space'] = 0
assert player.y > y0 + 1, f'полёт вверх не работает: {y0} -> {player.y}'
player.flying = False
print(f'OK полёт: {y0:.2f} -> {player.y:.2f}')

# --- 5. Блок нельзя поставить в игрока ---
foot = (floor(player.x), floor(player.y), floor(player.z))
assert player.intersects_block(foot), 'intersects_block не видит блок в ногах'
assert not player.intersects_block((foot[0] + 5, foot[1], foot[2])), 'ложное пересечение'
print('OK intersects_block')

# --- 6. Рейкаст: смотрим ровно вниз с осевым направлением ---
hit, prev = world.raycast(Vec3(player.x, player.y + 1.6, player.z),
                          Vec3(0, -1, 0), 25)
assert hit is not None and prev is not None
assert prev[1] == hit[1] + 1, f'prev должен быть над hit: {hit} {prev}'
print(f'OK рейкаст вниз: hit={hit}')

# --- 7. Вода: тонем медленно, пробел поднимает, падение в воду без урона ---
px, pz = floor(player.x), floor(player.z)
for y in range(5, 9):
    world.set_block((px, y, pz), None)
for y in range(5, 8):
    world.set_block((px, y, pz), 'water')
player.position = Vec3(px + 0.5, 6.0, pz + 0.5)
player.velocity_y = 0
steps(30)
assert player.velocity_y >= -3.0, f'в воде тонем слишком быстро: {player.velocity_y}'
held_keys['space'] = 1
steps(30)
held_keys['space'] = 0
assert player.velocity_y > 0, f'пробел в воде не поднимает: {player.velocity_y}'
falls.clear()
player.position = Vec3(px + 0.5, 20.0, pz + 0.5)
player.velocity_y = 0
steps(400)
big_falls = [f for f in falls if f > 3]
assert not big_falls, f'падение в воду нанесло урон: {big_falls}'
print('OK вода (плавучесть и защита от урона при падении)')

# --- 8. Мелкая вода (глубина 1 блок) тоже гасит урон от падения ---
for y in range(5, 9):
    world.set_block((px, y, pz), None)
world.set_block((px, 5, pz), 'stone')
world.set_block((px, 6, pz), 'water')
falls.clear()
player.position = Vec3(px + 0.5, 20.0, pz + 0.5)
player.velocity_y = 0
steps(400)
big_falls = [f for f in falls if f > 3]
assert not big_falls, f'мелкая вода не защитила от урона: {big_falls}'
print('OK мелкая вода')

print('PHYSICS OK')
