#!/usr/bin/env python3
"""
Location Generation System
Generates detailed location information and images for scenes
"""

import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import io

load_dotenv()

class LocationInfo(BaseModel):
    """Pydantic model for location information"""
    location_id: str = Field(..., description="Unique identifier for the location")
    name: str = Field(..., description="Name of the location")
    location_type: str = Field(..., description="Type of location (interior/exterior)")
    environment: str = Field(..., description="Environment description")
    time_of_day: str = Field(..., description="Time of day (Day/Night/Dawn/Dusk)")
    lighting: str = Field(..., description="Lighting conditions")
    atmosphere: str = Field(..., description="Atmospheric conditions")
    background_sfx: List[str] = Field(default=[], description="Background sound effects")
    set_details: str = Field(..., description="Detailed set description")
    mood: str = Field(..., description="Mood/tone of the location")
    image_path: Optional[str] = Field(None, description="Path to location image")
    location_image_prompt: Optional[str] = Field(None, description="Location image prompt")

class LocationGenerator:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Location Generator with Google Gemini API key"""
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini API key not found. Please set GEMINI_API_KEY environment variable.")
        
        genai.configure(api_key=self.api_key)
    
    def extract_locations_from_scenes(self, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract unique locations from scenes"""
        locations = []
        location_map = {}
        
        for scene in scenes:
            scene_info = scene.get('scene_info', {})
            location = scene_info.get('Location', '')
            location_id = scene_info.get('Scene_ID', '').replace('SC_', 'LOC_')
            
            if location and location_id not in location_map:
                # Extract location details
                location_parts = location.split(' - ')
                location_type = location_parts[0] if location_parts else 'UNKNOWN'
                time_of_day = location_parts[1] if len(location_parts) > 1 else 'UNKNOWN'
                
                # Get set info
                set_info = scene_info.get('Set_Info', {})
                
                location_data = {
                    'location_id': location_id,
                    'name': self._extract_location_name(location),
                    'location_type': location_type,
                    'environment': set_info.get('environment', ''),
                    'time_of_day': time_of_day,
                    'lighting': set_info.get('lighting', ''),
                    'atmosphere': scene_info.get('Scene_Tone', ''),
                    'background_sfx': set_info.get('background_sfx', []),
                    'set_details': self._create_set_details(scene_info),
                    'mood': scene_info.get('Scene_Tone', 'neutral')
                }
                
                locations.append(location_data)
                location_map[location_id] = location_data
        
        return locations
    
    def _extract_location_name(self, location: str) -> str:
        """Extract clean location name from location string"""
        # Remove EXT./INT. and time information
        parts = location.split(' - ')
        if parts:
            name = parts[0].replace('EXT. ', '').replace('INT. ', '').strip()
            return name
        return location
    
    def _create_set_details(self, scene_info: Dict[str, Any]) -> str:
        """Create detailed set description from scene info"""
        set_info = scene_info.get('Set_Info', {})
        plot = scene_info.get('Plot', {})
        
        details = []
        
        if set_info.get('environment'):
            details.append(f"Environment: {set_info['environment']}")
        
        if set_info.get('lighting'):
            details.append(f"Lighting: {set_info['lighting']}")
        
        if plot.get('summary'):
            details.append(f"Context: {plot['summary'][:100]}...")
        
        return " | ".join(details)
    
    def create_location_image_prompt(self, location: Dict[str, Any]) -> str:
        """Create detailed Indian-style prompt for location image generation"""
        name = location.get('name', 'Unknown Location')
        location_type = location.get('location_type', '')
        environment = location.get('environment', '')
        time_of_day = location.get('time_of_day', 'Day')
        lighting = location.get('lighting', '')
        mood = location.get('mood', 'neutral')
        atmosphere = location.get('atmosphere', '')
        set_details = location.get('set_details', '')
        
        # Create safe description to avoid content policy issues
        safe_environment = self._create_safe_description(environment)
        safe_set_details = self._create_safe_description(set_details)
        
        
        
        # Create web series context-specific prompt
        web_series_context = self._get_web_series_context(location_type, name, safe_environment)
        
        base_prompt = f"""
        Create a highly detailed, cinematic photograph of {name} for an Indian web series/thriller production.
        
        LOCATION SPECIFICATIONS:
        - Type: {location_type}
        - Environment: {safe_environment}
        - Time of Day: {time_of_day}
        - Lighting Conditions: {lighting}
        - Atmospheric Mood: {mood} {atmosphere}
        - Architectural Details: {safe_set_details}
        
        WEB SERIES PRODUCTION CONTEXT:
        {web_series_context}
        
        DETAILED VISUAL COMPOSITION:
        - Camera Angle: Medium-wide establishing shot to show complete location layout
        - Depth of Field: Deep focus showing foreground, middle ground, and background elements
        - Framing: Rule of thirds with key architectural elements positioned strategically
        - Perspective: Showcase the scale and authentic modern Indian architectural details
        - Object Placement: Clearly show where all furniture and objects are positioned for scene planning
        
        LIGHTING & ATMOSPHERE:
        - Natural lighting appropriate for {time_of_day.lower()} in Indian climate
        - Warm, golden tones if daytime; cool blues and warm artificial lights if night
        - Shadows and highlights that emphasize texture and depth
        - Atmospheric elements like dust particles, heat haze, or monsoon moisture as appropriate
        
        INDIAN WEB SERIES STYLING:
        - Contemporary modern Indian architecture with authentic local materials
        - Government/institutional buildings: cream/white walls, green accents, Indian flags
        - Educational institutions: red brick, concrete, traditional college architecture
        - Residential/commercial: modern Indian urban design with local characteristics
        - All locations should feel like authentic Indian settings suitable for thriller/drama web series
        - Include weathering and age appropriate to Indian climate and urban environment
        
        TECHNICAL REQUIREMENTS:
        - NO PEOPLE visible in the frame - focus purely on the location
        - Professional cinematography quality suitable for web series production
        - High resolution with sharp details
        - Authentic modern Indian aesthetic without stereotypes
        - Clean, well-composed shot suitable for film production reference
        - Show complete location layout with all objects and furniture clearly positioned
        
        SAFETY GUIDELINES FOR CONTENT FILTERS:
        - Focus on architectural and environmental elements only
        - Avoid any references to violence, weapons, or explicit content
        - Present locations as neutral, professional spaces
        - Emphasize the setting and atmosphere rather than any dramatic elements
        
        Create a location that feels authentically modern Indian, cinematically professional, and completely empty of people.
        """
        
        return base_prompt.strip()
    
    def _get_web_series_context(self, location_type: str, name: str, environment: str) -> str:
        """Generate web series specific context for different location types"""
        location_lower = (location_type + " " + name + " " + environment).lower()
        
        if 'college' in location_lower or 'university' in location_lower or 'campus' in location_lower:
            return """
This is a modern Indian college/university setting for a thriller/drama web series.
- Contemporary Indian educational architecture with mix of colonial and modern buildings
- Red brick or concrete buildings with large courtyards and verandas
- Modern amenities: Wi-Fi zones, computer labs, modern classrooms
- Indian college atmosphere: notice boards, institutional signage in Hindi/English
- Student-friendly spaces: canteens, libraries, sports facilities
- Lush green campus with native Indian trees (neem, banyan, gulmohar)
- Modern security features: CCTV cameras, guard posts, gates
            """.strip()
        
        elif 'police' in location_lower or 'station' in location_lower or 'interrogation' in location_lower:
            return """
This is a modern Indian police station/government building for a thriller/drama web series.
- Contemporary government architecture with Indian institutional characteristics
- Professional, clean environment suitable for official proceedings
- Modern facilities: computers, filing systems, communication equipment
- Indian government aesthetics: flags, emblems, official notices
- Functional furniture: metal desks, plastic chairs, filing cabinets
- Proper lighting: fluorescent tubes, windows with security grilles
- Climate-appropriate design: ceiling fans, ventilation, concrete floors
- Neutral, professional atmosphere suitable for investigative scenes
            """.strip()
        
        elif 'ground' in location_lower or 'field' in location_lower or 'sports' in location_lower:
            return """
This is a modern Indian sports ground/field for a web series.
- Well-maintained sports facility with proper infrastructure
- Modern amenities: floodlights, scoreboard, seating areas
- Indian sports ground characteristics: red soil/grass field, boundary walls
- Professional equipment: goal posts, nets, sports storage areas
- Spectator facilities: covered seating, basic amenities
- Landscaped surroundings with native Indian trees and plants
- Modern safety features: proper fencing, emergency access
- Suitable for youth-oriented sports and recreational scenes
            """.strip()
        
        elif 'room' in location_lower or 'office' in location_lower or 'interior' in location_lower:
            return """
This is a modern Indian interior space for a web series.
- Contemporary Indian interior design with functional aesthetics
- Modern furniture: ergonomic chairs, study tables, storage units
- Indian home/office characteristics: ceiling fans, tube lights, concrete floors
- Climate-appropriate features: good ventilation, practical layouts
- Modern amenities: electrical fittings, internet connectivity
- Cultural elements: subtle Indian decorative touches without stereotypes
- Professional/residential atmosphere suitable for character development scenes
- Clean, organized space that reflects modern Indian lifestyle
            """.strip()
        
        elif any(word in location_lower for word in ['street', 'road', 'outdoor', 'external', 'ext']):
            return """
This is a modern Indian outdoor/street location for a web series.
- Contemporary Indian urban environment with authentic local characteristics
- Modern infrastructure: paved roads, street lighting, signage
- Indian urban elements: mixed architecture, local businesses, transport
- Clean, well-maintained public spaces suitable for filming
- Modern amenities: proper drainage, telecommunications, utilities
- Authentic but presentable Indian street aesthetics
- Suitable for outdoor scenes, establishing shots, character interactions
- Professional appearance appropriate for web series production standards
            """.strip()
        
        else:
            return """
This is a modern Indian location for a contemporary web series production.
- Authentic Indian setting with modern, professional appearance
- Contemporary architecture and design suitable for current storytelling
- Clean, well-maintained environment appropriate for filming
- Modern amenities and infrastructure reflecting current Indian urban/suburban life
- Professional aesthetic suitable for thriller/drama web series
- Authentic local characteristics without outdated stereotypes
- Suitable for character-driven scenes and plot development
            """.strip()
    
    
    
    def _create_safe_description(self, description: str) -> str:
        """Create a safe description that won't trigger content filters"""
        if not description:
            return "professional environment"
        
        # Enhanced keyword filtering for crime scene and sensitive content
        problematic_keywords = {
            'violence': 'activity',
            'gun': 'equipment',
            'weapon': 'tools',
            'blood': 'materials',
            'death': 'situation',
            'murder': 'investigation',
            'crime': 'investigation',
            'body': 'covered area',
            'corpse': 'covered area',
            'dead': 'inactive',
            'killed': 'affected',
            'shot': 'marked',
            'stabbed': 'marked',
            'injured': 'affected',
            'wound': 'marking',
            'victim': 'person',
            'suspect': 'person',
            'criminal': 'individual',
            'police': 'official',
            'investigation': 'examination',
            'evidence': 'materials',
            'forensic': 'technical'
        }
        
        safe_description = description.lower()
        for problematic, safe_replacement in problematic_keywords.items():
            safe_description = safe_description.replace(problematic, safe_replacement)
        
        # Special handling for crime scene descriptions
        if 'covered' in safe_description and 'sheet' in safe_description:
            safe_description = "outdoor area with covered materials and official examination activity"
        
        # Clean up any remaining problematic phrases
        if 'disfigured' in safe_description:
            safe_description = safe_description.replace('disfigured', 'covered')
        
        return safe_description
    
    def generate_image(self, prompt: str, image_type: str, location_id: str, session_path: str = None) -> Optional[str]:
        """Generate image using Google Gemini"""
        try:
            model = genai.GenerativeModel('gemini-2.5-flash-image-preview')
            
            response = model.generate_content(prompt)

            # Initialize image_saved variable
            image_saved = False
            
            if session_path:
                images_dir = os.path.join(session_path, "location_generation", "images")
            else:
                images_dir = "story_generation_pipeline/sessions/HIndi Thriller_20250906_215416_ba18db6b/location_generation/images"
            os.makedirs(images_dir, exist_ok=True)
                        
            # Save image
            filename = f"{location_id}_{image_type}.png"
            image_path = os.path.join(images_dir, filename)

            if hasattr(response, 'parts') and response.parts:
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_data = part.inline_data.data
                        
                        image = Image.open(io.BytesIO(image_data))
                        image.save(image_path)
                        image_saved = True
                        print(f" Saved {image_type} image: {image_path}")
                        break
                    elif hasattr(part, 'text') and part.text:
                        print(f"Gemini response: {part.text[:100]}...")
            
            if not image_saved:
                print(f" No image data generated for {location_id} {image_type}")
                return None
            return image_path
            
                
        except Exception as e:
            print(f"❌ Error generating {image_type} image: {e}")
            return None
    
    def create_placeholder_image(self, location: Dict[str, Any], image_type: str, session_path: str = None) -> str:
        """Create a placeholder image when AI generation fails"""
        try:
            # Create images directory
            if session_path:
                images_dir = os.path.join(session_path, "location_generation", "images")
            else:
                images_dir = f"story_generation_pipeline/sessions/HIndi Thriller_20250906_215416_ba18db6b/location_generation/images"
            os.makedirs(images_dir, exist_ok=True)
            
            # Create placeholder image
            width, height = 800, 600
            image = Image.new('RGB', (width, height), color='lightgray')
            draw = ImageDraw.Draw(image)
            
            # Add text
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 40)
            except:
                font = ImageFont.load_default()
            
            text = f"{location.get('name', 'Location')}\n{image_type.replace('_', ' ').title()}"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            draw.text((x, y), text, fill='black', font=font)
            
            # Save image
            filename = f"{location.get('location_id', 'unknown')}_{image_type}.png"
            image_path = os.path.join(images_dir, filename)
            image.save(image_path)
            
            print(f"✅ Created placeholder {image_type} image: {image_path}")
            return image_path
            
        except Exception as e:
            print(f"❌ Error creating placeholder image: {e}")
            return None
    
    def generate_location_images(self, locations: List[Dict[str, Any]], session_path: str = None) -> List[LocationInfo]:
        """Generate images for all locations"""
        locations_with_images = []
        
        for location in locations:
            print(f"\n🏢 Generating image for {location.get('name', 'Unknown')}...")
            
            # Generate main location image only
            main_prompt = self.create_location_image_prompt(location)
            main_image_path = self.generate_image(main_prompt, "location", location.get('location_id', 'unknown'), session_path)
            
            if not main_image_path:
                # Try simpler prompt
                simple_prompt = f"Professional Indian-style photograph of {location.get('name', 'location')} - {location.get('environment', 'environment')} - NO PEOPLE visible"
                main_image_path = self.generate_image(simple_prompt, "location", location.get('location_id', 'unknown'), session_path)
            
            if not main_image_path:
                # Create placeholder
                main_image_path = self.create_placeholder_image(location, "location", session_path)
            
      
            location_info = LocationInfo(
                location_id=location.get('location_id', 'unknown'),
                name=location.get('name', 'Unknown'),
                location_type=location.get('location_type', ''),
                environment=location.get('environment', ''),
                time_of_day=location.get('time_of_day', 'Day'),
                lighting=location.get('lighting', ''),
                atmosphere=location.get('atmosphere', ''),
                background_sfx=location.get('background_sfx', []),
                set_details=location.get('set_details', ''),
                mood=location.get('mood', 'neutral'),
                image_path=main_image_path,
                location_image_prompt=main_prompt or None
            )
            
            locations_with_images.append(location_info)
            print(f"✅ Completed {location.get('name', 'Unknown')}")
        
        return locations_with_images
    
    def save_locations(self, locations: List[LocationInfo], output_file: str, session_path: str = None):
        """Save locations to JSON file"""
        try:
            # Create output directory
            if session_path:
                output_dir = os.path.join(session_path, "location_generation")
            else:
                output_dir = "story_generation_pipeline/sessions/HIndi Thriller_20250906_215416_ba18db6b/location_generation"
            os.makedirs(output_dir, exist_ok=True)
            
            # Convert to dictionary format
            locations_data = {
                "locations": [location.model_dump(by_alias=True) for location in locations]
            }
            
            # Save to file
            file_path = os.path.join(output_dir, output_file)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(locations_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Locations saved to: {file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving locations: {e}")
            return False

# def main():
#     """Main function to test location generation"""
#     try:
#         # Initialize location generator
#         location_generator = LocationGenerator()
        
#         # Load sample scenes (you would load from your actual data)
#         sample_scenes = [
#             {
#                 "scene_info": {
#                     "Scene_ID": "SC_01",
#                     "Location": "EXT. CRIME SCENE - DAY",
#                     "Set_Info": {
#                         "environment": "a disturbing and chaotic crime scene with police activity",
#                         "time": "Day",
#                         "lighting": "natural light",
#                         "background_sfx": ["police sirens", "murmurs of a crowd"]
#                     },
#                     "Scene_Tone": "tense"
#                 }
#             },
#             {
#                 "scene_info": {
#                     "Scene_ID": "SC_02",
#                     "Location": "INT. INTERROGATION ROOM - NIGHT",
#                     "Set_Info": {
#                         "environment": "a dimly lit interrogation room with a table and two chairs",
#                         "time": "Night",
#                         "lighting": "artificial light",
#                         "background_sfx": ["clock ticking", "distant police interactions"]
#                     },
#                     "Scene_Tone": "intriguing"
#                 }
#             }
#         ]
        
#         # Extract locations
#         print("🏢 Extracting locations from scenes...")
#         locations = location_generator.extract_locations_from_scenes(sample_scenes)
        
#         print(f"Found {len(locations)} unique locations:")
#         for loc in locations:
#             print(f"  - {loc['name']} ({loc['location_id']})")
        
#         # Generate images
#         print("\n🎨 Generating location images...")
#         locations_with_images = location_generator.generate_location_images(locations)
        
#         # Save locations
#         print("\n💾 Saving locations...")
#         location_generator.save_locations(locations_with_images, "locations.json")
        
#         print("\n✅ Location generation completed!")
        
#     except Exception as e:
#         print(f"❌ Error in main: {e}")

# if __name__ == "__main__":
#     main()
