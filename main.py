from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from models.item import Item
from models.project import Project
import json
import os
import uuid

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # For session management

PROJECTS_DIR = os.path.join(os.path.dirname(__file__), 'projects')
os.makedirs(PROJECTS_DIR, exist_ok=True)

def get_project_path(project_id):
    return os.path.join(PROJECTS_DIR, f'project_{project_id}.json')

def save_project_to_disk(project: Project, project_id: str):
    with open(get_project_path(project_id), 'w', encoding='utf-8') as f:
        json.dump(project.to_dict(), f, indent=2)

def load_project_from_disk(project_id: str) -> Project:
    with open(get_project_path(project_id), 'r', encoding='utf-8') as f:
        data = json.load(f)
        return Project.from_dict(data)

# In-memory project cache for unsaved changes (keyed by project_id)
project_cache = {}

@app.route('/project/<project_id>', methods=['GET'])
def view_project(project_id):
    # Prefer in-memory cache if present
    if project_id in project_cache:
        project = project_cache[project_id]
    else:
        project = load_project_from_disk(project_id)
        project.mark_clean()  # Mark as clean when loaded from disk
        project_cache[project_id] = project
    # List all projects for modal
    projects = []
    for fname in os.listdir(PROJECTS_DIR):
        if fname.startswith('project_') and fname.endswith('.json'):
            pid = fname[len('project_'):-len('.json')]
            try:
                p = load_project_from_disk(pid)
                projects.append({'id': pid, 'name': p.name})
            except Exception:
                projects.append({'id': pid, 'name': f"(corrupt or missing) {pid}"})
    items = Item.all_items()
    # Load resource item_ids from data.json
    data_path = os.path.join(os.path.dirname(__file__), 'raw_data', 'data.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    resource_ids = set(data.get('resources', {}).keys())
    resource_names = {item_id: res['name'] for item_id, res in data.get('resources', {}).items()}
    # Build a mapping from item_id to name for display
    item_names = items
    # Attach resource_names to project for report use
    project.resource_names = resource_names
    # Convert each item to a card dict for rendering
    project_items = [item.to_card_dict(item_names, None, resource_names, include_extra_products=True) for item in project.items]
    # --- Production report ---
    report = project.get_production_report(item_names=item_names, resource_ids=resource_ids)
    return render_template(
        'index.html',
        project=project,
        project_items=project_items,
        project_name=project.name,
        project_id=project_id,
        total_power=report['total_power'],
        machines=report['machines'],
        item_report=report['items'],
        projects=projects,
        items=items,
        item_names=item_names,
        resource_ids=resource_ids,
        resource_names=resource_names
    )

@app.route('/project/<project_id>/rename', methods=['POST'])
def rename_project(project_id):
    project = project_cache.get(project_id) or load_project_from_disk(project_id)
    new_name = request.form.get('new_name')
    if new_name:
        project.rename(new_name)
        project.mark_dirty()
        project_cache[project_id] = project
    return redirect(url_for('view_project', project_id=project_id))

@app.route('/new_project', methods=['POST'])
def new_project():
    project_id = str(uuid.uuid4())
    # Use the provided project name or a default
    new_project_name = request.form.get('new_project_name') or f"project-{project_id}"
    project = Project(name=new_project_name)
    project.mark_dirty()
    project_cache[project_id] = project
    # Always redirect to the new project page
    return redirect(url_for('view_project', project_id=project_id))

@app.route('/save_project', methods=['GET'])
def save_project():
    project_id = request.args.get('project_id')
    if not project_id or project_id not in project_cache:
        flash('No unsaved project to save.', 'error')
        return redirect(url_for('index'))
    project = project_cache[project_id]
    save_project_to_disk(project, project_id)
    project.mark_clean()
    project_cache[project_id] = project
    flash('Project saved.', 'success')
    return redirect(url_for('view_project', project_id=project_id))

@app.route('/project/<project_id>/add_item', methods=['POST'])
def add_item(project_id):
    project = Project.load(project_id, project_cache, load_project_from_disk)
    item_id = request.form.get('item')
    rate = float(request.form.get('rate', 0))
    # Create a new Item instance with the selected item_id and rate
    new_item = Item(item_id=item_id, rate=rate)
    project.add_item(new_item)
    project.save(project_id, project_cache, save_project_to_disk)
    return redirect(url_for('view_project', project_id=project_id))

@app.route('/project/<project_id>/item/<item_uuid>/edit', methods=['POST'])
def edit_item(project_id, item_uuid):
    """Edit an item's rate or recipe selection."""
    project = load_project_from_disk(project_id)
    item = project.find_item_by_uuid(item_uuid)
    if not item:
        flash('Item not found', 'error')
        return redirect(url_for('view_project', project_id=project_id))
    # Update rate
    if 'rate' in request.form:
        item.rate = float(request.form['rate'])
    # Update recipe
    if 'recipe_id' in request.form:
        item.recipe_id = request.form['recipe_id']
    save_project_to_disk(project, project_id)
    return redirect(url_for('view_project', project_id=project_id))

@app.route('/project/<project_id>/item/<item_uuid>/remove', methods=['POST'])
def remove_item(project_id, item_uuid):
    """Remove an item from the project."""
    project = Project.load(project_id, project_cache, load_project_from_disk)
    project.remove_item(item_uuid)
    project.save(project_id, project_cache, save_project_to_disk)
    return redirect(url_for('view_project', project_id=project_id))

@app.route('/project/<project_id>/item/<item_uuid>/change_rate', methods=['POST'])
def change_item_rate(project_id, item_uuid):
    project = Project.load(project_id, project_cache, load_project_from_disk)
    new_rate = float(request.form.get('rate', 0))
    project.change_rate(item_uuid, new_rate)
    project.save(project_id, project_cache, save_project_to_disk)
    return redirect(url_for('view_project', project_id=project_id))

@app.route('/project/<project_id>/item/<item_uuid>/add_extra_product', methods=['POST'])
def add_extra_product(project_id, item_uuid):
    project = project_cache.get(project_id) or load_project_from_disk(project_id)
    item = project.find_item_by_uuid(item_uuid)
    extra_item_id = request.form.get('extra_item_id')
    if item and extra_item_id:
        item.add_extra_product(extra_item_id)
        project.mark_dirty()
        save_project_to_disk(project, project_id)  # Ensure it is saved to disk
        project_cache[project_id] = project
    return redirect(url_for('view_project', project_id=project_id))

@app.route('/project/<project_id>/item/<item_uuid>/update_extra_product', methods=['POST'])
def update_extra_product(project_id, item_uuid):
    project = project_cache.get(project_id) or load_project_from_disk(project_id)
    item = project.find_item_by_uuid(item_uuid)
    extra_uuid = request.form.get('extra_uuid')
    new_rate = float(request.form.get('rate', 0))
    if item and extra_uuid:
        item.update_extra_product(extra_uuid, new_rate)
        project.mark_dirty()
        project_cache[project_id] = project
    return redirect(url_for('view_project', project_id=project_id))

@app.route('/project/<project_id>/item/<item_uuid>/remove_extra_product', methods=['POST'])
def remove_extra_product(project_id, item_uuid):
    project = project_cache.get(project_id) or load_project_from_disk(project_id)
    item = project.find_item_by_uuid(item_uuid)
    extra_uuid = request.form.get('extra_uuid')
    if item and extra_uuid:
        item.remove_extra_product(extra_uuid)
        project.mark_dirty()
        project_cache[project_id] = project
    return redirect(url_for('view_project', project_id=project_id))

@app.route('/project/<project_id>/item/<item_uuid>/set_extra_rate', methods=['POST'])
def set_extra_rate(project_id, item_uuid):
    project = project_cache.get(project_id) or load_project_from_disk(project_id)
    item = project.find_item_by_uuid(item_uuid)
    try:
        value = float(request.form.get('extra_rate', 0.0))
    except Exception:
        value = 0.0
    if item:
        item.set_extra_rate(value)
        # Recalculate rates for this item and its children
        parent = find_parent(project, item_uuid)
        parent_base_rate = get_base_rate(parent, item) if parent else item.rate
        item.update_rate(parent_base_rate)
        project.mark_dirty()
        save_project_to_disk(project, project_id)
        project_cache[project_id] = project
    return ('', 204)

@app.route('/project/<project_id>/item/<item_uuid>/set_use_extra_rate', methods=['POST'])
def set_use_extra_rate(project_id, item_uuid):
    project = project_cache.get(project_id) or load_project_from_disk(project_id)
    item = project.find_item_by_uuid(item_uuid)
    value = request.form.get('use_extra_rate', 'false').lower() == 'true'
    if item:
        item.set_use_extra_rate(value)
        # Recalculate rates for this item and its children
        parent = find_parent(project, item_uuid)
        parent_base_rate = get_base_rate(parent, item) if parent else item.rate
        item.update_rate(parent_base_rate)
        project.mark_dirty()
        save_project_to_disk(project, project_id)
        project_cache[project_id] = project
    return ('', 204)

@app.route('/', methods=['GET'])
def index():
    """Show the main UI with no project selected. All project management is via the sidebar and modals."""
    # List all projects for modal
    projects = []
    for fname in os.listdir(PROJECTS_DIR):
        if fname.startswith('project_') and fname.endswith('.json'):
            pid = fname[len('project_'):-len('.json')]
            try:
                p = load_project_from_disk(pid)
                projects.append({'id': pid, 'name': p.name})
            except Exception:
                projects.append({'id': pid, 'name': f"(corrupt or missing) {pid}"})
    items = Item.all_items()
    return render_template(
        'index.html',
        project=None,
        project_items=None,
        project_name=None,
        project_id=None,
        total_power=0,
        buildings={},
        summary={},
        projects=projects,
        items=items
    )

@app.route('/list_projects', methods=['GET'])
def list_projects():
    projects = []
    for fname in os.listdir(PROJECTS_DIR):
        if fname.startswith('project_') and fname.endswith('.json'):
            project_id = fname[len('project_'):-len('.json')]
            try:
                project = load_project_from_disk(project_id)
                projects.append({'id': project_id, 'name': project.name})
            except Exception:
                projects.append({'id': project_id, 'name': f"(corrupt or missing) {project_id}"})
    return jsonify(projects)

@app.route('/modal/rename_project')
def modal_rename_project():
    project_id = request.args.get('project_id')
    # No need to pass project_name for prefill, just pass project_id
    return render_template('modal_rename_project.html', project_id=project_id)

@app.route('/modal/open_project')
def modal_open_project():
    # List all projects for modal
    projects = []
    for fname in os.listdir(PROJECTS_DIR):
        if fname.startswith('project_') and fname.endswith('.json'):
            project_id = fname[len('project_'):-len('.json')]
            try:
                project = load_project_from_disk(project_id)
                projects.append({'id': project_id, 'name': project.name})
            except Exception:
                projects.append({'id': project_id, 'name': f"(corrupt or missing) {project_id}"})
    return render_template('modal_open_project.html', projects=projects)

@app.route('/project/<project_id>/add_item_modal', methods=['GET'])
def add_item_modal(project_id):
    items = Item.all_items()
    return render_template('modal_add_item.html', items=items, project_id=project_id)

@app.route('/project/<project_id>/item/<item_uuid>/select_recipe', methods=['GET', 'POST'])
def select_recipe(project_id, item_uuid):
    """
    Show a page to select a recipe for the given item in the project.
    Displays all available recipes, machine, power, inputs, outputs, etc.
    """
    project = Project.load(project_id, project_cache, load_project_from_disk)
    item = project.find_item_by_uuid(item_uuid)
    if not item:
        flash('Item not found', 'error')
        return redirect(url_for('view_project', project_id=project_id))

    # Load recipes data
    with open(os.path.join(os.path.dirname(__file__), 'raw_data', 'enhanced_recipes.json'), 'r', encoding='utf-8') as f:
        recipes = json.load(f)
    # Find all recipes that produce this item
    candidate_recipes = item.get_recipes()

    # Helper functions for template
    def get_item_name(item_id, recipes):
        # Use Item.all_items for names
        return Item.all_items().get(item_id, item_id)
    def get_recipe_name(recipe_id, recipes):
        if recipe_id == '__outsourced__':
            return 'Outsourced'
        return recipes.get(recipe_id, {}).get('name', recipe_id)
    def get_machine_name(machine_id):
        return Item.get_machine_name(machine_id)

    if request.method == 'POST':
        selected_recipe_id = request.form.get('recipe_id')
        if selected_recipe_id == '__outsourced__':
            item.recipe_id = None
            item.outsourced = True
            item.ingredients = []
        else:
            item.recipe_id = selected_recipe_id
            item.outsourced = False
            # Populate ingredients from recipe
            recipe = recipes.get(selected_recipe_id)
            item.ingredients = []
            if recipe:
                for ing in recipe.get('ingredients', []):
                    # Calculate the required rate for the ingredient
                    # Parent rate * (ingredient rate / product rate)
                    # Find the main product for this recipe
                    main_product = None
                    for prod in recipe.get('products', []):
                        if prod['item'] == item.item_id:
                            main_product = prod
                            break
                    if main_product and main_product.get('rate'):
                        factor = item.rate / main_product['rate']
                    else:
                        factor = 1
                    ing_rate = ing.get('rate', ing.get('amount', 1)) * factor
                    # Create new Item for ingredient, default to outsourced
                    new_ing = Item(
                        item_id=ing['item'],
                        rate=ing_rate,
                        recipe_id=None,
                        outsourced=True,
                        ingredients=[]
                    )
                    item.ingredients.append(new_ing)
        project.save(project_id, project_cache, save_project_to_disk)
        return redirect(url_for('view_project', project_id=project_id))

    return render_template(
        'select_recipe.html',
        project_id=project_id,
        item=item.item_id,
        item_name=get_item_name(item.item_id, recipes),
        rate=item.rate,
        candidate_recipes=candidate_recipes,
        recipes=recipes,
        get_item_name=get_item_name,
        get_recipe_name=get_recipe_name,
        get_machine_name=get_machine_name
    )

# Helper to find parent of an item by uuid

def find_parent(project, child_uuid):
    def walk(item):
        for ing in getattr(item, 'ingredients', []):
            if getattr(ing, 'uuid', None) == child_uuid:
                return item
            found = walk(ing)
            if found:
                return found
        return None
    for item in project.items:
        result = walk(item)
        if result:
            return result
    return None

# Helper to get the base rate for a child from its parent (excluding extra_rate)
def get_base_rate(parent, child):
    if not parent or not hasattr(parent, 'ingredients'):
        return child.rate
    # Find the recipe and the ingredient ratio
    import json, os
    recipes_path = os.path.join(os.path.dirname(__file__), 'raw_data/enhanced_recipes.json')
    with open(recipes_path, 'r', encoding='utf-8') as f:
        recipes = json.load(f)
    recipe = recipes.get(parent.recipe_id)
    if not recipe or 'ingredients' not in recipe or 'products' not in recipe:
        return child.rate
    prod_rate = None
    for prod in recipe['products']:
        if prod['item'] == parent.item_id:
            prod_rate = prod.get('rate')
            break
    if not prod_rate:
        return child.rate
    for ing in recipe['ingredients']:
        if ing['item'] == child.item_id:
            return parent.rate * (ing['rate'] / prod_rate)
    return child.rate

if __name__ == "__main__":
    app.run(debug=True)

