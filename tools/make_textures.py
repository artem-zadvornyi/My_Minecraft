# -*- coding: utf-8 -*-
"""Генератор оригинальных пиксельных текстур-заглушек 16x16.

Все текстуры рисуются процедурно с фиксированным зерном — никаких
заимствованных ассетов. Запуск пересоздаёт assets/textures/*.png:

    .venv/bin/python tools/make_textures.py
"""
import random
from pathlib import Path

from PIL import Image

SIZE = 16
OUT_DIR = Path(__file__).resolve().parents[1] / 'assets' / 'textures'


def clamp(v):
    return max(0, min(255, v))


def vary(color, spread, rng):
    """Случайное отклонение оттенка от базового цвета."""
    d = rng.randint(-spread, spread)
    return (clamp(color[0] + d), clamp(color[1] + d), clamp(color[2] + d),
            color[3] if len(color) > 3 else 255)


def filled(color):
    c = color if len(color) > 3 else color + (255,)
    return Image.new('RGBA', (SIZE, SIZE), c)


def speckle(img, base, spread, density, rng, rows=None):
    """Зернистость: случайные пиксели с разбросом оттенка."""
    for y in rows if rows is not None else range(SIZE):
        for x in range(SIZE):
            if rng.random() < density:
                img.putpixel((x, y), vary(base, spread, rng))


def grass_top():
    rng = random.Random(1)
    img = filled((95, 169, 61))
    speckle(img, (95, 169, 61), 22, 0.55, rng)
    return img


def dirt():
    rng = random.Random(2)
    img = filled((134, 96, 67))
    speckle(img, (134, 96, 67), 20, 0.55, rng)
    # редкие камешки
    for _ in range(5):
        img.putpixel((rng.randrange(SIZE), rng.randrange(SIZE)), (110, 105, 100, 255))
    return img


def grass_side():
    rng = random.Random(3)
    img = dirt()
    # зелёная полоса сверху с рваным краем
    for y in range(4):
        for x in range(SIZE):
            if y < 3 or rng.random() < 0.5:
                img.putpixel((x, y), vary((95, 169, 61), 20, rng))
    return img


def stone():
    rng = random.Random(4)
    img = filled((125, 125, 125))
    speckle(img, (125, 125, 125), 14, 0.5, rng)
    # трещины: короткие тёмные штрихи
    for _ in range(4):
        x, y = rng.randrange(SIZE), rng.randrange(SIZE)
        for _ in range(rng.randint(2, 4)):
            img.putpixel((x % SIZE, y % SIZE), (98, 98, 98, 255))
            x += rng.choice((-1, 0, 1))
            y += rng.choice((0, 1))
    return img


def sand():
    rng = random.Random(5)
    img = filled((219, 207, 163))
    speckle(img, (219, 207, 163), 16, 0.55, rng)
    return img


def water():
    rng = random.Random(6)
    img = filled((52, 110, 205, 150))
    # светлые горизонтальные гребни волн
    for y in (2, 6, 10, 14):
        for x in range(SIZE):
            if rng.random() < 0.45:
                img.putpixel((x, y), (92, 146, 224, 150))
    speckle(img, (52, 110, 205, 150), 10, 0.25, rng)
    return img


def oak_log():
    rng = random.Random(7)
    img = filled((103, 82, 49))
    # вертикальные борозды коры
    for x in range(SIZE):
        base = (88, 69, 40) if x % 4 in (0, 1) else (110, 88, 54)
        for y in range(SIZE):
            if rng.random() < 0.75:
                img.putpixel((x, y), vary(base, 10, rng))
    return img


def oak_log_top():
    rng = random.Random(8)
    img = filled((155, 125, 77))
    cx = cy = (SIZE - 1) / 2
    for y in range(SIZE):
        for x in range(SIZE):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if int(d) % 3 == 0:  # годовые кольца
                img.putpixel((x, y), vary((128, 100, 58), 8, rng))
    # кора по периметру
    for i in range(SIZE):
        for x, y in ((i, 0), (i, SIZE - 1), (0, i), (SIZE - 1, i)):
            img.putpixel((x, y), vary((96, 76, 45), 10, rng))
    return img


def leaves():
    rng = random.Random(9)
    img = filled((55, 124, 42))
    speckle(img, (44, 102, 33), 12, 0.45, rng)   # тёмные прогалины
    speckle(img, (70, 146, 52), 10, 0.18, rng)   # светлые листья
    return img


