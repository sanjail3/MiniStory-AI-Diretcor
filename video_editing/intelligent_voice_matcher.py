#!/usr/bin/env python3
"""
Intelligent Voice Matcher - Uses LLM to match characters with appropriate voices
"""

import os
import json
from typing import Dict, List, Any, Optional
from utils.llm import get_llm_model
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import requests

load_dotenv()

class VoiceAssignment(BaseModel):
    """Voice assignment for a character"""
    character_id: str = Field(..., description="Character ID")
    character_name: str = Field(..., description="Character name")
    assigned_voice_id: str = Field(..., description="Assigned voice ID")
    assigned_voice_name: str = Field(..., description="Assigned voice name")
    reasoning: str = Field(..., description="Reasoning for the voice assignment")
    confidence_score: float = Field(..., description="Confidence score (0-1) for the assignment")

class VoiceMatchingResult(BaseModel):
    """Result of voice matching for all characters"""
    assignments: List[VoiceAssignment] = Field(..., description="List of voice assignments")
    total_characters: int = Field(..., description="Total number of characters")
    successful_assignments: int = Field(..., description="Number of successful assignments")

class IntelligentVoiceMatcher:
    """Uses LLM to intelligently match characters with appropriate voices"""
    
    def __init__(self):
        self.llm = get_llm_model("gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
        
        # ElevenLabs API setup
        self.elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
        if not self.elevenlabs_api_key:
            raise ValueError("ElevenLabs API key not found. Please set ELEVENLABS_API_KEY environment variable.")
        
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "xi-api-key": self.elevenlabs_api_key,
            "Content-Type": "application/json"
        }
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get all available voices from ElevenLabs"""
        url = f"{self.base_url}/voices"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            result = response.json()
            voices = result.get('voices', [])
            print(f"✅ Retrieved {len(voices)} available voices")
            return voices
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error getting voices: {e}")
            return []
    
    def create_voice_matching_system_prompt(self) -> str:
        """Create system prompt for voice matching"""
        return """You are a professional voice casting director with expertise in matching character personalities with appropriate voice types.

Your task is to analyze character descriptions and assign the most suitable voice from available options.

ASSIGNMENT CRITERIA:
1. Age appropriateness (young adult, middle-aged, elderly)
2. Gender matching (male/female characters with corresponding voices)
3. Personality traits (confident, nervous, authoritative, friendly, etc.)
4. Role in story (protagonist, antagonist, supporting character)
5. Character background and profession
6. Voice quality that matches character's persona

IMPORTANT GUIDELINES:
- Match gender appropriately (male characters with male voices, female with female)
- Consider age groups (young characters with younger-sounding voices)
- Match personality traits (confident characters with strong voices, nervous with softer voices)
- Avoid assigning the same voice to multiple main characters
- Prioritize voice quality and suitability over availability
- Provide clear reasoning for each assignment
- Give confidence scores based on how well the voice matches

For each character, provide:
- character_id: The character's ID
- character_name: The character's name
- assigned_voice_id: The best matching voice ID
- assigned_voice_name: The name of the assigned voice
- reasoning: Clear explanation for why this voice fits the character
- confidence_score: Score from 0.0 to 1.0 indicating assignment confidence

