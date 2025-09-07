#!/usr/bin/env python3
"""
Video Assembly Manager - Orchestrates the complete video assembly workflow
"""

import os
import json
from typing import Dict, List, Any, Optional
from .voice_design.generate_voice_id import VoiceDesigner, load_characters, save_characters_with_voices
from .video_assembler import VideoAssembler

class VideoAssemblyManager:
    """Manages the complete video assembly workflow"""
    
    def __init__(self, session_path: str):
        self.session_path = session_path
        self.video_editing_dir = os.path.join(session_path, "video_editing")
        os.makedirs(self.video_editing_dir, exist_ok=True)
        
        # Create subdirectories
        self.voice_dir = os.path.join(self.video_editing_dir, "voices")
        self.audio_dir = os.path.join(self.video_editing_dir, "audio")
        self.dialog_dir = os.path.join(self.video_editing_dir, "dialog_mapping")
        
        for directory in [self.voice_dir, self.audio_dir, self.dialog_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Initialize video assembler
        self.video_assembler = VideoAssembler(session_path)
    
    def get_characters_file_path(self) -> str:
        """Get the path to the characters.json file"""
        return os.path.join(self.session_path, "character_generation", "characters.json")
    
    def get_script_with_descriptions_path(self) -> str:
        """Get the path to script with descriptions"""
        return os.path.join(self.session_path, "scene_creation", "script_with_descriptions.json")
    
    def load_characters(self) -> List[Dict[str, Any]]:
        """Load characters from the session"""
        characters_file = self.get_characters_file_path()
        if os.path.exists(characters_file):
            return load_characters(characters_file)
        return []
    
    def load_script_with_descriptions(self) -> Optional[Dict[str, Any]]:
        """Load script with scene descriptions"""
        script_file = self.get_script_with_descriptions_path()
        if os.path.exists(script_file):
            with open(script_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def generate_character_voices(self) -> Dict[str, Any]:
        """Generate voices for all characters"""
        print("🎤 Starting character voice generation...")
        
        # Load characters
        characters = self.load_characters()
        if not characters:
            return {"success": False, "error": "No characters found"}
        
        try:
            # Initialize voice designer
            voice_designer = VoiceDesigner()
            
            # Generate voices
            characters_with_voices = voice_designer.create_character_voice_descriptions(
                characters, self.voice_dir
            )
            
            # Save updated characters
            characters_file = self.get_characters_file_path()
            success = save_characters_with_voices(characters_file, characters_with_voices)
            
            if success:
                # Create summary
                successful_voices = sum(1 for char in characters_with_voices if char.get('generated_voice_id'))
                
                return {
                    "success": True,
                    "characters_processed": len(characters_with_voices),
                    "successful_voices": successful_voices,
                    "failed_voices": len(characters_with_voices) - successful_voices,
                    "characters_with_voices": characters_with_voices,
                    "voice_dir": self.voice_dir
                }
            else:
                return {"success": False, "error": "Failed to save characters with voices"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_voice_generation_status(self) -> Dict[str, Any]:
        """Check the status of voice generation"""
        characters = self.load_characters()
        if not characters:
            return {"voices_generated": False, "characters_count": 0}
        
        # Check if voices are generated
        voices_generated = all(char.get('generated_voice_id') for char in characters)
        characters_with_voices = sum(1 for char in characters if char.get('generated_voice_id'))
        
        return {
            "voices_generated": voices_generated,
            "characters_count": len(characters),
            "characters_with_voices": characters_with_voices,
            "characters": characters
        }
    
    def get_video_assembly_status(self) -> Dict[str, Any]:
        """Get the overall status of video assembly pipeline"""
        # Check voice generation status
        voice_status = self.get_voice_generation_status()
        
        # Check if dialog mapping exists
        dialog_mapping_file = os.path.join(self.dialog_dir, "shot_dialog_mapping.json")
        dialog_mapping_exists = os.path.exists(dialog_mapping_file)
        
        # Check if audio files exist
        audio_files = []
        if os.path.exists(self.audio_dir):
            audio_files = [f for f in os.listdir(self.audio_dir) if f.endswith(('.mp3', '.wav'))]
        
        return {
            "voice_generation": voice_status,
            "dialog_mapping_exists": dialog_mapping_exists,
            "audio_files_count": len(audio_files),
            "audio_files": audio_files,
            "ready_for_assembly": voice_status["voices_generated"] and dialog_mapping_exists
        }
    
    def create_narration_voice_config(self) -> Dict[str, Any]:
        """Create configuration for narration voice"""
        # This can be customized based on requirements
        return {
            "voice_id": "narrator_voice",
            "voice_description": "Professional, clear narrator voice for story narration",
            "is_narration": True,
            "language": "en"
        }
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information for video assembly"""
        return {
            "session_path": self.session_path,
            "video_editing_dir": self.video_editing_dir,
            "voice_dir": self.voice_dir,
            "audio_dir": self.audio_dir,
            "dialog_dir": self.dialog_dir,
            "characters_file": self.get_characters_file_path(),
            "script_file": self.get_script_with_descriptions_path()
        }
    
    def get_comprehensive_assembly_status(self) -> Dict[str, Any]:
        """Get comprehensive video assembly status including video assembler status"""
        # Get the existing status from the current method
        voice_status = self.get_voice_generation_status()
        dialog_mapping_file = os.path.join(self.dialog_dir, "shot_dialog_mapping.json")
        dialog_mapping_exists = os.path.exists(dialog_mapping_file)
        
        audio_files = []
        if os.path.exists(self.audio_dir):
            audio_files = [f for f in os.listdir(self.audio_dir) if f.endswith(('.mp3', '.wav'))]
        
        base_status = {
            "voice_generation": voice_status,
            "dialog_mapping_exists": dialog_mapping_exists,
            "audio_files_count": len(audio_files),
            "audio_files": audio_files,
            "ready_for_assembly": voice_status["voices_generated"] and dialog_mapping_exists
        }
        
        # Get video assembly specific status
        assembly_status = self.video_assembler.get_assembly_status()
        
        return {
            **base_status,
            "video_assembly": assembly_status,
            "ready_for_final_assembly": (
                base_status["ready_for_assembly"] and 
                assembly_status["ready_for_assembly"]
            )
        }
    
    def create_preview_video(self, max_scenes: int = 2) -> Dict[str, Any]:
        """Create a preview video with limited scenes"""
        return self.video_assembler.create_assembly_preview(max_scenes)
    
    def assemble_final_video(self, output_filename: Optional[str] = None) -> Dict[str, Any]:
        """Assemble the complete final video"""
        return self.video_assembler.assemble_full_video(output_filename)
    
    def get_assembled_videos(self) -> List[str]:
        """Get list of assembled video files"""
        assembly_status = self.video_assembler.get_assembly_status()
        return assembly_status.get("assembled_videos", [])
    
    def cleanup_assembly_temp_files(self):
        """Clean up temporary files from video assembly"""
        self.video_assembler.cleanup_temp_files()
