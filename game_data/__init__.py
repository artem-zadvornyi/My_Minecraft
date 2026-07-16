# -*- coding: utf-8 -*-
"""Игровые данные: реестры блоков и предметов, правила добычи.

Точка входа для остального кода:

    from game_data import BLOCKS, ITEMS, break_time, get_drops, can_harvest
"""
from game_data.blocks import BLOCKS
from game_data.definitions import BlockDef, Drop, FaceTextures, ItemDef, rgb
from game_data.items import ITEMS
from game_data.mining import break_time, can_harvest, get_drops
from game_data.registry import Registry, RegistryError


def validate():
    """Перекрёстная проверка реестров: битые ссылки — ошибка при импорте."""
    for block in BLOCKS:
        for drop in block.drops:
            if drop.item not in ITEMS:
                raise RegistryError(
                    f'блок {block.key!r}: дроп ссылается на '
                    f'несуществующий предмет {drop.item!r}')
            if not 0 < drop.chance <= 1:
                raise RegistryError(
                    f'блок {block.key!r}: вероятность дропа {drop.chance}')
            if drop.count < 1:
                raise RegistryError(
                    f'блок {block.key!r}: количество дропа {drop.count}')
    for item in ITEMS:
        if item.placeable_block is not None and item.placeable_block not in BLOCKS:
            raise RegistryError(
                f'предмет {item.key!r}: placeable_block ссылается на '
                f'несуществующий блок {item.placeable_block!r}')


validate()
