import json
import os
from typing import Dict, Any


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load JSON file and return data"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return {}

def save_json_file(file_path: str, data: Dict[str, Any]) -> bool:
    """Save data to JSON file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving {file_path}: {e}")
        return False



def attach_reference_images_to_shots(formatted_script_data: Dict[str, Any], characters_data: Dict[str, Any]) -> Dict[str, Any]:
    """Attach reference images to shots based on focus characters"""
    
    # Extract characters and create lookup
    characters = characters_data.get('characters', [])
    char_img_by_id = {}
    
    for char in characters:
        char_id = char.get('id', '')
        if char_id:
            char_img_by_id[char_id] = {
                'id': char_id,
                'name': char.get('name', ''),
                'image_path': char.get('image_path', ''),
                'overall_description': char.get('overall_description', ''),
                'gender': char.get('gender', 'unknown')
            }
    
    # Process each scene and shot
    scenes = formatted_script_data.get('scenes', [])
    
    for scene in scenes:
        shots = scene.get('shots', [])
        
        for shot in shots:
            # Initialize focus character images list
            shot['focus_character_images'] = []
            
            # Get focus characters from the shot
            focus_characters = shot.get('Focus_Characters', [])
            
            for char_ref in focus_characters:
                # Try to find character by ID first, then by name
                char_found = None
                
                # First try by ID
                if char_ref in char_img_by_id:
                    char_found = char_img_by_id[char_ref]
                else:
                    # Try by name (exact match and partial match)
                    for char in characters:
                        char_name = char.get('name', '').lower()
                        char_ref_lower = char_ref.lower()
                        
                        # Exact match
                        if char_name == char_ref_lower:
                            char_found = char
                            break
                        # Partial match (first name)
                        elif char_ref_lower in char_name or char_name.startswith(char_ref_lower):
                            char_found = char
                            break
                
                if char_found:
                    shot['focus_character_images'].append({
                        "character_id": char_found.get('id', ''),
                        "character_name": char_found.get('name', ''),
                        "image_path": char_found.get('image_path', ''),
                        "overall_description": char_found.get('overall_description', ''),
                        "gender": char_found.get('gender', 'unknown')
                    })
                else:
                    print(f"Warning: Character '{char_ref}' not found in character list")
    
    return formatted_script_data


formatted_script_data = load_json_file("/Users/sanjail/Akaike/Internal_project/story_generator/story_generation_pipeline/sessions/HIndi Thriller_20250906_215416_ba18db6b/script_planning/formatted_script.json")
characters_data = load_json_file("/Users/sanjail/Akaike/Internal_project/story_generator/story_generation_pipeline/sessions/HIndi Thriller_20250906_215416_ba18db6b/character_generation/characters.json")
    

updated_script = attach_reference_images_to_shots(formatted_script_data, characters_data)
