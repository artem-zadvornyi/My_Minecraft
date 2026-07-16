# -*- coding: utf-8 -*-
"""Замеры производительности мира (без окна).

Меряет: генерацию чанков, построение мешей, латентность правки блока,
размеры мешей. Для FPS используйте:  python main.py --benchmark
Запуск:  .venv/bin/python tools/benchmark.py
"""
import statistics
import sys
from math import floor
from time import perf_counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ursina import Ursina  # noqa: E402

from settings import CHUNK_SIZE, RENDER_DISTANCE, WORLD_SEED  # noqa: E402
from world import World  # noqa: E402


def noise_backend():
    """Какая реализация шума реально используется (порядок как в world.py)."""
    try:
        import noise  # noqa: F401
        return 'noise (C)'
    except ImportError:
        pass
    try:
        import perlin_noise  # noqa: F401
        return 'perlin-noise (чистый Python)'
    except ImportError:
        return 'встроенный Перлин (чистый Python)'


app = Ursina(window_type='none')
world = World(WORLD_SEED)
spawn = world.find_spawn()
pc = (floor(spawn.x / CHUNK_SIZE), floor(spawn.z / CHUNK_SIZE))
coords = [(pc[0] + dx, pc[1] + dz)
          for dx in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1)
          for dz in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1)]

# --- генерация чанков ---
gen_times = []
for c in coords:
    t0 = perf_counter()
    world._generate_chunk(c)
    gen_times.append((perf_counter() - t0) * 1000)

# --- построение мешей ---
mesh_times = []
for c in coords:
    t0 = perf_counter()
    world._build_chunk_mesh(world.chunks[c])
    mesh_times.append((perf_counter() - t0) * 1000)

# --- размеры мешей ---
solid_v = sum(len(ch.solid_entity.model.vertices)
              for ch in world.chunks.values() if ch.solid_entity)
water_v = sum(len(ch.water_entity.model.vertices)
              for ch in world.chunks.values() if ch.water_entity)

# --- латентность правки блока (set_block с перестройкой меша) ---
edit_times = []
bx, bz = floor(spawn.x), floor(spawn.z)
h = world.height_at(bx, bz)
for i in range(10):
    t0 = perf_counter()
    world.set_block((bx + i, h + 2, bz), 'stone')
    edit_times.append((perf_counter() - t0) * 1000)

print()
print('=== БАЗОВЫЕ ЗАМЕРЫ ===')
print(f'Python {sys.version.split()[0]}, шум: {noise_backend()}')
print(f'Чанков: {len(coords)} ({CHUNK_SIZE}x{CHUNK_SIZE}, радиус {RENDER_DISTANCE})')
print(f'Блоков в памяти: {len(world.blocks)}')
print(f'Генерация чанка, мс: медиана {statistics.median(gen_times):.1f}, '
      f'макс {max(gen_times):.1f}')
print(f'Меш чанка, мс: медиана {statistics.median(mesh_times):.1f}, '
      f'макс {max(mesh_times):.1f}')
print(f'Вершины мешей: твёрдые {solid_v}, вода {water_v} '
      f'(треугольников ~{(solid_v + water_v) // 2})')
print(f'Правка блока (с перестройкой меша), мс: '
      f'медиана {statistics.median(edit_times):.1f}, макс {max(edit_times):.1f}')
