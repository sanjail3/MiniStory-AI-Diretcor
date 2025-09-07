from typing import List, Optional, Dict, Any
from utils.llm import get_llm_model
from pydantic import BaseModel, Field
import json
import os
from models.pydantic_model import AllScenesInfo, SceneInfo
from dotenv import load_dotenv
from location_generation.location_generator import LocationGenerator

load_dotenv()

llm_client = get_llm_model("gpt-4o-mini",api_key=os.getenv("OPENAI_API_KEY"))


class ScriptFormatter:
    def __init__(self):
        self.llm = llm_client
        
    def create_all_scenes_system_prompt(self) -> str:
        
        return """You are a professional script analyzer. Your task is to convert raw script scenes into structured scene-level information for ALL scenes in ONE response.

        IMPORTANT STRUCTURE:
        1. Generate scene information with character IDs only (no full character details in scenes)
        2. At the END, provide complete character profiles separately

        REQUIRED FORMAT:
        ```json
        {
        "scenes": [
            {
            "Scene_ID": "SC_01",
            "Title": "Scene Title",
            "Location": "EXT. LOCATION - TIME",
            "Narration": true,
            "Scene_Tone": "emotional_tone",
            "Set_Info": {
                "Environment": "description",
                "Time": "Day/Night",
                "Lighting": "lighting_type",
                "Background_SFX": ["sfx1", "sfx2"]
            },
            "Scene_Characters": [
                {
                "character_id": "char_01",
                "character_name":"name_of_the_character",
                "emotion": "emotional_state_in_this_scene",
                "outfit": "basic_outfit_description",
                "detailed_outfit": {
                    "outfit_description": "detailed_description_of_complete_outfit",
                    "outfit_type": "casual/formal/uniform/sports/etc",
                    "clothing_items": ["specific", "clothing", "items"],
                    "colors": ["primary", "colors"],
                    "accessories": ["accessories", "worn"],
                    "outfit_context": "why_this_outfit_fits_the_scene_situation"
                },
                "scene_description": "how_they_behave_in_this_specific_scene"
                }
            ],
            "Plot": {
                "summary": "Detailed scene summary explaining what happens, character emotions, and visual elements",
                "theme": "main_theme"
            },
            "Transition": {
                "Transition_To": "SC_02",
                "type": "hard_cut"
            },
            "Given_Script": "original_script_text for the scene"
            }
        ],
        "characters": [
            {
            "name": "Character Full Name",
            "id": "char_01",
            "age": 25,
            "role": "main/supporting/minor",
            "first_appearance_scene": "SC_01",
            "voice_information": "voice_identifier_description",
            "gender": "male/female",
            "overall_description": "complete_character_description_personality_background"
            }
        ],
        "locations": [
            {
            "location_id": "LOC_01",
            "name": "Location Name",
            "location_type": "EXT./INT.",
            "environment": "environment_description",
            "time_of_day": "Day/Night/Dawn/Dusk",
            "lighting": "lighting_description",
            "atmosphere": "atmospheric_conditions",
            "background_sfx": ["sfx1", "sfx2"],
            "set_details": "detailed_set_description",
            "mood": "mood_tone"
            }
        ]
        }
        ```

        CHARACTER ASSIGNMENT RULES:
        1. Character IDs: char_01, char_02, char_03, etc. (consistent across all scenes)
        2. Same character = Same ID across all scenes
        3. In scenes: Only reference character_id + scene-specific info
        4. In characters section: Complete profile for each character

        OUTFIT CONSISTENCY RULES:
        1. Consider the story timeline and scene sequence
        2. Characters should wear appropriate outfits for their role and the situation
        3. Maintain outfit continuity unless there's a logical reason for change
        4. Include detailed outfit descriptions with specific clothing items
        5. Consider the character's personality, role, and the scene context
        6. Specify outfit type (casual, formal, uniform, sports, etc.)
        7. Include colors and accessories for visual consistency

        SCENE GUIDELINES:
        - Scene_ID: SC_01, SC_02, SC_03, etc.
        - Scene_Characters: Only IDs and scene-specific details (emotion, outfit, behavior)
        - Plot summary should be detailed and include character emotions
        - Environment should describe the physical setting clearly

        CHARACTER PROFILES (at the end):
        - Include complete information: name, age, role, gender, voice_information
        - overall_description: Personality, background, general traits
        - first_appearance_scene: Which scene they debut in

        LOCATION EXTRACTION RULES:
        1. Extract ALL unique locations from the script scenes
        2. Location IDs: LOC_01, LOC_02, LOC_03, etc.
        3. Include complete location information: name, type, environment, lighting, etc.
        4. Map each scene to its corresponding location
        5. Include atmospheric details and background SFX for each location

        Analyze ALL provided script scenes and generate complete scene-level information with separate character profiles and location information."""

    

    def generate_all_scenes_info(self, raw_scripts, model: str = "gpt-4o-mini") -> AllScenesInfo:
    
        try:
            print(f"Generating scene information")

            messages=[
                    {"role": "system", "content": self.create_all_scenes_system_prompt()},
                    {"role": "user", "content": f"Analyze these script scenes and generate complete scene-level information for ALL scenes. Ensure character consistency across scenes:\n\n{raw_scripts}"}
                ]
            self.llm=self.llm.with_structured_output(AllScenesInfo)
            all_scenes_info = self.llm.invoke(messages)
            

            
    
          
   
            for i, scene_info in enumerate(all_scenes_info.scenes):
                if not scene_info.given_script and i < len(raw_scripts):
                    scene_info.given_script = raw_scripts[i]
            
            print(f"Generated scene info for {len(all_scenes_info.scenes)} scenes")
            
            
            
            print(f"Character Summary:")
            for character in all_scenes_info.characters:
                print(f"  - {character.name} ({character.id}) age: {character.age} role: {character.role} voice_information: {character.voice_information} gender: {character.gender} overall_description: {character.overall_description}")
            
            return all_scenes_info
            
        except Exception as e:
            raise Exception(f"Error generating all scenes info: {str(e)}")

    def save_scenes_info(self, scenes_info: List[SceneInfo], output_file: str, output_dir="story_generation_pipeline"):
        scenes_dict = {"scenes": [scene.model_dump(by_alias=True) for scene in scenes_info]}
        file_path=os.path.join(output_dir, output_file)

        os.makedirs(output_dir, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(scenes_dict, f, indent=2, ensure_ascii=False)
        
        print(f"Scene information saved to {output_file}")

    def generate_locations(self, all_scenes_info: AllScenesInfo, output_file: str = "locations.json") -> List[Dict[str, Any]]:
        """Generate location information and images from scenes"""
        try:
            print("🏢 Generating locations from scenes...")
            
            # Initialize location generator
            location_generator = LocationGenerator()
            
            # Convert scenes to the format expected by location generator
            scenes_data = []
            for scene in all_scenes_info.scenes:
                scene_dict = {
                    "scene_info": {
                        "Scene_ID": scene.scene_id,
                        "Location": scene.location,
                        "Set_Info": {
                            "environment": scene.set_info.environment if scene.set_info else "",
                            "time": scene.set_info.time if scene.set_info else "",
                            "lighting": scene.set_info.lighting if scene.set_info else "",
                            "background_sfx": scene.set_info.background_sfx if scene.set_info else []
                        },
                        "Scene_Tone": scene.scene_tone
                    }
                }
                scenes_data.append(scene_dict)
            
            # Extract locations from scenes
            locations = location_generator.extract_locations_from_scenes(scenes_data)
            
            print(f"Found {len(locations)} unique locations:")
            for loc in locations:
                print(f"  - {loc['name']} ({loc['location_id']})")
            
            # Generate location images
            print("\n🎨 Generating location images...")
            locations_with_images = location_generator.generate_location_images(locations)
            
            # Save locations
            print("\n💾 Saving locations...")
            location_generator.save_locations(locations_with_images, output_file)
            
            print("✅ Location generation completed!")
            return [location.model_dump(by_alias=True) for location in locations_with_images]
            
        except Exception as e:
            print(f"❌ Error generating locations: {e}")
            return []

        