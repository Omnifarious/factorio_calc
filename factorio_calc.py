import pickle
import os
import os.path as _osp
from fractions import Fraction as _F
import sys
from collections import namedtuple
import re
from xml.etree import ElementTree

def _checkXMLHasNoText(xmlel):
    return ((xmlel.text is None) or (xmlel.text.strip() == '')) \
        and ((xmlel.tail is None) or (xmlel.tail.strip() == ''))

class ProductionItem:
    __slots__ = ('_name', '_time', '_ingredients', '_produced', '__weakref__')

    def __init__(self, name, time, ingredients, produced=1, **kargs):
        super().__init__(**kargs)
        self._produced = produced
        self._name = name
        self._time = time
        def lookup_ingredients(ingredients):
            for ct, item in ingredients:
                if not isinstance(item, ProductionItem):
                    item = item_db[item]
                    print(f"Wasn't already an item, found {item!s}",
                          file=sys.stderr)
                yield (ct, item)
        oldlen = len(ingredients)
        self._ingredients = tuple(item for item in lookup_ingredients(ingredients))
        assert(len(self._ingredients) == oldlen)

    def __hash__(self):
        return hash(self._name)

    def __eq__(self, other):
        if isinstance(other, ProductionItem):
            return self._name == other._name

    def __repr__(self):
        return f'ProductionItem({self._name!r}, {self._time}, ' \
            f'{self._ingredients!r}, produced={self._produced})'

    def __str__(self):
        return self._name

    @property
    def base_rate(self):
        if self._produced is None:
            return None
        else:
            base_rate = (self._produced / _F(1,1)) / (self._time / _F(1,1))
            return base_rate

    def factories(self, rate):
        if self._produced is None:
            return None
        else:
            return rate / self.base_rate

    def rate_with_factories(self, numfactories):
        if self._produced is None:
            return None
        else:
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

    @staticmethod
    def _itemId(item):
        idstr = item._name.lower()
        idstr = re.sub(r'\s+', '_', idstr)
        return idstr

    @staticmethod
    def _itemAsXML(item, item_idmap):
        if item not in item_idmap:
            cur_id = ItemSet._itemId(item)
            item_idmap[item] = (cur_id, False)
            for _, ingredient in item._ingredients:
                yield from ItemSet._itemAsXML(ingredient, item_idmap)
            if item._produced is not None:
                yield f'  <item id="{cur_id}" name="{item._name}" ' \
                      f'time="{item._time}" ' \
                      f'produced="{item._produced}">\n'
                for count, ingredient in item._ingredients:
                    ingredient_id = item_idmap[ingredient][0]
                    yield f'    <ingredient idref="{ingredient_id}" ' \
                          f'count="{count}" />\n'
                yield '  </item>\n'
            else:
                yield f'  <item id="{cur_id}" name="{item._name}" />\n'
            item_idmap[item] = (cur_id, True)
        elif not item_idmap[item][1]:
            raise RuntimeError(f"Circular reference detected '{item._name}'")

    def sortedItems(self):
        itemset = set(self)
        sortedset = set()
        sortedlist = []
        curlst = []
        while len(itemset) > 0:
            for testitem in itemset:
                ingredients = set((ingtuple[1] \
                                   for ingtuple in testitem._ingredients))
                if len(ingredients - sortedset) <= 0:
                    curlst.append(testitem)
            assert(len(curlst) > 0)
            curset = frozenset(curlst)
            itemset.difference_update(curset)
            curlst.sort(key=lambda x: self._itemId(x))
            sortedlist.extend(curlst)
            sortedset.update(curset)
            curset = None
            curlst = []
        return sortedlist

    def asXML(self):
        yield '<?xml version="1.0" encoding="utf-8" standalone="no" ?>\n'
        yield '<factorio_calc_item_db version="1.0">\n'
        item_idmap = {}
        for item in self.sortedItems():
            yield from self._itemAsXML(item, item_idmap)
        yield '</factorio_calc_item_db>\n'

    @staticmethod
    def createFromXML(infile):
        newdb = ItemSet()
        ET = ElementTree
        parser = ET.XMLParser()
        block = infile.read(4 * 1024 * 1024)
        while len(block) > 0:
            parser.feed(block)
            block = infile.read(4 * 1024 * 1024)
        block = None
        tree = parser.close()
        parser = None
        if tree.tag != 'factorio_calc_item_db':
            raise ValueError("Not an XML item database.")
        if tree.attrib.get('version', '1.0') != '1.0':
            raise ValueError(f"Do not know how to handle version "
                             f"{tree.attrib['version']}.")
        if not _checkXMLHasNoText(tree):
            raise ValueError("Invalid XML database.")
        item_idmap = {}
        for itemel in tree.getchildren():
            itemid, item = ItemSet.itemFromXML(item_idmap, itemel)
            item_idmap[itemid] = item
            newdb.add(item)
        return newdb

    @staticmethod
    def itemFromXML(item_idmap, itemel):
        if itemel.tag != 'item':
            raise ValueError(f"Got element '{itemel.tag}', expecting 'item'.")
        itemid = itemel.attrib['id']
        if not _checkXMLHasNoText(itemel):
            raise ValueError(f"Invalid item {itemid}")
        if itemid in item_idmap:
            raise ValueError(f"Item {itemid} defined twice.")
        name = itemel.attrib['name']
        time = itemel.attrib.get('time', None)
        produced = itemel.attrib.get('produced', None)
        if (produced is None) != (time is None):
            raise ValueError(f"Invalid item '{itemid}'.")
        if time is not None:
            time = _F(time)
            produced = int(produced)
        ingredients = []
        for ingredientel in itemel.getchildren():
            if ingredientel.tag != 'ingredient':
                raise ValueError(f"Item {itemid} has {ingredientel.tag}")
            ingid = ingredientel.attrib['idref']
            if not _checkXMLHasNoText(ingredientel):
                raise ValueError(f"Invalid ingredient '{ingid}' in '{itemid}'")
            ingcount = int(ingredientel.attrib['count'])
            if ingid not in item_idmap:
                raise ValueError(f"Item '{itemid}' mentions ingredient "
                                 f"'{ingid}' before it's defined.")
            ingredients.append((ingcount, item_idmap[ingid]))
        if (len(ingredients) > 0) and (time is None):
            raise ValueError(f"Item '{itemid}' has ingredients but "
                             "no production time.")
        return (itemid,
                ProductionItem(name, time, tuple(ingredients), produced))

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

