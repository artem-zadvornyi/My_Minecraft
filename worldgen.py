# -*- coding: utf-8 -*-
"""Процедурная генерация мира: слои шума, биомы, реки, деревья, украшения.

Вся генерация — чистые детерминированные функции от (x, z, зерно):
- никакого состояния, зависящего от порядка загрузки чанков;
- дерево может пересекать границу чанков: каждый чанк сканирует колонки
  с запасом TREE_MARGIN и берёт только блоки, попавшие в его границы;
- клеточные ГПСЧ сидируются только целыми числами (hash строк в Python
  нестабилен между процессами и запрещён).

Слои шума:
  continent   — континентальность: океаны и суша
  elevation   — базовый рельеф: холмы и долины
  erosion     — эрозия: гладкие равнины против скал и обрывов
  temperature — температура: пустыни против тайги и снегов
  humidity    — влажность: болота и леса против саванн
  river       — реки: русла там, где |шум| близок к нулю
"""
import random
from collections import namedtuple
from math import floor

from game_data import BIOMES, BLOCKS
from game_data.blocks import (DIRT, GRAVEL, SAND, SNOW, STONE, SUGAR_CANE,
                              WATER)
from settings import (CHUNK_SIZE, COARSE_STEP, DIRT_DEPTH, RIVER_WIDTH,
                      ROCK_LINE, SNOW_LINE, TREE_MARGIN, WATER_LEVEL,
                      WORLD_HEIGHT)

SEA = WATER_LEVEL

# (масштаб, октавы, сдвиг зерна) каждого слоя шума
_FIELDS = {
    'continent': (260.0, 2, 101),
    'elevation': (90.0, 3, 102),
    'erosion': (170.0, 2, 103),
    'temperature': (210.0, 2, 104),
    'humidity': (170.0, 2, 105),
    'river': (130.0, 1, 106),
}

# соли клеточных ГПСЧ (только целые числа!)
_SALT_TREE = 0x51F15EED
_SALT_DECO = 0x0DECA707
_SALT_SWAMP = 0x5A3B00B5

Column = namedtuple('Column', 'height biome river')
"""Итог генерации колонки: высота поверхности, ключ биома, река ли здесь."""


def _make_noise(seed, octaves):
    """Функция noise2(x, z) -> примерно -1..1 (как в М1, с фолбэками)."""
    try:
        from noise import pnoise2

        def noise2(x, z):
            return pnoise2(x, z, octaves=octaves, persistence=0.5,
                           base=seed % 256)
        return noise2
    except ImportError:
        pass
    try:
        from perlin_noise import PerlinNoise
        gens = [PerlinNoise(octaves=2 ** i, seed=seed + i)
                for i in range(octaves)]

        def noise2(x, z):
            return sum(g([x, z]) * 0.5 ** i for i, g in enumerate(gens)) * 2
        return noise2
    except ImportError:
        pass

    # резервная чистая реализация классического шума Перлина
    perm = list(range(256))
    random.Random(seed).shuffle(perm)
    perm += perm

    def _fade(t):
        return t * t * t * (t * (t * 6 - 15) + 10)

    def _grad(h, x, y):
        h &= 3
        u = x if h < 2 else y
        v = y if h < 2 else x
        return (u if h & 1 == 0 else -u) + (v if h & 2 == 0 else -v)

    def _perlin(x, y):
        xi, yi = floor(x) & 255, floor(y) & 255
        xf, yf = x - floor(x), y - floor(y)
        u, v = _fade(xf), _fade(yf)
        aa = perm[perm[xi] + yi]
        ab = perm[perm[xi] + yi + 1]
        ba = perm[perm[xi + 1] + yi]
        bb = perm[perm[xi + 1] + yi + 1]
        x1 = _grad(aa, xf, yf) + u * (_grad(ba, xf - 1, yf) - _grad(aa, xf, yf))
        x2 = (_grad(ab, xf, yf - 1)
              + u * (_grad(bb, xf - 1, yf - 1) - _grad(ab, xf, yf - 1)))
        return (x1 + v * (x2 - x1)) * 0.7

    def noise2(x, z):
        return sum(_perlin(x * 2 ** i, z * 2 ** i) * 0.5 ** i
                   for i in range(octaves))
    return noise2


def _smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _cell_rng(seed, x, z, salt):
    """Детерминированный ГПСЧ клетки, независимый от порядка чанков."""
    return random.Random(
        (x * 341873128712) ^ (z * 132897987541) ^ (seed * 2654435761) ^ salt)


