from collections import defaultdict
import math
from models.item import Item

class Project:
    def __init__(self, name="Untitled Project", items=None, dirty=False):
        self.name = name
        self.items = items or []  # List of top-level Item instances
        self.dirty = dirty  # True if unsaved changes exist

    @staticmethod
    def load(project_id, project_cache, load_func):
        if project_id in project_cache:
            return project_cache[project_id]
        project = load_func(project_id)
        project.mark_clean()
        project_cache[project_id] = project
        return project

    def save(self, project_id, project_cache, save_func):
        save_func(self, project_id)
        self.mark_clean()
        project_cache[project_id] = self

    def add_item(self, item: Item):
        self.items.append(item)
        self.mark_dirty()

    def remove_item(self, item_uuid):
        self.items = [item for item in self.items if getattr(item, 'uuid', None) != item_uuid]
        self.mark_dirty()

    def mark_dirty(self):
        self.dirty = True

    def mark_clean(self):
        self.dirty = False

    def to_dict(self):
        return {
            "name": self.name,
            "items": [item.to_dict() for item in self.items],
            "dirty": self.dirty
        }

    @classmethod
    def from_dict(cls, data):
        items = [Item.from_dict(d) for d in data.get("items", [])]
        return cls(name=data.get("name", "Untitled Project"), items=items, dirty=data.get("dirty", False))

    def rename(self, new_name):
        self.name = new_name
        self.mark_dirty()

    def change_rate(self, item_uuid, new_rate):
        for item in self.items:
            if getattr(item, 'uuid', None) == item_uuid:
                item.update_rate(new_rate)  # propagate to children
                self.mark_dirty()
                break

    def find_item_by_uuid(self, uuid_str):
        for item in self.items:
            found = item.find_by_uuid(uuid_str)
            if found:
                return found
        return None

    def get_production_report(self, item_names=None, resource_ids=None):
        """
        Returns a dict with:
            - total_power: float
            - machines: {machine_name: {count, power}}
            - items: {item_id: {name, rate, type}}
        """
        if item_names is None:
            item_names = Item.all_items()
        if resource_ids is None:
            resource_ids = set()
        resource_names = getattr(self, 'resource_names', {})
        total_power = 0.0
        machines = defaultdict(lambda: {'count': 0.0, 'power': 0.0})
        items = {}
        byproducts = defaultdict(float)
        # Track all types for each item_id, but allow byproduct/resource to be split
        project_root_ids = set(item.item_id for item in self.items)
        def item_key(item_id, item_type):
            # For byproduct/resource, use a tuple key
            if item_type == 'byproduct':
                return (item_id, 'byproduct')
            if item_type == 'resource':
                return (item_id, 'resource')
            return (item_id, item_type)
        def walk(item, parent_type=None, is_root=False):
            nonlocal total_power
            if item.item_id in project_root_ids:
                item_type = 'project'
            elif item.item_id in resource_ids:
                item_type = 'resource'
            elif getattr(item, 'outsourced', False):
                item_type = 'outsourced'
            elif parent_type == 'byproduct':
                item_type = 'byproduct'
            else:
                item_type = 'intermediate'
            key = item_key(item.item_id, item_type)
            display_name = item_names.get(item.item_id, item.item_id)
            if item_type == 'resource' and item.item_id in resource_names:
                display_name = resource_names[item.item_id]
            if item_type == 'byproduct' and item.item_id in resource_names:
                display_name = resource_names[item.item_id] + ' (byproduct)'
            if key not in items:
                items[key] = {
                    'name': display_name,
                    'rate': 0.0,
                    'type': item_type
                }
            items[key]['rate'] += item.rate
            card = item.to_card_dict(item_names, None, resource_names, include_extra_products=is_root)
            if card.get('machine_name') and card.get('num_machines') and card.get('total_power'):
                mname = card['machine_name']
                n_machines = math.ceil(card['num_machines'])
                machines[mname]['count'] += n_machines
                machines[mname]['power'] += n_machines * card['power_use'] if card.get('power_use') else 0.0
                total_power += n_machines * card['power_use'] if card.get('power_use') else 0.0
            for byp in card.get('byproducts', []):
                byp_key = item_key(byp['item_id'], 'byproduct')
                byp_name = item_names.get(byp['item_id'], byp['item_id'])
                if byp['item_id'] in resource_names:
                    byp_name = resource_names[byp['item_id']] + ' (byproduct)'
                if byp_key not in items:
                    items[byp_key] = {
                        'name': byp_name,
                        'rate': 0.0,
                        'type': 'byproduct'
                    }
                items[byp_key]['rate'] += byp['rate']
            for ing in getattr(item, 'ingredients', []):
                walk(ing, parent_type=item_type, is_root=False)
        for item in self.items:
            walk(item, is_root=True)
        # Flatten items for output
        flat_items = {}
        for (iid, typ), val in items.items():
            flat_items[f'{iid}__{typ}'] = val
        return {
            'total_power': round(total_power, 2),
            'machines': {k: {'count': int(v['count']), 'power': round(v['power'], 2)} for k, v in machines.items()},
            'items': flat_items
        }
