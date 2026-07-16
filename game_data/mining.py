# -*- coding: utf-8 -*-
"""Добыча: время разрушения, пригодность инструмента, дропы.

Вся конфигурация берётся из реестров; здесь только правила.
"""
import random

from game_data.blocks import BLOCKS
from game_data.items import ITEMS


def break_time(block_key, held_item_key=None):
    """Время разрушения блока с учётом предмета в руке, сек."""
    block = BLOCKS[block_key]
    t = block.hardness
    held = ITEMS.get(held_item_key) if held_item_key else None
    if (held and held.tool_type and held.tool_type == block.tool
            and held.tool_tier >= block.min_tool_tier):
        t /= held.mining_multiplier
    return t


def can_harvest(block_key, held_item_key=None):
    """Выпадет ли дроп при разрушении этим предметом.

    Задел на будущие уровни инструментов: сейчас у всех блоков
    min_tool_tier == 0, поэтому всё добывается рукой.
    """
    block = BLOCKS[block_key]
    if block.min_tool_tier <= 0:
        return True
    held = ITEMS.get(held_item_key) if held_item_key else None
    return bool(held and held.tool_type == block.tool
                and held.tool_tier >= block.min_tool_tier)


def get_drops(block_key, held_item_key=None, rng=random):
    """Список дропов [(ключ_предмета, количество), ...] за разрушение блока."""
    if not can_harvest(block_key, held_item_key):
        return []
    result = []
    for drop in BLOCKS[block_key].drops:
        if drop.chance >= 1.0 or rng.random() < drop.chance:
            result.append((drop.item, drop.count))
    return result