def production_rate(dest_item, rate, source_item, raw_materials=frozenset()):
    if dest_item is source_item:
        return rate
    if (dest_item._produced is None) or (dest_item in raw_materials):
        return 0
    produced = dest_item._produced / _F(1,1)
    scale = rate / produced
#    print(f"name, scale == {dest_item._name}, {scale}")
    total = 0
    for sub_item_ct, sub_item in dest_item._ingredients:
        sub_rate = production_rate(sub_item, scale * sub_item_ct, source_item,
                                   raw_materials=raw_materials)
        total += sub_rate
    return total

def how_many_produced(source_item, rate, dest_item):
    forward_rate = production_rate(dest_item, _F(1,1), source_item)
    return rate / forward_rate

FactoryInfo = namedtuple('FactoryInfo', ['factories', 'fractional_factories',
                                         'target_rate', 'item'])

def factories_for_each(dest_item, rate, raw_materials=frozenset()):
    items_so_far = set()
    factory_list = []
    def recursive_count(dest_item, rate, cur_source=None):
        if cur_source is None:
            cur_source = dest_item
        if cur_source in items_so_far:
            return
        items_so_far.add(cur_source)
        source_rate = production_rate(dest_item, rate, cur_source,
                                      raw_materials=raw_materials)
        if (cur_source._produced is None) or (cur_source in raw_materials):
            factory_list.append(FactoryInfo(None, None, source_rate, cur_source))
        else:
            factories = cur_source.factories(source_rate)
            int_fact = factories // _F(1,1)
            if (factories - int_fact) > 0:
                int_fact += 1
            assert(int_fact >= factories)
            factory_list.append(FactoryInfo(int_fact, factories,
                                            source_rate, cur_source))
            for _, next_source in cur_source._ingredients:
                recursive_count(dest_item, rate, next_source)
    recursive_count(dest_item, rate)
    return factory_list

def actual_production(dest_item, factory_list, raw_materials=frozenset()):
    def produced_for_each(dest_item, factory_list):
        for int_fact, _, _, item in factory_list:
            if int_fact is not None:
                rate = (_F(int_fact, 1) * item._produced) / item._time
                cur_produced = how_many_produced(item, rate, dest_item)
                yield cur_produced
    return min(produced_for_each(dest_item, factory_list))

def print_factories(factory_list, file=None):
    if file is None:
        file = sys.stdout
    raw = []
    print("Factories   (as a fraction)   Rate      Name", file=file)
    print("---------   ---------------   -------   ---------------------",
          file=file)
    for fi in factory_list:
        if fi.factories is None:
            raw.append(fi)
        else:
            print(f'{fi.factories:9}   {fi.fractional_factories!s:>15}   '
                  f'{fi.target_rate!s:>7}   {fi.item._name}', file=file)
    for fi in raw:
        print('                              '
              f'{fi.target_rate!s:>7}   {fi.item._name}', file=file)
