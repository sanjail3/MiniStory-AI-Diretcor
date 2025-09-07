#!/usr/bin/env python3
"""
Audio Generator - Generates audio files for each shot using ElevenLabs TTS
"""

import os
import json
import requests
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from .dialog_mapper import SceneDialogMapping, ShotDialog
from .intelligent_voice_matcher import IntelligentVoiceMatcher

load_dotenv()

class AudioGenerator:
    """Generates audio files for shots using ElevenLabs TTS"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ELEVENLABS_API_KEY')
        if not self.api_key:
            raise ValueError("ElevenLabs API key not found. Please set ELEVENLABS_API_KEY environment variable.")
        
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Default narration voice settings
        self.narration_voice_id = "21m00Tcm4TlvDq8ikWAM"  # Default ElevenLabs voice
        self.narration_voice_settings = {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.2,
            "use_speaker_boost": True
        }
        
        # Initialize intelligent voice matcher for fallback
        try:
            self.voice_matcher = IntelligentVoiceMatcher()
        except Exception as e:
            print(f"⚠️ Could not initialize voice matcher: {e}")
            self.voice_matcher = None
    
    def generate_speech(self, text: str, voice_id: str, output_path: str, 
                       voice_settings: Optional[Dict] = None) -> bool:
        """Generate speech audio file using ElevenLabs TTS"""
        
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        
        # Default voice settings
        if not voice_settings:
            voice_settings = {
                "stability": 0.5,
                "similarity_boost": 0.8,
                "style": 0.2,
                "use_speaker_boost": True
            }
        
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": voice_settings
        }
        
        try:
            print(f"🎤 Generating speech: '{text[:50]}...' with voice {voice_id}")
            
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            # Save audio file
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Audio saved: {output_path}")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error generating speech: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
                
                # Check for specific voice not found error
                if e.response.status_code == 404 and "voice_not_found" in e.response.text:
                    print(f"   💡 Voice ID {voice_id} not found. This usually means:")
                    print(f"      - Voice was not properly created from preview")
                    print(f"      - Using preview ID instead of actual voice ID")
                    print(f"      - Voice was deleted from account")
                    print(f"   🔧 Run fix_voice_ids.py to validate and fix voice IDs")
            
            return False
    
    def validate_voice_id(self, voice_id: str) -> bool:
        """Check if a voice ID is valid by making a test request"""
        if not voice_id:
            return False
        
        url = f"{self.base_url}/voices/{voice_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            return response.status_code == 200
        except:
            return False
    
    def get_character_voice_id(self, character_id: str, characters: List[Dict[str, Any]]) -> Optional[str]:
        """Get voice ID for a character"""
        for char in characters:
            if char.get('id') == character_id:
                return char.get('generated_voice_id')
        return None
    
    def intelligent_voice_assignment_fallback(self, characters: List[Dict[str, Any]], 
                                            characters_file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Use intelligent voice matching as fallback when voice IDs are invalid or duplicate"""
        
        if not self.voice_matcher:
            print("❌ Voice matcher not available for fallback")
            return characters
        
        print("🤖 Activating intelligent voice assignment fallback...")
        
        try:
            # Get available voices
            voices = self.voice_matcher.get_available_voices()
            if not voices:
                print("❌ No voices available for assignment")
                return characters
            
            # Find characters with invalid or duplicate voices
            voice_usage = {}
            characters_needing_assignment = []
            
            for char in characters:
                voice_id = char.get('generated_voice_id')
                if not voice_id or not self.validate_voice_id(voice_id):
                    characters_needing_assignment.append(char)
                    print(f"🔍 {char.get('name', 'Unknown')}: Invalid voice ID {voice_id}")
                else:
                    # Track voice usage to detect duplicates
                    if voice_id in voice_usage:
                        voice_usage[voice_id].append(char)
                    else:
                        voice_usage[voice_id] = [char]
            
            # Check for duplicate voice assignments (same voice for multiple characters)
            for voice_id, chars_using_voice in voice_usage.items():
                if len(chars_using_voice) > 1:
                    print(f"🔍 Found duplicate voice {voice_id} used by {len(chars_using_voice)} characters")
                    # Add all but the first character to reassignment list
                    characters_needing_assignment.extend(chars_using_voice[1:])
            
            if not characters_needing_assignment:
                print("✅ All character voices are valid and unique")
                return characters
            
            print(f"🎭 Found {len(characters_needing_assignment)} characters needing voice assignment")
            
            # Use LLM to match voices
            matching_result = self.voice_matcher.match_voices_to_characters(
                characters_needing_assignment, voices
            )
            
            if not matching_result:
                print("❌ Voice matching failed")
                return characters
            
            # Apply assignments to characters
            updated_characters = characters.copy()
            assignment_lookup = {assignment.character_id: assignment for assignment in matching_result.assignments}
            
            for i, char in enumerate(updated_characters):
                char_id = char.get('id', 'unknown')
                if char_id in assignment_lookup:
                    assignment = assignment_lookup[char_id]
                    
                    # Update character with new voice assignment
                    updated_characters[i] = char.copy()
                    updated_characters[i].update({
                        'generated_voice_id': assignment.assigned_voice_id,
                        'assigned_voice_name': assignment.assigned_voice_name,
                        'voice_assignment_reasoning': assignment.reasoning,
                        'voice_assignment_confidence': assignment.confidence_score,
                        'voice_assignment_method': 'llm_fallback_during_audio_generation',
                        'voice_assignment_timestamp': 'auto_assigned'
                    })
                    
                    print(f"✅ Assigned {assignment.assigned_voice_name} to {char.get('name', 'Unknown')} (confidence: {assignment.confidence_score:.2f})")
            
            # Save updated characters if file path provided
            if characters_file_path:
                try:
                    data = {"characters": updated_characters}
                    with open(characters_file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"✅ Updated character file: {characters_file_path}")
                except Exception as e:
                    print(f"⚠️ Could not update character file: {e}")
            
            return updated_characters
            
        except Exception as e:
            print(f"❌ Error in intelligent voice assignment fallback: {e}")
            return characters
    
    def generate_shot_audio(self, shot_dialog: ShotDialog, characters: List[Dict[str, Any]], 
                          output_dir: str) -> Dict[str, Any]:
        """Generate audio files for a single shot"""
        
        shot_id = shot_dialog.shot_id
        print(f"🎬 Generating audio for shot {shot_id}...")
        
        audio_files = []
        results = {
            "shot_id": shot_id,
            "audio_files": [],
            "success": True,
            "errors": []
        }
        
        # Generate character dialog audio
        if shot_dialog.has_dialog and shot_dialog.character_dialogs:
            for i, char_dialog in enumerate(shot_dialog.character_dialogs):
                character_id = char_dialog.character_id
                character_name = char_dialog.character_name
                dialog_text = char_dialog.dialog
                
                if not dialog_text.strip():
                    continue
                
                # Get character voice ID
                voice_id = self.get_character_voice_id(character_id, characters)
                if not voice_id:
                    error_msg = f"No voice ID found for character {character_name} ({character_id})"
                    print(f"❌ {error_msg}")
                    print(f"   💡 Tip: Run fix_voice_ids.py to validate and fix voice IDs")
                    results["errors"].append(error_msg)
                    results["success"] = False
                    continue
                
                # Generate audio filename
                audio_filename = f"{shot_id}_{character_id}_dialog_{i+1}.mp3"
                audio_path = os.path.join(output_dir, audio_filename)
                
                # Generate speech
                success = self.generate_speech(dialog_text, voice_id, audio_path)
                
                if success:
                    audio_info = {
                        "type": "dialog",
                        "character_id": character_id,
                        "character_name": character_name,
                        "text": dialog_text,
                        "audio_path": audio_path,
                        "voice_id": voice_id,
                        "sequence": i + 1
                    }
                    results["audio_files"].append(audio_info)
                else:
                    error_msg = f"Failed to generate audio for {character_name} dialog"
                    results["errors"].append(error_msg)
                    results["success"] = False
        
        # Generate narration audio
        if shot_dialog.has_narration and shot_dialog.narration:
            narration_text = shot_dialog.narration.strip()
            
            if narration_text:
                # Generate narration filename
                narration_filename = f"{shot_id}_narration.mp3"
                narration_path = os.path.join(output_dir, narration_filename)
                
                # Generate narration speech
                success = self.generate_speech(
                    narration_text, 
                    self.narration_voice_id, 
                    narration_path,
                    self.narration_voice_settings
                )
                
                if success:
                    narration_info = {
                        "type": "narration",
                        "text": narration_text,
                        "audio_path": narration_path,
                        "voice_id": self.narration_voice_id,
                        "sequence": 0  # Narration typically comes first
                    }
                    results["audio_files"].append(narration_info)
                else:
                    error_msg = f"Failed to generate narration audio for {shot_id}"
                    results["errors"].append(error_msg)
                    results["success"] = False
        
        # Sort audio files by sequence (narration first, then dialogs)
        results["audio_files"].sort(key=lambda x: x["sequence"])
        
        print(f"{'✅' if results['success'] else '❌'} Shot {shot_id}: {len(results['audio_files'])} audio files generated")
        
        return results
    
    def generate_scene_audio(self, scene_mapping: SceneDialogMapping, characters: List[Dict[str, Any]], 
                           output_dir: str) -> Dict[str, Any]:
        """Generate audio files for all shots in a scene"""
        
        scene_id = scene_mapping.scene_id
        print(f"\n🎭 Generating audio for scene {scene_id}...")
        
        scene_results = {
            "scene_id": scene_id,
            "shots": [],
            "total_audio_files": 0,
            "successful_shots": 0,
            "failed_shots": 0
        }
        
        for shot_dialog in scene_mapping.shots:
            shot_result = self.generate_shot_audio(shot_dialog, characters, output_dir)
            scene_results["shots"].append(shot_result)
            scene_results["total_audio_files"] += len(shot_result["audio_files"])
            
            if shot_result["success"]:
                scene_results["successful_shots"] += 1
            else:
                scene_results["failed_shots"] += 1
        
        print(f"✅ Scene {scene_id} complete: {scene_results['total_audio_files']} audio files generated")
        print(f"   Successful shots: {scene_results['successful_shots']}/{len(scene_mapping.shots)}")
        
        return scene_results
    
    def generate_all_audio(self, dialog_mappings: List[SceneDialogMapping], 
                          characters: List[Dict[str, Any]], output_dir: str, 
                          characters_file_path: Optional[str] = None) -> Dict[str, Any]:
        """Generate audio files for all scenes"""
        
        print(f"🎤 Generating audio for {len(dialog_mappings)} scenes...")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Check current voice assignments
        print("🔍 Checking current voice assignments...")
        for char in characters:
            name = char.get('name', 'Unknown')
            voice_id = char.get('generated_voice_id', 'None')
            print(f"   {name}: {voice_id}")
        
        # Use intelligent voice assignment fallback if needed
        validated_characters = self.intelligent_voice_assignment_fallback(
            characters, characters_file_path
        )
        
        overall_results = {
            "scenes": [],
            "total_scenes": len(dialog_mappings),
            "total_audio_files": 0,
            "successful_scenes": 0,
            "failed_scenes": 0,
            "output_dir": output_dir,
            "voice_assignments_applied": len(validated_characters) != len(characters)
        }
        
        for scene_mapping in dialog_mappings:
            scene_result = self.generate_scene_audio(scene_mapping, validated_characters, output_dir)
            overall_results["scenes"].append(scene_result)
            overall_results["total_audio_files"] += scene_result["total_audio_files"]
            
            if scene_result["failed_shots"] == 0:
                overall_results["successful_scenes"] += 1
            else:
                overall_results["failed_scenes"] += 1
        
        print(f"\n🎉 Audio generation complete!")
        print(f"   Total audio files: {overall_results['total_audio_files']}")
        print(f"   Successful scenes: {overall_results['successful_scenes']}/{overall_results['total_scenes']}")
        
        return overall_results
    
    def save_audio_results(self, results: Dict[str, Any], output_file: str) -> bool:
        """Save audio generation results to JSON file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Saved audio results to: {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving audio results: {e}")
            return False
    
    def get_audio_statistics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Get statistics about generated audio"""
        stats = {
            "total_scenes": results.get("total_scenes", 0),
            "total_audio_files": results.get("total_audio_files", 0),
            "successful_scenes": results.get("successful_scenes", 0),
            "failed_scenes": results.get("failed_scenes", 0),
            "audio_by_type": {"dialog": 0, "narration": 0},
            "audio_by_character": {}
        }
        
        for scene in results.get("scenes", []):
            for shot in scene.get("shots", []):
                for audio_file in shot.get("audio_files", []):
                    audio_type = audio_file.get("type", "unknown")
                    stats["audio_by_type"][audio_type] = stats["audio_by_type"].get(audio_type, 0) + 1
                    
                    if audio_type == "dialog":
                        char_name = audio_file.get("character_name", "Unknown")
                        stats["audio_by_character"][char_name] = stats["audio_by_character"].get(char_name, 0) + 1
        
        return stats
    
    def set_narration_voice(self, voice_id: str, voice_settings: Optional[Dict] = None):
        """Set custom narration voice"""
        self.narration_voice_id = voice_id
        if voice_settings:
            self.narration_voice_settings = voice_settings
        print(f"✅ Narration voice set to: {voice_id}")
