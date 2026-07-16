# -*- coding: utf-8 -*-
"""Крафт: рецепты и окно с сеткой 3x3 (клавиша E).

Управление в окне: ЛКМ — взять/положить всю стопку, ПКМ — половину/по одному.
"""
from ursina import Button, Entity, Text, Vec3, camera, mouse
from ursina.color import Color

from game_data import ITEMS
from inventory import Slot
from rendering.texture_atlas import apply_item_icon
from settings import HOTBAR_SLOTS

# ----------------------------------------------------------------------
# Рецепты
# ----------------------------------------------------------------------
# Шаблон — строки сетки; клетка: id предмета или None.
# Шаблоны сравниваются с сеткой после обрезки пустых строк и столбцов,
# поэтому рецепт можно выкладывать в любом углу сетки.
_RAW_RECIPES = [
    # бревно -> 4 доски
    ([['wood']], ('planks', 4)),
    # 2 доски вертикально -> 4 палки
    ([['planks'],
      ['planks']], ('stick', 4)),
    # кирка: 3 доски сверху, 2 палки ручкой
    ([['planks', 'planks', 'planks'],
      [None,     'stick',  None],
      [None,     'stick',  None]], ('wooden_pickaxe', 1)),
    # топор (и зеркальный вариант)
    ([['planks', 'planks'],
      ['planks', 'stick'],
      [None,     'stick']], ('wooden_axe', 1)),
    ([['planks', 'planks'],
      ['stick',  'planks'],
      ['stick',  None]], ('wooden_axe', 1)),
    # лопата: доска и 2 палки
    ([['planks'],
      ['stick'],
      ['stick']], ('wooden_shovel', 1)),
]

RECIPES = {tuple(tuple(row) for row in pattern): result
           for pattern, result in _RAW_RECIPES}


def normalize(cells):
    """Обрезает пустые строки и столбцы сетки 3x3 (список из 9 клеток)."""
    grid = [cells[r * 3:(r + 1) * 3] for r in range(3)]
    rows = [r for r in range(3) if any(grid[r])]
    cols = [c for c in range(3) if any(grid[r][c] for r in range(3))]
    if not rows:
        return None
    return tuple(tuple(grid[r][c] for c in range(cols[0], cols[-1] + 1))
                 for r in range(rows[0], rows[-1] + 1))


def match_recipe(cells):
    """Возвращает (id_результата, количество) или None."""
    key = normalize(cells)
    return RECIPES.get(key) if key else None


# ----------------------------------------------------------------------
# Окно крафта
# ----------------------------------------------------------------------
SLOT = 0.07    # размер клетки
STEP = 0.078   # шаг между клетками


