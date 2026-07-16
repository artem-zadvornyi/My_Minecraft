# -*- coding: utf-8 -*-
"""Реестр предметов. Блоки и предметы — разные системы:

- блок живёт в мире (world.blocks), предмет — в инвентаре;
- каждому блоку автоматически создаётся предмет-блок с тем же ключом
  и полем placeable_block, связывающим его с блоком;
- «чистые» предметы (палки, еда, инструменты) регистрируются вручную.

Числовые id предметов: 1-99 — предметы-блоки, 100+ — остальные.
"""
from game_data.blocks import BLOCKS
from game_data.definitions import ItemDef, rgb
from game_data.registry import Registry

ITEMS = Registry('предмет')

# Порядок палитры креатива (исторический порядок панели + снег)
_CREATIVE_PALETTE = ('grass', 'dirt', 'stone', 'sand', 'planks',
                     'wood', 'leaves', 'water', 'snow')

# --- предметы-блоки: по одному на каждый блок реестра ---
# id предмета-блока = id блока: block.id задан явно и зарезервирован,
# поэтому id предметов не зависят от порядка регистрации блоков
for _block in BLOCKS.values():
    _palette = (_CREATIVE_PALETTE.index(_block.key)
                if _block.key in _CREATIVE_PALETTE else None)
    ITEMS.register(ItemDef(
        id=_block.id, key=_block.key, name=_block.name, category='block',
        icon=_block.faces.north,  # боковая текстура нагляднее всего
        icon_color=_block.color,
        max_stack=_block.max_stack,
        placeable_block=_block.key,
        creative_palette=_palette))

# --- материалы и еда ---
STICK = ITEMS.register(ItemDef(
    id=100, key='stick', name='Палка', category='material',
    icon_color=rgb(117, 92, 55)))

APPLE = ITEMS.register(ItemDef(
    id=101, key='apple', name='Яблоко', category='food',
    icon_color=rgb(190, 44, 36), food=4))

# --- деревянные инструменты (уровень 1, добыча x4) ---
WOODEN_PICKAXE = ITEMS.register(ItemDef(
    id=102, key='wooden_pickaxe', name='Дер. кирка', category='tool',
    icon_color=rgb(158, 116, 66), label='К', max_stack=1,
    tool_type='pickaxe', tool_tier=1, mining_multiplier=4.0,
    durability=60, attack_damage=2.0))

WOODEN_AXE = ITEMS.register(ItemDef(
    id=103, key='wooden_axe', name='Дер. топор', category='tool',
    icon_color=rgb(146, 104, 56), label='Т', max_stack=1,
    tool_type='axe', tool_tier=1, mining_multiplier=4.0,
    durability=60, attack_damage=3.0))

WOODEN_SHOVEL = ITEMS.register(ItemDef(
    id=104, key='wooden_shovel', name='Дер. лопата', category='tool',
    icon_color=rgb(170, 128, 78), label='Л', max_stack=1,
    tool_type='shovel', tool_tier=1, mining_multiplier=4.0,
    durability=60, attack_damage=1.5))
