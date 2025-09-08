from typing import List, Optional, Dict, Any
from utils.llm import get_llm_model
from pydantic import BaseModel, Field
import json
import os
from models.pydantic_model import AllScenesInfo, SceneInfo, Shot, Scene, FormattedScript
from dotenv import load_dotenv
from location_generation.location_generator import LocationGenerator
from outfit_consistency.outfit_tracker import OutfitConsistencyTracker

load_dotenv()

llm_client = get_llm_model("gemini-2.0-flash",api_key=os.getenv("GEMINI_API_KEY"))


class ShotFormatter:
    def __init__(self):
        self.llm = llm_client

    def create_shot_system_prompt(self) -> str:
       
        return """You are a professional cinematographer and script breakdown artist. Your task is to convert ONE scene into detailed shot-by-shot breakdowns.

        REQUIRED SHOT FORMAT:
        - Shot_ID: Use format SC{scene_num}_SH{shot_num} (e.g., SC1_SH1, SC1_SH2)
        - Description: Visual description of what's happening in the shot
        - Focus_Characters: List of character names in focus (use exact names from scene)
        - Shot_Characters: Detailed character information for this shot including outfit details
        - Camera: Camera movement/angle (e.g., "aerial_slow_dolly", "handheld", "close-up", "tracking_shot")
        - Emotion: Emotional tone of the shot
        - Narration: Voice-over narration text (if any)
        - Background_SFX: List of background sound effects
        - Lighting: Lighting description
        - Shot_Tone: Tone of the shot (e.g., "tense", "haunting", "investigative")
        - Set_Details: Physical details visible in the shot
        - Dialog: Array of character dialog in format [{"character_name": "dialog_text"}]

        CINEMATOGRAPHY GUIDELINES:
        - Use 3-6 shots per scene typically
        - Vary camera angles: wide shots, close-ups, mid shots, tracking shots
        - Include appropriate lighting descriptions
        - Add realistic background SFX that match the environment
        - Ensure smooth narrative flow between shots
        - Each shot should advance the story or reveal character emotion
        - Use shot composition to enhance the emotional tone

        OUTFIT CONSISTENCY GUIDELINES:
        - For each character in focus, provide detailed outfit information in Shot_Characters
        - Maintain outfit continuity within the scene unless there's a logical reason for change
        - Reference the character's outfit from the scene information provided
        - Include specific clothing items, colors, and accessories
        - Note any changes from previous shots/scenes in outfit_continuity field
        - Consider the character's actions and how their outfit might be affected
        - Ensure outfit descriptions are detailed enough for visual consistency

        IMPORTANT: Return ONLY valid JSON in this exact format:
        {
          "shots": [
            {
              "Shot_ID": "SC1_SH1",
              "Description": "Wide shot of the crime scene with police, body under sheet",
              "Focus_Characters": [],
              "Shot_Characters": [],
              "Camera": "aerial_slow_dolly",
              "Emotion": "none",
              "Narration": "Hum dekhte hain ek crime scene. Ek aadmi ki laash safed kapde se dhaki hai.",
              "Background_SFX": ["wind", "sirens"],
              "Lighting": "harsh daylight",
              "Shot_Tone": "tense",
              "Set_Details": "Body covered under sheet, police moving around, yellow tape",
              "Dialog": []
            },
            {
              "Shot_ID": "SC1_SH2",
              "Description": "Close-up of Sanju sitting handcuffed",
              "Focus_Characters": ["Sanju"],
              "Shot_Characters": [
                {
                  "character_id": "char_01",
                  "character_name": "Sanju",
                  "outfit_description": "Casual clothes from earlier - jeans, t-shirt, now with handcuffs",
                  "outfit_continuity": "same as previous scene, but now handcuffed",
                  "character_action": "sitting quietly, looking at the crime scene with a vacant expression"
                }
              ],
              "Camera": "close-up",
              "Emotion": "somber",
              "Narration": "",
              "Background_SFX": ["distant police radio"],
              "Lighting": "natural light casting shadows",
              "Shot_Tone": "tense",
              "Set_Details": "Handcuffs visible, dirt on ground",
              "Dialog": []
            }
          ]
        }

        Break down the provided scene into cinematic shots that effectively tell the story. Return ONLY the JSON response."""



    def generate_shots_for_scene(self,scene_info: SceneInfo, model: str = "gpt-4o-mini") -> List[Shot]:
        
            try:
    
                # Build detailed character outfit information
                character_details = []
                for char in scene_info.scene_characters:
                    char_info = f"Character ID: {char.character_id}, Name: {char.character_name}"
                    char_info += f", Emotion: {char.emotion or 'N/A'}"
                    char_info += f", Basic Outfit: {char.outfit or 'N/A'}"
                    
                    if char.detailed_outfit:
                        char_info += f", Detailed Outfit: {char.detailed_outfit.outfit_description}"
                        char_info += f", Outfit Type: {char.detailed_outfit.outfit_type}"
                        char_info += f", Clothing Items: {', '.join(char.detailed_outfit.clothing_items)}"
                        char_info += f", Colors: {', '.join(char.detailed_outfit.colors)}"
                        char_info += f", Accessories: {', '.join(char.detailed_outfit.accessories)}"
                        char_info += f", Context: {char.detailed_outfit.outfit_context}"
                    
                    char_info += f", Scene Behavior: {char.scene_description or 'N/A'}"
                    character_details.append(char_info)

                scene_context = f"""
                Scene Information:
                - Scene ID: {scene_info.scene_id}
                - Title: {scene_info.title}
                - Location: {scene_info.location}
                - Scene Tone: {scene_info.scene_tone}
                - Plot Summary: {scene_info.plot.summary if scene_info.plot else 'N/A'}
                - Original Script: {scene_info.given_script}

                Character Details with Outfits:
                {chr(10).join(character_details)}

                Environment Details:
                - Environment: {scene_info.set_info.environment if scene_info.set_info else 'N/A'}
                - Time: {scene_info.set_info.time if scene_info.set_info else 'N/A'}
                - Lighting: {scene_info.set_info.lighting if scene_info.set_info else 'N/A'}
                - Background SFX: {scene_info.set_info.background_sfx if scene_info.set_info else 'N/A'}

                IMPORTANT: For each shot where characters are in focus, include detailed Shot_Characters information with outfit descriptions based on the character details above. Maintain outfit continuity throughout the scene.
                """
                
                print(f" Generating shots for {scene_info.scene_id}: {scene_info.title}")
                
                # Use LangChain's invoke method with JSON response format
                messages = [
                    {"role": "system", "content": self.create_shot_system_prompt()},
                    {"role": "user", "content": f"Generate detailed shots for this scene:\n\n{scene_context}"}
                ]
                
                response = self.llm.invoke(messages)
                
                # Parse the response as JSON
                try:
                    json_response = json.loads(response.content)
                except:
                    # If direct parsing fails, try to extract JSON from the response
                    content = response.content
                    if "```json" in content:
                        json_start = content.find("```json") + 7
                        json_end = content.find("```", json_start)
                        json_str = content[json_start:json_end].strip()
                        json_response = json.loads(json_str)
                    else:
                        # Fallback: try to parse the entire content as JSON
                        json_response = json.loads(content)
                shots = [Shot(**shot_data) for shot_data in json_response.get("shots", [])]
                
                print(f"Generated {len(shots)} shots for {scene_info.scene_id}")
                return shots
                
            except Exception as e:
                raise Exception(f"Error generating shots for scene {scene_info.scene_id}: {str(e)}")

    def generate_shots_for_all_scenes(self,all_scenes_info: AllScenesInfo, model: str = "gpt-4o-mini") -> FormattedScript:
            
            print(f"\n🎥 Step 1: Generating shots for each scene...")
            scenes = []
            
            for scene_info in all_scenes_info.scenes:
                print(f"\n  Processing {scene_info.scene_id}...")
                shots = self.generate_shots_for_scene(scene_info, model)
                
                scene = Scene(scene_info=scene_info, shots=shots)
                scenes.append(scene)
                
                print(f"Completed {scene_info.scene_id} with {len(shots)} shots")
            
            # Create formatted script
            formatted_script = FormattedScript(scenes=scenes, characters=all_scenes_info.characters, locations=all_scenes_info.locations)
            
            # Apply outfit consistency tracking
            print(f"\n🎭 Step 2: Applying outfit consistency...")
            outfit_tracker = OutfitConsistencyTracker()
            formatted_script = outfit_tracker.process_formatted_script(formatted_script)
            
            # Save outfit tracking data
            outfit_summary = outfit_tracker.get_outfit_summary()
            print(f"📊 Outfit Summary: {outfit_summary['character_count']} characters tracked")
            
            print(f"Script formatting complete! Generated {len(scenes)} scenes with consistent characters and outfits.")
            return formatted_script

    def save_formatted_script(self, formatted_script: FormattedScript, output_file: str):
            script_dict = formatted_script.model_dump(by_alias=True)
            file_path=os.path.join("story_generation_pipeline", output_file)
            os.makedirs("story_generation_pipeline", exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(script_dict, f, indent=2, ensure_ascii=False)
            print(f"Formatted script saved to {output_file}")

    def attach_location_references_to_shots(self, formatted_script: FormattedScript, locations: List[Dict[str, Any]]) -> FormattedScript:
        """Attach location reference images to shots"""
        try:
            print("🏢 Attaching location references to shots...")
            
            # Create location lookup by scene ID
            location_by_scene = {}
            for location in locations:
                # Map location to scene ID (e.g., LOC_01 -> SC_01)
                scene_id = location.get('location_id', '').replace('LOC_', 'SC_')
                location_by_scene[scene_id] = location
            
            # Process each scene and its shots
            for scene in formatted_script.scenes:
                scene_id = scene.scene_info.scene_id
                location = location_by_scene.get(scene_id)
                
                if location:
                    # Add location reference to each shot
                    for shot in scene.shots:
                        shot.location_reference = {
                            "location_id": location.get('location_id', ''),
                            "location_name": location.get('name', ''),
                            "location_image_path": location.get('image_path', ''),
                            "environment": location.get('environment', ''),
                            "lighting": location.get('lighting', ''),
                            "atmosphere": location.get('atmosphere', ''),
                            "background_sfx": location.get('background_sfx', [])
                        }
                    
                    print(f"✅ Attached location references to {len(scene.shots)} shots in {scene_id}")
                else:
                    print(f"⚠️ No location found for scene {scene_id}")
            
            print("✅ Location references attached to all shots!")
            return formatted_script
            
        except Exception as e:
            print(f"❌ Error attaching location references: {e}")
            return formatted_script