from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
import json
import os
import math
import io

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # For session management

RECIPES_PATH = os.path.join(os.path.dirname(__file__), 'raw_data', 'enhanced_recipes.json')
# Load item names from data.json for better display
DATA_PATH = os.path.join(os.path.dirname(__file__), 'raw_data', 'data.json')
def load_item_names():
    try:
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            items = data.get('items', {})
            resources = data.get('resources', {})
            names = {k: v.get('name', k) for k, v in items.items()}
            # Add/override with resource names
            for k, v in resources.items():
                names[k] = v.get('name', k)
            return names
    except Exception:
        return {}
ITEM_NAMES = load_item_names()

def load_recipes():
    with open(RECIPES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_item_name(item_id, recipes):
    # Try data.json first
    if item_id in ITEM_NAMES:
        return ITEM_NAMES[item_id]
    # Try to find a human-readable name for an item_id
    for recipe in recipes.values():
        for prod in recipe.get('products', []):
            if prod['item'] == item_id and 'name' in prod:
                return prod['name']
        for ing in recipe.get('ingredients', []):
            if ing['item'] == item_id and 'name' in ing:
                return ing['name']
    # Fallback: try to find a recipe with a name
    for recipe in recipes.values():
        if recipe.get('name') and recipe.get('recipe_id') == item_id:
            return recipe['name']
    return item_id

def get_recipe_name(recipe_id, recipes):
    recipe = recipes.get(recipe_id)
    if recipe and 'name' in recipe:
        return recipe['name']
    return recipe_id

# Load machine names from data.json for display
MACHINES = {}
def load_machine_names():
    try:
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            machines = data.get('machines', {})
            return {k: v.get('name', k) for k, v in machines.items()}
    except Exception:
        return {}
MACHINES = load_machine_names()

def get_machine_name(machine_id):
    return MACHINES.get(machine_id, machine_id)

def build_card_tree(item, rate, recipes, selected_recipes, path=None, byproduct_pool=None):
    """
    Recursively build a card tree for the item at the given rate.
    selected_recipes: dict {item_id: recipe_id} for user choices
    path: list of item_ids in the current expansion branch (for circular detection)
    byproduct_pool: dict {item_id: available_rate} for byproduct usage
    Returns a dict representing the card and its children.
    """
    if path is None:
        path = []
    if byproduct_pool is None:
        byproduct_pool = {}
    if item in path:
        # Circular dependency detected
        return {
            'item': item,
            'rate': rate,
            'name': get_item_name(item, recipes),
            'recipe_id': None,
            'recipe_name': None,
            'machines': None,
            'machine_id': None,
            'machine_name': None,
            'power': None,
            'ingredients': [],
            'children': [],
            'circular': True,
            'circular_path': path + [item]
        }
    recipe_id = selected_recipes.get(item)
    if not recipe_id or recipe_id == '__outsourced__':
        return {
            'item': item,
            'rate': rate,
            'name': get_item_name(item, recipes),
            'recipe_id': '__outsourced__',
            'recipe_name': 'Outsourced',
            'machines': None,
            'machine_id': None,
            'machine_name': None,
            'power': None,
            'ingredients': [],
            'recipe': None,
            'byproducts': [],
            'outsource': True
        }
    recipe = recipes[recipe_id]
    prod = next(prod for prod in recipe['products'] if prod['item'] == item)
    output_rate = prod['rate']
    machines = rate / output_rate
    machine_id = recipe.get('machine')
    machine_name = get_machine_name(machine_id)
    power = recipe.get('power_use', 0) * machines
    ingredients = []
    # --- Byproduct pool logic ---
    # Add byproducts from this recipe to the pool
    local_byproduct_pool = byproduct_pool.copy()
    for p in recipe.get('products', []):
        if p['item'] != item:
            produced = p['rate'] * machines
            local_byproduct_pool[p['item']] = local_byproduct_pool.get(p['item'], 0) + produced
    for ing in recipe.get('ingredients', []):
        ing_name = get_item_name(ing['item'], recipes)
        ing_rate = ing['rate'] * machines
        used_byproduct = 0
        # Try to use byproduct pool for this ingredient
        if not ing.get('resource', False) and ing['item'] in local_byproduct_pool and local_byproduct_pool[ing['item']] > 0:
            used_byproduct = min(ing_rate, local_byproduct_pool[ing['item']])
            local_byproduct_pool[ing['item']] -= used_byproduct
        ing_dict = {
            'item': ing['item'],
            'name': ing_name,
            'rate': ing_rate,
            'resource': ing.get('resource', False),
            'byproduct_used': used_byproduct if used_byproduct > 0 else None,
            'net_rate': ing_rate - used_byproduct if used_byproduct else ing_rate,
            'debug': f"ingredient: {ing['item']} ({ing_name})"
        }
        if not ing.get('resource', False):
            # Only produce the remainder if byproduct didn't cover all
            remainder = ing_rate - used_byproduct
            if remainder > 0:
                child_card = build_card_tree(ing['item'], remainder, recipes, selected_recipes, path + [item], local_byproduct_pool)
                if isinstance(child_card, dict):
                    child_card['debug'] = f"child for: {ing['item']} ({ing_name})"
                ing_dict['child_card'] = child_card
        ingredients.append(ing_dict)
    # Compute byproducts for this recipe (excluding the main product)
    byproducts = []
    for p in recipe.get('products', []):
        if p['item'] != item:
            byproducts.append({
                'name': get_item_name(p['item'], recipes),
                'rate': p['rate'] * machines
            })
    return {
        'item': item,
        'rate': rate,
        'name': get_item_name(item, recipes),
        'recipe_id': recipe_id,
        'recipe_name': get_recipe_name(recipe_id, recipes),
        'machines': machines,
        'machine_id': machine_id,
        'machine_name': machine_name,
        'power': power,
        'ingredients': ingredients,
        'recipe': recipe,
        'byproducts': byproducts
    }

def collect_byproducts(item, rate, recipes, selected_recipes, path=None, pool=None):
    if path is None:
        path = []
    if pool is None:
        pool = {}
    if item in path:
        return pool
    recipe_id = selected_recipes.get(item)
    if not recipe_id or recipe_id == '__outsourced__':
        return pool
    recipe = recipes[recipe_id]
    prod = next(prod for prod in recipe['products'] if prod['item'] == item)
    output_rate = prod['rate']
    machines = rate / output_rate
    # Add byproducts
    for p in recipe.get('products', []):
        if p['item'] != item:
            pool[p['item']] = pool.get(p['item'], 0) + p['rate'] * machines
    # Recurse for non-resource ingredients
    for ing in recipe.get('ingredients', []):
        if not ing.get('resource', False):
            ing_rate = ing['rate'] * machines
            collect_byproducts(ing['item'], ing_rate, recipes, selected_recipes, path + [item], pool)
    return pool

def get_all_product_items(recipes):
    """Return a list of (item_id, name) for all unique product items."""
    items = {}
    for recipe in recipes.values():
        for prod in recipe.get('products', []):
            if 'item' in prod:
                # Prefer data.json name if available
                items[prod['item']] = ITEM_NAMES.get(prod['item'], prod.get('name', prod['item']))
    # If no name is found, fallback to item_id
    for item_id in items:
        if not items[item_id] or items[item_id] == item_id:
            # Try to find a name in any ingredient
            for recipe in recipes.values():
                for ing in recipe.get('ingredients', []):
                    if ing['item'] == item_id and 'name' in ing:
                        items[item_id] = ing['name']
    return sorted(items.items(), key=lambda x: x[1].lower())

@app.route('/add_item', methods=['POST'])
def add_item():
    recipes = load_recipes()
    items = get_all_product_items(recipes)
    item_id = request.form['item']
    try:
        rate = float(request.form['rate'])
    except Exception:
        flash('Invalid rate value.')
        return redirect(url_for('index'))
    # Initialize project_items in session if not present
    project_items = session.get('project_items', [])
    # Prevent duplicate items (by id)
    for it in project_items:
        if it['item'] == item_id:
            flash('Item already in project. Remove it first to change rate.')
            return redirect(url_for('index'))
    # Add new item
    project_items.append({'item': item_id, 'rate': rate})
    session['project_items'] = project_items
    # Optionally, initialize selected_recipes for this item
    selected_recipes = session.get('selected_recipes', {})
    session['selected_recipes'] = selected_recipes
    return redirect(url_for('index'))

@app.route('/', methods=['GET'])
def index():
    recipes = load_recipes()
    items = get_all_product_items(recipes)
    project_items = session.get('project_items', [])
    selected_recipes = session.get('selected_recipes', {})
    print('DEBUG selected_recipes:', selected_recipes)
    # Build card for each item
    project_cards = []
    for it in project_items:
        item_id = it['item']
        rate = it['rate']
        # Byproduct pooling per item for now (can be global if needed)
        byproduct_pool = collect_byproducts(item_id, rate, recipes, selected_recipes)
        card = build_card_tree(item_id, rate, recipes, selected_recipes, byproduct_pool=byproduct_pool)
        # Add a flag if recipe is missing
        has_recipe = item_id in selected_recipes
        project_cards.append({'item': item_id, 'name': get_item_name(item_id, recipes), 'rate': rate, 'card': card, 'has_recipe': has_recipe})
    # Global summary for all items
    summary = {}
    byproducts = {}
    for pc in project_cards:
        if pc['card']:
            s, b = collect_tree_summary(pc['card'])
            for k, v in s.items():
                if k not in summary:
                    summary[k] = v
                else:
                    summary[k]['rate'] += v['rate']
            for k, v in b.items():
                if k not in byproducts:
                    byproducts[k] = v
                else:
                    byproducts[k] += v
    # Mark unused byproducts
    for bp_name, bp_rate in byproducts.items():
        if bp_name not in summary:
            summary[bp_name] = {'name': bp_name, 'rate': bp_rate, 'type': 'byproduct'}
        else:
            if summary[bp_name]['rate'] < bp_rate:
                summary[bp_name]['type'] = 'byproduct'
                summary[bp_name]['rate'] = bp_rate - summary[bp_name]['rate']
    buildings, total_power = collect_buildings_and_power(project_cards)
    project_name = get_project_name()
    return render_template('index.html', items=items, project_items=project_cards, summary=summary, recipes=recipes, get_item_name=get_item_name, get_machine_name=get_machine_name, buildings=buildings, total_power=total_power, project_name=project_name)

@app.route('/select_recipe/<item_id>', methods=['GET', 'POST'])
def select_recipe(item_id):
    recipes = load_recipes()
    project_items = session.get('project_items', [])
    selected_recipes = session.get('selected_recipes', {})
    # Find the item and its rate
    item = next((it for it in project_items if it['item'] == item_id), None)
    # If not a root project item, try to find the rate from a parent card
    if not item:
        # Try to find a parent that lists this as an ingredient
        parent_rate = 1.0
        for it in project_items:
            card = build_card_tree(it['item'], it['rate'], recipes, selected_recipes)
            def find_rate(card):
                if card['item'] == item_id:
                    return card['rate']
                for ing in card.get('ingredients', []):
                    if 'child_card' in ing and isinstance(ing['child_card'], dict):
                        r = find_rate(ing['child_card'])
                        if r is not None:
                            return r
                return None
            rate = find_rate(card)
            if rate is not None:
                parent_rate = rate
                break
        rate = parent_rate
    else:
        rate = item['rate']
    # Find all recipes that produce the selected item
    candidate_recipes = []
    for recipe_id, recipe in recipes.items():
        for prod in recipe.get('products', []):
            if prod['item'] == item_id:
                candidate_recipes.append((recipe_id, recipe, prod))
    # Add an 'Outsourced' (empty) recipe option for any item with recipes
    candidate_recipes.insert(0, (
        '__outsourced__',
        {
            'name': 'Outsourced',
            'machine': None,
            'power_use': 0,
            'products': [{'item': item_id, 'rate': 0, 'amount': 0}],
            'ingredients': []
        },
        {'item': item_id, 'rate': 0, 'amount': 0}
    ))
    if request.method == 'POST':
        selected_recipe = request.form['recipe_id']
        selected_recipes[item_id] = selected_recipe
        session['selected_recipes'] = selected_recipes
        return redirect(url_for('index'))
    return render_template('select_recipe.html', item=item_id, rate=rate, candidate_recipes=candidate_recipes, get_recipe_name=get_recipe_name, get_item_name=get_item_name, get_machine_name=get_machine_name, recipes=recipes)

def collect_tree_summary(card, summary=None, byproducts=None):
    if summary is None:
        summary = {}
    if byproducts is None:
        byproducts = {}
    # Add this item
    if card['item'] not in summary:
        summary[card['item']] = {
            'name': card['name'],
            'rate': card['rate'],
            'type': 'item',
            'recipe_id': card.get('recipe_id'),
            'outsource': card.get('outsource', False)
        }
    else:
        summary[card['item']]['rate'] += card['rate']
    # Track byproducts
    for bp in card.get('byproducts', []):
        if bp['name'] not in byproducts:
            byproducts[bp['name']] = 0
        byproducts[bp['name']] += bp['rate']
    # Recurse for ingredients
    for ing in card.get('ingredients', []):
        if ing.get('resource', False):
            if ing['item'] not in summary:
                summary[ing['item']] = {
                    'name': ing['name'],
                    'rate': ing['rate'],
                    'type': 'resource',
                }
            else:
                summary[ing['item']]['rate'] += ing['rate']
        elif 'child_card' in ing and isinstance(ing['child_card'], dict):
            collect_tree_summary(ing['child_card'], summary, byproducts)
    return summary, byproducts

@app.route('/show_card')
def show_card():
    recipes = load_recipes()
    item = session.get('target_item')
    rate = session.get('target_rate')
    selected_recipes = session.get('selected_recipes', {})
    selected_recipes[item] = session.get('selected_recipe')
    session['selected_recipes'] = selected_recipes
    # First pass: collect all byproducts
    byproduct_pool = collect_byproducts(item, rate, recipes, selected_recipes)
    # Second pass: build tree using the full pool
    card_tree = build_card_tree(item, rate, recipes, selected_recipes, byproduct_pool=byproduct_pool)
    # Collect summary for left-side recap
    summary, byproducts = collect_tree_summary(card_tree)
    # Mark unused byproducts
    for bp_name, bp_rate in byproducts.items():
        if bp_name not in summary:
            summary[bp_name] = {'name': bp_name, 'rate': bp_rate, 'type': 'byproduct'}
        else:
            # If byproduct is not fully used, mark as byproduct
            if summary[bp_name]['rate'] < bp_rate:
                summary[bp_name]['type'] = 'byproduct'
                summary[bp_name]['rate'] = bp_rate - summary[bp_name]['rate']
    return render_template('card.html', card=card_tree, summary=summary)

@app.route('/set_rate/<item_id>', methods=['POST'])
def set_rate(item_id):
    try:
        new_rate = float(request.form['new_rate'])
        # Update the rate for the correct item in the project
        project_items = session.get('project_items', [])
        for it in project_items:
            if it['item'] == item_id:
                it['rate'] = new_rate
        session['project_items'] = project_items
    except Exception:
        flash('Invalid rate value.')
    return redirect(url_for('index'))

def get_project_name():
    return session.get('project_name', 'satisfactory_project')

@app.route('/set_project_name', methods=['POST'])
def set_project_name():
    name = request.form.get('project_name', '').strip()
    if name:
        session['project_name'] = name
    return ('', 204)

@app.route('/new_project', methods=['POST'])
def new_project():
    # Clear all project/session data
    session['project_items'] = []
    session['selected_recipes'] = {}
    session['project_name'] = 'satisfactory_project'
    flash('Started a new project. All previous items were removed.')
    return jsonify({'success': True})

@app.route('/save_project', methods=['GET'])
def save_project():
    project = {
        'project_name': get_project_name(),
        'project_items': session.get('project_items', []),
        'selected_recipes': session.get('selected_recipes', {})
    }
    json_bytes = json.dumps(project, indent=2).encode('utf-8')
    filename = f"{get_project_name()}.json"
    return send_file(
        io.BytesIO(json_bytes),
        mimetype='application/json',
        as_attachment=True,
        download_name=filename
    )

@app.route('/open_project', methods=['POST'])
def open_project():
    if 'project_file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('index'))
    file = request.files['project_file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('index'))
    try:
        data = json.load(file)
        # Validate and restore project state
        session['project_name'] = data.get('project_name', 'Untitled Project')
        session['project_items'] = data.get('project_items', [])
        session['selected_recipes'] = data.get('selected_recipes', {})
        flash('Project loaded successfully!', 'success')
    except Exception as e:
        flash(f'Failed to load project: {e}', 'danger')
    return redirect(url_for('index'))

def collect_buildings_and_power(project_cards):
    buildings = {}
    total_power = 0.0
    for pc in project_cards:
        def walk(card):
            nonlocal total_power
            if card.get('machines') and card.get('machine_id'):
                machine_id = card['machine_id']
                machine_name = card.get('machine_name', machine_id)
                machines = math.ceil(card['machines'])
                power = card.get('power', 0.0)
                total_power += power
                if machine_id not in buildings:
                    buildings[machine_id] = {'name': machine_name, 'machines': 0, 'power': 0.0}
                buildings[machine_id]['machines'] += machines
                buildings[machine_id]['power'] += power
            for ing in card.get('ingredients', []):
                if 'child_card' in ing and isinstance(ing['child_card'], dict):
                    walk(ing['child_card'])
        if pc['card']:
            walk(pc['card'])
    return buildings, total_power

@app.route('/remove_item/<item_id>', methods=['POST'])
def remove_item(item_id):
    project_items = session.get('project_items', [])
    # Remove the item with the given id
    project_items = [it for it in project_items if it['item'] != item_id]
    session['project_items'] = project_items
    # Also remove from selected_recipes if present
    selected_recipes = session.get('selected_recipes', {})
    if item_id in selected_recipes:
        del selected_recipes[item_id]
        session['selected_recipes'] = selected_recipes
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)

