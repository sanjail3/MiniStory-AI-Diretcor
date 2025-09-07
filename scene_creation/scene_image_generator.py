#!/usr/bin/env python3
"""
Scene Image Generator for creating cinematic scene images with character and location references
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple
from io import BytesIO
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class SceneImageGenerator:
    """Generates scene images for shots using character and location reference images"""
    
    def __init__(self, output_dir: str = "scene_creation/images"):
        self.output_dir = output_dir
        self.model = genai.GenerativeModel('gemini-2.5-flash-image-preview')
        
        # Configure API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        genai.configure(api_key=api_key)
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Track generation progress
        self.generation_progress = {
            "current_scene": None,
            "completed_scenes": [],
            "current_shot": None,
            "generated_images": {},
            "failed_generations": []
        }
    
    def load_reference_images(self, character_refs: List[Dict], location_ref: Optional[Dict]) -> Tuple[List[Dict], Optional[Dict]]:
        """Load and prepare reference images for generation"""
        prepared_char_refs = []
        
        for char_ref in character_refs:
            char_data = {
                "character_id": char_ref.get("character_id", ""),
                "character_name": char_ref.get("character_name", ""),
                "image_path": char_ref.get("image_path", ""),
                "loaded_image": None
            }
            
            # Load character image as PIL Image
            if char_data["image_path"] and os.path.exists(char_data["image_path"]):
                try:
                    char_data["loaded_image"] = Image.open(char_data["image_path"])
                    print(f"✅ Loaded character image: {char_data['character_name']}")
                except Exception as e:
                    print(f"Warning: Could not load character image {char_data['image_path']}: {e}")
            
            prepared_char_refs.append(char_data)
        
        # Prepare location reference
        prepared_location_ref = None
        if location_ref:
            prepared_location_ref = {
                "location_id": location_ref.get("location_id", ""),
                "location_name": location_ref.get("location_name", ""),
                "image_path": location_ref.get("location_image_path", ""),
                "environment": location_ref.get("environment", ""),
                "lighting": location_ref.get("lighting", ""),
                "atmosphere": location_ref.get("atmosphere", ""),
                "loaded_image": None,
                "location_image_detailed_description": location_ref.get("location_image_prompt", "")
            }
            
            # Load location image as PIL Image
            if prepared_location_ref["image_path"] and os.path.exists(prepared_location_ref["image_path"]):
                try:
                    prepared_location_ref["loaded_image"] = Image.open(prepared_location_ref["image_path"])
                    print(f"✅ Loaded location image: {prepared_location_ref['location_name']}")
                except Exception as e:
                    print(f"Warning: Could not load location image {prepared_location_ref['image_path']}: {e}")
        
        return prepared_char_refs, prepared_location_ref
    
    def create_enhanced_prompt(self, shot_info: Dict, character_refs: List[Dict], location_ref: Optional[Dict]) -> str:
        """Create enhanced prompt with reference image context"""
        
        # Base prompt from scene description
        base_prompt = shot_info.get('scene_description', {}).get('scene_image_prompt', '')
        
        # Add character reference context
        char_context = []
        for char_ref in character_refs:
            if char_ref.get('loaded_image'):
                char_context.append(f"Character: {char_ref['character_name']} (reference image provided)")
            else:
                char_context.append(f"Character: {char_ref['character_name']} (no reference image)")
        
        # Add detailed location reference context
        location_context = ""
        if location_ref and location_ref.get('loaded_image'):
            location_context = f"""Location: {location_ref['location_name']} (reference image provided)
            - Location Image Detailed Description: {location_ref.get('location_image_detailed_description', 'Unknown')}
            - Environment: {location_ref.get('environment', 'Unknown')}
            - Lighting: {location_ref.get('lighting', 'Natural')}
            - Atmosphere: {location_ref.get('atmosphere', 'Neutral')}"""
        elif location_ref:
            location_context = f"""Location: {location_ref['location_name']} (no reference image)
            - Location Image Detailed Description: {location_ref.get('location_image_detailed_description', 'Unknown')}
            - Environment: {location_ref.get('environment', 'Unknown')}
            - Lighting: {location_ref.get('lighting', 'Natural')}
            - Atmosphere: {location_ref.get('atmosphere', 'Neutral')}"""
        
       
        enhanced_prompt = f"""
        {base_prompt}
        
        REFERENCE CONTEXT:
        Characters:
        {chr(10).join(f'- {ctx}' for ctx in char_context)}
        
        Location Details:
        - {location_context}
        
        GENERATION REQUIREMENTS:
        - Generate a cinematic scene image that matches the reference images provided
        - Ensure character consistency and location consistency with the reference images and maintain outfit details
        - Always created detailed scene image with the location image detailed description like which character is in which position and which object is in which position.
        - Maintain the specified lighting and atmospheric conditions
        - Use the provided character and location reference images to maintain visual consistency
        - Ensure the scene feels authentically Indian without stereotypes

        EXAMPLE
        """
        
        return enhanced_prompt.strip()
    
    def generate_scene_image(self, shot_info: Dict, character_refs: List[Dict], location_ref: Optional[Dict], scene_id: str = "unknown") -> Optional[str]:
        """Generate a single scene image for a shot"""
        
        shot_id = shot_info.get('Shot_ID', 'unknown')
        
        print(f"🎨 Generating scene image for {shot_id}...")
        
        try:
            # Load reference images
            prepared_char_refs, prepared_location_ref = self.load_reference_images(character_refs, location_ref)
            
            # Create enhanced prompt
            prompt = self.create_enhanced_prompt(shot_info, prepared_char_refs, prepared_location_ref)
            
            # Prepare content for Gemini - using PIL Images directly
            contents = [prompt]
            
            # Add character reference images (use main image, fallback to sheet)
            for char_ref in prepared_char_refs:
                if char_ref.get('loaded_image'):
                    contents.append(char_ref['loaded_image'])
                    print(f"📸 Added character reference: {char_ref['character_name']}")
                elif char_ref.get('loaded_sheet'):
                    contents.append(char_ref['loaded_sheet'])
                    print(f"📸 Added character sheet: {char_ref['character_name']}")
            
            # Add location reference image (use main image, fallback to sheet)
            if prepared_location_ref:
                if prepared_location_ref.get('loaded_image'):
                    contents.append(prepared_location_ref['loaded_image'])
                    print(f"🏢 Added location reference: {prepared_location_ref['location_name']}")
                elif prepared_location_ref.get('loaded_sheet'):
                    contents.append(prepared_location_ref['loaded_sheet'])
                    print(f"🏢 Added location sheet: {prepared_location_ref['location_name']}")
            
            print(f"🎨 Generating scene image with {len(contents)} content items (prompt + {len(contents)-1} reference images)")
            
            # Generate image
            response = self.model.generate_content(contents)
            
            # Save generated image
            filename = f"{scene_id}_{shot_id}_scene.png"
            filepath = os.path.join(self.output_dir, filename)
            
            image_saved = False
            if hasattr(response, 'parts') and response.parts:
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_data = part.inline_data.data
                        image = Image.open(BytesIO(image_data))
                        image.save(filepath)
                        image_saved = True
                        print(f"✅ Saved scene image: {filepath}")
                        break
                    elif hasattr(part, 'text') and part.text:
                        print(f"Gemini response: {part.text[:100]}...")
            
            if not image_saved:
                print(f"❌ No image data generated for {shot_id}")
                return None
            
            # Update progress tracking
            self.generation_progress["generated_images"][shot_id] = {
                "filepath": filepath,
                "scene_id": scene_id,
                "shot_id": shot_id,
                "status": "success"
            }
            
            return filepath
            
        except Exception as e:
            print(f"❌ Error generating scene image for {shot_id}: {e}")
            self.generation_progress["failed_generations"].append({
                "shot_id": shot_id,
                "scene_id": scene_id,
                "error": str(e)
            })
            return None
    
    def generate_scene_images(self, scene_info: Dict) -> Dict[str, Any]:
        """Generate images for all shots in a scene"""
        
        scene_id = scene_info.get('scene_info', {}).get('Scene_ID', 'unknown')
        shots = scene_info.get('shots', [])
        
        print(f"\n🎬 Generating images for scene: {scene_id}")
        print(f"📊 Total shots to process: {len(shots)}")
        
        # Update progress
        self.generation_progress["current_scene"] = scene_id
        
        scene_results = {
            "scene_id": scene_id,
            "total_shots": len(shots),
            "generated_shots": [],
            "failed_shots": [],
            "images": {}
        }
        
        # Get location reference for this scene
        location_ref = scene_info.get('scene_info', {}).get('location_reference')
        
        for i, shot in enumerate(shots):
            shot_id = shot.get('Shot_ID', f'shot_{i}')
            self.generation_progress["current_shot"] = shot_id
            
            print(f"\n📸 Processing shot {i+1}/{len(shots)}: {shot_id}")
            
            # Get character references for this shot
            character_refs = shot.get('focus_character_images', [])
            
            # Generate scene image
            image_path = self.generate_scene_image(shot, character_refs, location_ref, scene_id)
            
            if image_path:
                scene_results["generated_shots"].append(shot_id)
                scene_results["images"][shot_id] = {
                    "image_path": image_path,
                    "shot_info": shot,
                    "character_refs": character_refs,
                    "location_ref": location_ref
                }
                print(f"✅ Successfully generated image for {shot_id}")
            else:
                scene_results["failed_shots"].append(shot_id)
                print(f"❌ Failed to generate image for {shot_id}")
        
        # Update progress
        self.generation_progress["completed_scenes"].append(scene_id)
        
        print(f"\n📈 Scene {scene_id} completed:")
        print(f"  ✅ Generated: {len(scene_results['generated_shots'])}")
        print(f"  ❌ Failed: {len(scene_results['failed_shots'])}")
        
        return scene_results
    
    def generate_all_scene_images(self, formatted_script: Dict[str, Any], start_from_scene: int = 0) -> Dict[str, Any]:
        """Generate images for all scenes in the formatted script"""
        
        scenes = formatted_script.get('scenes', [])
        total_scenes = len(scenes)
        
        print(f"🎬 Starting scene image generation for {total_scenes} scenes")
        print(f"🚀 Starting from scene {start_from_scene}")
        
        all_results = {
            "total_scenes": total_scenes,
            "processed_scenes": 0,
            "scene_results": {},
            "overall_stats": {
                "total_shots": 0,
                "generated_shots": 0,
                "failed_shots": 0
            }
        }
        
        for i, scene in enumerate(scenes[start_from_scene:], start_from_scene):
            scene_id = scene.get('scene_info', {}).get('Scene_ID', f'scene_{i}')
            
            print(f"\n{'='*60}")
            print(f"🎬 Processing Scene {i+1}/{total_scenes}: {scene_id}")
            print(f"{'='*60}")
            
            # Generate images for this scene
            scene_result = self.generate_scene_images(scene)
            all_results["scene_results"][scene_id] = scene_result
            all_results["processed_scenes"] += 1
            
            # Update overall stats
            all_results["overall_stats"]["total_shots"] += scene_result["total_shots"]
            all_results["overall_stats"]["generated_shots"] += len(scene_result["generated_shots"])
            all_results["overall_stats"]["failed_shots"] += len(scene_result["failed_shots"])
            
            # Wait for confirmation before next scene
            print(f"\n⏳ Scene {scene_id} completed. Waiting for confirmation to proceed to next scene...")
            print("Press Enter to continue to next scene, or 'q' to quit...")
            
            user_input = input().strip().lower()
            if user_input == 'q':
                print("🛑 Generation stopped by user")
                break
        
        # Save results
        self.save_generation_results(all_results)
        
        return all_results
    
    def regenerate_single_shot(self, shot_info: Dict, character_refs: List[Dict], location_ref: Optional[Dict], scene_id: str = "unknown") -> Optional[str]:
        """Regenerate image for a single shot"""
        
        shot_id = shot_info.get('Shot_ID', 'unknown')
        print(f"🔄 Regenerating image for shot: {shot_id}")
        
        # Generate new image
        new_image_path = self.generate_scene_image(shot_info, character_refs, location_ref, scene_id)
        
        if new_image_path:
            # Update progress tracking
            self.generation_progress["generated_images"][shot_id] = {
                "filepath": new_image_path,
                "shot_id": shot_id,
                "status": "regenerated"
            }
            print(f"✅ Successfully regenerated image for {shot_id}")
        else:
            print(f"❌ Failed to regenerate image for {shot_id}")
        
        return new_image_path
    
    def save_generation_results(self, results: Dict[str, Any], filename: str = "scene_generation_results.json"):
        """Save generation results to file"""
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Add progress information to results
        results["generation_progress"] = self.generation_progress
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Generation results saved to: {filepath}")
    
    def get_generation_status(self) -> Dict[str, Any]:
        """Get current generation status"""
        return {
            "current_scene": self.generation_progress["current_scene"],
            "current_shot": self.generation_progress["current_shot"],
            "completed_scenes": len(self.generation_progress["completed_scenes"]),
            "generated_images": len(self.generation_progress["generated_images"]),
            "failed_generations": len(self.generation_progress["failed_generations"])
        }
    
    def list_generated_images(self) -> List[Dict[str, str]]:
        """List all generated images"""
        images = []
        for shot_id, info in self.generation_progress["generated_images"].items():
            images.append({
                "shot_id": shot_id,
                "scene_id": info.get("scene_id", "unknown"),
                "filepath": info["filepath"],
                "status": info["status"]
            })
        return images
    
    def load_existing_generation_results(self, filename: str = "scene_generation_results.json") -> bool:
        """Load existing generation results from file"""
        filepath = os.path.join(self.output_dir, filename)
        
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    results = json.load(f)
                
                # Restore generation progress if it exists
                if "generation_progress" in results:
                    self.generation_progress = results["generation_progress"]
                    print(f"✅ Loaded existing generation progress: {len(self.generation_progress.get('generated_images', {}))} images")
                    return True
                    
            except Exception as e:
                print(f"⚠️ Warning: Could not load existing results: {e}")
        
        return False