Return assignments for ALL characters provided."""

    def create_character_context(self, characters: List[Dict[str, Any]]) -> str:
        """Create detailed context about characters"""
        context = "CHARACTERS TO ASSIGN VOICES:\n\n"
        
        for i, char in enumerate(characters, 1):
            context += f"{i}. CHARACTER: {char.get('name', 'Unknown')}\n"
            context += f"   ID: {char.get('id', 'unknown')}\n"
            context += f"   Age: {char.get('age', 'Unknown')}\n"
            context += f"   Gender: {char.get('gender', 'Unknown')}\n"
            context += f"   Role: {char.get('role', 'Unknown')}\n"
            context += f"   Description: {char.get('overall_description', 'No description')}\n"
            
            # Add voice information if available
            voice_info = char.get('voice_information', '')
            if voice_info:
                context += f"   Voice Notes: {voice_info}\n"
            
            # Add personality traits
            personality = char.get('personality_traits', [])
            if personality:
                context += f"   Personality: {', '.join(personality)}\n"
            
            context += "\n"
        
        return context
    
    def create_voices_context(self, voices: List[Dict[str, Any]]) -> str:
        """Create context about available voices"""
        context = "AVAILABLE VOICES:\n\n"
        
        for i, voice in enumerate(voices, 1):
            context += f"{i}. VOICE: {voice.get('name', 'Unknown')}\n"
            context += f"   ID: {voice.get('voice_id', 'unknown')}\n"
            context += f"   Category: {voice.get('category', 'Unknown')}\n"
            context += f"   Description: {voice.get('description', 'No description')}\n"
            
            # Add gender info if available in labels
            labels = voice.get('labels', {})
            if labels:
                gender = labels.get('gender')
                age = labels.get('age')
                accent = labels.get('accent')
                
                if gender:
                    context += f"   Gender: {gender}\n"
                if age:
                    context += f"   Age: {age}\n"
                if accent:
                    context += f"   Accent: {accent}\n"
            
            context += "\n"
        
        return context
    
    def match_voices_to_characters(self, characters: List[Dict[str, Any]], 
                                 voices: List[Dict[str, Any]]) -> Optional[VoiceMatchingResult]:
        """Use LLM to match voices to characters"""
        
        print(f"🎭 Matching {len(characters)} characters with {len(voices)} available voices...")
        
        # Create contexts
        character_context = self.create_character_context(characters)
        voices_context = self.create_voices_context(voices)
        
        full_context = character_context + "\n" + voices_context
        
        messages = [
            {"role": "system", "content": self.create_voice_matching_system_prompt()},
            {"role": "user", "content": f"Match voices to characters based on their descriptions:\n\n{full_context}"}
        ]
        
        try:
            # Use structured output
            structured_llm = self.llm.with_structured_output(VoiceMatchingResult, method="function_calling")
            result = structured_llm.invoke(messages)
            
            print(f"✅ Generated voice assignments for {result.successful_assignments}/{result.total_characters} characters")
            return result
            
        except Exception as e:
            print(f"❌ Error matching voices to characters: {e}")
            return None
    
    def apply_voice_assignments(self, characters: List[Dict[str, Any]], 
                              assignments: List[VoiceAssignment]) -> List[Dict[str, Any]]:
        """Apply voice assignments to character data"""
        
        print("🔄 Applying voice assignments to characters...")
        
        # Create assignment lookup
        assignment_lookup = {assignment.character_id: assignment for assignment in assignments}
        
        updated_characters = []
        
        for char in characters:
            char_id = char.get('id', 'unknown')
            char_copy = char.copy()
            
            if char_id in assignment_lookup:
                assignment = assignment_lookup[char_id]
                
                # Update voice information
                char_copy.update({
                    'generated_voice_id': assignment.assigned_voice_id,
                    'assigned_voice_name': assignment.assigned_voice_name,
                    'voice_assignment_reasoning': assignment.reasoning,
                    'voice_assignment_confidence': assignment.confidence_score,
                    'voice_assignment_method': 'llm_intelligent_matching',
                    'voice_assignment_timestamp': 'auto_assigned'
                })
                
                print(f"✅ {char.get('name', 'Unknown')}: {assignment.assigned_voice_name} (confidence: {assignment.confidence_score:.2f})")
            else:
                print(f"⚠️ No assignment found for {char.get('name', 'Unknown')}")
            
            updated_characters.append(char_copy)
        
        return updated_characters
    
    def save_updated_characters(self, characters_file: str, updated_characters: List[Dict[str, Any]]) -> bool:
        """Save updated characters with new voice assignments"""
        try:
            # Create backup
            backup_file = characters_file.replace('.json', '_backup_voice_assignment.json')
            if os.path.exists(characters_file):
                with open(characters_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, ensure_ascii=False)
                print(f"📋 Created backup: {backup_file}")
            
            # Save updated data
            data = {"characters": updated_characters}
            with open(characters_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Saved updated characters to: {characters_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving characters: {e}")
            return False
    
    def intelligent_voice_assignment(self, characters_file: str) -> bool:
        """Complete intelligent voice assignment workflow"""
        
        print("🎭 Starting intelligent voice assignment...")
        
        try:
            # Load characters
            with open(characters_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            characters = data.get('characters', [])
            if not characters:
                print("❌ No characters found")
                return False
            
            # Get available voices
            voices = self.get_available_voices()
            if not voices:
                print("❌ No voices available")
                return False
            
            # Match voices to characters
            matching_result = self.match_voices_to_characters(characters, voices)
            if not matching_result:
                print("❌ Voice matching failed")
                return False
            
            # Apply assignments
            updated_characters = self.apply_voice_assignments(characters, matching_result.assignments)
            
            # Save updated characters
            success = self.save_updated_characters(characters_file, updated_characters)
            
            if success:
                print(f"🎉 Intelligent voice assignment completed!")
                print(f"   📊 Successfully assigned voices to {matching_result.successful_assignments}/{matching_result.total_characters} characters")
                
                # Display assignments
                print(f"\n🎤 Voice Assignments:")
                for assignment in matching_result.assignments:
                    print(f"   - {assignment.character_name}: {assignment.assigned_voice_name}")
                    print(f"     Reasoning: {assignment.reasoning}")
                    print(f"     Confidence: {assignment.confidence_score:.2f}")
                    print()
            
            return success
            
        except Exception as e:
            print(f"❌ Error in intelligent voice assignment: {e}")
            return False
    
    def get_voice_assignment_summary(self, characters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary of voice assignments"""
        summary = {
            "total_characters": len(characters),
            "characters_with_voices": 0,
            "llm_assigned_voices": 0,
            "manual_assigned_voices": 0,
            "unassigned_characters": 0,
            "assignments": []
        }
        
        for char in characters:
            name = char.get('name', 'Unknown')
            voice_id = char.get('generated_voice_id')
            voice_name = char.get('assigned_voice_name', 'Unknown')
            assignment_method = char.get('voice_assignment_method', 'unknown')
            confidence = char.get('voice_assignment_confidence', 0.0)
            
            assignment_info = {
                "character_name": name,
                "voice_id": voice_id,
                "voice_name": voice_name,
                "assignment_method": assignment_method,
                "confidence": confidence
            }
            
            if voice_id:
                summary["characters_with_voices"] += 1
                if assignment_method == 'llm_intelligent_matching':
                    summary["llm_assigned_voices"] += 1
                else:
                    summary["manual_assigned_voices"] += 1
            else:
                summary["unassigned_characters"] += 1
            
            summary["assignments"].append(assignment_info)
        
        return summary