def planks():
    rng = random.Random(10)
    img = filled((162, 131, 79))
    speckle(img, (162, 131, 79), 10, 0.4, rng)
    # горизонтальные швы между досками
    for y in (3, 7, 11, 15):
        for x in range(SIZE):
            img.putpixel((x, y), vary((118, 93, 54), 6, rng))
    # вертикальные стыки со смещением на каждой доске
    for band in range(4):
        x = (band * 5 + 2) % SIZE
        for y in range(band * 4, band * 4 + 3):
            img.putpixel((x, y), vary((124, 98, 58), 6, rng))
    return img


def gravel():
    rng = random.Random(11)
    img = filled((136, 126, 120))
    # крупная галька: пятна 2x2 разных оттенков
    for _ in range(22):
        x, y = rng.randrange(SIZE), rng.randrange(SIZE)
        c = vary(rng.choice(((150, 140, 132), (112, 104, 99), (95, 90, 88))), 8, rng)
        for dx in range(2):
            for dy in range(2):
                img.putpixel(((x + dx) % SIZE, (y + dy) % SIZE), c)
    return img


def snow():
    rng = random.Random(12)
    img = filled((238, 244, 250))
    speckle(img, (226, 234, 244), 6, 0.35, rng)
    return img


def birch_log():
    rng = random.Random(13)
    img = filled((216, 215, 204))
    speckle(img, (216, 215, 204), 8, 0.35, rng)
    # чёрные чечевички берёзовой коры
    for _ in range(9):
        x, y = rng.randrange(SIZE), rng.randrange(SIZE)
        w = rng.randint(2, 4)
        for dx in range(w):
            img.putpixel(((x + dx) % SIZE, y), (48, 46, 42, 255))
    return img


def birch_log_top():
    rng = random.Random(14)
    img = filled((198, 187, 155))
    cx = cy = (SIZE - 1) / 2
    for y in range(SIZE):
        for x in range(SIZE):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if int(d) % 3 == 0:
                img.putpixel((x, y), vary((172, 160, 128), 8, rng))
    for i in range(SIZE):
        for x, y in ((i, 0), (i, SIZE - 1), (0, i), (SIZE - 1, i)):
            img.putpixel((x, y), vary((214, 212, 200), 8, rng))
    return img


def spruce_log():
    rng = random.Random(15)
    img = filled((74, 55, 34))
    for x in range(SIZE):
        base = (60, 44, 27) if x % 3 == 0 else (84, 63, 39)
        for y in range(SIZE):
            if rng.random() < 0.7:
                img.putpixel((x, y), vary(base, 8, rng))
    return img


def spruce_log_top():
    rng = random.Random(16)
    img = filled((122, 96, 60))
    cx = cy = (SIZE - 1) / 2
    for y in range(SIZE):
        for x in range(SIZE):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if int(d) % 2 == 0:
                img.putpixel((x, y), vary((100, 78, 48), 6, rng))
    for i in range(SIZE):
        for x, y in ((i, 0), (i, SIZE - 1), (0, i), (SIZE - 1, i)):
            img.putpixel((x, y), vary((66, 49, 30), 8, rng))
    return img


def birch_leaves():
    rng = random.Random(17)
    img = filled((96, 160, 78))
    speckle(img, (78, 136, 62), 10, 0.45, rng)
    speckle(img, (118, 182, 96), 8, 0.2, rng)
    return img


def spruce_leaves():
    rng = random.Random(18)
    img = filled((38, 84, 56))
    speckle(img, (30, 68, 46), 8, 0.45, rng)
    speckle(img, (52, 104, 70), 8, 0.18, rng)
    return img


def _transparent():
    return Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))


def tall_grass():
    rng = random.Random(19)
    img = _transparent()
    # пучок травинок от земли вверх
    for bx in range(2, SIZE - 2, 2):
        h = rng.randint(6, 12)
        x = bx
        for i in range(h):
            y = SIZE - 1 - i
            img.putpixel((max(0, min(SIZE - 1, x)), y),
                         vary((88, 152, 58), 18, rng))
            if rng.random() < 0.3:
                x += rng.choice((-1, 1))
    return img


