# -*- coding: utf-8 -*-
"""Тесты реестров блоков/предметов и атласа текстур.

Не требуют окна и экземпляра Ursina.
Запуск:  .venv/bin/python tests/test_registry.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from game_data import (BLOCKS, ITEMS, RegistryError, break_time,  # noqa: E402
                       can_harvest, get_drops, validate)
from game_data.definitions import BlockDef, FaceTextures, rgb  # noqa: E402
from game_data.registry import Registry  # noqa: E402
from rendering.texture_atlas import (TILE, WHITE_TILE,  # noqa: E402
                                     TextureAtlas)

# ----------------------------------------------------------------------
# Уникальность ключей и id
# ----------------------------------------------------------------------
block_ids = [b.id for b in BLOCKS]
item_ids = [i.id for i in ITEMS]
assert len(set(block_ids)) == len(block_ids), 'дубли id блоков'
assert len(set(item_ids)) == len(item_ids), 'дубли id предметов'
assert all(i > 0 for i in block_ids), 'id 0 зарезервирован под воздух'
assert len(set(BLOCKS.keys())) == len(block_ids)
assert len(set(ITEMS.keys())) == len(item_ids)

# реестр отвергает дубликаты
r = Registry('тест')
d1 = BlockDef(id=1, key='a', name='А', category='t', hardness=1,
              faces=FaceTextures.all('dirt'), color=rgb(1, 1, 1))
r.register(d1)
for bad in (
    BlockDef(id=1, key='b', name='Б', category='t', hardness=1,
             faces=FaceTextures.all('dirt'), color=rgb(1, 1, 1)),   # дубль id
    BlockDef(id=2, key='a', name='В', category='t', hardness=1,
             faces=FaceTextures.all('dirt'), color=rgb(1, 1, 1)),   # дубль key
    BlockDef(id=0, key='c', name='Г', category='t', hardness=1,
             faces=FaceTextures.all('dirt'), color=rgb(1, 1, 1)),   # id=0
):
    try:
        r.register(bad)
        raise AssertionError(f'реестр принял некорректное: {bad.key}')
    except RegistryError:
        pass
# доступ по числовому id
assert BLOCKS.by_id(1).key == 'grass'
assert BLOCKS.by_id(999) is None
print('OK уникальность реестров')

# ----------------------------------------------------------------------
# Валидность дропов и связи предмет->блок
# ----------------------------------------------------------------------
validate()  # перекрёстные ссылки целы
for block in BLOCKS:
    for drop in block.drops:
        assert drop.item in ITEMS
        assert 0 < drop.chance <= 1 and drop.count >= 1
# у каждого блока есть предмет-блок с обратной ссылкой
for block in BLOCKS:
    item = ITEMS[block.key]
    assert item.placeable_block == block.key, block.key
    assert item.max_stack == block.max_stack
    # контракт стабильности: id предмета-блока равен явному id блока
    # и не зависит от порядка регистрации
    assert item.id == block.id, block.key
# блоки и предметы — разные объекты разных типов
assert type(BLOCKS['grass']) is not type(ITEMS['grass'])
# вода: жидкость без коллизии, перекрываемая, не даёт дроп
w = BLOCKS['water']
assert w.liquid and not w.collision and w.replaceable and w.transparent
assert not w.solid and not w.blocks_skylight and w.drops == ()
print('OK дропы и связи')

# ----------------------------------------------------------------------
# Добыча: время, уровни инструментов, множители
# ----------------------------------------------------------------------
assert break_time('stone') == 7.5
assert break_time('stone', 'wooden_pickaxe') == 7.5 / 4
assert break_time('stone', 'wooden_axe') == 7.5      # чужой инструмент
assert break_time('wood', 'wooden_axe') == 3.0 / 4
assert can_harvest('stone') and can_harvest('stone', 'wooden_pickaxe')
assert ITEMS['wooden_pickaxe'].tool_tier == 1
assert ITEMS['wooden_pickaxe'].mining_multiplier == 4.0
assert ITEMS['wooden_pickaxe'].durability is not None  # задел на будущее
print('OK добыча')

# ----------------------------------------------------------------------
# Лимиты стопок и еда
# ----------------------------------------------------------------------
for key in ('wooden_pickaxe', 'wooden_axe', 'wooden_shovel'):
    assert ITEMS[key].max_stack == 1, key
    assert ITEMS[key].placeable_block is None, key
for key in ('grass', 'dirt', 'stone', 'sand', 'planks'):
    assert ITEMS[key].max_stack == 64, key
assert ITEMS['apple'].food == 4
assert ITEMS['stick'].food == 0 and ITEMS['stick'].placeable_block is None
print('OK стопки и еда')

# ----------------------------------------------------------------------
# Совместимость с крафтом: все ингредиенты и результаты существуют
# ----------------------------------------------------------------------
from crafting import RECIPES  # noqa: E402

for pattern, (result, count) in RECIPES.items():
    assert result in ITEMS, f'результат {result!r} не зарегистрирован'
    assert count >= 1
    for row in pattern:
        for cell in row:
            if cell is not None:
                assert cell in ITEMS, f'ингредиент {cell!r} не зарегистрирован'
print('OK совместимость крафта')

# ----------------------------------------------------------------------
# Атлас текстур: раскладка и UV (чистая логика, без GPU)
# ----------------------------------------------------------------------
atlas = TextureAtlas()
w_px, h_px = atlas.image.size
assert w_px % TILE == 0 and h_px % TILE == 0
# все текстуры всех граней всех блоков есть в атласе
for block in BLOCKS:
    for fi in range(6):
        name = block.faces.by_index(fi)
        assert atlas.uv(name) is not None, f'{block.key}: нет текстуры {name}'
# белый тайл для граней без текстур
assert atlas.uv(WHITE_TILE) is not None
# запас на будущее: неизвестное имя -> None (запасной цвет)
assert atlas.uv('no_such_texture') is None
# каждый прямоугольник внутри [0,1], поджат на полтекселя, не пересекается
seen = set()
for name, (u0, v0, u1, v1) in atlas._uv.items():
    assert 0 < u0 < u1 < 1 and 0 < v0 < v1 < 1, name
    # ширина тайла = TILE-1 текселей (по полтекселя с каждого края)
    assert abs((u1 - u0) * w_px - (TILE - 1)) < 1e-6, name
    assert abs((v1 - v0) * h_px - (TILE - 1)) < 1e-6, name
    cell = (round(u0 * w_px) // TILE, round((1 - v1) * h_px) // TILE)
    assert cell not in seen, f'{name}: тайлы пересекаются'
    seen.add(cell)
# у травы верх/бок/низ — разные текстуры
g = BLOCKS['grass'].faces
assert len({g.top, g.bottom, g.north}) == 3
assert atlas.uv(g.top) != atlas.uv(g.north) != atlas.uv(g.bottom)
# иконки предметов-блоков указывают на существующие тайлы
for block in BLOCKS:
    assert atlas.uv(ITEMS[block.key].icon) is not None, block.key
print('OK атлас')

print('REGISTRY OK')
