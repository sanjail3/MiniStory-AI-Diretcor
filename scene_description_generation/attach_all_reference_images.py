#!/usr/bin/env python3
"""
Comprehensive script to attach both character and location reference images to formatted script
"""

import json
import os
import sys
from typing import Dict, Any

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .attach_character_reference_images import attach_reference_images_to_shots
from .attach_location_reference_images import attach_location_reference_images_to_scenes

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

def attach_all_reference_images(formatted_script_data: Dict[str, Any], 
                              characters_data: Dict[str, Any], 
                              locations_data: Dict[str, Any]) -> Dict[str, Any]:
    """Attach both character and location reference images to formatted script"""
    
    print("🎬 Attaching all reference images to formatted script...")
    
    # Step 1: Attach character reference images to shots
    print("\n👥 Step 1: Attaching character reference images...")
    script_with_characters = attach_reference_images_to_shots(formatted_script_data, characters_data)
    
    # Step 2: Attach location reference images to scenes
    print("\n🏢 Step 2: Attaching location reference images...")
    script_with_all_refs = attach_location_reference_images_to_scenes(script_with_characters, locations_data)
    
    print("\n✅ All reference images attached successfully!")
    return script_with_all_refs

def get_session_summary(script_data: Dict[str, Any]) -> Dict[str, Any]:
    """Get summary of attached reference images"""
    summary = {
        "total_scenes": len(script_data.get('scenes', [])),
        "total_shots": 0,
        "scenes_with_location_refs": 0,
        "shots_with_character_refs": 0,
        "scenes_summary": []
    }
    
    for scene in script_data.get('scenes', []):
        scene_id = scene.get('scene_info', {}).get('Scene_ID', 'Unknown')
        shots = scene.get('shots', [])
        
        # Check if scene has location reference
        has_location_ref = 'location_reference' in scene.get('scene_info', {})
        if has_location_ref:
            summary["scenes_with_location_refs"] += 1
        
        # Count shots with character references
        shots_with_char_refs = 0
        for shot in shots:
            summary["total_shots"] += 1
            if shot.get('focus_character_images'):
                shots_with_char_refs += 1
        
        summary["shots_with_character_refs"] += shots_with_char_refs
        
        summary["scenes_summary"].append({
            "scene_id": scene_id,
            "total_shots": len(shots),
            "has_location_ref": has_location_ref,
            "shots_with_character_refs": shots_with_char_refs
        })
    
    return summary

def main():
    """Main function to attach all reference images"""
    
    # Define session path
    session_path = "story_generation_pipeline/sessions/Hindi_thriller_20250907_010736_ccdbdb9d"
    
    # Load data files
    print("📂 Loading data files...")
    formatted_script_data = load_json_file(f"{session_path}/script_planning/formatted_script.json")
    characters_data = load_json_file(f"{session_path}/character_generation/characters.json")
    locations_data = load_json_file(f"{session_path}/location_generation/locations.json")
    
    if not formatted_script_data:
        print("❌ Failed to load formatted script data")
        return
    
    if not characters_data:
        print("❌ Failed to load character data")
        return
    
    if not locations_data:
        print("❌ Failed to load location data")
        return
    
    print("✅ All data files loaded successfully")
    
    # Attach all reference images
    updated_script = attach_all_reference_images(formatted_script_data, characters_data, locations_data)
    
    # Get summary
    summary = get_session_summary(updated_script)
    print(f"\n📊 Summary:")
    print(f"  - Total scenes: {summary['total_scenes']}")
    print(f"  - Total shots: {summary['total_shots']}")
    print(f"  - Scenes with location refs: {summary['scenes_with_location_refs']}")
    print(f"  - Shots with character refs: {summary['shots_with_character_refs']}")
    
    # Save updated script
    output_path = f"{session_path}/script_planning/formatted_script_with_refs.json"
    if save_json_file(output_path, updated_script):
        print(f"\n✅ Updated script with all reference images saved to: {output_path}")
    else:
        print("\n❌ Failed to save updated script")
    
    # Also save as the main formatted_script.json (backup first)
    backup_path = f"{session_path}/script_planning/formatted_script_backup.json"
    if save_json_file(backup_path, formatted_script_data):
        print(f"📦 Original script backed up to: {backup_path}")
    
    if save_json_file(f"{session_path}/script_planning/formatted_script.json", updated_script):
        print(f"✅ Main formatted script updated with reference images")

if __name__ == "__main__":
    main()
