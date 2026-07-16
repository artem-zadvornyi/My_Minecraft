# -*- coding: utf-8 -*-
"""Структуры данных реестров: определения блоков, предметов, дропов, граней."""
from dataclasses import dataclass

from ursina.color import Color


def rgb(r, g, b, a=255):
    """Цвет из компонентов 0-255 (Ursina ожидает 0-1)."""
    return Color(r / 255, g / 255, b / 255, a / 255)


WHITE = rgb(255, 255, 255)


@dataclass(frozen=True)
class Drop:
    """Что выпадает из блока: предмет, количество, вероятность."""
    item: str          # ключ предмета
    count: int = 1
    chance: float = 1.0


@dataclass(frozen=True)
class FaceTextures:
    """Имена текстур по граням куба.

    Порядок индексов совпадает с world._FACES:
    0 — верх, 1 — низ, 2 — +x, 3 — -x, 4 — +z, 5 — -z.
    """
    top: str = None
    bottom: str = None
    east: str = None   # +x
    west: str = None   # -x
    north: str = None  # +z
    south: str = None  # -z

    @staticmethod
    def all(name):
        """Одна текстура на все грани."""
        return FaceTextures(name, name, name, name, name, name)

    @staticmethod
    def tbs(top, bottom, side):
        """Верх / низ / четыре боковые."""
        return FaceTextures(top, bottom, side, side, side, side)

    def by_index(self, face_index):
        return (self.top, self.bottom, self.east,
                self.west, self.north, self.south)[face_index]


@dataclass(frozen=True)
class BlockDef:
    """Определение блока мира."""
    id: int                      # стабильный числовой id (для сериализации)
    key: str                     # внутренний ключ (хранится в world.blocks)
    name: str                    # отображаемое имя
    category: str                # 'natural' / 'liquid' / 'wood' / 'building'...
    hardness: float              # время разрушения рукой, сек
    faces: FaceTextures          # текстуры граней (атлас)
    color: Color                 # запасной цвет граней, если текстуры нет
    top_color: Color = None      # запасной цвет верхней грани
    bottom_color: Color = None   # запасной цвет нижней грани
    tool: str = None             # предпочтительный инструмент
    min_tool_tier: int = 0       # минимальный уровень инструмента (0 — рука)
    transparent: bool = False    # видно ли сквозь блок (отсечение граней)
    solid: bool = True           # твёрдый материал (не жидкость/газ)
    replaceable: bool = False    # можно ли ставить блок ПОВЕРХ этого
    liquid: bool = False         # жидкость: не выбирается лучом, плавучесть
    collision: bool = True       # сталкивается ли с игроком
    emitted_light: int = 0       # испускаемый свет 0-15 (задел на М9)
    blocks_skylight: bool = True # перекрывает ли небесный свет (задел на М9)
    max_stack: int = 64
    drops: tuple = ()            # tuple[Drop, ...]; () — ничего не выпадает
    tint: Color = None           # множитель цвета поверх текстуры
    behavior: str = None         # ключ будущего поведения (двери, печи...)
    sound_group: str = None      # группа звуков (задел)


@dataclass(frozen=True)
class ItemDef:
    """Определение предмета инвентаря."""
    id: int                      # стабильный числовой id
    key: str                     # внутренний ключ (хранится в слотах)
    name: str                    # отображаемое имя
    category: str                # 'block' / 'material' / 'tool' / 'food'
    icon: str = None             # имя текстуры-иконки в атласе
    icon_color: Color = WHITE    # запасной цвет иконки, если текстуры нет
    label: str = ''              # буква на иконке (инструменты без текстур)
    max_stack: int = 64
    placeable_block: str = None  # ключ блока, который ставит этот предмет
    tool_type: str = None        # 'pickaxe' / 'axe' / 'shovel'
    tool_tier: int = 0           # уровень инструмента (дерево = 1)
    durability: int = None       # прочность (задел, пока не расходуется)
    mining_multiplier: float = 1.0  # ускорение добычи своим типом блоков
    attack_damage: float = 1.0   # урон (задел на М13)
    food: int = 0                # сколько голода восстанавливает (0 — не еда)
    creative_palette: int = None # позиция в палитре креатива (None — нет)
