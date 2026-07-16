# -*- coding: utf-8 -*-
"""Мир: процедурная генерация чанками, построение мешей, воксельный рейкаст.

Для производительности каждый чанк — это ОДНА сущность Ursina с общим мешем
(отдельная — для полупрозрачной воды), а не тысячи отдельных кубов.
Коллизии и выбор блока делаются по словарю блоков, без физики Ursina.
Содержимое чанков считает worldgen.Generator; здесь — жизненный цикл
чанков, меши и правки игрока.
"""
from math import floor

from panda3d.core import TransparencyAttrib
from ursina import Entity, Mesh, Vec3, destroy
from ursina.color import Color

from game_data import BLOCKS
from rendering.texture_atlas import get_atlas
from settings import (CHUNK_SIZE, FOG_END, FOG_START, REACH,
                      RENDER_DISTANCE, WORLD_SEED)
from worldgen import Generator


_WHITE = Color(1, 1, 1, 1)


def _face_uvs(face_index, corners, rect):
    """UV четырёх вершин грани: развёртка тайла по осям грани.

    Для верха/низа текстура ложится в плане XZ, для боковых граней
    вертикаль текстуры следует за Y (верх тайла — верх блока).
    """
    u0, v0, u1, v1 = rect
    result = []
    for cx, cy, cz in corners:
        if face_index in (0, 1):    # верх / низ
            a, b = cx, cz
        elif face_index in (2, 3):  # +x / -x
            a, b = cz, cy
        else:                       # +z / -z
            a, b = cx, cy
        result.append((u0 + (u1 - u0) * a, v0 + (v1 - v0) * b))
    return result


# Грани куба: (смещение к соседу, 4 вершины обхода, множитель яркости).
# Разная яркость граней создаёт эффект объёма без настоящего освещения.
_FACES = (
    ((0, 1, 0), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)), 1.00),  # верх
    ((0, -1, 0), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)), 0.45),  # низ
    ((1, 0, 0), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)), 0.72),  # +x
    ((-1, 0, 0), ((0, 0, 1), (0, 1, 1), (0, 1, 0), (0, 0, 0)), 0.72),  # -x
    ((0, 0, 1), ((1, 0, 1), (1, 1, 1), (0, 1, 1), (0, 0, 1)), 0.85),  # +z
    ((0, 0, -1), ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)), 0.62),  # -z
)


class Chunk:
    """Один чанк 16x16: множество позиций блоков и его меши."""

    def __init__(self, coord):
        self.coord = coord       # (cx, cz)
        self.positions = set()   # мировые координаты блоков чанка
        self.solid_entity = None  # меш непрозрачных блоков
        self.water_entity = None  # полупрозрачный меш воды


