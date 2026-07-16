# -*- coding: utf-8 -*-
"""PyCraft — воксельная игра на Ursina.

Точка входа: собирает мир, игрока, инвентарь, крафт, интерфейс и режимы.
Запуск:  python main.py           — обычная игра
         python main.py --smoke   — самопроверка (запуск на пару секунд)
"""
import sys
import time
from math import floor

from ursina import (Entity, Ursina, Vec3, application, camera, held_keys,
                    invoke, mouse, scene, window)
from ursina.color import Color

from blocks import ITEMS, break_time, get_drop, rgb
from crafting import CraftingUI
from game import GameState
from inventory import Inventory
from player import Player
from settings import (APPLE_FOOD, FOG_END, FOG_START, MAX_HUNGER, REACH,
                      WORLD_SEED)
from ui import UI
from world import World

SKY_COLOR = rgb(140, 190, 237)

if sys.platform == 'darwin':
    # macOS даёт контекст OpenGL 2.1: шейдеры Ursina (GLSL 130/140) не
    # компилируются. Отключаем их — рендер идёт по классическому конвейеру
    # (вершинные цвета и туман работают), а сообщения об ошибках скрываем.
    from panda3d.core import loadPrcFileData
    loadPrcFileData('', 'notify-level-glgsg fatal')
    Entity.default_shader = None

app = Ursina()
# на macOS событие aspectRatioChanged не приходит при старте, из-за чего
# интерфейс остаётся немасштабированным — обновляем линзы вручную
window.update_aspect_ratio()
window.title = 'PyCraft — воксельный мир на Python'
window.exit_button.enabled = False
window.fps_counter.enabled = True
window.color = SKY_COLOR
scene.fog_color = SKY_COLOR
scene.fog_density = (FOG_START, FOG_END)  # линейный туман скрывает край мира

print('Генерация мира...')
world = World(WORLD_SEED)
spawn = world.find_spawn()
world.pregenerate(spawn)
print(f'Готово: {len(world.chunks)} чанков, {len(world.blocks)} блоков.')

player = Player(world, position=spawn)
inventory = Inventory()
ui = UI(inventory)
craft = CraftingUI(inventory)
state = GameState(player, inventory, ui)
inventory.notify()


def _on_death():
    """Смерть закрывает окно крафта, иначе игрок останется замороженным."""
    if craft.enabled:
        craft.close()
        player.frozen = False


state.on_death = _on_death


