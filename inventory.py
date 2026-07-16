# -*- coding: utf-8 -*-
"""Инвентарь: данные слотов панели быстрого доступа (без интерфейса).

Имена, размеры стопок и палитра креатива берутся из реестра предметов.
"""
from game_data import ITEMS
from settings import HOTBAR_SLOTS


class Slot:
    """Один слот: предмет, количество и флаг бесконечности (креатив)."""
    __slots__ = ('item', 'count', 'infinite')

    def __init__(self, item=None, count=0, infinite=False):
        self.item = item
        self.count = count
        self.infinite = infinite

    @property
    def empty(self):
        return self.item is None or self.count <= 0

    def clear(self):
        self.item = None
        self.count = 0
        self.infinite = False

    def take(self, n):
        """Забрать до n предметов. Возвращает (предмет, сколько взято)."""
        if self.empty:
            return None, 0
        item = self.item
        if self.infinite:
            return item, n  # бесконечный слот не истощается
        n = min(n, self.count)
        self.count -= n
        if self.count <= 0:
            self.clear()
        return item, n


class Inventory:
    def __init__(self):
        self.slots = [Slot() for _ in range(HOTBAR_SLOTS)]
        self.selected = 0
        self.creative = False
        self.on_change = None  # колбэк обновления интерфейса

    def notify(self):
        if self.on_change:
            self.on_change()

    @property
    def selected_slot(self):
        return self.slots[self.selected]

    def select(self, index):
        self.selected = index % HOTBAR_SLOTS
        self.notify()

    def add(self, item_id, count=1):
        """Добавить предметы. Возвращает, сколько не поместилось."""
        if self.creative:
            return 0  # в креативе блоки бесконечные — подбирать нечего
        max_stack = ITEMS[item_id].max_stack
        # сначала пополняем существующие стопки
        for slot in self.slots:
            if count <= 0:
                break
            if slot.item == item_id and not slot.infinite and slot.count < max_stack:
                move = min(count, max_stack - slot.count)
                slot.count += move
                count -= move
        # затем занимаем пустые слоты
        for slot in self.slots:
            if count <= 0:
                break
            if slot.empty:
                move = min(count, max_stack)
                slot.item = item_id
                slot.count = move
                slot.infinite = False
                count -= move
        self.notify()
        return count

    def can_add(self, item_id, count=1):
        """Поместятся ли предметы (без изменения инвентаря)."""
        if self.creative:
            return True
        max_stack = ITEMS[item_id].max_stack
        free = 0
        for slot in self.slots:
            if slot.item == item_id and not slot.infinite:
                free += max_stack - slot.count
            elif slot.empty:
                free += max_stack
            if free >= count:
                return True
        return False

    def consume_selected(self, n=1):
        """Израсходовать n предметов из выбранного слота."""
        slot = self.selected_slot
        if slot.infinite:
            return
        slot.count -= n
        if slot.count <= 0:
            slot.clear()
        self.notify()

    def set_creative_palette(self):
        """Креатив: бесконечная палитра из реестра предметов."""
        self.creative = True
        palette = sorted(
            (item for item in ITEMS if item.creative_palette is not None),
            key=lambda item: item.creative_palette)
        self.slots = [Slot(item.key, 1, infinite=True)
                      for item in palette[:HOTBAR_SLOTS]]
        while len(self.slots) < HOTBAR_SLOTS:
            self.slots.append(Slot())
        self.selected = min(self.selected, HOTBAR_SLOTS - 1)
        self.notify()

    def set_slots(self, slots):
        """Вернуть сохранённые слоты (переход в выживание)."""
        self.creative = False
        self.slots = slots
        self.notify()
