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

def attach_location_reference_images_to_scenes(formatted_script_data: Dict[str, Any], locations_data: Dict[str, Any]) -> Dict[str, Any]:
    """Attach location reference images to scenes based on scene location"""
    
    # Extract locations and create lookup
    locations = locations_data.get('locations', [])
    location_lookup = {}
    
    for loc in locations:
        location_id = loc.get('location_id', '')
        if location_id:
            location_lookup[location_id] = {
                'location_id': location_id,
                'name': loc.get('name', ''),
                'image_path': loc.get('image_path', ''),
                'environment': loc.get('environment', ''),
                'lighting': loc.get('lighting', ''),
                'atmosphere': loc.get('atmosphere', ''),
                'background_sfx': loc.get('background_sfx', [])
            }
    
    # Process each scene
    scenes = formatted_script_data.get('scenes', [])
    
    for scene in scenes:
        scene_info = scene.get('scene_info', {})
        scene_location = scene_info.get('Location', '')
        
        # Try to match location by name or ID
        matched_location = None
        
        # First try to match by location name in the scene location string
        for loc_id, loc_data in location_lookup.items():
            if loc_data['name'].lower() in scene_location.lower():
                matched_location = loc_data
                break
        
        # If no match found, try to match by location ID pattern
        if not matched_location:
            # Extract potential location ID from scene location
            # e.g., "EXT. CRIME SCENE - DAY" -> try to match with "Crime Scene"
            location_name_parts = scene_location.replace('EXT.', '').replace('INT.', '').split('-')[0].strip()
            for loc_id, loc_data in location_lookup.items():
                if any(part.lower() in loc_data['name'].lower() for part in location_name_parts.split()):
                    matched_location = loc_data
                    break
        
        # Add location reference to scene info
        if matched_location:
            location_ref_data = {
                "location_id": matched_location['location_id'],
                "location_name": matched_location['name'],
                "location_image_path": matched_location['image_path'],
                "environment": matched_location['environment'],
                "lighting": matched_location['lighting'],
                "atmosphere": matched_location['atmosphere'],
                "background_sfx": matched_location['background_sfx']
            }
            
            # Add to scene info
            scene_info['location_reference'] = location_ref_data
            
            # Also add to each shot in this scene
            for shot in scene.get('shots', []):
                shot['location_reference'] = location_ref_data.copy()
            
            print(f"✅ Attached location reference for scene: {scene_info.get('Scene_ID', 'Unknown')} -> {matched_location['name']}")
        else:
            print(f"⚠️ No location match found for scene: {scene_info.get('Scene_ID', 'Unknown')} - {scene_location}")
    
    return formatted_script_data

def main():
    """Main function to attach location reference images"""
    # Load data files
    formatted_script_data = load_json_file("story_generation_pipeline/sessions/Hindi_thriller_20250907_010736_ccdbdb9d/script_planning/formatted_script.json")
    locations_data = load_json_file("story_generation_pipeline/sessions/Hindi_thriller_20250907_010736_ccdbdb9d/location_generation/locations.json")
    
    if not formatted_script_data or not locations_data:
        print("❌ Failed to load required data files")
        return
    
    # Attach location reference images
    updated_script = attach_location_reference_images_to_scenes(formatted_script_data, locations_data)
    
    # Save updated script
    output_path = "story_generation_pipeline/sessions/Hindi_thriller_20250907_010736_ccdbdb9d/script_planning/formatted_script_with_location_refs.json"
    if save_json_file(output_path, updated_script):
        print(f"✅ Updated script saved to: {output_path}")
    else:
        print("❌ Failed to save updated script")

if __name__ == "__main__":
    main()

