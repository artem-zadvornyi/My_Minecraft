# -*- coding: utf-8 -*-
"""Атлас текстур: все тайлы 16x16 склеиваются в одну текстуру.

- Раскладка и UV считаются чистым кодом (тестируется без окна),
  GPU-текстура создаётся лениво при первом обращении к .texture.
- UV каждого тайла поджаты на полтекселя внутрь: вместе с фильтрацией
  «ближайший сосед» это исключает протекание соседних тайлов.
- Тайл 0 всегда чисто-белый: грани без текстуры рисуются им с запасным
  цветом вершин — конвейер один и тот же с текстурами и без.
- Если атлас собрать не удалось (нет PIL, нет папки), get_atlas()
  возвращает None и мир рисуется цветами, как раньше.
"""
import math
from pathlib import Path

TILE = 16
TEXTURE_DIR = Path(__file__).resolve().parents[1] / 'assets' / 'textures'
WHITE_TILE = '__white__'


class TextureAtlas:
    def __init__(self, texture_dir=TEXTURE_DIR):
        from PIL import Image
        files = sorted(texture_dir.glob('*.png'))
        if not files:
            raise FileNotFoundError(f'нет текстур в {texture_dir}')
        names = [WHITE_TILE] + [p.stem for p in files]
        cols = math.ceil(math.sqrt(len(names)))
        rows = math.ceil(len(names) / cols)
        self.image = Image.new('RGBA', (cols * TILE, rows * TILE),
                               (255, 255, 255, 255))
        w, h = self.image.size
        self._uv = {}
        for i, name in enumerate(names):
            col, row = i % cols, i // cols
            if name != WHITE_TILE:
                tile = Image.open(texture_dir / f'{name}.png').convert('RGBA')
                if tile.size != (TILE, TILE):
                    tile = tile.resize((TILE, TILE))
                self.image.paste(tile, (col * TILE, row * TILE))
            # полтекселя отступа от краёв тайла против протекания
            u0 = (col * TILE + 0.5) / w
            u1 = ((col + 1) * TILE - 0.5) / w
            # PIL хранит картинку сверху вниз, OpenGL считает v=0 низом:
            # верх тайла — это v1
            v1 = 1 - (row * TILE + 0.5) / h
            v0 = 1 - ((row + 1) * TILE - 0.5) / h
            self._uv[name] = (u0, v0, u1, v1)
        self._texture = None

    # ------------------------------------------------------------------
    def uv(self, name):
        """(u0, v0, u1, v1) тайла или None, если текстуры нет."""
        return self._uv.get(name)

    @property
    def white_uv(self):
        """UV чисто-белого тайла (для граней с запасным цветом)."""
        return self._uv[WHITE_TILE]

    @property
    def texture(self):
        """GPU-текстура (лениво): «ближайший сосед», без сглаживания."""
        if self._texture is None:
            from ursina import Texture
            self._texture = Texture(self.image, filtering='nearest')
        return self._texture

    def icon_model(self, name):
        """Новый quad-меш с UV тайла (каждой сущности — свой экземпляр)."""
        rect = self.uv(name)
        if rect is None:
            return None
        from ursina import Mesh
        u0, v0, u1, v1 = rect
        return Mesh(vertices=[(-.5, -.5, 0), (.5, -.5, 0),
                              (.5, .5, 0), (-.5, .5, 0)],
                    triangles=[0, 1, 2, 0, 2, 3],
                    uvs=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)],
                    static=True)


# ----------------------------------------------------------------------
_atlas = None
_atlas_failed = False


def get_atlas():
    """Общий атлас (None, если собрать не удалось — рисуем цветами)."""
    global _atlas, _atlas_failed
    if _atlas is None and not _atlas_failed:
        try:
            _atlas = TextureAtlas()
        except Exception as e:  # noqa: BLE001 — любой сбой => запасной путь
            print(f'Атлас текстур недоступен ({e}), мир рисуется цветами')
            _atlas_failed = True
    return _atlas


def apply_item_icon(entity, item):
    """Иконка предмета на quad-сущности: тайл атласа или запасной цвет.

    Единый конвейер: с атласом иконка всегда текстурирована (белый тайл
    подкрашивается icon_color), без атласа — цветной квад, как раньше.
    """
    from game_data.definitions import WHITE
    atlas = get_atlas()
    if atlas is not None:
        name = item.icon if item.icon and atlas.uv(item.icon) else WHITE_TILE
        entity.model = atlas.icon_model(name)
        entity.texture = atlas.texture
        entity.color = WHITE if name != WHITE_TILE else item.icon_color
    else:
        entity.model = 'quad'
        entity.color = item.icon_color
