#!/usr/bin/env python3
"""
Outfit Consistency Tracker - Manages character outfit consistency across scenes and shots
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from models.pydantic_model import FormattedScript, Scene, Shot, SceneCharacter, CharacterOutfit, ShotCharacter
import json
import os

@dataclass
class OutfitState:
    """Tracks the current outfit state of a character"""
    character_id: str
    character_name: str
    current_outfit: str
    outfit_type: str
    clothing_items: List[str]
    colors: List[str]
    accessories: List[str]
    last_scene_id: str
    last_shot_id: str
    outfit_history: List[Dict[str, Any]]

class OutfitConsistencyTracker:
    """Manages outfit consistency across the entire script"""
    
    def __init__(self):
        self.character_outfits: Dict[str, OutfitState] = {}
        self.scene_outfit_changes: Dict[str, List[str]] = {}  # scene_id -> list of character_ids with outfit changes
    
    def initialize_character_outfits(self, characters: List[Dict[str, Any]]):
        """Initialize character outfit states from character data"""
        for char in characters:
            char_id = char.get('id', '')
            char_name = char.get('name', '')
            
            if char_id:
                # Create initial outfit state based on character persona
                initial_outfit = self._generate_initial_outfit(char)
                
                self.character_outfits[char_id] = OutfitState(
                    character_id=char_id,
                    character_name=char_name,
                    current_outfit=initial_outfit['description'],
                    outfit_type=initial_outfit['type'],
                    clothing_items=initial_outfit['items'],
                    colors=initial_outfit['colors'],
                    accessories=initial_outfit['accessories'],
                    last_scene_id="",
                    last_shot_id="",
                    outfit_history=[]
                )
    
    def _generate_initial_outfit(self, character: Dict[str, Any]) -> Dict[str, Any]:
        """Generate initial outfit for a character based on their persona"""
        role = character.get('role', 'character').lower()
        age = character.get('age', 25)
        gender = character.get('gender', 'person').lower()
        description = character.get('overall_description', '').lower()
        
        # Define outfit templates based on character roles
        outfit_templates = {
            'student': {
                'description': f"Casual college attire - comfortable jeans, casual t-shirt, sneakers",
                'type': 'casual',
                'items': ['jeans', 'casual t-shirt', 'sneakers'],
                'colors': ['blue', 'white'],
                'accessories': ['backpack']
            },
            'detective': {
                'description': f"Professional detective attire - dark blazer, dress shirt, dress pants, dress shoes",
                'type': 'professional',
                'items': ['dark blazer', 'dress shirt', 'dress pants', 'dress shoes'],
                'colors': ['dark blue', 'white'],
                'accessories': ['badge', 'watch']
            },
            'inspector': {
                'description': f"Police inspector uniform - crisp police uniform with badges",
                'type': 'uniform',
                'items': ['police uniform shirt', 'police pants', 'police shoes', 'badge'],
                'colors': ['navy blue', 'black'],
                'accessories': ['badge', 'radio', 'belt']
            },
            'main': {
                'description': f"Smart casual attire - well-fitted clothes reflecting personality",
                'type': 'smart_casual',
                'items': ['casual shirt', 'jeans', 'casual shoes'],
                'colors': ['varied'],
                'accessories': ['watch']
            }
        }
        
        # Select appropriate template
        if 'student' in role or 'college' in description:
            return outfit_templates['student']
        elif 'detective' in role:
            return outfit_templates['detective']
        elif 'inspector' in role or 'police' in description:
            return outfit_templates['inspector']
        else:
            return outfit_templates['main']
    
    def track_scene_outfits(self, scene: Scene) -> Scene:
        """Track and ensure outfit consistency for a scene"""
        scene_id = scene.scene_info.scene_id
        
        # Process each character in the scene
        for scene_char in scene.scene_info.scene_characters:
            char_id = scene_char.character_id
            
            if char_id in self.character_outfits:
                # Check if this is a new scene or outfit change
                current_state = self.character_outfits[char_id]
                
                # If detailed outfit is provided, use it; otherwise maintain consistency
                if scene_char.detailed_outfit:
                    # Update character's outfit state
                    self._update_outfit_state(char_id, scene_char.detailed_outfit, scene_id, "")
                else:
                    # Generate consistent outfit based on current state
                    scene_char.detailed_outfit = self._generate_consistent_outfit(char_id, scene_id)
        
        return scene
    
    def track_shot_outfits(self, shot: Shot, scene_id: str) -> Shot:
        """Track and ensure outfit consistency for a shot"""
        shot_id = shot.shot_id
        
        # Process each character in the shot
        if shot.shot_characters:
            for shot_char in shot.shot_characters:
                char_id = shot_char.character_id
                
                if char_id in self.character_outfits:
                    current_state = self.character_outfits[char_id]
                    
                    # Ensure outfit consistency within the scene
                    if not shot_char.outfit_description:
                        shot_char.outfit_description = current_state.current_outfit
                        shot_char.outfit_continuity = "same as scene outfit"
                    
                    # Update last shot tracking
                    current_state.last_shot_id = shot_id
        else:
            # If no shot_characters provided, create them for focus characters
            shot.shot_characters = []
            for char_name in shot.focus_characters:
                # Find character by name
                char_id = self._find_character_id_by_name(char_name)
                if char_id and char_id in self.character_outfits:
                    current_state = self.character_outfits[char_id]
                    
                    shot_char = ShotCharacter(
                        character_id=char_id,
                        character_name=char_name,
                        outfit_description=current_state.current_outfit,
                        outfit_continuity="consistent with scene",
                        character_action="appears in shot"
                    )
                    shot.shot_characters.append(shot_char)
        
        return shot
    
    def _update_outfit_state(self, char_id: str, new_outfit: CharacterOutfit, scene_id: str, shot_id: str):
        """Update a character's outfit state"""
        if char_id in self.character_outfits:
            current_state = self.character_outfits[char_id]
            
            # Save current outfit to history
            current_state.outfit_history.append({
                'outfit': current_state.current_outfit,
                'scene_id': current_state.last_scene_id,
                'shot_id': current_state.last_shot_id,
                'timestamp': len(current_state.outfit_history)
            })
            
            # Update to new outfit
            current_state.current_outfit = new_outfit.outfit_description
            current_state.outfit_type = new_outfit.outfit_type
            current_state.clothing_items = new_outfit.clothing_items
            current_state.colors = new_outfit.colors
            current_state.accessories = new_outfit.accessories
            current_state.last_scene_id = scene_id
            current_state.last_shot_id = shot_id
            
            # Track outfit changes
            if scene_id not in self.scene_outfit_changes:
                self.scene_outfit_changes[scene_id] = []
            if char_id not in self.scene_outfit_changes[scene_id]:
                self.scene_outfit_changes[scene_id].append(char_id)
    
    def _generate_consistent_outfit(self, char_id: str, scene_id: str) -> CharacterOutfit:
        """Generate a consistent outfit for a character"""
        if char_id in self.character_outfits:
            current_state = self.character_outfits[char_id]
            
            return CharacterOutfit(
                outfit_description=current_state.current_outfit,
                outfit_type=current_state.outfit_type,
                clothing_items=current_state.clothing_items,
                colors=current_state.colors,
                accessories=current_state.accessories,
                outfit_context=f"Consistent with previous appearance in {current_state.last_scene_id or 'initial setup'}"
            )
        
        # Fallback if character not found
        return CharacterOutfit(
            outfit_description="Casual everyday clothes",
            outfit_type="casual",
            clothing_items=["shirt", "pants", "shoes"],
            colors=["neutral"],
            accessories=[],
            outfit_context="Default outfit"
        )
    
    def _find_character_id_by_name(self, char_name: str) -> Optional[str]:
        """Find character ID by name"""
        for char_id, state in self.character_outfits.items():
            if state.character_name.lower() == char_name.lower() or char_name.lower() in state.character_name.lower():
                return char_id
        return None
    
    def process_formatted_script(self, formatted_script: FormattedScript) -> FormattedScript:
        """Process entire formatted script to ensure outfit consistency"""
        print("🎭 Processing script for outfit consistency...")
        
        # Initialize character outfits
        self.initialize_character_outfits([char.model_dump() for char in formatted_script.characters])
        
        # Process each scene
        for scene in formatted_script.scenes:
            print(f"  Processing outfits for {scene.scene_info.scene_id}")
            
            # Track scene-level outfits
            scene = self.track_scene_outfits(scene)
            
            # Track shot-level outfits
            for shot in scene.shots:
                shot = self.track_shot_outfits(shot, scene.scene_info.scene_id)
        
        print("✅ Outfit consistency processing complete!")
        return formatted_script
    
    def get_outfit_summary(self) -> Dict[str, Any]:
        """Get a summary of outfit states and changes"""
        summary = {
            "character_count": len(self.character_outfits),
            "characters": {},
            "outfit_changes": self.scene_outfit_changes
        }
        
        for char_id, state in self.character_outfits.items():
            summary["characters"][char_id] = {
                "name": state.character_name,
                "current_outfit": state.current_outfit,
                "outfit_type": state.outfit_type,
                "last_scene": state.last_scene_id,
                "outfit_changes": len(state.outfit_history)
            }
        
        return summary
    
    def save_outfit_tracking(self, output_path: str):
        """Save outfit tracking data to file"""
        tracking_data = {
            "character_outfits": {},
            "scene_outfit_changes": self.scene_outfit_changes,
            "summary": self.get_outfit_summary()
        }
        
        # Convert outfit states to serializable format
        for char_id, state in self.character_outfits.items():
            tracking_data["character_outfits"][char_id] = {
                "character_id": state.character_id,
                "character_name": state.character_name,
                "current_outfit": state.current_outfit,
                "outfit_type": state.outfit_type,
                "clothing_items": state.clothing_items,
                "colors": state.colors,
                "accessories": state.accessories,
                "last_scene_id": state.last_scene_id,
                "last_shot_id": state.last_shot_id,
                "outfit_history": state.outfit_history
            }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(tracking_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Outfit tracking data saved to: {output_path}")
