#!/usr/bin/env python3
"""
Voice Validator - Validates and fixes voice IDs for ElevenLabs TTS
"""

import os
import json
import requests
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()

class VoiceValidator:
    """Validates and fixes voice IDs for TTS usage"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ELEVENLABS_API_KEY')
        if not self.api_key:
            raise ValueError("ElevenLabs API key not found. Please set ELEVENLABS_API_KEY environment variable.")
        
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get all available voices in the account"""
        url = f"{self.base_url}/voices"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            result = response.json()
            voices = result.get('voices', [])
            return voices
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error getting voices: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return []
    
    def validate_voice_id(self, voice_id: str) -> bool:
        """Check if a voice ID is valid and usable"""
        url = f"{self.base_url}/voices/{voice_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return True
            
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 404:
                    return False
            print(f"❌ Error validating voice {voice_id}: {e}")
            return False
    
    def validate_character_voices(self, characters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate all character voice IDs and provide report"""
        
        print("🔍 Validating character voice IDs...")
        
        available_voices = self.get_available_voices()
        available_voice_ids = {voice['voice_id']: voice for voice in available_voices}
        
        validation_report = {
            "total_characters": len(characters),
            "valid_voices": 0,
            "invalid_voices": 0,
            "missing_voices": 0,
            "character_status": [],
            "available_voices": available_voices
        }
        
        for char in characters:
            name = char.get('name', 'Unknown')
            voice_id = char.get('generated_voice_id')
            
            status = {
                "character_name": name,
                "character_id": char.get('id', 'unknown'),
                "voice_id": voice_id,
                "status": "unknown",
                "message": ""
            }
            
            if not voice_id:
                status["status"] = "missing"
                status["message"] = "No voice ID assigned"
                validation_report["missing_voices"] += 1
            elif voice_id in available_voice_ids:
                status["status"] = "valid"
                status["message"] = f"Voice found: {available_voice_ids[voice_id]['name']}"
                validation_report["valid_voices"] += 1
            else:
                status["status"] = "invalid"
                status["message"] = "Voice ID not found in account"
                validation_report["invalid_voices"] += 1
            
            validation_report["character_status"].append(status)
        
        return validation_report
    
    def suggest_voice_fixes(self, characters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Suggest voice fixes for characters with invalid voices"""
        
        validation_report = self.validate_character_voices(characters)
        available_voices = validation_report["available_voices"]
        
        suggestions = []
        
        for char_status in validation_report["character_status"]:
            if char_status["status"] in ["invalid", "missing"]:
                char_name = char_status["character_name"]
                
                # Find best matching voice from available voices
                best_match = self._find_best_voice_match(char_name, available_voices)
                
                suggestion = {
                    "character_name": char_name,
                    "character_id": char_status["character_id"],
                    "current_voice_id": char_status["voice_id"],
                    "suggested_voice_id": best_match["voice_id"] if best_match else None,
                    "suggested_voice_name": best_match["name"] if best_match else None,
                    "reason": f"Best match from available voices" if best_match else "No suitable match found"
                }
                
                suggestions.append(suggestion)
        
        return suggestions
    
    def _find_best_voice_match(self, character_name: str, available_voices: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find the best matching voice for a character"""
        
        if not available_voices:
            return None
        
        # Simple matching logic - can be enhanced
        character_lower = character_name.lower()
        
        # Look for exact name matches first
        for voice in available_voices:
            if character_lower in voice['name'].lower() or voice['name'].lower() in character_lower:
                return voice
        
        # Return first available voice as fallback
        return available_voices[0]
    
    def fix_character_voices(self, characters_file: str, apply_fixes: bool = False) -> bool:
        """Fix character voices by updating the characters file"""
        
        try:
            # Load characters
            with open(characters_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            characters = data.get('characters', [])
            
            # Get validation report and suggestions
            validation_report = self.validate_character_voices(characters)
            suggestions = self.suggest_voice_fixes(characters)
            
            print(f"\n📊 Validation Report:")
            print(f"   Total characters: {validation_report['total_characters']}")
            print(f"   Valid voices: {validation_report['valid_voices']}")
            print(f"   Invalid voices: {validation_report['invalid_voices']}")
            print(f"   Missing voices: {validation_report['missing_voices']}")
            
            if suggestions:
                print(f"\n💡 Voice Fix Suggestions:")
                for suggestion in suggestions:
                    print(f"   - {suggestion['character_name']}: {suggestion['suggested_voice_name']} ({suggestion['suggested_voice_id']})")
                
                if apply_fixes:
                    # Apply the fixes
                    for char in characters:
                        for suggestion in suggestions:
                            if char.get('id') == suggestion['character_id'] and suggestion['suggested_voice_id']:
                                char['generated_voice_id'] = suggestion['suggested_voice_id']
                                char['voice_fix_applied'] = True
                                char['original_voice_id'] = suggestion['current_voice_id']
                    
                    # Save the updated file
                    with open(characters_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    print(f"✅ Applied voice fixes to {characters_file}")
                    return True
            else:
                print("✅ No voice fixes needed")
                return True
                
        except Exception as e:
            print(f"❌ Error fixing character voices: {e}")
            return False
        
        return False
    
    def print_available_voices(self):
        """Print all available voices in a readable format"""
        voices = self.get_available_voices()
        
        if voices:
            print(f"\n🎤 Available Voices ({len(voices)} total):")
            print("-" * 60)
            for voice in voices:
                print(f"Name: {voice['name']}")
                print(f"ID: {voice['voice_id']}")
                print(f"Category: {voice.get('category', 'N/A')}")
                print(f"Description: {voice.get('description', 'N/A')[:100]}...")
                print("-" * 60)
        else:
            print("❌ No voices found in account")
