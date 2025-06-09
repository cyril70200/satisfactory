import json
from collections import defaultdict
import math

# Global constants
MAX_RECURSION_DEPTH = 5  # Default max recursion depth

def load_data():
    """Load the Satisfactory data from the JSON file."""
    with open("raw_data/data.json", 'r', encoding='utf-8') as file:
        return json.load(file)

def get_recipes_for_item(data, item_id):
    """Find all recipes that produce the given item."""
    recipes = []

    # First, validate that the item actually exists
    item_name = get_item_name(data, item_id)
    if item_name == item_id and item_id not in data.get('items', {}) and item_id not in data.get('resources', {}):
        print(f"Warning: Item '{item_id}' does not exist in the data!")
        return []

    # Find recipes that produce this item
    for recipe_id, recipe_data in data['recipes'].items():
        if not recipe_data.get('products'):
            continue

        for product in recipe_data.get('products', []):
            if not isinstance(product, dict):
                continue

            product_item = product.get('item')
            if product_item == item_id:
                recipes.append(recipe_id)
                print(f"  Found recipe: {recipe_data.get('name', recipe_id)}")
                break

    if not recipes:
        print(f"No recipes found that produce {item_name} ({item_id})")
    else:
        print(f"Found {len(recipes)} recipes that produce {item_name} ({item_id})")

    return recipes

def is_resource(data, item_id):
    """Check if an item is a resource (has no recipe)."""
    # Check if item exists at all
    if item_id not in data.get('items', {}) and item_id not in data.get('resources', {}):
        print(f"Warning: Item {item_id} does not exist in data!")
        return True  # Treat as resource to avoid further recursion

    # If it's explicitly defined as a resource
    if item_id in data.get('resources', {}):
        return True

    # If it's not defined as a resource, but there are no recipes that produce it
    # then we'll consider it a terminal resource as well
    recipes = get_recipes_for_item(data, item_id)
    return len(recipes) == 0

def get_item_name(data, item_id):
    """Get the human-readable name of an item."""
    if item_id in data.get('items', {}):
        return data['items'][item_id].get('name', item_id)
    elif item_id in data.get('resources', {}):
        return data['resources'][item_id].get('name', item_id)
    return item_id

def calculate_production_rate(recipe_data):
    """Calculate items produced per minute based on recipe time."""
    time_seconds = recipe_data.get('time', 1.0)
    items_per_cycle = {}

    for product in recipe_data.get('products', []):
        item_id = product.get('item')
        amount = product.get('amount', 0)
        if item_id:
            items_per_cycle[item_id] = amount

    # Calculate items per minute
    items_per_minute = {}
    for item_id, amount in items_per_cycle.items():
        items_per_minute[item_id] = (amount * 60) / time_seconds

    return items_per_minute

