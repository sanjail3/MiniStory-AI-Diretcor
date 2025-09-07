
from openai import OpenAI
import base64
import os
from typing import Optional, Dict
from pydantic import BaseModel, Field
from PIL import Image
import google.generativeai as genai
import google.genai.types as types
from io import BytesIO

import io
from typing import List
import datetime
import PIL.Image as PILImage
import os
import tempfile

from dotenv import load_dotenv

load_dotenv()


class FullCharacter(BaseModel):
    name: str
    id: str
    age: Optional[int] = None
    role: Optional[str] = None
    voice_information: Optional[str] = None
    gender: Optional[str] = None
    overall_description: Optional[str] = None
    image_path: Optional[str] = None


class CharacterGenerator:
    def __init__(self, output_dir: str = "character_images"):
        # Configure Google Generative AI
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.client = genai
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def create_front_facing_prompt(self, character: dict) -> str:
        # Extract character traits
        name = character.get('name', 'Character')
        age = character.get('age', 25)
        gender = character.get('gender', 'person')
        role = character.get('role', 'character')
        
        # Create a safe, persona-based description
        safe_description = self._create_safe_description(character.get('overall_description', ''))
        
        # Generate persona-based outfit
        # outfit_description = self._generate_persona_outfit(character)
        
        base_prompt = f"""
        Create a realistic portrait photograph of a {age}-year-old {gender} named {name}.
        
        Character Details:
        - Age: {age} years old
        - Gender: {gender}
        - Role: {role}
        - Personality: {safe_description}
        
        Outfit & Appearance:
        Based on the personality and role of the character, create a outfit and appearance that is authentic to their role and personality in more detailed way.

        IMPORTANT REQUIREMENTS:
        Always create character in indian style
        
        Photography Style:
        - Realistic portrait style
        - Front-facing, looking directly at camera
        - Natural, authentic appearance
        - Soft, natural lighting
        - Neutral background (white or light gray)
        - High resolution, detailed
        - Expression that matches personality: {safe_description}
        
        Focus on creating a character that looks authentic to their role and personality, not generic or overly professional.
        """
        return base_prompt.strip()
    
    def _create_safe_description(self, description: str) -> str:
        """Create a safe description by removing potentially problematic content"""
        if not description:
            return "friendly and professional"
        
        # Remove crime/violence related words
        problematic_words = [
            'crime', 'murder', 'kill', 'death', 'violence', 'gun', 'weapon', 
            'interrogation', 'police', 'detective', 'suspect', 'guilt', 'fear',
            'betrayal', 'reckless', 'aggressive', 'tough', 'commanding'
        ]
        
        safe_desc = description.lower()
        for word in problematic_words:
            safe_desc = safe_desc.replace(word, '')
        
        # Clean up and create a positive description
        safe_desc = safe_desc.strip()
        if not safe_desc or len(safe_desc) < 10:
            return "friendly and professional"
        
        # Add positive traits
        positive_traits = ["confident", "friendly", "professional", "approachable"]
        return f"{safe_desc[:100]}, {', '.join(positive_traits[:2])}"
    
    
    
   
    
    def generate_image(self, prompt: str, image_type: str, character_id: str) -> Optional[str]:
        try:
            print(f"Generating {image_type} image for {character_id} using Gemini...")
            
            # Use the correct Google Generative AI API with image generation
            model = genai.GenerativeModel('gemini-2.5-flash-image-preview')
            
            # Configure the model to generate images
            response =model.generate_content(prompt
 
            # contents=prompt,
            # config=types.GenerateContentConfig(
            #     response_modalities=['Text', 'Image']
            # )
)
            
            image_saved = False
            filename = f"{character_id}_{image_type}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            # Check if response has images
            if hasattr(response, 'parts') and response.parts:
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_data = part.inline_data.data
                        image = Image.open(BytesIO(image_data))
                        image.save(filepath)
                        image_saved = True
                        print(f" Saved {image_type} image: {filepath}")
                        break
                    elif hasattr(part, 'text') and part.text:
                        print(f"Gemini response: {part.text[:100]}...")
            
            if not image_saved:
                print(f" No image data generated for {character_id} {image_type}")
                return None
                
            return filepath
            
        except Exception as e:
            print(f" Error generating {image_type} image for {character_id}: {str(e)}")
            return None

    
    

    def generate_character_images(self, character: FullCharacter) -> FullCharacter:
        character_id = character.id
        print(f"\nGenerating image for {character.name} ({character_id})")

        character_dict = character.model_dump()

        # Generate character image
        character_prompt = self.create_front_facing_prompt(character_dict)
        print(f"Character prompt: {character_prompt[:100]}...")
        character_image_path = self.generate_image(character_prompt, "character", character_id)

        if not character_image_path:
            print(f"Trying simpler prompt for {character.name}...")
            simple_prompt = f"Professional portrait of a {character.age}-year-old {character.gender} named {character.name}, friendly expression, neutral background"
            character_image_path = self.generate_image(simple_prompt, "character", character_id)
        
        if not character_image_path:
            print(f"Creating placeholder for {character.name}...")
            character_image_path = self.create_placeholder_image(character_id, character.name)

        # Update character with image path
        character_dict['image_path'] = character_image_path
        character_with_images = FullCharacter(**character_dict)

        return character_with_images

    def create_placeholder_image(self, character_id: str, character_name: str) -> str:
        """Create a placeholder image when AI generation fails"""
        try:
            # Create a simple placeholder image
            filename = f"{character_id}_character.png"
            filepath = os.path.join(self.output_dir, filename)
            
            # Create a simple colored rectangle as placeholder
            img = Image.new('RGB', (400, 400), color='lightgray')
            
            # Add text (if PIL supports it)
            try:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(img)
                
                # Try to use a default font
                try:
                    font = ImageFont.truetype("arial.ttf", 20)
                except:
                    font = ImageFont.load_default()
                
                # Add character name
                text = f"{character_name}\n(Placeholder)"
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                x = (400 - text_width) // 2
                y = (400 - text_height) // 2
                
                draw.text((x, y), text, fill='black', font=font)
            except:
                # If text fails, just save the colored rectangle
                pass
            
            img.save(filepath)
            print(f" Created placeholder image: {filepath}")
            return filepath
            
        except Exception as e:
            print(f" Error creating placeholder: {str(e)}")
            return None

    def generate_images_for_all_characters(self, characters: List[FullCharacter]) -> List[FullCharacter]:
        characters_with_images = []

        print(f"Starting image generation for {len(characters)} characters...")

        for i, character in enumerate(characters, 1):
            print(f"\n--- Character {i}/{len(characters)} ---")
            character_with_images = self.generate_character_images(character)
            characters_with_images.append(character_with_images)

        print(f"\nImage generation complete for all characters!")
        return characters_with_images

    
    
    
    def save_characters_with_images(self, characters: list[FullCharacter], filename: str):
       
        import json
        
        characters_dict = {
            "characters": [char.model_dump() for char in characters]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(characters_dict, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Characters with image paths saved to {filename}")





# example_characters = [
#     FullCharacter(
#         name="Arya",
#         id="char_001",
#         age=21,
#         role="Detective",
#         gender="Female",
#         overall_description="Smart, sharp-eyed and emotionally resilient young detective.",
#         voice_information="Soft but firm voice with a calm tone.",
#     ),
# ]

