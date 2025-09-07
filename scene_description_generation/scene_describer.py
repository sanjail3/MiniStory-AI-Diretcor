from typing import List, Optional, Dict, Any
from utils.llm import get_llm_model
from pydantic import BaseModel, Field
import json
import os
from dotenv import load_dotenv

load_dotenv()

llm_client = get_llm_model("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

class SceneDescriberVideoInfo(BaseModel):
    """Pydantic model for scene video description information"""
    camera_angle: str = Field(..., description="Specific camera angle and lens details")
    scene_description: str = Field(..., description="Detailed visual description of setting and action")
    character_visual_description: str = Field(..., description="Physical appearance and styling of characters present")
    mood_emotion: str = Field(..., description="Emotional tone and psychological atmosphere")
    lighting: str = Field(..., description="Detailed lighting setup and color temperature")
    dialogue: str = Field(default="", description="Exact dialogue if present")
    narration: str = Field(default="", description="Exact narration if present")

class SceneDescriberInfo(BaseModel):
    """Pydantic model for scene description information"""
    scene_image_prompt: str = Field(..., description="Optimized prompt for scene image generation with reference images")
    scene_video_prompt: SceneDescriberVideoInfo = Field(..., description="Optimized prompt for scene video generation")

class SceneDescriber:
    def __init__(self):
        self.llm = llm_client
        
    def create_scene_description_system_prompt(self) -> str:
        """Create comprehensive system prompt for scene description generation"""
        return """
        You are a professional visual director and cinematographer with expertise in creating cinematic prompts for AI image and video generation.

        Your task is to analyze shot information and generate detailed, cinematic prompts optimized for:
        1. Scene Image Generation (using reference images of characters and locations)
        2. Scene Video Generation (using Veo3 with the scene image as reference)

        CRITICAL REQUIREMENTS:

        SCENE IMAGE PROMPT GUIDELINES:
        - Create prompts that work with reference images of characters and locations
        - Use character names with gender markers: "Arjun(male)" and "Priya(female)"
        - Include specific visual elements: [[scene description]][action description][lighting][camera angle]
        - Reference character and location images will be provided during generation
        - Focus on composition, framing, and visual storytelling
        - Include specific details about character positioning, expressions, and interactions
        -Based on location image detailed description and environment details, specify the position of characters and alignment of characters how each character is placed in the location and they are interacting with each other 
         and most of location images will be wide angle or medium angle shot based on that we should align the characters in the location image and also we should mention the alignment of characters in the location image  with object if any.
        - Specify environmental details, props, and atmospheric elements
        - Use cinematic terminology and professional photography language
        - IMPORTANT: Include detailed character outfit descriptions for visual consistency
        - Specify clothing items, colors, and accessories for each character
        - Maintain outfit continuity as specified in the shot information
        - Format: "Cinematic scene: [description] with [character_name(male/female)] and [character_name(male/female)] in [location][position of characters][ALIGNMENT of characters] setting, [camera_angle], [lighting], [mood]"

        SCENE VIDEO PROMPT GUIDELINES:
        - Provide extremely detailed descriptions for video generation
        - Include camera movements, transitions, and dynamic elements
        - Specify timing, pacing, and rhythm of the scene
        - Describe character movements, gestures, and micro-expressions
        - Include environmental dynamics (wind, lighting changes, etc.)
        - Specify audio cues and sound design elements
        - Detail the emotional arc and narrative progression
        - Format: "Cinematic video sequence: [detailed_description] with [camera_movements], [character_actions], [environmental_dynamics]"

        TECHNICAL SPECIFICATIONS:
        - Camera angles should be specific (e.g., "low angle close-up", "dutch tilt wide shot")
        - Lighting should include color temperature, direction, and mood
        - Character descriptions should reference the provided character images
        - Scene descriptions should be vivid and cinematic
        - Include specific visual metaphors and symbolic elements

        OUTPUT FORMAT:
        You must generate responses in this exact JSON structure:
        {
            "scene_image_prompt": "Cinematic scene: [description] with [character_name(male/female)] and [character_name(male/female)] in [location] setting, [camera_angle], [lighting], [mood]",
            "scene_video_prompt": {
                "camera_angle": "[Specific angle and lens details]",
                "scene_description": "[Detailed visual description of setting and action]",
                "character_visual_description": "[Physical appearance and styling of characters present]",
                "mood_emotion": "[Emotional tone and psychological atmosphere]",
                "lighting": "[Detailed lighting setup and color temperature]",
                "dialogue": "[Exact dialogue if present]",
                "narration": "[Exact narration if present]"
            }
        }

        Remember: Your prompts will be used with reference images to generate professional-quality cinematic content, so be precise, detailed, and artistically compelling.
        """

    def generate_scene_description(self, shot_info: Dict[str, Any], character_references: Optional[Dict[str, Any]] = None, location_reference: Optional[Dict[str, Any]] = None) -> SceneDescriberInfo:
        """Generate detailed scene description for a single shot"""
        
        # Build comprehensive shot context
        shot_context = self._build_shot_context(shot_info, character_references, location_reference)
        
        messages = [
            {"role": "system", "content": self.create_scene_description_system_prompt()},
            {"role": "user", "content": f"Generate a detailed cinematic description for this shot:\n\n{shot_context}"}
        ]
        
        try:
            # Use structured output for consistent formatting
            structured_llm = self.llm.with_structured_output(SceneDescriberInfo)
            scene_describer_info = structured_llm.invoke(messages)
            return scene_describer_info
        except Exception as e:
            print(f"Error generating scene description: {e}")
            # Return a fallback description
            return self._create_fallback_description(shot_info)

    def _build_shot_context(self, shot_info: Dict[str, Any], character_references: Optional[Dict[str, Any]] = None, location_reference: Optional[Dict[str, Any]] = None) -> str:
        """Build comprehensive context for shot description"""
        context = f"""
SHOT INFORMATION:
- Shot ID: {shot_info.get('Shot_ID', 'Unknown')}
- Description: {shot_info.get('Description', 'No description')}
- Focus Characters: {shot_info.get('Focus_Characters', [])}
- Camera: {shot_info.get('Camera', 'Unknown')}
- Emotion: {shot_info.get('Emotion', 'neutral')}
- Narration: {shot_info.get('Narration', '')}
- Dialog: {shot_info.get('Dialog', [])}
- Background SFX: {shot_info.get('Background_SFX', [])}
- Lighting: {shot_info.get('Lighting', '')}
- Shot Tone: {shot_info.get('Shot_Tone', 'neutral')}

CHARACTER OUTFIT DETAILS:"""
        
        # Add character outfit information
        shot_chars = shot_info.get('Shot_Characters', [])
        if shot_chars:
            for shot_char in shot_chars:
                context += f"""
- {shot_char.get('character_name', 'Unknown')} ({shot_char.get('character_id', 'N/A')}):
  * Outfit: {shot_char.get('outfit_description', 'N/A')}
  * Outfit Continuity: {shot_char.get('outfit_continuity', 'N/A')}
  * Action: {shot_char.get('character_action', 'N/A')}"""
        else:
            context += "\n- No detailed character outfit information available"
        
        context += """

"""
        
        
        if character_references:
            context += "\nCHARACTER REFERENCES:\n"
            for char_id, char_info in character_references.items():
                context += f"- {char_id}: {char_info.get('name', 'Unknown')} - {char_info.get('description', 'No description')}\n"
        
        # Add location reference information if available
        if location_reference:
            context += f"\nLOCATION REFERENCE:\n"
            context += f"- Name: {location_reference.get('location_name', 'Unknown')}\n"
            context += f"- Location Image Detailed Description: {location_reference.get('location_image_detailed_description', '')}\n"
            context += f"- Environment: {location_reference.get('environment', '')}\n"
            context += f"- Lighting: {location_reference.get('lighting', '')}\n"
            context += f"- Atmosphere: {location_reference.get('atmosphere', '')}\n"
        
        return context

    def _create_fallback_description(self, shot_info: Dict[str, Any]) -> SceneDescriberInfo:
        """Create a fallback description if LLM fails"""
        video_info = SceneDescriberVideoInfo(
            camera_angle=shot_info.get('Camera', 'medium shot'),
            scene_description=shot_info.get('Description', 'A cinematic scene'),
            character_visual_description="Characters as described in the script",
            mood_emotion=shot_info.get('Emotion', 'neutral'),
            lighting=shot_info.get('Lighting', 'natural lighting'),
            dialogue=shot_info.get('Dialog', ''),
            narration=shot_info.get('Narration', '')
        )
        
        return SceneDescriberInfo(
            scene_image_prompt=f"Cinematic scene: {shot_info.get('Description', 'A dramatic moment')}",
            scene_video_prompt=video_info
        )

    def generate_all_scene_descriptions(self, formatted_script: Dict[str, Any], character_data: Optional[Dict[str, Any]] = None, location_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate scene descriptions for all shots in the formatted script"""
        
        # Create character lookup for references
        character_lookup = {}
        if character_data and 'characters' in character_data:
            for char in character_data['characters']:
                character_lookup[char.get('id', '')] = char
        
        # Create location lookup for references
        location_lookup = {}
        if location_data and 'locations' in location_data:
            for loc in location_data['locations']:
                location_lookup[loc.get('location_id', '')] = loc
        
        # Process each scene
        for scene in formatted_script.get('scenes', []):
            scene_id = scene.get('scene_info', {}).get('Scene_ID', 'Unknown')
            print(f"Processing scene: {scene_id}")
            
            # Get location reference for this scene
            scene_location_ref = None
            if 'location_reference' in scene.get('scene_info', {}):
                scene_location_ref = scene['scene_info']['location_reference']
            
            # Process each shot in the scene
            for shot in scene.get('shots', []):
                shot_id = shot.get('Shot_ID', 'Unknown')
                print(f"  Processing shot: {shot_id}")
                
                # Get character references for this shot
                shot_character_refs = {}
                for char_id in shot.get('Focus_Characters', []):
                    if char_id in character_lookup:
                        shot_character_refs[char_id] = character_lookup[char_id]
                
                # Generate scene description
                try:
                    scene_description = self.generate_scene_description(
                        shot, 
                        shot_character_refs, 
                        scene_location_ref
                    )
                    
                    # Add the description to the shot
                    shot['scene_description'] = scene_description.model_dump()
                    
                except Exception as e:
                    print(f"Error processing shot {shot_id}: {e}")
                    # Add fallback description
                    shot['scene_description'] = self._create_fallback_description(shot).model_dump()
        
        return formatted_script

    def save_scene_descriptions(self, formatted_script: Dict[str, Any], output_file: str, session_path: str = None):
        """Save scene descriptions to file"""
        if session_path:
            output_dir = os.path.join(session_path, "scene_description")
        else:
            output_dir = "story_generation_pipeline/scene_description"
        
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, output_file)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(formatted_script, f, indent=2, ensure_ascii=False)
        
        print(f"Scene descriptions saved to: {filepath}")

    def get_scene_summary(self, formatted_script: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of all scene descriptions"""
        summary = {
            "total_scenes": len(formatted_script.get('scenes', [])),
            "total_shots": 0,
            "scenes_with_descriptions": 0,
            "scenes_summary": []
        }
        
        for scene in formatted_script.get('scenes', []):
            scene_id = scene.get('scene_info', {}).get('Scene_ID', 'Unknown')
            shots = scene.get('shots', [])
            shots_with_descriptions = sum(1 for shot in shots if 'scene_description' in shot)
            
            summary["total_shots"] += len(shots)
            if shots_with_descriptions > 0:
                summary["scenes_with_descriptions"] += 1
            
            summary["scenes_summary"].append({
                "scene_id": scene_id,
                "total_shots": len(shots),
                "shots_with_descriptions": shots_with_descriptions,
                "completion_percentage": (shots_with_descriptions / len(shots) * 100) if shots else 0
            })
        
        return summary

    def create_enhanced_image_prompt(self, shot_info: Dict[str, Any], character_refs: Dict[str, Any], location_ref: Dict[str, Any]) -> str:
        """Create enhanced image prompt with character and location references"""
        
        # Extract character information
        character_descriptions = []
        for char_id, char_info in character_refs.items():
            char_name = char_info.get('name', 'Character')
            char_gender = char_info.get('gender', 'unknown')
            char_description = char_info.get('overall_description', '')
            character_descriptions.append(f"{char_name}({char_gender}): {char_description}")
        
        # Extract location information
        location_desc = ""
        if location_ref:
            location_desc = f"Location: {location_ref.get('environment', '')} with {location_ref.get('lighting', '')} lighting"
        
        # Build the enhanced prompt
        prompt_parts = [
            "Cinematic film still,",
            f"Scene: {shot_info.get('Description', '')}",
            f"Camera: {shot_info.get('Camera', 'medium shot')}",
            f"Lighting: {shot_info.get('Lighting', 'natural lighting')}",
            f"Mood: {shot_info.get('Shot_Tone', 'neutral')}",
        ]
        
        if character_descriptions:
            prompt_parts.append(f"Characters: {', '.join(character_descriptions)}")
        
        if location_desc:
            prompt_parts.append(location_desc)
        
        # Add technical specifications
        prompt_parts.extend([
            "Professional cinematography,",
            "High quality, detailed,",
            "Cinematic composition,",
            "Film photography style"
        ])
        
        return " ".join(prompt_parts)

    def create_enhanced_video_prompt(self, shot_info: Dict[str, Any], character_refs: Dict[str, Any], location_ref: Dict[str, Any]) -> str:
        """Create enhanced video prompt with detailed motion and timing"""
        
        # Extract character information for video
        character_actions = []
        for char_id, char_info in character_refs.items():
            char_name = char_info.get('name', 'Character')
            char_emotion = shot_info.get('Emotion', 'neutral')
            character_actions.append(f"{char_name} expressing {char_emotion}")
        
        # Build the enhanced video prompt
        prompt_parts = [
            "Cinematic video sequence,",
            f"Scene: {shot_info.get('Description', '')}",
            f"Camera movement: {shot_info.get('Camera', 'static')}",
            f"Duration: 3-5 seconds,",
            f"Pacing: {shot_info.get('Shot_Tone', 'moderate')}",
        ]
        
        if character_actions:
            prompt_parts.append(f"Character actions: {', '.join(character_actions)}")
        
        # Add environmental dynamics
        if location_ref:
            prompt_parts.append(f"Environment: {location_ref.get('environment', '')}")
            if location_ref.get('background_sfx'):
                prompt_parts.append(f"Audio: {', '.join(location_ref.get('background_sfx', []))}")
        
        # Add technical video specifications
        prompt_parts.extend([
            "Smooth camera movements,",
            "Professional cinematography,",
            "High quality video,",
            "Cinematic lighting transitions,",
            "Film grain texture"
        ])
        
        return " ".join(prompt_parts)
