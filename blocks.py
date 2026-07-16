# -*- coding: utf-8 -*-
"""Определения блоков и предметов: цвета, прочность, свойства."""
import random
from dataclasses import dataclass

from ursina.color import Color

from settings import TOOL_SPEED_FACTOR


def rgb(r, g, b, a=255):
    """Цвет из компонентов 0-255 (Ursina ожидает 0-1)."""
    return Color(r / 255, g / 255, b / 255, a / 255)


@dataclass(frozen=True)
class ItemDef:
    """Описание блока или предмета."""
    id: str
    name: str                   # отображаемое имя
    color: Color                # цвет боковых граней и иконки
    top_color: Color = None     # цвет верхней грани (если отличается)
    bottom_color: Color = None  # цвет нижней грани (если отличается)
    is_block: bool = True       # можно ли ставить в мир
    solid: bool = True          # есть ли коллизия
    transparent: bool = False   # видно ли соседние грани сквозь блок
    hardness: float = 1.0       # время разрушения голой рукой, сек
    tool: str = None            # каким инструментом блок ломается быстрее
    tool_type: str = None       # для инструментов: 'pickaxe' / 'axe' / 'shovel'
    max_stack: int = 64         # максимум в одной стопке
    label: str = ''             # буква на иконке (для инструментов)


ITEMS = {}


def _add(item):
    ITEMS[item.id] = item


# --- Блоки ---
_add(ItemDef('grass', 'Трава', rgb(116, 132, 58),
             top_color=rgb(95, 169, 61), bottom_color=rgb(134, 96, 67),
             hardness=0.9, tool='shovel'))
_add(ItemDef('dirt', 'Земля', rgb(134, 96, 67), hardness=0.75, tool='shovel'))
_add(ItemDef('stone', 'Камень', rgb(125, 125, 125), hardness=7.5, tool='pickaxe'))
_add(ItemDef('sand', 'Песок', rgb(219, 207, 163), hardness=0.75, tool='shovel'))
_add(ItemDef('water', 'Вода', rgb(52, 110, 205, 150),
             solid=False, transparent=True, hardness=float('inf')))
_add(ItemDef('wood', 'Бревно', rgb(103, 82, 49),
             top_color=rgb(155, 125, 77), hardness=3.0, tool='axe'))
_add(ItemDef('leaves', 'Листва', rgb(55, 124, 42), hardness=0.35))
_add(ItemDef('planks', 'Доски', rgb(162, 131, 79), hardness=3.0, tool='axe'))

# --- Предметы (нельзя ставить в мир) ---
_add(ItemDef('stick', 'Палка', rgb(117, 92, 55), is_block=False))
_add(ItemDef('apple', 'Яблоко', rgb(190, 44, 36), is_block=False))
_add(ItemDef('wooden_pickaxe', 'Дер. кирка', rgb(158, 116, 66),
             is_block=False, tool_type='pickaxe', max_stack=1, label='К'))
_add(ItemDef('wooden_axe', 'Дер. топор', rgb(146, 104, 56),
             is_block=False, tool_type='axe', max_stack=1, label='Т'))
_add(ItemDef('wooden_shovel', 'Дер. лопата', rgb(170, 128, 78),
             is_block=False, tool_type='shovel', max_stack=1, label='Л'))


def get_drop(block_id):
    """Что выпадает при разрушении блока (None — ничего)."""
    if block_id == 'grass':
        return 'dirt'  # как в Minecraft: трава даёт землю
    if block_id == 'leaves':
        return 'apple' if random.random() < 0.2 else None
    return block_id


def break_time(block_id, held_item_id):
    """Время разрушения блока с учётом инструмента в руке, сек."""
    block = ITEMS[block_id]
    t = block.hardness
    held = ITEMS.get(held_item_id)
    if held and held.tool_type and held.tool_type == block.tool:
        t /= TOOL_SPEED_FACTOR
    return t
