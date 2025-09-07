#!/usr/bin/env python3
"""
Voice Design System for Character Voice Generation
Uses ElevenLabs API to design unique voices for each character
"""

import os
import json
import base64
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import requests


load_dotenv()

class VoiceDesigner:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Voice Designer with ElevenLabs API key"""
        self.api_key = api_key or os.getenv('ELEVENLABS_API_KEY')
        if not self.api_key:
            raise ValueError("ElevenLabs API key not found. Please set ELEVENLABS_API_KEY environment variable.")
        
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
    
    def design_voice(self, voice_description: str, model_id: str = "eleven_multilingual_ttv_v2", 
                    text: Optional[str] = None, auto_generate_text: bool = True) -> Dict[str, Any]:
        """Design a voice using ElevenLabs API"""
        url = f"{self.base_url}/text-to-voice/design"
        
        payload = {
            "voice_description": voice_description,
            "model_id": model_id,
            "auto_generate_text": auto_generate_text
        }
        
        if text:
            payload["text"] = text
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            print(f"✅ Voice designed successfully for: {voice_description[:50]}...")
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error designing voice: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return {}
    
    def create_voice_from_preview(self, generated_voice_id: str, voice_name: str, voice_description: str) -> Optional[str]:
        """Create an actual voice from a generated preview"""
        url = f"{self.base_url}/text-to-voice"
        
        payload = {
            "voice_name": voice_name,
            "voice_description": voice_description,
            "generated_voice_id": generated_voice_id
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            actual_voice_id = result.get('voice_id')
            print(f"✅ Created actual voice: {voice_name} -> {actual_voice_id}")
            return actual_voice_id
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error creating voice from preview: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return None
    
    def list_available_voices(self) -> List[Dict[str, Any]]:
        """List all available voices in the account"""
        url = f"{self.base_url}/voices"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            result = response.json()
            voices = result.get('voices', [])
            print(f"✅ Found {len(voices)} voices in account")
            return voices
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error listing voices: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            return []
    
    def download_voice_preview(self, audio_base64: str, character_id: str, output_dir: str) -> Optional[str]:
        """Download and save voice preview audio file"""
        try:
            # Decode base64 audio data
            audio_data = base64.b64decode(audio_base64)
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename
            filename = f"{character_id}_voice_preview.mp3"
            file_path = os.path.join(output_dir, filename)
            
            # Save audio file
            with open(file_path, 'wb') as f:
                f.write(audio_data)
            
            print(f"✅ Downloaded voice preview: {file_path}")
            return file_path
            
        except Exception as e:
            print(f"❌ Error downloading voice preview: {e}")
            return None
    
    def create_character_voice_descriptions(self, characters: List[Dict[str, Any]], output_dir: str = "voice_previews") -> List[Dict[str, Any]]:
        """Create voice descriptions for each character based on their attributes"""
        characters_with_voices = []
        
        # Create output directory for voice previews
        os.makedirs(output_dir, exist_ok=True)
        
        for char in characters:
            # Extract character information
            name = char.get('name', 'Unknown')
            char_id = char.get('id', 'unknown')
            age = char.get('age', 25)
            gender = char.get('gender', 'neutral')
            role = char.get('role', 'supporting')
            voice_info = char.get('voice_information', '')
            overall_desc = char.get('overall_description', '')
            
            # Create detailed voice description
            voice_description = self._create_voice_description(
                name, age, gender, role, voice_info, overall_desc
            )
            
            print(f"\n🎭 Designing voice for {name}...")
            print(f"Description: {voice_description}")
            
            # Design the voice
            voice_result = self.design_voice(voice_description)
            
            if voice_result and 'previews' in voice_result and voice_result['previews']:
                # Get the first preview (best match)
                preview = voice_result['previews'][0]
                generated_voice_id = preview.get('generated_voice_id', '')
                audio_base64 = preview.get('audio_base_64', '')
                
                # Download and save voice preview
                voice_preview_path = None
                if audio_base64:
                    voice_preview_path = self.download_voice_preview(audio_base64, char_id, output_dir)
                
                # Create actual voice from preview
                actual_voice_id = None
                if generated_voice_id:
                    voice_name = f"{name}_voice"
                    actual_voice_id = self.create_voice_from_preview(
                        generated_voice_id, voice_name, voice_description
                    )
                
                # Add voice information to character
                char_with_voice = char.copy()
                char_with_voice.update({
                    'voice_description': voice_description,
                    'generated_voice_id': actual_voice_id or generated_voice_id,  # Use actual voice ID if available
                    'preview_voice_id': generated_voice_id,  # Keep preview ID for reference
                    'voice_preview_path': voice_preview_path,
                    'voice_duration_secs': preview.get('duration_secs', 0),
                    'voice_language': preview.get('language', 'en'),
                    'voice_media_type': preview.get('media_type', 'audio/mpeg'),
                    'voice_name': voice_name if actual_voice_id else None
                })
                
                characters_with_voices.append(char_with_voice)
                if actual_voice_id:
                    print(f"✅ Actual voice created: {actual_voice_id}")
                else:
                    print(f"⚠️ Using preview voice ID: {generated_voice_id}")
                if voice_preview_path:
                    print(f"✅ Voice preview saved: {voice_preview_path}")
            else:
                print(f"❌ Failed to generate voice for {name}")
                # Add character without voice ID
                char_with_voice = char.copy()
                char_with_voice.update({
                    'voice_description': voice_description,
                    'generated_voice_id': None,
                    'voice_preview_path': None,
                    'voice_duration_secs': 0,
                    'voice_language': 'en',
                    'voice_media_type': 'audio/mpeg'
                })
                characters_with_voices.append(char_with_voice)
        
        return characters_with_voices
    
    def _create_voice_description(self, name: str, age: int, gender: str, role: str, 
                                voice_info: str, overall_desc: str) -> str:
        """Create a detailed voice description for the character"""
        
        # Base voice characteristics
        age_group = self._get_age_group(age)
        gender_voice = self._get_gender_voice_characteristics(gender)
        role_voice = self._get_role_voice_characteristics(role)
        
        # Extract personality traits from description
        personality_traits = self._extract_personality_traits(overall_desc)
        
        # Combine voice information
        voice_characteristics = []
        if voice_info:
            voice_characteristics.append(voice_info)
        
        voice_characteristics.extend([
            f"{age_group} voice",
            gender_voice,
            role_voice
        ])
        
        if personality_traits:
            voice_characteristics.extend(personality_traits)
        
        # Create final description
        description = f"A {age}-year-old {gender} named {name} with a {' '.join(voice_characteristics)}. "
        description += f"The voice should reflect their {role} role and personality traits. "
        description += f"Overall character: {overall_desc[:200]}..."
        
        return description
    
    def _get_age_group(self, age: int) -> str:
        """Get age group description"""
        if age < 18:
            return "young, youthful"
        elif age < 30:
            return "young adult"
        elif age < 50:
            return "mature adult"
        else:
            return "older, experienced"
    
    def _get_gender_voice_characteristics(self, gender: str) -> str:
        """Get gender-specific voice characteristics"""
        if gender.lower() == 'male':
            return "masculine, deep tone"
        elif gender.lower() == 'female':
            return "feminine, clear tone"
        else:
            return "neutral, balanced tone"
    
    def _get_role_voice_characteristics(self, role: str) -> str:
        """Get role-specific voice characteristics"""
        role_voices = {
            'main': 'confident, expressive',
            'supporting': 'distinctive, memorable',
            'antagonist': 'commanding, intimidating',
            'protagonist': 'relatable, engaging'
        }
        return role_voices.get(role.lower(), 'distinctive, clear')
    
    def _extract_personality_traits(self, description: str) -> List[str]:
        """Extract personality traits from character description"""
        traits = []
        description_lower = description.lower()
        
        # Common personality traits
        trait_mapping = {
            'confident': ['confident', 'bold', 'assertive'],
            'nervous': ['nervous', 'anxious', 'worried', 'fearful'],
            'authoritative': ['authoritative', 'commanding', 'stern'],
            'friendly': ['friendly', 'warm', 'approachable'],
            'aggressive': ['aggressive', 'intense', 'harsh'],
            'calm': ['calm', 'composed', 'steady'],
            'energetic': ['energetic', 'lively', 'enthusiastic'],
            'serious': ['serious', 'grave', 'solemn']
        }
        
        for trait, keywords in trait_mapping.items():
            if any(keyword in description_lower for keyword in keywords):
                traits.append(trait)
        
        return traits[:3]  # Limit to 3 traits

def load_characters(file_path: str) -> List[Dict[str, Any]]:
    """Load characters from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('characters', [])
    except Exception as e:
        print(f"Error loading characters: {e}")
        return []

