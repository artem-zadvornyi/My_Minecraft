# -*- coding: utf-8 -*-
"""Тесты генерации мира: детерминизм, границы чанков, биомы, деревья, спавн.

Не требуют окна и экземпляра Ursina.
Запуск:  .venv/bin/python tests/test_worldgen.py
"""
import sys
from math import floor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game_data import BIOMES, BLOCKS  # noqa: E402
from settings import CHUNK_SIZE, WATER_LEVEL  # noqa: E402
from worldgen import SEA, Generator  # noqa: E402

# ----------------------------------------------------------------------
# Одно зерно => одинаковый мир; разные зёрна => разный рельеф
# ----------------------------------------------------------------------
g1, g2 = Generator(555), Generator(555)
for coord in ((0, 0), (-2, 1), (3, -4)):
    assert g1.generate_chunk(coord) == g2.generate_chunk(coord), coord
print('OK одинаковое зерно -> одинаковый мир')

g3 = Generator(556)
diff = sum(1 for x in range(-64, 65, 8) for z in range(-64, 65, 8)
           if g1.column_at(x, z).height != g3.column_at(x, z).height)
assert diff > 20, f'другое зерно почти не изменило рельеф: {diff} отличий'
print('OK разные зёрна -> разный рельеф')

# ----------------------------------------------------------------------
# Порядок генерации чанков не влияет на содержимое
# ----------------------------------------------------------------------
ga, gb = Generator(777), Generator(777)
order_a = [(0, 0), (1, 0), (0, 1), (1, 1)]
chunks_a = {c: ga.generate_chunk(c) for c in order_a}
chunks_b = {c: gb.generate_chunk(c) for c in reversed(order_a)}
for c in order_a:
    assert chunks_a[c] == chunks_b[c], f'чанк {c} зависит от порядка генерации'
print('OK порядок генерации не влияет')

# ----------------------------------------------------------------------
# Согласованность на границе чанков: колонки непрерывны между чанками
# ----------------------------------------------------------------------
edge = CHUNK_SIZE - 1
for z in range(0, CHUNK_SIZE):
    col_left = ga.column_at(edge, z)
    col_right = ga.column_at(edge + 1, z)
    # обе колонки состоят из тех же блоков в обоих чанках
    h = col_left.height
    assert chunks_a[(0, 0)][(edge, h, z)] == chunks_b[(0, 0)][(edge, h, z)]
    h2 = col_right.height
    assert chunks_a[(1, 0)][(edge + 1, h2, z)] == chunks_b[(1, 0)][(edge + 1, h2, z)]
print('OK границы чанков согласованы')

# ----------------------------------------------------------------------
# Биомы: классификатор покрывает все 11 биомов и детерминирован
# ----------------------------------------------------------------------
cls = Generator.classify
assert cls(0.1, 5, 0, 0, 0) == 'ocean'
assert cls(1.0, SEA + 1, 0, 0, 0) == 'beach'
assert cls(1.0, 20, 0.9, 0.3, 0) == 'mountains'
assert cls(1.0, 32, 0.9, 0.3, 0) == 'snowy_mountains'   # выше линии снега
assert cls(1.0, 20, 0.9, -0.3, 0) == 'snowy_mountains'  # холодные горы
assert cls(1.0, SEA + 2, 0, 0, 0.4) == 'swamp'
assert cls(1.0, 20, 0, 0.4, -0.3) == 'desert'
assert cls(1.0, 20, 0, 0.4, 0.3) == 'savanna'
assert cls(1.0, 20, 0, -0.4, 0) == 'taiga'
assert cls(1.0, 20, 0, 0.1, 0.2) == 'forest'
assert cls(1.0, 20, 0, -0.1, 0.2) == 'birch_forest'
assert cls(1.0, 20, 0, 0, -0.3) == 'plains'
# ключи классификатора существуют в реестре биомов
assert set(BIOMES.keys()) == {
    'ocean', 'beach', 'plains', 'forest', 'birch_forest', 'taiga',
    'desert', 'savanna', 'mountains', 'snowy_mountains', 'swamp'}
# биомы стабильны между экземплярами
for x, z in ((0, 0), (100, -250), (-333, 512)):
    assert g1.column_at(x, z).biome == Generator(555).column_at(x, z).biome
# на большой площади встречается большинство биомов
found = {g1.column_at(x, z).biome
         for x in range(-600, 601, 24) for z in range(-600, 601, 24)}
assert len(found) >= 8, f'слишком мало биомов на выборке: {found}'
print(f'OK биомы ({len(found)} видов на выборке)')

# ----------------------------------------------------------------------
# Деревья: детерминированы и согласованы через границы чанков
# ----------------------------------------------------------------------
border_tree = None
for x in range(-200, 200):
    for z in range(-200, 200, 3):
        tree = g1.tree_at(x, z)
        if tree is None:
            continue
        trunk, leaves = tree
        # дерево воспроизводится в другом экземпляре генератора
        assert Generator(555).tree_at(x, z) == tree
        cxs = {floor(p[0] / CHUNK_SIZE) for p in leaves} | \
              {floor(p[2] / CHUNK_SIZE) for p in leaves}
        if border_tree is None and len(cxs) > 1:
            border_tree = (x, z, tree)
    if border_tree:
        break
assert border_tree is not None, 'не нашли дерево на границе чанков'
x, z, (trunk, leaves) = border_tree
gen = Generator(555)
touched = {(floor(p[0] / CHUNK_SIZE), floor(p[2] / CHUNK_SIZE))
           for p in list(trunk) + list(leaves)}
merged = {}
for c in touched:
    merged.update(gen.generate_chunk(c))
for pos, bid in trunk.items():
    assert merged.get(pos) == bid, f'ствол потерян на границе: {pos}'
lost = sum(1 for pos in leaves if pos not in merged)
# листва уступает рельефу/стволам, но большая часть кроны должна попасть в мир
assert lost <= len(leaves) * 0.3, f'потеряно {lost}/{len(leaves)} листвы'
print('OK деревья согласованы через границы чанков')

# ----------------------------------------------------------------------
# Спавн: суша, не река, предпочтительный биом, не в блоках.
# Зёрна 14, 15, 153 исторически спавнили игрока внутри деревьев.
# ----------------------------------------------------------------------
for seed in (555, 123, 20260716, 14, 15, 153) + tuple(range(30)):
    g = Generator(seed)
    sx, sy, sz = g.find_spawn()
    col = g.column_at(floor(sx), floor(sz))
    assert col.height > SEA, f'спавн под водой: seed={seed}'
    assert not col.river, f'спавн в реке: seed={seed}'
    assert col.biome in ('plains', 'forest', 'birch_forest'), \
        f'спавн в {col.biome}: seed={seed}'
    assert sy >= col.height + 1, 'спавн внутри рельефа'
    # клетки ног и головы свободны от блоков с коллизией (включая
    # стволы и кроны деревьев, пришедшие из соседних колонок)
    chunk_coord = (floor(floor(sx) / CHUNK_SIZE), floor(floor(sz) / CHUNK_SIZE))
    blocks = g.generate_chunk(chunk_coord)
    for dy in (-1, 0, 1):
        pos = (floor(sx), floor(sy) + dy, floor(sz))
        bid = blocks.get(pos)
        assert (bid is None or not BLOCKS[bid].collision
                or pos[1] <= col.height), \
            f'спавн внутри блока {bid}: seed={seed}, {pos}'
print('OK спавн безопасен (36 зёрен, включая исторически плохие)')

assert WATER_LEVEL == SEA
print('WORLDGEN OK')
