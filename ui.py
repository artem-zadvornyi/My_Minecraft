# -*- coding: utf-8 -*-
"""Интерфейс: прицел, панель быстрого доступа, полоски здоровья и голода."""
from ursina import Entity, Text, Vec2, camera, invoke, window
from ursina.color import Color

from blocks import ITEMS
from settings import HOTBAR_SLOTS, MAX_HEALTH, MAX_HUNGER

SLOT_SIZE = 0.06
SLOT_STEP = 0.066
HOTBAR_Y = -0.44
BAR_WIDTH = 0.26


class UI(Entity):
    def __init__(self, inventory, **kwargs):
        super().__init__(parent=camera.ui, **kwargs)
        self.inventory = inventory
        inventory.on_change = self.refresh_hotbar

        # --- прицел ---
        self.crosshair = Text(parent=self, text='+', origin=(0, 0), scale=1.5,
                              color=Color(1, 1, 1, 0.75), position=(0, 0, -0.1))

        # --- панель быстрого доступа (9 слотов) ---
        self.slot_icons = []
        self.slot_labels = []
        self.slot_counts = []
        for i in range(HOTBAR_SLOTS):
            x = (i - (HOTBAR_SLOTS - 1) / 2) * SLOT_STEP
            Entity(parent=self, model='quad', color=Color(0.1, 0.1, 0.1, 0.65),
                   position=(x, HOTBAR_Y, 0), scale=SLOT_SIZE)
            icon = Entity(parent=self, model='quad', position=(x, HOTBAR_Y, -0.01),
                          scale=SLOT_SIZE * 0.72, enabled=False)
            label = Text(parent=self, text='', origin=(0, 0),
                         position=(x, HOTBAR_Y, -0.02), scale=0.7)
            count = Text(parent=self, text='', origin=(0.5, -0.5),
                         position=(x + SLOT_SIZE * 0.45,
                                   HOTBAR_Y - SLOT_SIZE * 0.42, -0.02),
                         scale=0.65)
            # номер слота в углу
            Text(parent=self, text=str(i + 1), origin=(-0.5, 0.5),
                 position=(x - SLOT_SIZE * 0.45, HOTBAR_Y + SLOT_SIZE * 0.48, -0.02),
                 scale=0.5, color=Color(1, 1, 1, 0.5))
            self.slot_icons.append(icon)
            self.slot_labels.append(label)
            self.slot_counts.append(count)
        # рамка выбранного слота (белый квадрат чуть больше слота, позади)
        self.selection = Entity(parent=self, model='quad',
                                color=Color(1, 1, 1, 0.9),
                                scale=SLOT_SIZE * 1.14,
                                position=(0, HOTBAR_Y, 0.005))
        # имя выбранного предмета над панелью
        self.item_name = Text(parent=self, text='', origin=(0, 0),
                              position=(0, HOTBAR_Y + 0.095, -0.02), scale=0.8)

        # --- полоски здоровья и голода (только выживание) ---
        self.bars_root = Entity(parent=self)
        bar_y = HOTBAR_Y + 0.055
        Text(parent=self.bars_root, text='ХП', origin=(0.5, 0),
             position=(-BAR_WIDTH - 0.045, bar_y, -0.02), scale=0.6)
        Entity(parent=self.bars_root, model='quad', color=Color(0, 0, 0, 0.6),
               position=(-BAR_WIDTH / 2 - 0.02, bar_y, 0), scale=(BAR_WIDTH, 0.018))
        self.health_fill = Entity(parent=self.bars_root, model='quad',
                                  color=Color(0.85, 0.15, 0.15, 1),
                                  origin=(-0.5, 0),
                                  position=(-BAR_WIDTH - 0.02, bar_y, -0.01),
                                  scale=(BAR_WIDTH, 0.012))
        Text(parent=self.bars_root, text='ЕДА', origin=(-0.5, 0),
             position=(BAR_WIDTH + 0.045, bar_y, -0.02), scale=0.6)
        Entity(parent=self.bars_root, model='quad', color=Color(0, 0, 0, 0.6),
               position=(BAR_WIDTH / 2 + 0.02, bar_y, 0), scale=(BAR_WIDTH, 0.018))
        self.hunger_fill = Entity(parent=self.bars_root, model='quad',
                                  color=Color(0.85, 0.55, 0.15, 1),
                                  origin=(-0.5, 0),
                                  position=(0.02, bar_y, -0.01),
                                  scale=(BAR_WIDTH, 0.012))

        # --- режим игры и подсказки (верхний левый угол) ---
        self.mode_text = Text(parent=self, text='',
                              position=window.top_left + Vec2(0.02, -0.03),
                              scale=0.9)
        self.hint_text = Text(
            parent=self,
            text=('WASD — движение, пробел — прыжок, G — режим, E — крафт\n'
                  'ЛКМ — сломать, ПКМ — поставить/съесть, 1-9 — слоты\n'
                  'В креативе: двойной пробел — полёт (shift — вниз)'),
            position=window.top_left + Vec2(0.02, -0.07),
            scale=0.6, color=Color(1, 1, 1, 0.55))

        # --- полоса прогресса разрушения (под прицелом) ---
        self.break_bg = Entity(parent=self, model='quad',
                               color=Color(0, 0, 0, 0.55),
                               position=(0, -0.06, 0), scale=(0.12, 0.014),
                               enabled=False)
        self.break_fill = Entity(parent=self, model='quad',
                                 color=Color(1, 1, 1, 0.9), origin=(-0.5, 0),
                                 position=(-0.06, -0.06, -0.01),
                                 scale=(0.12, 0.009), enabled=False)

        # --- экран смерти ---
        self.death_overlay = Entity(parent=self, model='quad',
                                    color=Color(0.45, 0, 0, 0.4),
                                    scale=(3, 2), z=0.5, enabled=False)
        self.death_text = Text(parent=self, text='Вы умерли!', origin=(0, 0),
                               scale=2.5, color=Color(1, 0.9, 0.9, 1),
                               position=(0, 0.1, -0.3), enabled=False)

    # ------------------------------------------------------------------
    def refresh_hotbar(self):
        """Перерисовывает панель быстрого доступа по данным инвентаря."""
        inv = self.inventory
        for i, slot in enumerate(inv.slots):
            icon = self.slot_icons[i]
            label = self.slot_labels[i]
            count = self.slot_counts[i]
            if slot.empty:
                icon.enabled = False
                label.text = ''
                count.text = ''
                continue
            item = ITEMS[slot.item]
            icon.enabled = True
            icon.color = item.color
            label.text = item.label
            if slot.infinite:
                count.text = '∞'
            else:
                count.text = str(slot.count) if slot.count > 1 else ''
        self.selection.x = (inv.selected - (HOTBAR_SLOTS - 1) / 2) * SLOT_STEP
        sel = inv.selected_slot
        self.item_name.text = ITEMS[sel.item].name if not sel.empty else ''

    def set_bars(self, health, hunger):
        self.health_fill.scale_x = BAR_WIDTH * max(0, health) / MAX_HEALTH
        self.hunger_fill.scale_x = BAR_WIDTH * max(0, hunger) / MAX_HUNGER

    def set_mode(self, mode):
        name = 'Творчество' if mode == 'creative' else 'Выживание'
        self.mode_text.text = f'Режим: {name}  (G — сменить)'
        self.bars_root.enabled = mode == 'survival'

    def set_break_progress(self, progress):
        """progress: 0..1 или None, чтобы скрыть полосу."""
        show = progress is not None
        self.break_bg.enabled = show
        self.break_fill.enabled = show
        if show:
            self.break_fill.scale_x = 0.12 * min(progress, 1)

    def flash_death(self):
        self.death_overlay.enabled = True
        self.death_text.enabled = True
        invoke(self._hide_death, delay=1.5)

    def _hide_death(self):
        self.death_overlay.enabled = False
        self.death_text.enabled = False