class GameController(Entity):
    """Связывает ввод с миром: разрушение, установка блоков, режимы."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # полупрозрачная подсветка блока под прицелом
        self.selector = Entity(model='cube', color=Color(1, 1, 1, 0.18),
                               scale=1.02, enabled=False)
        self.break_pos = None       # какой блок сейчас ломаем
        self.break_progress = 0.0   # прогресс разрушения 0..1

    # ------------------------------------------------------------------
    @staticmethod
    def target():
        """Блок под прицелом: (позиция, позиция для установки)."""
        return world.raycast(camera.world_position, camera.forward, REACH)

    def update(self):
        world.update_chunks(player.position)
        if craft.enabled or not mouse.locked:
            self.selector.enabled = False
            self._reset_breaking()
            return
        hit, _ = self.target()
        if hit:
            self.selector.enabled = True
            self.selector.position = Vec3(hit[0] + .5, hit[1] + .5, hit[2] + .5)
        else:
            self.selector.enabled = False
        # выживание: разрушение с зажатой ЛКМ занимает время
        if state.mode == 'survival' and held_keys['left mouse'] and hit:
            if hit != self.break_pos:
                self.break_pos = hit
                self.break_progress = 0.0
            bid = world.get_block(hit)
            if bid is not None:
                t = break_time(bid, inventory.selected_slot.item)
                self.break_progress += time.dt / t
                ui.set_break_progress(self.break_progress)
                if self.break_progress >= 1:
                    self._finish_break(hit, bid)
        else:
            self._reset_breaking()

    def _reset_breaking(self):
        self.break_pos = None
        self.break_progress = 0.0
        ui.set_break_progress(None)

    def _finish_break(self, pos, bid):
        """Блок сломан: кладём добычу в инвентарь и убираем блок из мира."""
        drop = get_drop(bid)
        if drop and inventory.add(drop, 1) > 0:
            # инвентарь полон: блок не ломаем, чтобы добыча не пропала
            self._reset_breaking()
            return
        world.set_block(pos, None)
        self._reset_breaking()

    # ------------------------------------------------------------------
    def input(self, key):
        # G — переключение режима игры
        if key == 'g':
            if craft.enabled:
                craft.close()
                player.frozen = False
            state.toggle_mode()
            return
        # E — окно крафта
        if key == 'e':
            if craft.enabled:
                craft.close()
                player.frozen = False
            else:
                craft.open()
                player.frozen = True
            return
        # Esc — закрыть крафт или отпустить/захватить мышь
        if key == 'escape':
            if craft.enabled:
                craft.close()
                player.frozen = False
            else:
                mouse.locked = not mouse.locked
            return
        # выбор слота: цифры 1-9 и колесо мыши
        if len(key) == 1 and key.isdigit() and key != '0':
            inventory.select(int(key) - 1)
            return
        if key == 'scroll down':
            inventory.select(inventory.selected + 1)
            return
        if key == 'scroll up':
            inventory.select(inventory.selected - 1)
            return

        if craft.enabled or not mouse.locked:
            return  # пока открыт интерфейс, с миром не взаимодействуем

        # творчество: мгновенное разрушение по клику
        if key == 'left mouse down' and state.mode == 'creative':
            hit, _ = self.target()
            if hit:
                world.set_block(hit, None)
            return
        # ПКМ: съесть яблоко или поставить блок
        if key == 'right mouse down':
            slot = inventory.selected_slot
            if slot.empty:
                return
            if slot.item == 'apple':
                # при полной сытости яблоко не тратится впустую
                if state.hunger < MAX_HUNGER:
                    state.eat(APPLE_FOOD)
                    inventory.consume_selected(1)
                return
            if not ITEMS[slot.item].is_block:
                return
            hit, prev = self.target()
            if hit is None or prev is None:
                return
            existing = world.get_block(prev)
            if existing is not None and existing != 'water':
                return  # место занято (в воду ставить можно)
            if ITEMS[slot.item].solid and player.intersects_block(prev):
                return  # нельзя ставить блок в самого себя
            world.set_block(prev, slot.item)
            inventory.consume_selected(1)


controller = GameController()


# ----------------------------------------------------------------------
# Режим самопроверки: python main.py --smoke
# ----------------------------------------------------------------------
def _smoke_checks():
    """Быстрые проверки логики и снимок экрана, затем выход."""
    from crafting import match_recipe
    # рецепты
    assert match_recipe(['wood', None, None, None, None, None, None, None, None]) == ('planks', 4)
    assert match_recipe([None, 'planks', None, None, 'planks', None, None, None, None]) == ('stick', 4)
    assert match_recipe(['planks', 'planks', 'planks',
                         None, 'stick', None,
                         None, 'stick', None]) == ('wooden_pickaxe', 1)
    assert match_recipe([None, None, None, None, 'wood', None, None, None, None]) == ('planks', 4)
    # мир: сломать и поставить блок
    pos = (floor(spawn.x), floor(spawn.y) - 2, floor(spawn.z))
    assert world.get_block(pos) is not None
    world.set_block(pos, None)
    assert world.get_block(pos) is None
    world.set_block(pos, 'stone')
    assert world.get_block(pos) == 'stone'
    # рейкаст вниз находит поверхность
    hit, prev = world.raycast(Vec3(spawn.x, spawn.y + 1, spawn.z),
                              Vec3(0, -1, 0), 10)
    assert hit is not None and prev is not None
    # инвентарь: стопки по 64
    inventory.add('dirt', 70)
    total = sum(s.count for s in inventory.slots if s.item == 'dirt')
    assert total == 70
    stacks = sorted(s.count for s in inventory.slots if s.item == 'dirt')
    assert stacks == [6, 64]
    # переключение режимов
    state.toggle_mode()
    assert state.mode == 'creative' and inventory.creative
    state.toggle_mode()
    assert state.mode == 'survival'
    total = sum(s.count for s in inventory.slots if s.item == 'dirt')
    assert total == 70  # инвентарь выживания сохранился
    # окно крафта: собираем лопату программно
    craft.open()
    player.frozen = True
    craft.grid[1].item, craft.grid[1].count = 'planks', 1
    craft.grid[4].item, craft.grid[4].count = 'stick', 1
    craft.grid[7].item, craft.grid[7].count = 'stick', 1
    craft.refresh()
    assert craft.result == ('wooden_shovel', 1)
    craft._take_result()
    assert craft.cursor.item == 'wooden_shovel'
    assert all(s.empty for s in craft.grid)  # ингредиенты израсходованы
    craft.refresh()
    # скриншоты делаем с задержкой, чтобы кадр успел отрисоваться
    invoke(_smoke_shot_craft, delay=0.5)


def _smoke_shot_craft():
    from inventory import Slot
    try:
        base.win.saveScreenshot('smoke_craft.png')  # noqa: F821
    except Exception as e:
        print('screenshot failed:', e)
    craft.close()  # лопата с курсора вернётся в инвентарь
    player.frozen = False
    assert any(s.item == 'wooden_shovel' for s in inventory.slots)
    # закрытие окна с ПОЛНЫМ инвентарём не теряет предметы из сетки
    craft.open()
    saved_slots = inventory.slots
    inventory.slots = [Slot('stone', 64) for _ in range(len(saved_slots))]
    craft.grid[0].item, craft.grid[0].count = 'wood', 1
    craft.close()
    assert craft.grid[0].item == 'wood' and craft.grid[0].count == 1, \
        'предмет пропал при закрытии крафта с полным инвентарём'
    craft.grid[0].clear()
    inventory.slots = saved_slots
    inventory.notify()
    invoke(_smoke_finish, delay=0.5)


def _smoke_finish():
    try:
        base.win.saveScreenshot('smoke.png')  # noqa: F821 (base создаёт panda3d)
    except Exception as e:
        print('screenshot failed:', e)
    print('SMOKE OK')
    application.quit()


if '--smoke' in sys.argv:
    invoke(_smoke_checks, delay=2)


# ----------------------------------------------------------------------
# Режим замера FPS: python main.py --benchmark
# ----------------------------------------------------------------------
class _FpsBenchmark(Entity):
    """2 секунды прогрева, затем 6 секунд сбора длительностей кадров."""

    WARMUP = 2.0
    DURATION = 8.0

    def __init__(self):
        super().__init__()
        self.elapsed = 0.0
        self.samples = []

    def update(self):
        self.elapsed += time.dt
        if self.elapsed > self.WARMUP:
            self.samples.append(time.dt)
        if self.elapsed > self.DURATION and self.samples:
            dts = sorted(self.samples)
            avg = sum(dts) / len(dts)
            slow = dts[int(len(dts) * 0.95)]  # 5% худших кадров
            print(f'BENCHMARK кадров={len(dts)} '
                  f'средний FPS={1 / avg:.1f} '
                  f'FPS в худших 5% кадров={1 / slow:.1f} '
                  f'макс. кадр={dts[-1] * 1000:.1f} мс')
            application.quit()


if '--benchmark' in sys.argv:
    _FpsBenchmark()

app.run()
