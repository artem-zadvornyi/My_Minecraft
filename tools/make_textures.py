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
}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, fn in TEXTURES.items():
        path = OUT_DIR / f'{name}.png'
        fn().save(path)
        print(f'записано {path.relative_to(OUT_DIR.parents[1])}')


if __name__ == '__main__':
    main()