def find_all_crafting_paths(data, target_item_id, desired_rate=None, path=None, visited=None, depth=0):
    """
    Find all possible ways to craft an item recursively.

    Args:
        data: The loaded game data
        target_item_id: The ID of the item to craft
        desired_rate: Desired items per minute (None for recipe default)
        path: Current crafting path (for recursion)
        visited: Set of visited items (to prevent cycles)
        depth: Current recursion depth for debugging

    Returns:
        List of all possible crafting paths
    """
    # Check if the item exists at all
    if target_item_id not in data.get('items', {}) and target_item_id not in data.get('resources', {}):
        print(f"Warning: Item {target_item_id} does not exist in data, skipping.")
        return []

    # Set recursion depth limit to prevent infinite loops
    global MAX_RECURSION_DEPTH
    if depth > MAX_RECURSION_DEPTH:
        print(f"WARNING: Max recursion depth ({MAX_RECURSION_DEPTH}) reached for {target_item_id}. Stopping this branch.")
        return []

    if path is None:
        path = []
    if visited is None:
        visited = set()

    # Debugging
    indent = '  ' * depth
    print(f"{indent}Exploring {get_item_name(data, target_item_id)} (depth: {depth}, path: {path})")

    # Prevent cycles in the recursion
    if target_item_id in visited:
        print(f"{indent}Cycle detected! {target_item_id} already visited in path: {visited}")
        return []

    # Add the current item to the visited set
    visited = visited.copy()
    visited.add(target_item_id)

    # If it's a resource, we've reached a base case
    if is_resource(data, target_item_id):
        resource_name = get_item_name(data, target_item_id)
        print(f"{indent}Found resource: {resource_name}")
        return [{
            'item_id': target_item_id,
            'item_name': resource_name,
            'is_resource': True,
            'rate': desired_rate,
            'children': []
        }]

    # Find all recipes that produce this item
    recipe_ids = get_recipes_for_item(data, target_item_id)
    if not recipe_ids:
        # No recipe found, treat as a terminal node
        item_name = get_item_name(data, target_item_id)
        print(f"{indent}No recipes found for {item_name}, treating as terminal node")
        return [{
            'item_id': target_item_id,
            'item_name': item_name,
            'is_resource': False,
            'rate': desired_rate,
            'children': []
        }]

    all_paths = []

    # Process each recipe
    for recipe_id in recipe_ids:
        recipe_data = data['recipes'][recipe_id]
        recipe_name = recipe_data.get('name', recipe_id)
        print(f"{indent}Processing recipe: {recipe_name}")

        # Calculate production rates
        production_rates = calculate_production_rate(recipe_data)

        # Get the production rate for our target item
        base_rate = 0
        target_found = False
        for product in recipe_data.get('products', []):
            if product.get('item') == target_item_id:
                target_found = True
                amount = product.get('amount', 0)
                time_seconds = recipe_data.get('time', 1.0)
                base_rate = (amount * 60) / time_seconds
                print(f"{indent}  Base production rate: {base_rate}/min")
                break

        # Skip this recipe if it doesn't actually produce our target item
        if not target_found:
            print(f"{indent}  WARNING: Recipe {recipe_name} doesn't actually produce {target_item_id}, skipping")
            continue

        # Calculate the multiplier needed to achieve the desired rate
        multiplier = 1.0
        if desired_rate is not None and base_rate > 0:
            multiplier = desired_rate / base_rate
            print(f"{indent}  Need {multiplier:.2f}x to achieve {desired_rate}/min")

        # Process each ingredient recursively
        ingredient_paths = []
        for ingredient in recipe_data.get('ingredients', []):
            ingredient_id = ingredient.get('item')
            if not ingredient_id:
                print(f"{indent}  WARNING: Invalid ingredient (no item ID) in recipe {recipe_name}")
                continue

            ingredient_amount = ingredient.get('amount', 0)
            ingredient_name = get_item_name(data, ingredient_id)
            print(f"{indent}  Ingredient: {ingredient_name} x{ingredient_amount}")

            # Calculate the required rate for this ingredient
            ingredient_rate = (ingredient_amount * 60 / recipe_data.get('time', 1.0)) * multiplier
            print(f"{indent}  Need {ingredient_rate:.2f}/min of {ingredient_name}")

            # Recursively find paths for this ingredient
            sub_paths = find_all_crafting_paths(
                data,
                ingredient_id,
                ingredient_rate,
                path + [recipe_id],
                visited,
                depth + 1
            )

            if sub_paths:
                ingredient_paths.append({
                    'ingredient_id': ingredient_id,
                    'paths': sub_paths
                })
            else:
                print(f"{indent}  WARNING: No valid paths found for ingredient {ingredient_name}")

        # Add this recipe as a possible path
        all_paths.append({
            'item_id': target_item_id,
            'item_name': get_item_name(data, target_item_id),
            'recipe_id': recipe_id,
            'recipe_name': recipe_name,
            'machine': recipe_data.get('machine', 'Unknown'),
            'machine_count': math.ceil(multiplier) if multiplier > 0 else 1,
            'power_usage': recipe_data.get('power_use', 0) * math.ceil(multiplier) if multiplier > 0 else recipe_data.get('power_use', 0),
            'base_rate': base_rate,
            'desired_rate': desired_rate,
            'is_resource': False,
            'ingredients': ingredient_paths
        })

    return all_paths

def format_crafting_tree(tree, indent=0, rate_precision=2):
    """Format a crafting tree for display."""
    result = []

    for path in tree:
        # Handle resource nodes
        if path.get('is_resource', False):
            rate_str = f"{path.get('rate', 0):.{rate_precision}f}/min" if path.get('rate') else "as needed"
            result.append(f"{' ' * indent}• {path['item_name']} (Resource) - {rate_str}")
            continue

        # Handle recipe nodes
        if 'recipe_name' in path:
            desired_rate = path.get('desired_rate')
            rate_str = f"{desired_rate:.{rate_precision}f}/min" if desired_rate else "as needed"
            machine_count = path.get('machine_count', 1)
            power_usage = path.get('power_usage', 0)

            result.append(f"{' ' * indent}• {path['item_name']} - {rate_str}")
            result.append(f"{' ' * (indent+2)}Recipe: {path['recipe_name']}")
            result.append(f"{' ' * (indent+2)}Machine: {path['machine']} x{machine_count} ({power_usage:.1f} MW total)")

            # Process ingredients
            if path.get('ingredients'):
                result.append(f"{' ' * (indent+2)}Ingredients:")
                for ingredient in path['ingredients']:
                    for ingredient_path in ingredient['paths']:
                        formatted = format_crafting_tree([ingredient_path], indent+4, rate_precision)
                        result.extend(formatted)
        else:
            # Simple item node
            rate_str = f"{path.get('rate', 0):.{rate_precision}f}/min" if path.get('rate') else "as needed"
            result.append(f"{' ' * indent}• {path['item_name']} - {rate_str}")

    return result

