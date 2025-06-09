import json

def load_json():
    """
    Load a JSON file and return its content as a dictionary.

    :param file_path: Path to the JSON file.
    :return: Dictionary containing the JSON data.
    """
    with open("raw_data\data.json", 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

