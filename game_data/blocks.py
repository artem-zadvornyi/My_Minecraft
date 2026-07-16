# -*- coding: utf-8 -*-
"""Реестр блоков. Все блоки мира определяются здесь — и только здесь.

Числовые id стабильны и зарезервированы навсегда (0 — воздух):
менять их нельзя, новые блоки получают следующие свободные номера.
"""
from game_data.definitions import BlockDef, Drop, FaceTextures, rgb
from game_data.registry import Registry

BLOCKS = Registry('блок')


def _self_drop(key):
    """Дроп по умолчанию: блок выпадает сам."""
    return (Drop(key),)


GRASS = BLOCKS.register(BlockDef(
    id=1, key='grass', name='Трава', category='natural',
    hardness=0.9, tool='shovel',
    faces=FaceTextures.tbs('grass_top', 'dirt', 'grass_side'),
    color=rgb(116, 132, 58), top_color=rgb(95, 169, 61),
    bottom_color=rgb(134, 96, 67),
    drops=(Drop('dirt'),),  # как в Minecraft: трава даёт землю
    sound_group='grass'))

DIRT = BLOCKS.register(BlockDef(
    id=2, key='dirt', name='Земля', category='natural',
    hardness=0.75, tool='shovel',
    faces=FaceTextures.all('dirt'), color=rgb(134, 96, 67),
    drops=_self_drop('dirt'), sound_group='grass'))

STONE = BLOCKS.register(BlockDef(
    id=3, key='stone', name='Камень', category='natural',
    hardness=7.5, tool='pickaxe',
    faces=FaceTextures.all('stone'), color=rgb(125, 125, 125),
    drops=_self_drop('stone'), sound_group='stone'))

SAND = BLOCKS.register(BlockDef(
    id=4, key='sand', name='Песок', category='natural',
    hardness=0.75, tool='shovel',
    faces=FaceTextures.all('sand'), color=rgb(219, 207, 163),
    drops=_self_drop('sand'), sound_group='sand'))

WATER = BLOCKS.register(BlockDef(
    id=5, key='water', name='Вода', category='liquid',
    hardness=float('inf'),
    faces=FaceTextures.all('water'), color=rgb(52, 110, 205, 150),
    transparent=True, solid=False, replaceable=True, liquid=True,
    collision=False, blocks_skylight=False,
    drops=(), sound_group='water'))

WOOD = BLOCKS.register(BlockDef(
    id=6, key='wood', name='Бревно', category='wood',
    hardness=3.0, tool='axe',
    faces=FaceTextures.tbs('oak_log_top', 'oak_log_top', 'oak_log'),
    color=rgb(103, 82, 49), top_color=rgb(155, 125, 77),
    bottom_color=rgb(155, 125, 77),
    drops=_self_drop('wood'), sound_group='wood'))

LEAVES = BLOCKS.register(BlockDef(
    id=7, key='leaves', name='Листва', category='plants',
    hardness=0.35,
    faces=FaceTextures.all('leaves'), color=rgb(55, 124, 42),
    drops=(Drop('apple', 1, 0.2),),  # яблоко с шансом 20%
    sound_group='grass'))

PLANKS = BLOCKS.register(BlockDef(
    id=8, key='planks', name='Доски', category='building',
    hardness=3.0, tool='axe',
    faces=FaceTextures.all('planks'), color=rgb(162, 131, 79),
    drops=_self_drop('planks'), sound_group='wood'))
