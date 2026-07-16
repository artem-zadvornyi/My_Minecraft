# -*- coding: utf-8 -*-
"""Реестр биомов: что растёт и из чего состоит поверхность.

Границы биомов (по температуре/влажности/рельефу) определяет worldgen.py;
здесь — только содержимое. Все ссылки на блоки проверяются в validate().
"""
from game_data.definitions import BiomeDef
from game_data.registry import Registry

BIOMES = Registry('биом')

OCEAN = BIOMES.register(BiomeDef(
    id=1, key='ocean', name='Океан',
    surface='sand', subsurface='sand', underwater='sand'))

BEACH = BIOMES.register(BiomeDef(
    id=2, key='beach', name='Пляж',
    surface='sand', subsurface='sand', underwater='sand',
    decorations=(('sugar_cane', 0.04),)))

PLAINS = BIOMES.register(BiomeDef(
    id=3, key='plains', name='Равнины',
    surface='grass', subsurface='dirt', underwater='sand',
    trees=(('oak', 1),), tree_chance=0.003,
    decorations=(('tall_grass', 0.06), ('flower_red', 0.012),
                 ('flower_yellow', 0.015))))

FOREST = BIOMES.register(BiomeDef(
    id=4, key='forest', name='Лес',
    surface='grass', subsurface='dirt', underwater='sand',
    trees=(('oak', 5), ('birch', 1)), tree_chance=0.045,
    decorations=(('tall_grass', 0.03), ('mushroom_brown', 0.006),
                 ('flower_yellow', 0.008))))

BIRCH_FOREST = BIOMES.register(BiomeDef(
    id=5, key='birch_forest', name='Берёзовая роща',
    surface='grass', subsurface='dirt', underwater='sand',
    trees=(('birch', 5), ('oak', 1)), tree_chance=0.04,
    decorations=(('tall_grass', 0.03), ('flower_red', 0.01),
                 ('mushroom_brown', 0.004))))

TAIGA = BIOMES.register(BiomeDef(
    id=6, key='taiga', name='Тайга',
    surface='grass', subsurface='dirt', underwater='gravel',
    trees=(('spruce', 1),), tree_chance=0.035,
    decorations=(('mushroom_red', 0.008), ('mushroom_brown', 0.008),
                 ('tall_grass', 0.01))))

DESERT = BIOMES.register(BiomeDef(
    id=7, key='desert', name='Пустыня',
    surface='sand', subsurface='sand', underwater='sand',
    decorations=(('cactus', 0.006), ('dead_bush', 0.01))))

SAVANNA = BIOMES.register(BiomeDef(
    id=8, key='savanna', name='Саванна',
    surface='grass', subsurface='dirt', underwater='sand',
    trees=(('oak', 1),), tree_chance=0.004,
    decorations=(('tall_grass', 0.12), ('dead_bush', 0.015))))

MOUNTAINS = BIOMES.register(BiomeDef(
    id=9, key='mountains', name='Горы',
    surface='grass', subsurface='dirt', underwater='gravel',
    trees=(('spruce', 1),), tree_chance=0.008,
    decorations=(('stone', 0.004),)))  # валуны

SNOWY_MOUNTAINS = BIOMES.register(BiomeDef(
    id=10, key='snowy_mountains', name='Снежные горы',
    surface='snow', subsurface='stone', underwater='gravel',
    trees=(('spruce', 1),), tree_chance=0.004,
    decorations=(('stone', 0.003),)))

SWAMP = BIOMES.register(BiomeDef(
    id=11, key='swamp', name='Болото',
    surface='grass', subsurface='dirt', underwater='dirt',
    trees=(('oak', 1),), tree_chance=0.015,
    decorations=(('mushroom_brown', 0.02), ('mushroom_red', 0.008),
                 ('tall_grass', 0.04), ('sugar_cane', 0.05))))