class Generator:
    """Детерминированный генератор: колонки, биомы, деревья, украшения."""

    def __init__(self, seed):
        self.seed = seed
        self._noises = {
            name: _make_noise(seed + shift, octaves)
            for name, (scale, octaves, shift) in _FIELDS.items()}
        self._scales = {name: spec[0] for name, spec in _FIELDS.items()}
        self._coarse = {name: {} for name in _FIELDS}  # узлы грубой сетки
        self._columns = {}   # (x, z) -> Column
        self._trees = {}     # (x, z) -> (ствол, листва) или None

    # ------------------------------------------------------------------
    # Слои шума (грубая сетка + билинейная интерполяция, как в М1)
    # ------------------------------------------------------------------
    def _coarse_node(self, name, gx, gz):
        cache = self._coarse[name]
        key = (gx, gz)
        v = cache.get(key)
        if v is None:
            scale = self._scales[name]
            v = self._noises[name](gx * COARSE_STEP / scale,
                                   gz * COARSE_STEP / scale)
            cache[key] = v
        return v

    def field_at(self, name, x, z):
        gx, gz = floor(x / COARSE_STEP), floor(z / COARSE_STEP)
        fx = x / COARSE_STEP - gx
        fz = z / COARSE_STEP - gz
        n00 = self._coarse_node(name, gx, gz)
        n10 = self._coarse_node(name, gx + 1, gz)
        n01 = self._coarse_node(name, gx, gz + 1)
        n11 = self._coarse_node(name, gx + 1, gz + 1)
        return (n00 * (1 - fx) * (1 - fz) + n10 * fx * (1 - fz)
                + n01 * (1 - fx) * fz + n11 * fx * fz)

    # ------------------------------------------------------------------
    # Колонка: высота + биом + река
    # ------------------------------------------------------------------
    @staticmethod
    def classify(land, height, mount, temp, hum):
        """Ключ биома по факторам колонки (чистая функция, тестируется)."""
        if land < 0.35:
            return 'ocean'
        if mount > 0.5:
            if temp < -0.2 or height >= SNOW_LINE:
                return 'snowy_mountains'
            return 'mountains'
        if hum > 0.28 and height <= SEA + 3 and temp > -0.3:
            return 'swamp'
        if height <= SEA + 1:
            return 'beach'
        if temp > 0.25:
            return 'desert' if hum < 0.02 else 'savanna'
        if temp < -0.28:
            return 'taiga'
        if hum > 0.02:
            return 'forest' if temp >= -0.03 else 'birch_forest'
        return 'plains'

    def column_at(self, x, z):
        key = (x, z)
        col = self._columns.get(key)
        if col is not None:
            return col
        c = self.field_at('continent', x, z)
        e = self.field_at('elevation', x, z)
        er = (self.field_at('erosion', x, z) + 1) / 2   # 0 скалы .. 1 гладко
        t = self.field_at('temperature', x, z)
        hum = self.field_at('humidity', x, z)
        rough = 1 - er

        # узкая прибрежная полоса: суша быстро поднимается от моря
        land = _smoothstep((c + 0.18) / 0.20)
        # горный фактор: высокий рельеф + низкая эрозия (пороги по p80-p99
        # реального распределения шума)
        mount = _smoothstep((e * 0.8 + rough - 0.62) / 0.22)

        # суша: холмы + горы; долины мельче холмов, чтобы внутренняя суша
        # не проседала до уровня моря
        ebase = e * (4 + rough * 7)
        if ebase < 0:
            ebase *= 0.3
        h_land = SEA + 4.5 + ebase + mount * (15 + e * 8)
        # в скалистых горных зонах — террасы-обрывы
        cliff = mount * _smoothstep((rough - 0.5) / 0.2)
        if cliff > 0:
            h_land = h_land * (1 - cliff) + round(h_land / 5) * 5 * cliff
        # дно океана
        h_ocean = SEA - 7 + e * 3.5
        hf = h_ocean + (h_land - h_ocean) * land

        # реки: русло там, где |шум| мал; в горах рек нет.
        # Домен повёрнут и искривлён другими полями: иначе однооктавный
        # Перлин даёт прямые русла вдоль линий своей решётки
        river = False
        if land > 0.45 and mount < 0.85:
            wx = 0.857 * x - 0.515 * z + e * 40
            wz = 0.515 * x + 0.857 * z + hum * 40
            rv = abs(self.field_at('river', wx, wz))
            width = RIVER_WIDTH * (1 + er)  # в равнинах шире
            if rv < width:
                bank = _smoothstep(rv / width)   # 0 центр .. 1 берег
                channel = SEA - 2.5 + bank * 1.5
                carved = hf * bank + channel * (1 - bank)
                if carved < hf:
                    hf = carved
                river = bank < 0.8

        h = max(1, min(int(round(hf)), WORLD_HEIGHT - 6))
        biome = self.classify(land, h, mount, t, hum)
        if biome == 'swamp':
            # болото прижато к морю: детерминированные лужи глубиной 1
            r = _cell_rng(self.seed, x, z, _SALT_SWAMP).random()
            h = SEA - 1 + int(r * 3)
        col = Column(h, biome, river)
        self._columns[key] = col
        return col

    # ------------------------------------------------------------------
    # Деревья (детерминированно, могут пересекать границы чанков)
    # ------------------------------------------------------------------
    def tree_at(self, x, z):
        """(ствол, листва) дерева с корнем в (x, z) или None."""
        key = (x, z)
        if key in self._trees:
            return self._trees[key]
        tree = None
        col = self.column_at(x, z)
        biome = BIOMES[col.biome]
        if (biome.trees and biome.tree_chance > 0 and not col.river
                and col.height > SEA
                and not (col.biome == 'mountains' and col.height >= ROCK_LINE)):
            rng = _cell_rng(self.seed, x, z, _SALT_TREE)
            if rng.random() < biome.tree_chance:
                total = sum(w for _, w in biome.trees)
                pick = rng.random() * total
                kind = biome.trees[-1][0]
                for k, w in biome.trees:
                    pick -= w
                    if pick < 0:
                        kind = k
                        break
                tree = _build_tree(kind, x, col.height, z, rng)
        self._trees[key] = tree
        return tree

    # ------------------------------------------------------------------
    # Украшения (цветы, грибы, кактусы, тростник, валуны)
    # ------------------------------------------------------------------
    def decorations_at(self, x, z):
        """Список [(pos, ключ)] украшений колонки (без учёта занятости)."""
        col = self.column_at(x, z)
        if col.river or col.height < SEA:
            return []
        biome = BIOMES[col.biome]
        if not biome.decorations:
            return []
        rng = _cell_rng(self.seed, x, z, _SALT_DECO)
        roll = rng.random()
        acc = 0.0
        for block_key, chance in biome.decorations:
            acc += chance
            if roll >= acc:
                continue
            base = (x, col.height + 1, z)
            if block_key == SUGAR_CANE.key:
                # тростник — только у кромки воды
                if col.height > SEA + 1 or not self._water_nearby(x, z):
                    return []
                return [((x, col.height + 1 + i, z), block_key)
                        for i in range(rng.randint(2, 3))]
            if block_key == 'cactus':
                return [((x, col.height + 1 + i, z), block_key)
                        for i in range(rng.randint(1, 3))]
            if block_key == STONE.key:  # валун
                return [(base, block_key)]
            return [(base, block_key)]
        return []

    def _water_nearby(self, x, z):
        """Есть ли вода в одной из четырёх соседних колонок."""
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if self.column_at(x + dx, z + dz).height < SEA:
                return True
        return False

    # ------------------------------------------------------------------
    # Сборка чанка
    # ------------------------------------------------------------------
    def generate_chunk(self, coord):
        """Все блоки чанка: рельеф -> деревья -> украшения.

        Результат зависит только от (зерно, координаты) — порядок
        генерации чанков значения не имеет.
        """
        cx, cz = coord
        x0, z0 = cx * CHUNK_SIZE, cz * CHUNK_SIZE
        x1, z1 = x0 + CHUNK_SIZE, z0 + CHUNK_SIZE
        blocks = {}

        # 1) рельеф и вода
        for x in range(x0, x1):
            for z in range(z0, z1):
                col = self.column_at(x, z)
                h = col.height
                biome = BIOMES[col.biome]
                if h < SEA:
                    surface = biome.underwater
                    if SEA - h > 4:
                        surface = GRAVEL.key  # глубокое дно
                else:
                    surface = biome.surface
                    if col.biome == 'mountains':
                        if h >= SNOW_LINE:
                            surface = SNOW.key
                        elif h >= ROCK_LINE:
                            surface = STONE.key
                subsurface = biome.subsurface
                for y in range(0, h + 1):
                    if y <= h - DIRT_DEPTH:
                        bid = STONE.key
                    elif y < h:
                        bid = subsurface
                    else:
                        bid = surface
                    blocks[(x, y, z)] = bid
                for y in range(h + 1, SEA + 1):
                    blocks[(x, y, z)] = WATER.key

        # 2) деревья (сканируем с запасом — кроны соседних корней)
        for x in range(x0 - TREE_MARGIN, x1 + TREE_MARGIN):
            for z in range(z0 - TREE_MARGIN, z1 + TREE_MARGIN):
                tree = self.tree_at(x, z)
                if tree is None:
                    continue
                trunk, leaves = tree
                for pos, bid in leaves.items():
                    if (x0 <= pos[0] < x1 and z0 <= pos[2] < z1
                            and pos not in blocks):
                        blocks[pos] = bid
                for pos, bid in trunk.items():
                    if x0 <= pos[0] < x1 and z0 <= pos[2] < z1:
                        blocks[pos] = bid

        # 3) украшения — только в свободные клетки (деревья уже стоят)
        for x in range(x0, x1):
            for z in range(z0, z1):
                for pos, bid in self.decorations_at(x, z):
                    if pos not in blocks and pos[1] < WORLD_HEIGHT:
                        blocks[pos] = bid
        return blocks

    # ------------------------------------------------------------------
    # Точка возрождения
    # ------------------------------------------------------------------
    def find_spawn(self):
        """Безопасный спавн: суша, не река; лучше равнина или лес."""
        preferred = {'plains', 'forest', 'birch_forest'}
        fallback = None
        for radius in range(0, 400, 8):
            points = ([(0, 0)] if radius == 0 else
                      [(dx, dz) for dx in range(-radius, radius + 1, 8)
                       for dz in range(-radius, radius + 1, 8)
                       if max(abs(dx), abs(dz)) == radius])
            for dx, dz in points:
                col = self.column_at(dx, dz)
                if col.height <= SEA + 1 or col.river:
                    continue  # под водой/у воды не спавнимся
                if col.biome in preferred:
                    return (dx + 0.5, col.height + 2, dz + 0.5)
                if fallback is None and col.biome not in ('ocean', 'beach'):
                    fallback = (dx + 0.5, col.height + 2, dz + 0.5)
        return fallback or (0.5, self.column_at(0, 0).height + 2, 0.5)