def _flower(seed, petal):
    rng = random.Random(seed)
    img = _transparent()
    # стебель
    for i in range(7):
        img.putpixel((8, SIZE - 1 - i), vary((62, 118, 48), 10, rng))
    img.putpixel((7, SIZE - 4), (62, 118, 48, 255))  # листик
    # цветок 3x3 с сердцевиной
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            img.putpixel((8 + dx, 7 + dy), vary(petal, 12, rng))
    img.putpixel((8, 7), (240, 208, 82, 255))
    return img


def flower_red():
    return _flower(20, (196, 46, 38))


def flower_yellow():
    return _flower(21, (222, 188, 34))


def _mushroom(seed, cap):
    rng = random.Random(seed)
    img = _transparent()
    # ножка
    for i in range(4):
        img.putpixel((8, SIZE - 1 - i), vary((214, 205, 186), 8, rng))
    # шляпка
    for dx in range(-2, 3):
        img.putpixel((8 + dx, SIZE - 5), vary(cap, 10, rng))
    for dx in range(-1, 2):
        img.putpixel((8 + dx, SIZE - 6), vary(cap, 10, rng))
    img.putpixel((8, SIZE - 5), (238, 232, 220, 255))  # пятнышко
    return img


def mushroom_red():
    return _mushroom(22, (176, 42, 36))


def mushroom_brown():
    return _mushroom(23, (128, 92, 62))


def cactus_side():
    rng = random.Random(24)
    img = filled((58, 122, 48))
    # вертикальные рёбра
    for x in (2, 7, 12):
        for y in range(SIZE):
            img.putpixel((x, y), vary((44, 100, 38), 6, rng))
    # колючки
    for _ in range(8):
        img.putpixel((rng.randrange(SIZE), rng.randrange(SIZE)),
                     (206, 214, 160, 255))
    return img


def cactus_top():
    rng = random.Random(25)
    img = filled((66, 132, 54))
    for i in range(SIZE):
        for x, y in ((i, 0), (i, SIZE - 1), (0, i), (SIZE - 1, i)):
            img.putpixel((x, y), vary((48, 104, 40), 6, rng))
    img.putpixel((8, 8), (206, 214, 160, 255))
    return img


def sugar_cane():
    rng = random.Random(26)
    img = _transparent()
    # три стебля с сегментами
    for x in (3, 8, 13):
        for y in range(SIZE):
            c = (118, 174, 88) if (y % 5) != 4 else (94, 142, 70)  # узлы
            img.putpixel((x, y), vary(c, 10, rng))
            if rng.random() < 0.35:
                img.putpixel((max(0, min(SIZE - 1, x + rng.choice((-1, 1)))), y),
                             vary((104, 158, 80), 10, rng))
    return img


def dead_bush():
    rng = random.Random(27)
    img = _transparent()
    # веточки от основания
    for _ in range(6):
        x, y = 8, SIZE - 1
        dx = rng.choice((-1, 0, 1))
        for i in range(rng.randint(5, 9)):
            img.putpixel((max(0, min(SIZE - 1, x)), max(0, y)),
                         vary((124, 92, 48), 14, rng))
            y -= 1
            if rng.random() < 0.5:
                x += dx
    return img


TEXTURES = {
    'grass_top': grass_top,
    'grass_side': grass_side,
    'dirt': dirt,
    'stone': stone,
    'sand': sand,
    'water': water,
    'oak_log': oak_log,
    'oak_log_top': oak_log_top,
    'leaves': leaves,
    'planks': planks,
    'gravel': gravel,
    'snow': snow,
    'birch_log': birch_log,
    'birch_log_top': birch_log_top,
    'spruce_log': spruce_log,
    'spruce_log_top': spruce_log_top,
    'birch_leaves': birch_leaves,
    'spruce_leaves': spruce_leaves,
    'tall_grass': tall_grass,
    'flower_red': flower_red,
    'flower_yellow': flower_yellow,
    'mushroom_red': mushroom_red,
    'mushroom_brown': mushroom_brown,
    'cactus_side': cactus_side,
    'cactus_top': cactus_top,
    'sugar_cane': sugar_cane,
    'dead_bush': dead_bush,
}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, fn in TEXTURES.items():
        path = OUT_DIR / f'{name}.png'
        fn().save(path)
        print(f'записано {path.relative_to(OUT_DIR.parents[1])}')


if __name__ == '__main__':
    main()
