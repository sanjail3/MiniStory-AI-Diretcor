
#!/usr/bin/env python3
"""
Scene Creator - Orchestrates the complete scene creation workflow
"""

import os
import json
from typing import Dict, Any, List, Optional
from .scene_image_generator import SceneImageGenerator
from .scene_video_generator import SceneVideoGenerator
from scene_description_generation.scene_describer import SceneDescriber

class SceneCreator:
    """Manages the complete scene creation workflow including description and image generation"""
    
    def __init__(self, session_path: str):
        self.session_path = session_path
        self.scene_describer = SceneDescriber()
        self.image_generator = SceneImageGenerator(
            output_dir=os.path.join(session_path, "scene_creation", "images")
        )
        self.video_generator = SceneVideoGenerator(session_path)
        
        # Load existing generation results if they exist
        self.image_generator.load_existing_generation_results()
        
    def generate_scene_descriptions(self, formatted_script: Dict[str, Any], 
                                  character_data: Dict[str, Any], 
                                  location_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate scene descriptions for all shots"""
        
        print("🎭 Starting scene description generation...")
        
        # Step 1: Attach reference images to shots first
        print("📸 Attaching reference images to shots...")
        script_with_references = self._attach_all_reference_images(
            formatted_script, character_data, location_data
        )
        
        # Step 2: Generate descriptions with references
        script_with_descriptions = self.scene_describer.generate_all_scene_descriptions(
            script_with_references, character_data, location_data
        )
        
        # Save the updated script with descriptions
        output_path = os.path.join(self.session_path, "scene_creation", "script_with_descriptions.json")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(script_with_descriptions, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Scene descriptions saved to: {output_path}")
        
        return script_with_descriptions
    
    def generate_scene_images(self, script_with_descriptions: Dict[str, Any], 
                            start_from_scene: int = 0) -> Dict[str, Any]:
        """Generate scene images for all shots"""
        
        print("🎨 Starting scene image generation...")
        
        # Generate images
        results = self.image_generator.generate_all_scene_images(
            script_with_descriptions, start_from_scene
        )
        
        return results
    
    def regenerate_single_shot_image(self, shot_info: Dict, character_refs: List[Dict], 
                                   location_ref: Optional[Dict], scene_id: str = "unknown") -> Optional[str]:
        """Regenerate image for a single shot"""
        return self.image_generator.regenerate_single_shot(shot_info, character_refs, location_ref, scene_id)
    
    def generate_scene_videos(self, scene_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate videos for all shots in a scene"""
        return self.video_generator.generate_scene_videos(scene_info)
    
    def regenerate_single_shot_video(self, shot_info: Dict, scene_image_path: str, 
                                   scene_description: Dict, scene_id: str = "unknown") -> Optional[str]:
        """Regenerate video for a single shot"""
        return self.video_generator.regenerate_single_shot_video(shot_info, scene_image_path, scene_description, scene_id)
    
    def list_generated_videos(self) -> List[Dict[str, Any]]:
        """List all generated videos"""
        return self.video_generator.list_generated_videos()
    
    def load_existing_video_results(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load existing video generation results grouped by scene"""
        return self.video_generator.load_existing_generation_results()
    
    def get_scene_creation_status(self) -> Dict[str, Any]:
        """Get current scene creation status"""
        return {
            "descriptions_generated": self._check_descriptions_exist(),
            "images_generated": len(self.image_generator.list_generated_images()),
            "current_progress": self.image_generator.get_generation_status()
        }
    
    def _check_descriptions_exist(self) -> bool:
        """Check if scene descriptions have been generated"""
        desc_path = os.path.join(self.session_path, "scene_creation", "script_with_descriptions.json")
        return os.path.exists(desc_path)
    
    def load_script_with_descriptions(self) -> Optional[Dict[str, Any]]:
        """Load script with descriptions if it exists"""
        desc_path = os.path.join(self.session_path, "scene_creation", "script_with_descriptions.json")
        if os.path.exists(desc_path):
            with open(desc_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    
    def _attach_all_reference_images(self, formatted_script: Dict[str, Any], 
                                   character_data: Dict[str, Any], 
                                   location_data: Dict[str, Any]) -> Dict[str, Any]:
        """Attach character and location reference images to shots"""
        
        # Import the attachment functions
        from scene_description_generation.attach_all_reference_images import attach_all_reference_images
        
        # Attach all reference images
        script_with_references = attach_all_reference_images(
            formatted_script, character_data, location_data
        )
        
        print("✅ Reference images attached to all shots!")
        return script_with_references