# ----------------------------------------------------------------------
# Формы деревьев (чистые функции от ГПСЧ дерева)
# ----------------------------------------------------------------------
def _canopy_layer(leaves, x, y, z, radius, leaf, rng, skip_corners=True):
    for dx in range(-radius, radius + 1):
        for dz in range(-radius, radius + 1):
            if dx == 0 and dz == 0:
                continue
            if (skip_corners and radius > 1 and abs(dx) == radius
                    and abs(dz) == radius and rng.random() < 0.6):
                continue  # рваные углы — естественнее
            leaves[(x + dx, y, z + dz)] = leaf
    leaves[(x, y, z)] = leaf


def _build_tree(kind, x, ground, z, rng):
    """Блоки дерева: (ствол {pos: key}, листва {pos: key}).

    Радиус кроны не превышает TREE_MARGIN.
    """
    trunk, leaves = {}, {}
    if kind == 'oak':
        th = rng.randint(3, 5)
        for i in range(1, th + 1):
            trunk[(x, ground + i, z)] = 'wood'
        top = ground + th
        _canopy_layer(leaves, x, top, z, 2, 'leaves', rng)
        _canopy_layer(leaves, x, top + 1, z, 2, 'leaves', rng)
        _canopy_layer(leaves, x, top + 2, z, 1, 'leaves', rng)
        leaves[(x, top + 3, z)] = 'leaves'
    elif kind == 'birch':
        th = rng.randint(5, 7)
        for i in range(1, th + 1):
            trunk[(x, ground + i, z)] = 'birch_log'
        top = ground + th
        _canopy_layer(leaves, x, top - 1, z, 2, 'birch_leaves', rng)
        _canopy_layer(leaves, x, top, z, 1, 'birch_leaves', rng)
        _canopy_layer(leaves, x, top + 1, z, 1, 'birch_leaves', rng)
        leaves[(x, top + 2, z)] = 'birch_leaves'
    else:  # spruce — ель конусом
        th = rng.randint(6, 9)
        for i in range(1, th + 1):
            trunk[(x, ground + i, z)] = 'spruce_log'
        for dy in range(2, th + 2):
            dist_top = th + 1 - dy
            if dist_top <= 0:
                radius = 0
            elif dist_top % 2 == 1:
                radius = 1
            else:
                radius = 2
            if radius:
                _canopy_layer(leaves, x, ground + dy, z, radius,
                              'spruce_leaves', rng, skip_corners=False)
        leaves[(x, ground + th + 1, z)] = 'spruce_leaves'
        leaves[(x, ground + th + 2, z)] = 'spruce_leaves'
    return trunk, leaves
