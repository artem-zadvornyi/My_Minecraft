# -*- coding: utf-8 -*-
"""Игровое состояние: режимы (выживание/творчество), здоровье, голод."""
import time

from ursina import Entity

from settings import (HUNGER_TICK, MAX_HEALTH, MAX_HUNGER, REGEN_HUNGER,
                      REGEN_TICK, SAFE_FALL_HEIGHT, STARVE_TICK)


class GameState(Entity):
    """Хранит режим игры и показатели выживания, тикает голод."""

    def __init__(self, player, inventory, ui, **kwargs):
        super().__init__(**kwargs)
        self.player = player
        self.inventory = inventory
        self.ui = ui
        self.mode = 'survival'
        self.health = MAX_HEALTH
        self.hunger = MAX_HUNGER
        self._hunger_timer = 0.0
        self._starve_timer = 0.0
        self._regen_timer = 0.0
        self._survival_slots = None  # инвентарь выживания на время креатива
        self.on_death = None  # колбэк: закрыть интерфейсы при смерти
        player.on_hard_land = self.fall_damage
        self.apply_mode()

    # ------------------------------------------------------------------
    def toggle_mode(self):
        self.mode = 'creative' if self.mode == 'survival' else 'survival'
        self.apply_mode()

    def apply_mode(self):
        inv, player = self.inventory, self.player
        if self.mode == 'creative':
            self._survival_slots = inv.slots  # сохраняем инвентарь выживания
            inv.set_creative_palette()
            player.can_fly = True
        else:
            if self._survival_slots is not None:
                inv.set_slots(self._survival_slots)
            else:
                inv.creative = False
                inv.notify()
            player.can_fly = False
            player.flying = False
        self.ui.set_mode(self.mode)
        self.ui.set_bars(self.health, self.hunger)

    # ------------------------------------------------------------------
    def update(self):
        if self.mode != 'survival':
            return
        dt = time.dt
        # голод постепенно убывает
        self._hunger_timer += dt
        if self._hunger_timer >= HUNGER_TICK:
            self._hunger_timer = 0.0
            if self.hunger > 0:
                self.hunger -= 1
                self.ui.set_bars(self.health, self.hunger)
        if self.hunger <= 0:
            # голодание наносит урон
            self._starve_timer += dt
            if self._starve_timer >= STARVE_TICK:
                self._starve_timer = 0.0
                self.damage(1)
        elif self.hunger >= REGEN_HUNGER and self.health < MAX_HEALTH:
            # при сытости здоровье восстанавливается
            self._regen_timer += dt
            if self._regen_timer >= REGEN_TICK:
                self._regen_timer = 0.0
                self.health = min(MAX_HEALTH, self.health + 1)
                self.ui.set_bars(self.health, self.hunger)

    # ------------------------------------------------------------------
    def fall_damage(self, fall):
        """Урон от падения: 1 урона за каждый блок сверх безопасной высоты."""
        self.damage(int(fall - SAFE_FALL_HEIGHT))

    def damage(self, amount):
        if self.mode != 'survival' or amount <= 0:
            return
        self.health -= amount
        self.ui.set_bars(self.health, self.hunger)
        if self.health <= 0:
            self.die()

    def die(self):
        """Смерть: возрождение на точке спавна с полными шкалами."""
        self.health = MAX_HEALTH
        self.hunger = MAX_HUNGER
        if self.on_death:
            self.on_death()  # например, закрыть открытое окно крафта
        self.player.respawn()
        self.ui.set_bars(self.health, self.hunger)
        self.ui.flash_death()

    def eat(self, amount):
        self.hunger = min(MAX_HUNGER, self.hunger + amount)
        self.ui.set_bars(self.health, self.hunger)
