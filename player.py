# -*- coding: utf-8 -*-
"""Игрок: камера от первого лица, движение, гравитация, коллизии, полёт."""
import time
from math import floor

from ursina import Entity, Vec3, camera, clamp, held_keys, mouse

from settings import (DOUBLE_TAP_TIME, EYE_HEIGHT, FLY_SPEED, GRAVITY,
                      JUMP_SPEED, MAX_FALL_SPEED, MOUSE_SENSITIVITY,
                      PLAYER_HEIGHT, PLAYER_WIDTH, SINK_SPEED, SWIM_UP_SPEED,
                      WALK_SPEED)

EPS = 1e-4  # зазор, чтобы не «прилипать» к граням блоков


class Player(Entity):
    """Контроллер от первого лица с собственной воксельной физикой.

    Игрок — невидимая сущность (точка у ног), камера прикреплена на уровне
    глаз. Поворот по горизонтали — у сущности, наклон — у камеры.
    """

    def __init__(self, world, position, **kwargs):
        super().__init__(position=position, **kwargs)
        self.world = world
        camera.parent = self
        camera.position = Vec3(0, EYE_HEIGHT, 0)
        camera.rotation = Vec3(0, 0, 0)
        camera.fov = 90
        mouse.locked = True

        self.velocity_y = 0.0
        self.grounded = False
        self.frozen = False       # True, пока открыт интерфейс крафта
        self.can_fly = False      # разрешён ли полёт (креатив)
        self.flying = False
        self.on_hard_land = None  # колбэк урона от падения: f(высота)
        self.spawn_point = Vec3(position)
        self._peak_y = self.y     # максимальная высота с начала падения
        self._last_space = -10.0  # время прошлого нажатия пробела

    # ------------------------------------------------------------------
    def input(self, key):
        if self.frozen:
            return
        if key == 'space':
            now = time.time()
            # двойное нажатие пробела — переключение полёта (в креативе)
            if self.can_fly and now - self._last_space < DOUBLE_TAP_TIME:
                self.flying = not self.flying
                self.velocity_y = 0
                self._peak_y = self.y
            self._last_space = now

    # ------------------------------------------------------------------
    def update(self):
        if self.frozen:
            return
        dt = min(time.dt, 0.05)  # защита от туннелирования при долгом кадре

        # --- обзор мышью ---
        if mouse.locked:
            self.rotation_y += mouse.velocity[0] * MOUSE_SENSITIVITY
            camera.rotation_x = clamp(
                camera.rotation_x - mouse.velocity[1] * MOUSE_SENSITIVITY,
                -89, 89)

        # --- горизонтальное движение (WASD относительно взгляда) ---
        move = (self.forward * (held_keys['w'] - held_keys['s'])
                + self.right * (held_keys['d'] - held_keys['a']))
        move.y = 0
        if move.length() > 0:
            move = move.normalized()
        speed = FLY_SPEED if self.flying else WALK_SPEED
        dx = move.x * speed * dt
        dz = move.z * speed * dt

        in_water = self.world.is_liquid(self._feet_block())

        # --- вертикальная скорость ---
        if self.flying:
            # в полёте: пробел — вверх, shift — вниз
            self.velocity_y = (held_keys['space'] - held_keys['shift']) * FLY_SPEED
        elif in_water:
            # в воде медленно тонем, пробел — плывём вверх
            if held_keys['space']:
                self.velocity_y = SWIM_UP_SPEED
            else:
                self.velocity_y = max(self.velocity_y - GRAVITY * dt * 0.4,
                                      -SINK_SPEED)
        else:
            self.velocity_y = max(self.velocity_y - GRAVITY * dt,
                                  -MAX_FALL_SPEED)
            if self.grounded and held_keys['space']:
                self.velocity_y = JUMP_SPEED
        dy = self.velocity_y * dt

        # --- перемещение с коллизиями, по одной оси за раз ---
        self.x += dx
        self._collide_axis('x', dx)
        self.z += dz
        self._collide_axis('z', dz)

        self.y += dy
        self.grounded = False
        if self._collide_axis('y', dy):
            if dy < 0:
                self.grounded = True
                # урон от падения считается по высшей точке полёта;
                # воду проверяем и в точке приземления: in_water с начала
                # кадра устаревает при быстром падении в мелкую воду
                landed_in_water = self.world.is_liquid(self._feet_block())
                fall = self._peak_y - self.y
                if not in_water and not landed_in_water and self.on_hard_land:
                    self.on_hard_land(fall)
            self.velocity_y = 0

        # отслеживаем высшую точку для расчёта высоты падения
        if self.grounded or self.flying or in_water:
            self._peak_y = self.y
        else:
            self._peak_y = max(self._peak_y, self.y)

        # провалились под мир — возвращаемся на точку возрождения
        if self.y < -30:
            self.respawn()

    # ------------------------------------------------------------------
    def _feet_block(self):
        """Координаты блока на уровне ног (для проверки воды)."""
        return (floor(self.x), floor(self.y + 0.3), floor(self.z))

    def _collide_axis(self, axis, delta):
        """Выталкивает игрока из твёрдых блоков вдоль одной оси.

        Возвращает True, если была коллизия.
        """
        if delta == 0:
            return False
        hw = PLAYER_WIDTH / 2
        x0, x1 = floor(self.x - hw), floor(self.x + hw)
        y0, y1 = floor(self.y), floor(self.y + PLAYER_HEIGHT)
        z0, z1 = floor(self.z - hw), floor(self.z + hw)
        is_solid = self.world.is_solid
        hit = False
        for bx in range(x0, x1 + 1):
            for by in range(y0, y1 + 1):
                for bz in range(z0, z1 + 1):
                    if not is_solid((bx, by, bz)):
                        continue
                    hit = True
                    if axis == 'x':
                        self.x = bx - hw - EPS if delta > 0 else bx + 1 + hw + EPS
                    elif axis == 'z':
                        self.z = bz - hw - EPS if delta > 0 else bz + 1 + hw + EPS
                    else:
                        self.y = by - PLAYER_HEIGHT - EPS if delta > 0 else by + 1
        return hit

    def intersects_block(self, pos):
        """Пересекается ли игрок с блоком pos (запрет ставить блок в себя)."""
        hw = PLAYER_WIDTH / 2
        bx, by, bz = pos
        return (bx < self.x + hw and bx + 1 > self.x - hw
                and by < self.y + PLAYER_HEIGHT and by + 1 > self.y
                and bz < self.z + hw and bz + 1 > self.z - hw)

    def respawn(self):
        self.position = Vec3(self.spawn_point)
        self.velocity_y = 0
        self._peak_y = self.y
        self.flying = False