def save_characters_with_voices(file_path: str, characters: List[Dict[str, Any]]) -> bool:
    """Save characters with voice information to JSON file"""
    try:
        # Create backup
        backup_path = file_path.replace('.json', '_backup.json')
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            print(f"Created backup: {backup_path}")
        
        # Save updated data
        data = {"characters": characters}
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved characters with voice information to: {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving characters: {e}")
        return False

def main():
    """Main function to generate voices for all characters"""
    
    # Check for API key
    if not os.getenv('ELEVENLABS_API_KEY'):
        print("❌ Please set ELEVENLABS_API_KEY environment variable")
        print("You can get your API key from: https://elevenlabs.io/")
        return
    
    # Initialize voice designer
    try:
        voice_designer = VoiceDesigner()
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    # Find characters file
    characters_file = "story_generation_pipeline/sessions/HIndi Thriller_20250906_215416_ba18db6b/character_generation/characters.json"
    
    if not os.path.exists(characters_file):
        print(f"❌ Characters file not found: {characters_file}")
        return
    
    # Load characters
    print("🎭 Loading characters...")
    characters = load_characters(characters_file)
    
    if not characters:
        print("❌ No characters found")
        return
    
    print(f"📋 Found {len(characters)} characters:")
    for char in characters:
        print(f"  - {char.get('name', 'Unknown')} ({char.get('role', 'unknown')})")
    
    # Generate voices
    print(f"\n🎤 Generating voices for {len(characters)} characters...")
    voice_output_dir = "story_generation_pipeline/sessions/HIndi Thriller_20250906_215416_ba18db6b/character_generation/voice_previews"
    characters_with_voices = voice_designer.create_character_voice_descriptions(characters, voice_output_dir)
    
    # Save updated characters
    if save_characters_with_voices(characters_file, characters_with_voices):
        print(f"\n✅ Successfully generated voices for all characters!")
        print(f"📁 Updated file: {characters_file}")
        
        # Display summary
        print(f"\n📊 Voice Generation Summary:")
        successful = sum(1 for char in characters_with_voices if char.get('generated_voice_id'))
        print(f"  - Successfully generated: {successful}/{len(characters_with_voices)}")
        print(f"  - Failed: {len(characters_with_voices) - successful}/{len(characters_with_voices)}")
        
        # Show voice IDs and preview paths
        print(f"\n🎵 Generated Voice Information:")
        for char in characters_with_voices:
            voice_id = char.get('generated_voice_id')
            voice_preview_path = char.get('voice_preview_path')
            if voice_id:
                print(f"  - {char.get('name', 'Unknown')}:")
                print(f"    Voice ID: {voice_id}")
                if voice_preview_path:
                    print(f"    Preview: {voice_preview_path}")
                else:
                    print(f"    Preview: ❌ Not downloaded")
            else:
                print(f"  - {char.get('name', 'Unknown')}: ❌ Failed to generate")
    else:
        print("❌ Failed to save characters with voice information")

if __name__ == "__main__":
    main()