class World:
    def __init__(self, seed=WORLD_SEED):
        self.seed = seed
        self.gen = Generator(seed)  # вся генерация — в worldgen.py
        self.blocks = {}   # (x, y, z) -> id блока (только загруженные чанки)
        self.chunks = {}   # (cx, cz) -> Chunk
        self.edits = {}    # правки игрока: (x, y, z) -> id или None (сломан)
        self._face_styles = {}    # кэш граней: (ключ, грань) -> (uv, Color)
        self._gen_queue = []      # чанки, ожидающие генерации
        self._mesh_queue = []     # сгенерированы, ждут построения меша
        self._dirty = set()       # чанки, ожидающие перестройки меша
        self._last_player_chunk = None

    # ------------------------------------------------------------------
    # Рельеф (делегируется генератору)
    # ------------------------------------------------------------------
    def height_at(self, x, z):
        """Высота поверхности в колонке (x, z)."""
        return self.gen.column_at(x, z).height

    def biome_at(self, x, z):
        """Ключ биома в колонке (x, z)."""
        return self.gen.column_at(x, z).biome

    def find_spawn(self):
        """Безопасная точка возрождения (суша, не река, лучше равнина)."""
        x, y, z = self.gen.find_spawn()
        return Vec3(x, y, z)

    # ------------------------------------------------------------------
    # Доступ к блокам
    # ------------------------------------------------------------------
    @staticmethod
    def chunk_coord(pos):
        return (floor(pos[0] / CHUNK_SIZE), floor(pos[2] / CHUNK_SIZE))

    def get_block(self, pos):
        return self.blocks.get(pos)

    def is_solid(self, pos):
        """Есть ли в клетке блок с коллизией (для физики игрока)."""
        bid = self.blocks.get(pos)
        return bid is not None and BLOCKS[bid].collision

    def is_liquid(self, pos):
        """Жидкость ли в клетке (плавучесть, гашение урона от падения)."""
        bid = self.blocks.get(pos)
        return bid is not None and BLOCKS[bid].liquid

    def set_block(self, pos, bid):
        """Поставить блок (bid) или сломать (bid=None) с обновлением меша."""
        self.edits[pos] = bid  # правка переживает выгрузку чанка
        coord = self.chunk_coord(pos)
        chunk = self.chunks.get(coord)
        if chunk is None:
            return  # чанк не загружен — правка применится при генерации
        if bid is None:
            self.blocks.pop(pos, None)
            chunk.positions.discard(pos)
        else:
            self.blocks[pos] = bid
            chunk.positions.add(pos)
        self._build_chunk_mesh(chunk)
        # правка на границе чанка меняет видимые грани соседа
        x, _, z = pos
        for ncoord in {self.chunk_coord((x - 1, 0, z)),
                       self.chunk_coord((x + 1, 0, z)),
                       self.chunk_coord((x, 0, z - 1)),
                       self.chunk_coord((x, 0, z + 1))}:
            if ncoord != coord and ncoord in self.chunks:
                self._build_chunk_mesh(self.chunks[ncoord])

    # ------------------------------------------------------------------
    # Генерация чанков
    # ------------------------------------------------------------------
    def _generate_chunk(self, coord):
        chunk = Chunk(coord)
        self.chunks[coord] = chunk
        # блоки чанка целиком считает генератор (детерминированно,
        # независимо от порядка загрузки чанков)
        new_blocks = self.gen.generate_chunk(coord)
        self.blocks.update(new_blocks)
        chunk.positions = set(new_blocks)
        # применяем сохранённые правки игрока
        for pos, bid in self.edits.items():
            if self.chunk_coord(pos) == coord:
                if bid is None:
                    self.blocks.pop(pos, None)
                    chunk.positions.discard(pos)
                else:
                    self.blocks[pos] = bid
                    chunk.positions.add(pos)
        return chunk

    # ------------------------------------------------------------------
    # Построение мешей
    # ------------------------------------------------------------------
    def _face_style(self, bid, face_index, shade):
        """(цвет, 4 UV-координаты) грани блока с кэшированием.

        С текстурой цвет вершин — только затенение (и tint, если задан);
        без текстуры — белый тайл атласа + запасной цвет блока.
        UV зависят только от (блок, грань), поэтому кэшируются целиком.
        """
        key = (bid, face_index)
        style = self._face_styles.get(key)
        if style is None:
            block = BLOCKS[bid]
            atlas = get_atlas()
            rect = atlas.uv(block.faces.by_index(face_index)) if atlas else None
            if rect is not None:
                base = block.tint if block.tint is not None else _WHITE
            else:
                rect = atlas.white_uv if atlas else (0.0, 0.0, 1.0, 1.0)
                if face_index == 0 and block.top_color is not None:
                    base = block.top_color
                elif face_index == 1 and block.bottom_color is not None:
                    base = block.bottom_color
                else:
                    base = block.color
            col = Color(base[0] * shade, base[1] * shade, base[2] * shade,
                        base[3])
            corners = _FACES[face_index][1]
            style = (col, tuple(_face_uvs(face_index, corners, rect)))
            self._face_styles[key] = style
        return style

    def _build_chunk_mesh(self, chunk):
        """Собирает меш чанка: только грани, видимые снаружи."""
        blocks = self.blocks
        solid = ([], [], [], [])  # вершины, треугольники, цвета, uv
        liquid = ([], [], [], [])
        for pos in chunk.positions:
            bid = blocks.get(pos)
            if bid is None:
                continue
            x, y, z = pos
            block = BLOCKS[bid]
            if block.render == 'cross':
                # растение: два пересечённых по диагоналям квада
                verts, tris, cols, uvs = solid
                col, uv_quad = self._face_style(bid, 4, 1.0)
                for (ax, az), (bx, bz) in (((0, 0), (1, 1)), ((1, 0), (0, 1))):
                    b = len(verts)
                    verts += ((x + ax, y, z + az), (x + bx, y, z + bz),
                              (x + bx, y + 1, z + bz), (x + ax, y + 1, z + az))
                    tris += (b, b + 1, b + 2, b, b + 2, b + 3)
                    cols += (col, col, col, col)
                    uvs += uv_quad
                continue
            is_liquid = block.liquid
            for fi, (n, corners, shade) in enumerate(_FACES):
                npos = (x + n[0], y + n[1], z + n[2])
                if npos[1] < 0:
                    continue  # дно мира не рисуем
                nb = blocks.get(npos)
                if is_liquid:
                    # жидкость рисует грань только на границе с воздухом
                    if nb is not None:
                        continue
                    verts, tris, cols, uvs = liquid
                else:
                    # грань скрыта, если сосед непрозрачный
                    if nb is not None and not BLOCKS[nb].transparent:
                        continue
                    verts, tris, cols, uvs = solid
                b = len(verts)
                for c in corners:
                    verts.append((x + c[0], y + c[1], z + c[2]))
                tris += (b, b + 1, b + 2, b, b + 2, b + 3)
                col, uv_quad = self._face_style(bid, fi, shade)
                cols += (col, col, col, col)
                uvs += uv_quad
        chunk.solid_entity = self._apply_mesh(
            chunk.solid_entity, *solid, water=False)
        chunk.water_entity = self._apply_mesh(
            chunk.water_entity, *liquid, water=True)

    @staticmethod
    def _apply_mesh(entity, verts, tris, cols, uvs, water):
        # сущность пересоздаётся целиком: замена model на живой сущности
        # оставляет артефакты старой геометрии
        if entity:
            destroy(entity)
        if not verts:
            return None
        mesh = Mesh(vertices=verts, triangles=tris, colors=cols, uvs=uvs,
                    static=True)
        entity = Entity(model=mesh, double_sided=True)
        atlas = get_atlas()
        if atlas is not None:
            entity.texture = atlas.texture
        # новые сущности не получают туман автоматически — задаём вручную
        entity.set_shader_input('fog_start', FOG_START)
        entity.set_shader_input('fog_end', FOG_END)
        if water:
            entity.setTransparency(TransparencyAttrib.M_alpha)
        else:
            # альфа-тест: дырки в текстурах растений (без сортировки)
            entity.setTransparency(TransparencyAttrib.M_binary)
        return entity

    # ------------------------------------------------------------------
    # Загрузка / выгрузка чанков вокруг игрока
    # ------------------------------------------------------------------
    def pregenerate(self, center):
        """Синхронная генерация стартовой зоны (перед запуском игры)."""
        pc = (floor(center.x / CHUNK_SIZE), floor(center.z / CHUNK_SIZE))
        coords = sorted(
            ((pc[0] + dx, pc[1] + dz)
             for dx in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1)
             for dz in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1)),
            key=lambda c: (c[0] - pc[0]) ** 2 + (c[1] - pc[1]) ** 2)
        for coord in coords:
            self._generate_chunk(coord)
        for coord in coords:
            self._build_chunk_mesh(self.chunks[coord])
        self._last_player_chunk = pc

    def update_chunks(self, player_pos):
        """Вызывается каждый кадр: подгружает чанки по мере движения.

        За кадр генерируется не больше одного чанка, чтобы не было рывков.
        """
        pc = (floor(player_pos.x / CHUNK_SIZE), floor(player_pos.z / CHUNK_SIZE))
        if pc != self._last_player_chunk:
            self._last_player_chunk = pc
            needed = {(pc[0] + dx, pc[1] + dz)
                      for dx in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1)
                      for dz in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1)}
            # очередь отсортирована так, что ближние чанки берутся первыми
            self._gen_queue = sorted(
                (c for c in needed if c not in self.chunks),
                key=lambda c: (c[0] - pc[0]) ** 2 + (c[1] - pc[1]) ** 2,
                reverse=True)
            # выгружаем чанки далеко за пределами видимости
            far = [c for c in self.chunks
                   if max(abs(c[0] - pc[0]), abs(c[1] - pc[1])) > RENDER_DISTANCE + 1]
            for coord in far:
                self._unload_chunk(coord)
        # бюджет кадра: генерация и меш разнесены по разным кадрам,
        # чтобы пиковый кадр не тянул обе стоимости сразу
        if self._mesh_queue:
            coord = self._mesh_queue.pop(0)
            if coord in self.chunks:
                self._build_chunk_mesh(self.chunks[coord])
                # сосед теперь может скрыть грани на общей границе
                for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nc = (coord[0] + d[0], coord[1] + d[1])
                    if nc in self.chunks:
                        self._dirty.add(nc)
        elif self._gen_queue:
            coord = self._gen_queue.pop()
            if coord not in self.chunks:
                self._generate_chunk(coord)
                self._mesh_queue.append(coord)
        elif self._dirty:
            coord = self._dirty.pop()
            if coord in self.chunks:
                self._build_chunk_mesh(self.chunks[coord])

    def _unload_chunk(self, coord):
        chunk = self.chunks.pop(coord)
        for pos in chunk.positions:
            self.blocks.pop(pos, None)
        if chunk.solid_entity:
            destroy(chunk.solid_entity)
        if chunk.water_entity:
            destroy(chunk.water_entity)
        self._dirty.discard(coord)
        if coord in self._mesh_queue:
            self._mesh_queue.remove(coord)

    # ------------------------------------------------------------------
    # Воксельный рейкаст
    # ------------------------------------------------------------------
    def raycast(self, origin, direction, max_dist=REACH):
        """Луч по сетке блоков (алгоритм Аманатидеса—Ву).

        Возвращает (позиция_блока, позиция_перед_ним) или (None, None).
        Вода лучом не выбирается.
        """
        ox, oy, oz = origin.x, origin.y, origin.z
        dx, dy, dz = direction.x, direction.y, direction.z
        x, y, z = floor(ox), floor(oy), floor(oz)
        inf = float('inf')
        step_x = 1 if dx > 0 else -1
        step_y = 1 if dy > 0 else -1
        step_z = 1 if dz > 0 else -1
        t_dx = abs(1 / dx) if dx else inf
        t_dy = abs(1 / dy) if dy else inf
        t_dz = abs(1 / dz) if dz else inf
        t_mx = ((x + (step_x > 0)) - ox) / dx if dx else inf
        t_my = ((y + (step_y > 0)) - oy) / dy if dy else inf
        t_mz = ((z + (step_z > 0)) - oz) / dz if dz else inf
        prev = None
        t = 0.0
        while t <= max_dist:
            bid = self.blocks.get((x, y, z))
            if bid is not None and not BLOCKS[bid].liquid:
                return (x, y, z), prev
            prev = (x, y, z)
            if t_mx <= t_my and t_mx <= t_mz:
                t = t_mx
                x += step_x
                t_mx += t_dx
            elif t_my <= t_mz:
                t = t_my
                y += step_y
                t_my += t_dy
            else:
                t = t_mz
                z += step_z
                t_mz += t_dz
        return None, None
