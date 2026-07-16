# -*- coding: utf-8 -*-
"""Фототур по биомам: находит их в мире, снимает скриншоты и выходит.

Запуск:  .venv/bin/python tools/biome_shots.py [папка_для_снимков]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OUT_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('.')

from ursina import Entity, Ursina, Vec3, application, camera, invoke, scene, window  # noqa: E402

if sys.platform == 'darwin':  # те же обходы, что в main.py
    from panda3d.core import loadPrcFileData
    loadPrcFileData('', 'notify-level-glgsg fatal')
    Entity.default_shader = None

from game_data.definitions import rgb  # noqa: E402
from settings import FOG_END, FOG_START, WORLD_SEED  # noqa: E402
from world import World  # noqa: E402
from worldgen import SEA  # noqa: E402

SKY = rgb(140, 190, 237)
app = Ursina()
window.update_aspect_ratio()
window.color = SKY
scene.fog_color = SKY
scene.fog_density = (FOG_START, FOG_END)

world = World(WORLD_SEED)

# --- ищем по одному представителю каждой цели ---
WANTED = ['ocean', 'river', 'mountains', 'snowy_mountains', 'desert',
          'taiga', 'swamp', 'savanna']
targets = {}
for radius in range(0, 1500, 24):
    pts = ([(0, 0)] if radius == 0 else
           [(dx, dz) for dx in range(-radius, radius + 1, 24)
            for dz in range(-radius, radius + 1, 24)
            if max(abs(dx), abs(dz)) == radius])
    for x, z in pts:
        col = world.gen.column_at(x, z)
        if 'river' not in targets and col.river:
            targets['river'] = (x, z)
        if col.biome in WANTED and col.biome not in targets:
            targets[col.biome] = (x, z)
    if len(targets) >= len(WANTED):
        break
print('найдено:', {k: v for k, v in targets.items()})

queue = [(name, targets[name]) for name in WANTED if name in targets]


def next_shot():
    if not queue:
        print('TOUR OK')
        application.quit()
        return
    name, (x, z) = queue[0]
    col = world.gen.column_at(x, z)
    print(f'снимаем {name} в ({x}, {z}), биом {col.biome}, h={col.height}')
    world.pregenerate(Vec3(x, 0, z))
    ground = max(col.height, SEA)
    camera.position = Vec3(x + 0.5, ground + 13, z - 20)
    camera.rotation = Vec3(28, 0, 0)
    invoke(take_shot, delay=0.7)


def take_shot():
    name, _ = queue.pop(0)
    path = str(OUT_DIR / f'shot_{name}.png')
    base.win.saveScreenshot(path)  # noqa: F821
    print('->', path)
    invoke(next_shot, delay=0.1)


invoke(next_shot, delay=1.0)
app.run()
