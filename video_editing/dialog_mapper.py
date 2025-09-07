#!/usr/bin/env python3
"""
Dialog Mapper - Creates shot-level dialog mapping using LLM
Maps which character speaks which dialog in each shot
"""

import os
import json
from typing import Dict, List, Any, Optional
from utils.llm import get_llm_model
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class CharacterDialog(BaseModel):
    """Individual character dialog"""
    character_id: str = Field(..., description="Character ID")
    character_name: str = Field(..., description="Character name")
    dialog: str = Field(..., description="Dialog text")

class ShotDialog(BaseModel):
    """Dialog information for a shot"""
    shot_id: str = Field(..., description="Shot ID")
    character_dialogs: List[CharacterDialog] = Field(default_factory=list, description="List of character dialogs")
    narration: Optional[str] = Field(default=None, description="Narration text if any")
    has_dialog: bool = Field(default=False, description="Whether shot has dialog")
    has_narration: bool = Field(default=False, description="Whether shot has narration")

class SceneDialogMapping(BaseModel):
    """Dialog mapping for a complete scene"""
    scene_id: str = Field(..., description="Scene ID")
    shots: List[ShotDialog] = Field(..., description="List of shot dialogs")

class DialogMapper:
    """Maps dialog and narration to characters for each shot"""
    
    def __init__(self):
        self.llm = get_llm_model("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
    
    def create_dialog_mapping_system_prompt(self) -> str:
        """Create system prompt for dialog mapping"""
        return """You are a professional script analyzer specializing in dialog and narration mapping for video production.

Your task is to analyze each shot in a scene and determine:
1. Which character speaks which dialog
2. What narration (if any) accompanies the shot
3. The timing and context of speech

IMPORTANT RULES:
- Map dialog ONLY to characters who are present in the shot (check Focus_Characters)
- If dialog mentions a character but they're not in the shot, it's likely narration
- Narration is typically scene-setting, internal thoughts, or omniscient commentary
- Some shots may have no dialog or narration
- Dialog should match the character's personality and role
- Keep dialog natural and conversational

For each shot, provide:
1. character_dialogs: Array of character dialog objects with character_id, character_name, and dialog
2. narration: Any narration text (null if none)
3. has_dialog: true/false
4. has_narration: true/false

Return ONLY valid JSON in this exact format:
{
  "scene_id": "SC_01",
  "shots": [
    {
      "shot_id": "SC1_SH1",
      "character_dialogs": [
        {"character_id": "char_01", "character_name": "John", "dialog": "Hello there!"}
      ],
      "narration": "The morning sun cast long shadows across the room",
      "has_dialog": true,
      "has_narration": true
    }
  ]
}"""
    
    def create_dialog_context(self, scene_info: Dict[str, Any], characters: List[Dict[str, Any]]) -> str:
        """Create context for dialog mapping"""
        context = f"SCENE: {scene_info.get('Scene_ID', 'Unknown')}\n"
        context += f"SETTING: {scene_info.get('Setting', 'Unknown')}\n"
        context += f"TIME: {scene_info.get('Time_of_Day', 'Unknown')}\n\n"
        
        # Add character information
        context += "CHARACTERS IN STORY:\n"
        for char in characters:
            context += f"- {char.get('name', 'Unknown')} (ID: {char.get('id', 'unknown')}): {char.get('role', 'unknown')} - {char.get('overall_description', '')[:100]}...\n"
        
        context += "\nSCENE CHARACTERS:\n"
        for scene_char in scene_info.get('Scene_Characters', []):
            context += f"- {scene_char.get('character_name', 'Unknown')} (ID: {scene_char.get('character_id', 'unknown')}): {scene_char.get('character_role', 'unknown')}\n"
        
        return context
    
    def create_shots_context(self, shots: List[Dict[str, Any]]) -> str:
        """Create context for shots"""
        context = "\nSHOTS TO ANALYZE:\n"
        
        for shot in shots:
            shot_id = shot.get('Shot_ID', 'unknown')
            context += f"\n--- {shot_id} ---\n"
            context += f"Description: {shot.get('Description', 'N/A')}\n"
            context += f"Focus Characters: {shot.get('Focus_Characters', [])}\n"
            context += f"Camera: {shot.get('Camera', 'N/A')}\n"
            context += f"Dialog: {shot.get('Dialog', 'N/A')}\n"
            context += f"Narration: {shot.get('Narration', 'N/A')}\n"
            context += f"Emotion: {shot.get('Emotion', 'N/A')}\n"
            
            # Add character-specific details if available
            if 'Shot_Characters' in shot:
                context += "Shot Characters:\n"
                for shot_char in shot['Shot_Characters']:
                    context += f"  - {shot_char.get('character_name', 'Unknown')} (ID: {shot_char.get('character_id', 'unknown')}): {shot_char.get('character_action', 'N/A')}\n"
        
        return context
    
    def generate_dialog_mapping(self, scene_info: Dict[str, Any], shots: List[Dict[str, Any]], 
                              characters: List[Dict[str, Any]]) -> Optional[SceneDialogMapping]:
        """Generate dialog mapping for a scene"""
        
        scene_id = scene_info.get('Scene_ID', 'unknown')
        print(f"🎭 Generating dialog mapping for {scene_id}...")
        
        # Create context
        dialog_context = self.create_dialog_context(scene_info, characters)
        shots_context = self.create_shots_context(shots)
        
        full_context = dialog_context + shots_context
        
        messages = [
            {"role": "system", "content": self.create_dialog_mapping_system_prompt()},
            {"role": "user", "content": f"Analyze this scene and create dialog mapping:\n\n{full_context}"}
        ]
        
        try:
            # Use function calling method to avoid schema issues
            structured_llm = self.llm.with_structured_output(SceneDialogMapping, method="function_calling")
            result = structured_llm.invoke(messages)
            
            print(f"✅ Generated dialog mapping for {scene_id}")
            return result
            
        except Exception as e:
            print(f"❌ Error generating dialog mapping for {scene_id}: {e}")
            return None
    
    def generate_all_dialog_mappings(self, script_data: Dict[str, Any], 
                                   characters: List[Dict[str, Any]]) -> List[SceneDialogMapping]:
        """Generate dialog mappings for all scenes"""
        
        scenes = script_data.get('scenes', [])
        dialog_mappings = []
        
        print(f"🎬 Generating dialog mappings for {len(scenes)} scenes...")
        
        for scene in scenes:
            scene_info = scene.get('scene_info', {})
            shots = scene.get('shots', [])
            
            if not shots:
                print(f"⚠️ No shots found for scene {scene_info.get('Scene_ID', 'unknown')}")
                continue
            
            dialog_mapping = self.generate_dialog_mapping(scene_info, shots, characters)
            if dialog_mapping:
                dialog_mappings.append(dialog_mapping)
        
        return dialog_mappings
    
    def save_dialog_mappings(self, dialog_mappings: List[SceneDialogMapping], output_file: str) -> bool:
        """Save dialog mappings to JSON file"""
        try:
            # Convert to dict format for JSON serialization
            mappings_data = {
                "dialog_mappings": [mapping.dict() for mapping in dialog_mappings],
                "total_scenes": len(dialog_mappings),
                "generated_at": json.dumps({"timestamp": "auto-generated"})
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(mappings_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Saved dialog mappings to: {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving dialog mappings: {e}")
            return False
    
    def load_dialog_mappings(self, input_file: str) -> List[SceneDialogMapping]:
        """Load dialog mappings from JSON file"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            mappings = []
            for mapping_data in data.get('dialog_mappings', []):
                mappings.append(SceneDialogMapping(**mapping_data))
            
            print(f"✅ Loaded {len(mappings)} dialog mappings from: {input_file}")
            return mappings
            
        except Exception as e:
            print(f"❌ Error loading dialog mappings: {e}")
            return []
    
    def get_dialog_statistics(self, dialog_mappings: List[SceneDialogMapping]) -> Dict[str, Any]:
        """Get statistics about dialog mappings"""
        total_shots = 0
        shots_with_dialog = 0
        shots_with_narration = 0
        character_dialog_count = {}
        
        for mapping in dialog_mappings:
            for shot in mapping.shots:
                total_shots += 1
                
                if shot.has_dialog:
                    shots_with_dialog += 1
                    
                    for char_dialog in shot.character_dialogs:
                        char_name = char_dialog.character_name
                        character_dialog_count[char_name] = character_dialog_count.get(char_name, 0) + 1
                
                if shot.has_narration:
                    shots_with_narration += 1
        
        return {
            "total_scenes": len(dialog_mappings),
            "total_shots": total_shots,
            "shots_with_dialog": shots_with_dialog,
            "shots_with_narration": shots_with_narration,
            "shots_without_audio": total_shots - shots_with_dialog - shots_with_narration,
            "character_dialog_count": character_dialog_count
        }
