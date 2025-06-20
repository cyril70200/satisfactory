import uuid
import json
import os

class Item:
    def __init__(self, item_id, rate, recipe_id=None, outsourced=False, ingredients=None, uuid_str=None, extra_rate=0.0, use_extra_rate=False):
        self.item_id = item_id
        self.rate = rate
        self.recipe_id = recipe_id
        self.outsourced = outsourced
        self.ingredients = ingredients or []  # List of Item instances
        self.uuid = uuid_str or uuid.uuid4().hex
        self.extra_rate = extra_rate  # float, default 0.0
        self.use_extra_rate = use_extra_rate  # boolean, default False

    def update_rate(self, new_rate):
        # If use_extra_rate is True, add extra_rate to the calculated rate
        effective_rate = new_rate + self.extra_rate if self.use_extra_rate else new_rate
        self.rate = effective_rate
        # Propagate to ingredients based on recipe ratios
        if self.recipe_id and self.ingredients:
            recipes_path = os.path.join(os.path.dirname(__file__), '../raw_data/enhanced_recipes.json')
            with open(recipes_path, 'r', encoding='utf-8') as f:
                recipes = json.load(f)
            recipe = recipes.get(self.recipe_id)
            if recipe and 'ingredients' in recipe and 'products' in recipe:
                # Find the product rate for this item
                prod_rate = None
                for prod in recipe['products']:
                    if prod['item'] == self.item_id:
                        prod_rate = prod.get('rate')
                        break
                if prod_rate:
                    for ing_obj in self.ingredients:
                        # Find the matching ingredient in the recipe
                        for ing in recipe['ingredients']:
                            if ing['item'] == ing_obj.item_id:
                                # Set child rate proportionally
                                ing_obj.update_rate(self.rate * (ing['rate'] / prod_rate))
                                break

    def select_recipe(self, recipe_id):
        self.recipe_id = recipe_id
        # Optionally update ingredients based on recipe

    def set_extra_rate(self, value):
        self.extra_rate = value

    def set_use_extra_rate(self, value):
        self.use_extra_rate = value

    def to_dict(self):
        return {
            'item_id': self.item_id,
            'rate': self.rate,
            'recipe_id': self.recipe_id,
            'outsourced': self.outsourced,
            'ingredients': [ing.to_dict() for ing in self.ingredients],
            'uuid': self.uuid,
            'extra_rate': self.extra_rate,
            'use_extra_rate': self.use_extra_rate
        }

    @classmethod
    def from_dict(cls, data):
        item = cls(
            data['item_id'],
            data['rate'],
            data.get('recipe_id'),
            data.get('outsourced', False),
            [cls.from_dict(ing) for ing in data.get('ingredients', [])],
            data.get('uuid'),
            data.get('extra_rate', 0.0),
            data.get('use_extra_rate', False)
        )
        return item

    def find_by_uuid(self, uuid_str):
        if self.uuid == uuid_str:
            return self
        for ing in self.ingredients:
            found = ing.find_by_uuid(uuid_str)
            if found:
                return found
        return None

    @classmethod
    def all_items(cls):
        """Load all items from data.json and return a dict of item_id to item name."""
        data_path = os.path.join(os.path.dirname(__file__), '../raw_data/data.json')
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        items = data.get('items', {})
        return {item_id: item_data['name'] for item_id, item_data in items.items()}

    def get_recipes(self):
        """
        Return a list of (recipe_id, recipe, product) for all recipes that produce this item.
        Ensures only one outsourced entry.
        """
        recipes_path = os.path.join(os.path.dirname(__file__), '../raw_data/enhanced_recipes.json')
        with open(recipes_path, 'r', encoding='utf-8') as f:
            recipes = json.load(f)
        result = []
        for recipe_id, recipe in recipes.items():
            for prod in recipe.get('products', []):
                if prod['item'] == self.item_id:
                    result.append((recipe_id, recipe, prod))
        # Remove all outsourced entries, then add one at the end
        result = [r for r in result if r[0] != '__outsourced__']
        result.append(('__outsourced__', {}, {'item': self.item_id, 'rate': self.rate}))
        return result

    @staticmethod
    def get_machine_name(machine_id):
        data_path = os.path.join(os.path.dirname(__file__), '../raw_data/data.json')
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        machines = data.get('machines', {})
        if machine_id in machines:
            return machines[machine_id].get('name', machine_id)
        return machine_id or 'Unknown'

    def to_card_dict(self, item_names=None, ingredient_ids=None, resource_names=None, include_extra_products=False):
        """
        Return a dict with all info needed for card rendering, including children and recipe info.
        item_names: dict of item_id to name (optional, for display)
        ingredient_ids: set of item_ids used as ingredients in the current tree (for byproduct detection)
        include_extra_products: only True for the root card, False for all children
        """
        if item_names is None:
            item_names = Item.all_items()
        if ingredient_ids is None:
            # Build a set of all ingredient item_ids in this subtree (excluding self)
            ingredient_ids = set()
            def collect_ingredient_ids(item):
                for ing in item.ingredients:
                    ingredient_ids.add(ing.item_id)
                    collect_ingredient_ids(ing)
            collect_ingredient_ids(self)
        if resource_names is None and hasattr(self, 'resource_names'):
            resource_names = getattr(self, 'resource_names', {})
        elif resource_names is None:
            resource_names = {}
        card = {
            'item_id': self.item_id,
            'name': item_names.get(self.item_id, self.item_id) if self.item_id else 'Unknown Item',
            'rate': self.rate,
            'recipe_id': self.recipe_id,
            'outsourced': self.outsourced,
            'uuid': self.uuid,
            'ingredients': [ing.to_card_dict(item_names, None, resource_names, include_extra_products=False) for ing in self.ingredients],
            'recipe_name': None,
            'machine': None,
            'machine_name': None,
            'power_use': None,
            'products': [],
            'num_machines': None,
            'total_power': None,
            'byproducts': [],
            'extra_rate': self.extra_rate,
            'use_extra_rate': self.use_extra_rate
        }
        # Add recipe info if recipe_id is set
        if self.recipe_id:
            recipes_path = os.path.join(os.path.dirname(__file__), '../raw_data/enhanced_recipes.json')
            with open(recipes_path, 'r', encoding='utf-8') as f:
                recipes = json.load(f)
            recipe = recipes.get(self.recipe_id)
            if recipe:
                card['recipe_name'] = recipe.get('name', self.recipe_id)
                card['machine'] = recipe.get('machine')
                card['machine_name'] = Item.get_machine_name(recipe.get('machine')) if recipe.get('machine') else None
                card['power_use'] = recipe.get('power_use')
                card['products'] = [
                    {
                        'item_id': prod['item'],
                        'name': (resource_names.get(prod['item']) if resource_names and prod['item'] in resource_names else item_names.get(prod['item'], prod['item'])) if prod.get('item') else 'Unknown Item',
                        'rate': prod.get('rate')
                    }
                    for prod in recipe.get('products', [])
                ]
                # Calculate number of machines and total power
                prod_rate = None
                for prod in card['products']:
                    if prod['item_id'] == self.item_id:
                        prod_rate = prod['rate']
                        break
                if prod_rate and card['power_use']:
                    card['num_machines'] = round(self.rate / prod_rate, 2)
                    card['total_power'] = round(card['num_machines'] * card['power_use'], 2)
                # Byproducts: products not matching self.item_id (show all, even if also ingredient)
                if card['num_machines']:
                    card['byproducts'] = [
                        {
                            **prod,
                            'rate': round(prod['rate'] * card['num_machines'], 2)
                        }
                        for prod in card['products']
                        if prod['item_id'] != self.item_id
                    ]
                else:
                    card['byproducts'] = [
                        prod for prod in card['products']
                        if prod['item_id'] != self.item_id
                    ]
        elif self.outsourced or not self.recipe_id:
            card['recipe_name'] = 'Outsourced'
        # Fallbacks if still None
        if not card['name']:
            card['name'] = 'Unknown Item'
        if not card['recipe_name']:
            card['recipe_name'] = 'Unknown Recipe'
        return card