class CraftingUI(Entity):
    def __init__(self, inventory, **kwargs):
        super().__init__(parent=camera.ui, enabled=False, **kwargs)
        self.inventory = inventory
        self.grid = [Slot() for _ in range(9)]  # сетка крафта 3x3
        self.cursor = Slot()                    # стопка «в руке»
        self.result = None                      # (id, количество) или None

        # фон окна
        Entity(parent=self, model='quad', color=Color(0.08, 0.08, 0.1, 0.94),
               scale=(0.78, 0.6), z=0.02)
        Text(parent=self, text='Крафт', origin=(0, 0), position=(0, 0.24, -0.03),
             scale=1.2)
        Text(parent=self, text='ЛКМ — взять/положить всё, ПКМ — половину/по одному',
             origin=(0, 0), position=(0, 0.19, -0.03), scale=0.6,
             color=Color(1, 1, 1, 0.6))

        # сетка 3x3
        self.grid_buttons = []
        for r in range(3):
            for c in range(3):
                pos = (-0.13 + (c - 1) * STEP, 0.055 + (1 - r) * STEP)
                self.grid_buttons.append(self._make_slot(pos))
        # стрелка и слот результата
        Text(parent=self, text='>', origin=(0, 0), position=(0.045, 0.055, -0.03),
             scale=1.6)
        self.result_button = self._make_slot((0.16, 0.055))
        # слоты инвентаря внизу окна
        self.inv_buttons = []
        for i in range(HOTBAR_SLOTS):
            pos = ((i - (HOTBAR_SLOTS - 1) / 2) * STEP, -0.2)
            self.inv_buttons.append(self._make_slot(pos))

        # иконка стопки на курсоре
        self.cursor_icon = Entity(parent=self, model='quad', scale=SLOT * 0.7,
                                  z=-0.1, enabled=False)
        self.cursor_text = Text(parent=self, text='', origin=(-0.5, 0.5),
                                z=-0.11, scale=0.7)

    # ------------------------------------------------------------------
    def _make_slot(self, position):
        """Кнопка-слот с иконкой, буквой и счётчиком."""
        b = Button(parent=self, model='quad', color=Color(0.22, 0.22, 0.25, 1),
                   highlight_color=Color(0.32, 0.32, 0.36, 1),
                   position=position, scale=SLOT, z=-0.01)
        # имя item_icon, т.к. Button.icon — встроенное свойство Ursina
        b.item_icon = Entity(parent=self, model='quad', scale=SLOT * 0.7,
                             position=(position[0], position[1], -0.04),
                             enabled=False)
        b.item_label = Text(parent=self, text='', origin=(0, 0),
                            position=(position[0], position[1], -0.05), scale=0.7)
        b.count_text = Text(parent=self, text='', origin=(0.5, -0.5),
                            position=(position[0] + SLOT * 0.42,
                                      position[1] - SLOT * 0.38, -0.05),
                            scale=0.7)
        return b

    @staticmethod
    def _paint(button, slot):
        """Обновляет вид слота по его содержимому."""
        if slot.empty:
            button.item_icon.enabled = False
            button.item_label.text = ''
            button.count_text.text = ''
            return
        item = ITEMS[slot.item]
        button.item_icon.enabled = True
        apply_item_icon(button.item_icon, item)
        button.item_label.text = item.label
        if slot.infinite:
            button.count_text.text = '∞'
        else:
            button.count_text.text = str(slot.count) if slot.count > 1 else ''

    def refresh(self):
        for i, b in enumerate(self.grid_buttons):
            self._paint(b, self.grid[i])
        for i, b in enumerate(self.inv_buttons):
            self._paint(b, self.inventory.slots[i])
        # пересчитываем результат по текущей сетке
        self.result = match_recipe([s.item if not s.empty else None
                                    for s in self.grid])
        if self.result:
            self._paint(self.result_button, Slot(self.result[0], self.result[1]))
        else:
            self._paint(self.result_button, Slot())
        # курсор
        if self.cursor.empty:
            self.cursor_icon.enabled = False
            self.cursor_text.text = ''
        else:
            self.cursor_icon.enabled = True
            apply_item_icon(self.cursor_icon, ITEMS[self.cursor.item])
            self.cursor_text.text = (str(self.cursor.count)
                                     if self.cursor.count > 1 else '')

    def update(self):
        # стопка на курсоре следует за мышью
        self.cursor_icon.position = Vec3(mouse.x, mouse.y, -0.1)
        self.cursor_text.position = Vec3(mouse.x + 0.015, mouse.y - 0.015, -0.11)

    # ------------------------------------------------------------------
    def input(self, key):
        if key not in ('left mouse down', 'right mouse down'):
            return
        right = key == 'right mouse down'
        b = mouse.hovered_entity
        if b in self.grid_buttons:
            self._click_slot(self.grid[self.grid_buttons.index(b)], right)
        elif b in self.inv_buttons:
            self._click_slot(self.inventory.slots[self.inv_buttons.index(b)], right)
        elif b is self.result_button and not right:
            self._take_result()
        else:
            return
        self.refresh()
        self.inventory.notify()  # синхронизируем панель быстрого доступа

    def _click_slot(self, slot, right):
        """Обмен предметами между слотом и курсором."""
        cur = self.cursor
        if cur.empty:
            if slot.empty:
                return
            if slot.infinite:
                # из бесконечной палитры: ЛКМ — стопка, ПКМ — один предмет
                take = 1 if right else ITEMS[slot.item].max_stack
            else:
                take = (slot.count + 1) // 2 if right else slot.count
            item, n = slot.take(take)
            cur.item, cur.count = item, n
            return
        if slot.infinite:
            cur.clear()  # предмет, брошенный в палитру, исчезает
            return
        if slot.empty or slot.item == cur.item:
            max_stack = ITEMS[cur.item].max_stack
            move = 1 if right else cur.count
            move = min(move, max_stack - slot.count)
            if move <= 0:
                return
            slot.item = cur.item
            slot.count += move
            cur.count -= move
            if cur.count <= 0:
                cur.clear()
        elif not right:
            # обмен стопками
            slot.item, cur.item = cur.item, slot.item
            slot.count, cur.count = cur.count, slot.count

    def _take_result(self):
        """Забрать результат крафта, израсходовав ингредиенты."""
        if not self.result:
            return
        item, count = self.result
        cur = self.cursor
        if cur.empty:
            cur.item, cur.count = item, count
        elif cur.item == item and cur.count + count <= ITEMS[item].max_stack:
            cur.count += count
        else:
            return  # курсор занят другим предметом
        # по одному предмету из каждой занятой клетки сетки
        for s in self.grid:
            if not s.empty:
                s.take(1)

    # ------------------------------------------------------------------
    def open(self):
        self.enabled = True
        mouse.locked = False
        self.refresh()

    def close(self):
        """Закрыть окно, вернув содержимое сетки и курсора в инвентарь.

        Что не поместилось (инвентарь полон) — НЕ теряется: остаётся в
        сетке/на курсоре и будет на месте при следующем открытии окна.
        """
        for s in list(self.grid) + [self.cursor]:
            if s.empty:
                continue
            if self.inventory.creative:
                s.clear()  # в креативе предметы не возвращаются
                continue
            leftover = self.inventory.add(s.item, s.count)
            if leftover:
                s.count = leftover
            else:
                s.clear()
        self.result = None
        self.enabled = False
        mouse.locked = True
