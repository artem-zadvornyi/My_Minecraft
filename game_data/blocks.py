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

GRAVEL = BLOCKS.register(BlockDef(
    id=9, key='gravel', name='Гравий', category='natural',
    hardness=0.8, tool='shovel',
    faces=FaceTextures.all('gravel'), color=rgb(136, 126, 120),
    drops=_self_drop('gravel'), sound_group='sand'))

SNOW = BLOCKS.register(BlockDef(
    id=10, key='snow', name='Снег', category='natural',
    hardness=0.3, tool='shovel',
    faces=FaceTextures.all('snow'), color=rgb(238, 244, 250),
    drops=_self_drop('snow'), sound_group='sand'))

BIRCH_LOG = BLOCKS.register(BlockDef(
    id=11, key='birch_log', name='Берёза', category='wood',
    hardness=3.0, tool='axe',
    faces=FaceTextures.tbs('birch_log_top', 'birch_log_top', 'birch_log'),
    color=rgb(216, 215, 204), top_color=rgb(198, 187, 155),
    bottom_color=rgb(198, 187, 155),
    drops=_self_drop('birch_log'), sound_group='wood'))

SPRUCE_LOG = BLOCKS.register(BlockDef(
    id=12, key='spruce_log', name='Ель', category='wood',
    hardness=3.0, tool='axe',
    faces=FaceTextures.tbs('spruce_log_top', 'spruce_log_top', 'spruce_log'),
    color=rgb(74, 55, 34), top_color=rgb(122, 96, 60),
    bottom_color=rgb(122, 96, 60),
    drops=_self_drop('spruce_log'), sound_group='wood'))

BIRCH_LEAVES = BLOCKS.register(BlockDef(
    id=13, key='birch_leaves', name='Берёзовая листва', category='plants',
    hardness=0.35,
    faces=FaceTextures.all('birch_leaves'), color=rgb(96, 160, 78),
    drops=(), sound_group='grass'))

SPRUCE_LEAVES = BLOCKS.register(BlockDef(
    id=14, key='spruce_leaves', name='Хвоя', category='plants',
    hardness=0.35,
    faces=FaceTextures.all('spruce_leaves'), color=rgb(38, 84, 56),
    drops=(), sound_group='grass'))

CACTUS = BLOCKS.register(BlockDef(
    id=15, key='cactus', name='Кактус', category='plants',
    hardness=0.5,
    faces=FaceTextures.tbs('cactus_top', 'cactus_top', 'cactus_side'),
    color=rgb(58, 122, 48), top_color=rgb(66, 132, 54),
    bottom_color=rgb(66, 132, 54),
    drops=_self_drop('cactus'), sound_group='grass'))


def _plant(num_id, key, name, texture, drops=(), replace=True):
    """Растение-декорация: два пересечённых квада, без коллизии."""
    return BLOCKS.register(BlockDef(
        id=num_id, key=key, name=name, category='plants',
        hardness=0.05,
        faces=FaceTextures.all(texture), color=rgb(88, 152, 58),
        transparent=True, solid=False, collision=False, replaceable=replace,
        blocks_skylight=False, drops=drops, sound_group='grass',
        render='cross'))


TALL_GRASS = _plant(16, 'tall_grass', 'Высокая трава', 'tall_grass')
FLOWER_RED = _plant(17, 'flower_red', 'Мак', 'flower_red',
                    drops=_self_drop('flower_red'))
FLOWER_YELLOW = _plant(18, 'flower_yellow', 'Одуванчик', 'flower_yellow',
                       drops=_self_drop('flower_yellow'))
MUSHROOM_RED = _plant(19, 'mushroom_red', 'Мухомор', 'mushroom_red',
                      drops=_self_drop('mushroom_red'))
MUSHROOM_BROWN = _plant(20, 'mushroom_brown', 'Гриб', 'mushroom_brown',
                        drops=_self_drop('mushroom_brown'))
SUGAR_CANE = _plant(21, 'sugar_cane', 'Тростник', 'sugar_cane',
                    drops=_self_drop('sugar_cane'))
DEAD_BUSH = _plant(22, 'dead_bush', 'Сухой куст', 'dead_bush')