def analyze_recipe(item_id, desired_rate=None, max_depth=None):
    """Analyze all possible ways to craft an item at the desired rate."""
    data = load_data()

    # Check if the item exists
    if item_id not in data.get('items', {}) and item_id not in data.get('resources', {}):
        print(f"Error: Item ID '{item_id}' not found in data. Please check the item ID.")
        return

    item_name = get_item_name(data, item_id)
    print(f"Analyzing crafting options for: {item_name} ({item_id})")
    if desired_rate:
        print(f"Desired production rate: {desired_rate}/min")

    # Override max_depth in the find_all_crafting_paths function
    global MAX_RECURSION_DEPTH
    if max_depth is not None:
        old_depth = MAX_RECURSION_DEPTH
        MAX_RECURSION_DEPTH = max_depth
        print(f"Setting max recursion depth to {MAX_RECURSION_DEPTH}")

    # Find all crafting paths
    print(f"Finding all crafting paths for {item_name}...")
    crafting_paths = find_all_crafting_paths(data, item_id, desired_rate)

    # Restore original max depth
    if max_depth is not None:
        MAX_RECURSION_DEPTH = old_depth

    if not crafting_paths:
        print(f"No recipes found for {item_name}.")
        return

    # Format and display results
    print("\nAll possible crafting solutions:")
    print("=" * 80)

    for i, path in enumerate(crafting_paths, 1):
        print(f"\nSolution {i}:")
        print("-" * 40)
        formatted_tree = format_crafting_tree([path])
        print("\n".join(formatted_tree))
        print()

def list_all_items():
    """List all items available in the game data."""
    data = load_data()

    print("Available Items:")
    print("=" * 80)

    # Group by items and resources
    items = []
    for item_id, item_data in data.get('items', {}).items():
        items.append((item_id, item_data.get('name', item_id), 'Item'))

    for item_id, item_data in data.get('resources', {}).items():
        items.append((item_id, item_data.get('name', item_id), 'Resource'))

    # Sort by name
    items.sort(key=lambda x: x[1])

    # Print the list
    for item_id, name, item_type in items:
        print(f"{name} ({item_type}): {item_id}")

def main():
    print("Satisfactory Recipe Analyzer")
    print("=" * 80)

    while True:
        print("\nOptions:")
        print("1. Analyze a specific item")
        print("2. Quick analysis (limited depth)")
        print("3. List all available items")
        print("4. Exit")

        choice = input("\nEnter your choice (1-4): ")

        if choice == '1':
            default_item_id = "Desc_SteelPipe_C"
            item_id = input(f"Enter the item ID (e.g., {default_item_id}): ").strip()
            if not item_id:
                item_id = default_item_id
            rate_input = input("Enter desired production rate per minute (or press Enter for default, e.g., 30): ")
            if not rate_input.strip():
                rate_input = "30"

            rate = None
            if rate_input.strip():
                try:
                    rate = float(rate_input)
                except ValueError:
                    print("Invalid rate. Using default.")

            analyze_recipe(item_id, rate)

        elif choice == '2':
            default_item_id = "Desc_SteelPipe_C"
            item_id = input(f"Enter the item ID (e.g., {default_item_id}): ").strip()
            if not item_id:
                item_id = default_item_id
            rate_input = input("Enter desired production rate per minute (or press Enter for default, e.g., 30): ")
            if not rate_input.strip():
                rate_input = "30"
            depth_input = input("Enter max recursion depth (or press Enter for default, e.g., 2): ")
            if not depth_input.strip():
                depth_input = "2"

            rate = None
            if rate_input.strip():
                try:
                    rate = float(rate_input)
                except ValueError:
                    print("Invalid rate. Using default.")

            depth = None
            if depth_input.strip():
                try:
                    depth = int(depth_input)
                except ValueError:
                    print("Invalid depth. Using default.")
                    depth = 2

            analyze_recipe(item_id, rate, depth)

        elif choice == '3':
            list_all_items()

        elif choice == '4':
            print("Exiting...")
            break

        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
