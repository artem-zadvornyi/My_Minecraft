# -*- coding: utf-8 -*-
"""Юнит-тесты чистой логики: рецепты, инвентарь, блоки, генерация, рейкаст.

Не требуют окна и экземпляра Ursina — только импорты модулей.
Запуск:  .venv/bin/python tests/test_logic.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ursina import Vec3  # noqa: E402

from game_data import BLOCKS, ITEMS, break_time, get_drops  # noqa: E402
from crafting import match_recipe, normalize  # noqa: E402
from inventory import Inventory, Slot  # noqa: E402
from settings import CHUNK_SIZE, DIRT_DEPTH, HOTBAR_SLOTS, WATER_LEVEL  # noqa: E402
from world import World  # noqa: E402


def grid(cells):
    """Сетка 3x3 из словаря {индекс: id} для читаемых тестов."""
    return [cells.get(i) for i in range(9)]


# ----------------------------------------------------------------------
# Рецепты
# ----------------------------------------------------------------------
# бревно в любой клетке -> доски
for i in range(9):
    assert match_recipe(grid({i: 'wood'})) == ('planks', 4), f'wood в клетке {i}'
# палки: 2 доски строго вертикально
assert match_recipe(grid({0: 'planks', 3: 'planks'})) == ('stick', 4)
assert match_recipe(grid({4: 'planks', 7: 'planks'})) == ('stick', 4)
# горизонтальные доски палок НЕ дают
assert match_recipe(grid({0: 'planks', 1: 'planks'})) is None
# кирка
assert match_recipe(grid({0: 'planks', 1: 'planks', 2: 'planks',
                          4: 'stick', 7: 'stick'})) == ('wooden_pickaxe', 1)
# топор и зеркальный топор
assert match_recipe(grid({0: 'planks', 1: 'planks',
                          3: 'planks', 4: 'stick',
                          7: 'stick'})) == ('wooden_axe', 1)
assert match_recipe(grid({1: 'planks', 2: 'planks',
                          4: 'stick', 5: 'planks',
                          7: 'stick'})) == ('wooden_axe', 1)
# лопата, смещённая в правый столбец
assert match_recipe(grid({2: 'planks', 5: 'stick', 8: 'stick'})) == ('wooden_shovel', 1)
# пустая сетка и мусор
assert match_recipe(grid({})) is None
assert match_recipe(grid({0: 'stone'})) is None
assert normalize(grid({})) is None
print('OK рецепты')

# ----------------------------------------------------------------------
# Инвентарь
# ----------------------------------------------------------------------
inv = Inventory()
left = inv.add('dirt', 70)
assert left == 0
counts = sorted(s.count for s in inv.slots if s.item == 'dirt')
assert counts == [6, 64], counts
# переполнение: 9 слотов по 64 = 576 максимум
inv2 = Inventory()
left = inv2.add('stone', 600)
assert left == 600 - 9 * 64, left
# расход выбранного
inv.select(0)
sel_before = inv.selected_slot.count
inv.consume_selected(1)
assert inv.selected_slot.count == sel_before - 1
# выбор по кругу
inv.select(HOTBAR_SLOTS + 2)
assert inv.selected == 2
# креативная палитра: бесконечные слоты не истощаются
inv.set_creative_palette()
assert inv.creative
s = inv.slots[0]
item, n = s.take(64)
assert n == 64 and not s.empty and s.infinite
assert inv.add('dirt', 5) == 0 and all(sl.item != 'dirt' or sl.infinite for sl in inv.slots)
# возврат в выживание
saved = [Slot('dirt', 10)] + [Slot() for _ in range(HOTBAR_SLOTS - 1)]
inv.set_slots(saved)
assert not inv.creative and inv.slots[0].count == 10
# инструменты не стопкуются
inv3 = Inventory()
inv3.add('wooden_pickaxe', 2)
picks = [s for s in inv3.slots if s.item == 'wooden_pickaxe']
assert len(picks) == 2 and all(p.count == 1 for p in picks)
print('OK инвентарь')

# ----------------------------------------------------------------------
# Клики по слотам крафта (без окна: метод не трогает интерфейс)
# ----------------------------------------------------------------------
from crafting import CraftingUI  # noqa: E402


class _StubCraft:
    """Заглушка: _click_slot использует только self.cursor."""
    def __init__(self):
        self.cursor = Slot()


stub = _StubCraft()
palette = Slot('stone', 1, infinite=True)
# ПКМ по бесконечной палитре — один предмет
CraftingUI._click_slot(stub, palette, right=True)
assert stub.cursor.item == 'stone' and stub.cursor.count == 1, stub.cursor.count
stub.cursor.clear()
# ЛКМ — полная стопка
CraftingUI._click_slot(stub, palette, right=False)
assert stub.cursor.count == ITEMS['stone'].max_stack
assert not palette.empty  # палитра не истощается
# бросок в палитру уничтожает предмет с курсора
CraftingUI._click_slot(stub, palette, right=False)
assert stub.cursor.empty
print('OK клики по палитре')

# ----------------------------------------------------------------------
# Блоки: добыча и скорость разрушения
# ----------------------------------------------------------------------
import random as _random  # noqa: E402

assert get_drops('grass') == [('dirt', 1)]   # трава даёт землю
assert get_drops('stone') == [('stone', 1)]
rng = _random.Random(7)
leaf_drops = {tuple(get_drops('leaves', rng=rng)) for _ in range(300)}
assert leaf_drops == {(), (('apple', 1),)}, leaf_drops  # яблоко или ничего
assert break_time('stone', 'wooden_pickaxe') < break_time('stone', None)
assert break_time('stone', 'wooden_shovel') == break_time('stone', None)
assert break_time('dirt', 'wooden_shovel') < break_time('dirt', None)
assert BLOCKS['water'].hardness == float('inf')
print('OK блоки')

# ----------------------------------------------------------------------
# Генерация мира (без мешей: только словари блоков)
# ----------------------------------------------------------------------
w = World(seed=42)
# детерминизм высот и кэш
h1 = w.height_at(10, -7)
h2 = w.height_at(10, -7)
assert h1 == h2 == World(seed=42).height_at(10, -7)
assert World(seed=43).blocks == {}  # генерации ещё не было
# чанк с отрицательными координатами
chunk = w._generate_chunk((-1, -1))
assert chunk.positions, 'пустой чанк'
xs = [p[0] for p in chunk.positions]
zs = [p[2] for p in chunk.positions]
assert min(xs) >= -CHUNK_SIZE and max(xs) < 0, (min(xs), max(xs))
assert min(zs) >= -CHUNK_SIZE and max(zs) < 0
# послойность: y=0 камень, поверхность трава/песок, под ней земля
x, z = -8, -8
h = w.height_at(x, z)
assert w.blocks[(x, 0, z)] == 'stone'
top = w.blocks[(x, h, z)]
assert top in ('grass', 'sand', 'wood'), top
if top == 'grass':
    assert w.blocks[(x, h - 1, z)] == 'dirt'
    assert w.blocks[(x, h - DIRT_DEPTH, z)] == 'stone'
# вода заполняет низины до уровня воды
lake = [(p, b) for p, b in w.blocks.items() if b == 'water']
for p, _ in lake:
    assert p[1] <= WATER_LEVEL
# правки игрока переживают перегенерацию
pos = (-8, h, -8)
w.edits[pos] = None            # блок «сломан»
w.edits[(-8, 30, -8)] = 'stone'  # блок «поставлен» в воздухе
del w.chunks[(-1, -1)]
for p in list(w.blocks):
    w.blocks.pop(p)
chunk = w._generate_chunk((-1, -1))
assert pos not in w.blocks
assert w.blocks.get((-8, 30, -8)) == 'stone'
print('OK генерация')

# ----------------------------------------------------------------------
# Координаты чанков и воксельный рейкаст
# ----------------------------------------------------------------------
assert World.chunk_coord((0, 0, 0)) == (0, 0)
assert World.chunk_coord((-1, 5, -1)) == (-1, -1)
assert World.chunk_coord((15, 0, 16)) == (0, 1)
assert World.chunk_coord((-16, 0, -17)) == (-1, -2)

w2 = World(seed=1)
w2.blocks[(5, 5, 5)] = 'stone'
# осевые направления
hit, prev = w2.raycast(Vec3(5.5, 8.0, 5.5), Vec3(0, -1, 0), 10)
assert hit == (5, 5, 5) and prev == (5, 6, 5)
hit, prev = w2.raycast(Vec3(2.5, 5.5, 5.5), Vec3(1, 0, 0), 10)
assert hit == (5, 5, 5) and prev == (4, 5, 5)
# диагональ
hit, prev = w2.raycast(Vec3(3.5, 7.5, 5.5), Vec3(1, -1, 0).normalized(), 10)
assert hit == (5, 5, 5), hit
# мимо и дальше дистанции
hit, _ = w2.raycast(Vec3(0, 20, 0), Vec3(0, -1, 0), 5)
assert hit is None
# вода не выбирается лучом
w2.blocks[(5, 7, 5)] = 'water'
hit, prev = w2.raycast(Vec3(5.5, 9.0, 5.5), Vec3(0, -1, 0), 10)
assert hit == (5, 5, 5) and prev == (5, 6, 5)
# отрицательные координаты
w2.blocks[(-3, -2, -3)] = 'stone'
hit, prev = w2.raycast(Vec3(-2.5, 1.0, -2.5), Vec3(0, -1, 0).normalized(), 10)
assert hit is None or hit[1] >= -2  # луч не должен «проскочить» блок
print('OK рейкаст и координаты')

print('LOGIC OK')
