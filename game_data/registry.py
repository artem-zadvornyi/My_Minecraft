# -*- coding: utf-8 -*-
"""Универсальный реестр определений.

Каждое определение обязано иметь уникальные `key` (строковый внутренний
ключ, используется в рантайме) и `id` (стабильный числовой идентификатор
для будущей сериализации миров). Порядок итерации — порядок регистрации.
"""


class RegistryError(ValueError):
    """Конфликт ключей/идентификаторов или ссылка на несуществующую запись."""


class Registry:
    def __init__(self, kind):
        self.kind = kind          # человекочитаемое имя ('блок', 'предмет')
        self._by_key = {}
        self._by_id = {}

    def register(self, definition):
        """Регистрирует определение и возвращает его же (удобно для констант)."""
        key, num_id = definition.key, definition.id
        if key in self._by_key:
            raise RegistryError(f'{self.kind}: ключ {key!r} уже зарегистрирован')
        if num_id in self._by_id:
            raise RegistryError(
                f'{self.kind}: id {num_id} уже занят ({self._by_id[num_id].key!r})')
        if num_id <= 0:
            raise RegistryError(f'{self.kind}: id должен быть > 0 (0 — воздух)')
        self._by_key[key] = definition
        self._by_id[num_id] = definition
        return definition

    # --- доступ ---
    def __getitem__(self, key):
        return self._by_key[key]

    def get(self, key, default=None):
        return self._by_key.get(key, default)

    def by_id(self, num_id, default=None):
        return self._by_id.get(num_id, default)

    def __contains__(self, key):
        return key in self._by_key

    def __iter__(self):
        return iter(self._by_key.values())

    def keys(self):
        return self._by_key.keys()

    def values(self):
        return self._by_key.values()

    def __len__(self):
        return len(self._by_key)
