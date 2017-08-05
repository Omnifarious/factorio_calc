#!/usr/bin/python3

import pickle
import os
import os.path as _osp
from fractions import Fraction as _F

class ProductionItem:
    __slots__ = ('_name', '_time', '_ingredients', '_produced', '__weakref__')

    def __init__(self, name, time, ingredients, produced=1, **kargs):
        super().__init__(**kargs)
        self._produced = produced
        self._name = name
        self._time = time
        self._ingredients = ingredients

    def __hash__(self):
        return hash(self._name)

    def __eq__(self, other):
        if isinstance(other, ProductionItem):
            return self._name == other._name

    def __repr__(self):
        return f'ProductionItem({self._name!r}, {self._time}, ' \
            f'{self._ingredients!r}, produced={self._produced})'

    @property
    def base_rate(self):
        base_rate = (self._produced / _F(1,1)) / (self._time / _F(1,1))
        return base_rate

    def factories(self, rate):
        return rate / self.base_rate

    def rate_with_factories(self, numfactories):
        return numfactories * self.base_rate

class ItemSet(set):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self._by_name = dict()

    def __getitem__(self, name):
        item = self._by_name.get(name)
        if item is not None:
            return item
        else:
            for item in self:
                if item._name == name:
                    self._by_name[item._name] = item
                    return item
        raise KeyError(name)

_mod_dir = _osp.dirname(__file__)
db_fname = _osp.join(_mod_dir, 'item-db.pickle')

if _osp.exists(db_fname):
    with open(db_fname, 'rb') as _item_f:
        item_db = pickle.load(_item_f)
else:
    item_db = set()

def save_items():
    tmp_new = db_fname + '.new'
    with open(tmp_new, 'wb') as item_f:
        pickle.dump(item_db, item_f, -1)
    os.unlink(db_fname)
    os.link(tmp_new, db_fname)
    os.unlink(tmp_new)

def production_rate(dest_item, rate, source_item):
    if dest_item is source_item:
        return rate
    if dest_item._produced is None:
        return 0
    produced = dest_item._produced / _F(1,1)
    scale = rate / produced
    print(f"name, scale == {dest_item._name}, {scale}")
    total = 0
    for sub_item_ct, sub_item in dest_item._ingredients:
        sub_rate = production_rate(sub_item, scale * sub_item_ct, source_item)
        total += sub_rate
    return total

def how_many_produced(source_item, rate, dest_item):
    forward_rate = production_rate(dest_item, _F(1,1), source_item)
    return rate / forward_rate
