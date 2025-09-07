import streamlit as st
import os
from typing import List, Dict, Any, Optional
from project_manager import ProjectManager
from ui_components import render_character_display, render_script_display, render_debug_info, render_step_header
from script_planning.script_formater import ScriptFormatter
from script_planning.shot_formater import ShotFormatter
from character_generation.character_generator import CharacterGenerator, FullCharacter
from models.pydantic_model import AllScenesInfo, FormattedScript, LocationInfo
from location_generation_step import location_generation_step

def extract_characters_from_scenes_and_shots(script_data, scenes_data):
    """Extract character information from scenes and shots data"""
    characters = []
    character_info = {}
    char_counter = 1
    
    # Extract from scenes data
    if scenes_data and "scenes" in scenes_data:
        for scene in scenes_data["scenes"]:
            if "Scene_Characters" in scene:
                for char in scene["Scene_Characters"]:
                    char_id = char.get("character_id", "")
                    if char_id and char_id not in character_info:
                        character_info[char_id] = {
                            "id": char_id,
                            "name": char.get("character_name", f"Character {char_id}"),
                            "age": None,
                            "role": "supporting",
                            "voice_information": "Default voice",
                            "gender": "unknown",
                            "overall_description": char.get("scene_description", "Character from script")
                        }
    
    # Extract from script data (formatted script with shots)
    if script_data and "scenes" in script_data:
        for scene in script_data["scenes"]:
            # Check scene_info for characters
            if "scene_info" in scene and "Scene_Characters" in scene["scene_info"]:
                for char in scene["scene_info"]["Scene_Characters"]:
                    char_id = char.get("character_id", "")
                    if char_id and char_id not in character_info:
                        character_info[char_id] = {
                            "id": char_id,
                            "name": char.get("character_name", f"Character {char_id}"),
                            "age": None,
                            "role": "supporting",
                            "voice_information": "Default voice",
                            "gender": "unknown",
                            "overall_description": char.get("scene_description", "Character from script")
                        }
            
            # Check shots for focus characters
            if "shots" in scene:
                for shot in scene["shots"]:
                    if "Focus_Characters" in shot:
                        for char_name in shot["Focus_Characters"]:
                            # Create a character ID from the name
                            char_id = f"char_{char_name.lower().replace(' ', '_')}"
                            if char_id not in character_info:
                                character_info[char_id] = {
                                    "id": char_id,
                                    "name": char_name,
                                    "age": None,
                                    "role": "supporting",
                                    "voice_information": "Default voice",
                                    "gender": "unknown",
                                    "overall_description": f"Character {char_name} from script"
                                }
    
    # Convert to list and fix duplicate IDs
    characters = list(character_info.values())
    
    # Fix duplicate IDs by reassigning them
    seen_ids = set()
    for i, char in enumerate(characters):
        if char["id"] in seen_ids:
            char["id"] = f"char_{i+1:02d}"
        seen_ids.add(char["id"])
    
    return characters

def fix_duplicate_character_ids(characters):
    """Fix duplicate character IDs in the character list"""
    if not characters:
        return characters
    
    seen_ids = set()
    fixed_characters = []
    
    for i, char in enumerate(characters):
        char_id = char.get("id", "")
        
        # If ID is already seen, create a new unique ID
        if char_id in seen_ids:
            char_id = f"char_{i+1:02d}"
            char["id"] = char_id
        
        seen_ids.add(char_id)
        fixed_characters.append(char)
    
    return fixed_characters

def script_planning_step(project_manager: ProjectManager):
    """Handle script planning step"""
    render_step_header("Script Planning", 1)
    
    # Input section
    st.subheader("📖 Input Your Story")
    
    input_type = st.radio(
        "Choose input type:",
        ["Story Idea", "Raw Script", "Upload Script File"],
        horizontal=True
    )
    
    raw_script = ""
    
    if input_type == "Story Idea":
        raw_script = st.text_area(
            "Describe your story idea:",
            placeholder="A young detective investigates a mysterious crime...",
            height=200
        )
    elif input_type == "Raw Script":
        raw_script = st.text_area(
            "Paste your script:",
            placeholder="SCENE 1: EXT. CRIME SCENE - DAY\nA detective examines the evidence...",
            height=300
        )
    elif input_type == "Upload Script File":
        uploaded_file = st.file_uploader("Upload script file", type=['txt', 'md'])
        if uploaded_file:
            raw_script = str(uploaded_file.read(), "utf-8")
            st.text_area("File content:", value=raw_script, height=300)
    
    # Check for regeneration
    regenerate_script = st.session_state.get("regenerate_script", False)
    regenerate_shots = st.session_state.get("regenerate_shots", False)
    
    if st.button("🎬 Generate Script Structure", type="primary") and raw_script:
        with st.spinner("Analyzing script and generating scene structure..."):
            try:
                # Generate scenes
                script_formatter = ScriptFormatter()
                all_scenes_info = script_formatter.generate_all_scenes_info([raw_script])
                
                # Save script data
                project_manager.save_script_data(all_scenes_info)
                
                # Generate shots
                shot_formatter = ShotFormatter()
                formatted_script = shot_formatter.generate_shots_for_all_scenes(all_scenes_info)
                
                # Save formatted script
                project_manager.save_formatted_script(formatted_script)
                
                st.success("✅ Script planning completed!")
                
                # Display results
                render_script_display(formatted_script, show_regenerate=True)
                
                # Clear regeneration flags
                if "regenerate_script" in st.session_state:
                    del st.session_state["regenerate_script"]
                if "regenerate_shots" in st.session_state:
                    del st.session_state["regenerate_shots"]
                    
            except Exception as e:
                st.error(f"Error generating script: {str(e)}")
    
    # Display existing script if available
    existing_script = project_manager.get_session_data("formatted_script")
    if existing_script:
        st.subheader("📋 Current Script")
        render_script_display(FormattedScript(**existing_script), show_regenerate=True)

def character_generation_step(project_manager: ProjectManager):
    """Handle character generation step"""
    render_step_header("Character Generation", 2)
    
    # Get characters from script - try both formatted_script and scenes_info
    script_data = project_manager.get_session_data("formatted_script")
    scenes_data = project_manager.get_session_data("script")
    
    characters = []
    
    # First try to get characters from formatted_script
    if script_data and "characters" in script_data:
        characters = script_data.get("characters", [])
        # Fix duplicate IDs in the data
        characters = fix_duplicate_character_ids(characters)
    # If not found, try to get from scenes_info
    elif scenes_data and "characters" in scenes_data:
        characters = scenes_data.get("characters", [])
        # Fix duplicate IDs in the data
        characters = fix_duplicate_character_ids(characters)
    else:
        st.error("No script data found. Please complete script planning first.")
        return
    
    # If still no characters, try to extract from scenes and shots
    if not characters:
        characters = extract_characters_from_scenes_and_shots(script_data, scenes_data)
    
    if not characters:
        st.warning("No characters found in the script.")
        return
    
    # Debug information
    render_debug_info(script_data, scenes_data, characters)
    
    # Display characters
    st.subheader(f"🎭 Found {len(characters)} Characters")
    
    # Display characters
    for i, char_data in enumerate(characters):
        with st.expander(f"Character {i+1}: {char_data.get('name', 'Unknown')}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**ID:** {char_data.get('id', 'N/A')}")
                st.write(f"**Age:** {char_data.get('age', 'N/A')}")
                st.write(f"**Role:** {char_data.get('role', 'N/A')}")
                st.write(f"**Gender:** {char_data.get('gender', 'N/A')}")
            
            with col2:
                st.write(f"**Voice:** {char_data.get('voice_information', 'N/A')}")
                st.write(f"**Description:** {char_data.get('overall_description', 'N/A')}")
    
    # Check if characters already exist
    existing_characters = project_manager.get_session_data("characters")
    
    if existing_characters and not st.session_state.get("regenerate_characters", False):
        # Display existing characters
        st.subheader("🎭 Generated Characters")
        characters_list = existing_characters.get("characters", [])
        render_character_display([FullCharacter(**char) for char in characters_list], show_regenerate=True)
        
        # Show regenerate button
        if st.button("🔄 Regenerate All Characters", type="secondary"):
            st.session_state["regenerate_characters"] = True
            st.rerun()
    else:
        # Character generation
        if st.button("🎨 Generate Character Images", type="primary"):
            with st.spinner("Generating character images..."):
                try:
                    # Convert to FullCharacter objects
                    full_characters = []
                    for i, char_data in enumerate(characters):
                        try:
                            # Ensure we have required fields
                            char_name = char_data.get('name', f'Character_{i+1}')
                            char_id = char_data.get('id', f'char_{i+1:02d}')
                            
                            full_char = FullCharacter(
                                name=char_name,
                                id=char_id,
                                age=char_data.get('age'),
                                role=char_data.get('role'),
                                voice_information=char_data.get('voice_information'),
                                gender=char_data.get('gender'),
                                overall_description=char_data.get('overall_description')
                            )
                            full_characters.append(full_char)
                            st.write(f"✅ Created character: {char_name} ({char_id})")
                        except Exception as e:
                            st.error(f"❌ Error creating character {i+1}: {str(e)}")
                            st.write(f"Character data: {char_data}")
                            continue
                    
                    # Generate images
                    character_generator = CharacterGenerator(
                        output_dir=os.path.join(project_manager.session_dir, "character_generation", "images")
                    )
                    
                    characters_with_images = []
                    progress_bar = st.progress(0)
                    
                    for i, character in enumerate(full_characters):
                        try:
                            st.write(f"Generating images for {character.name}...")
                            character_with_images = character_generator.generate_character_images(character)
                            characters_with_images.append(character_with_images)
                            
                            # Show result
                            if character_with_images.image_path:
                                st.write(f"✅ Generated images for {character.name}")
                                if "placeholder" in character_with_images.image_path.lower():
                                    st.info(f"📷 Created placeholder image for {character.name}")
                            else:
                                st.warning(f"⚠️ No image generated for {character.name}")
                                
                        except Exception as e:
                            st.error(f"❌ Error generating images for {character.name}: {str(e)}")
                            # Add character without images
                            characters_with_images.append(character)
                        finally:
                            progress_bar.progress((i + 1) / len(full_characters))
                    
                    # Save characters with images
                    project_manager.save_characters(characters_with_images)
                    
                    st.success("✅ Character generation completed!")
                    
                    # Clear regeneration flag
                    if "regenerate_characters" in st.session_state:
                        del st.session_state["regenerate_characters"]
                    
                    # Display generated characters
                    render_character_display(characters_with_images, show_regenerate=True)
                    
                except Exception as e:
                    st.error(f"Error generating characters: {str(e)}")

def location_generation_step(project_manager: ProjectManager):
    """Handle location generation step"""
    render_step_header("Location Generation", 2)
    
    # Check if we have script data
    script_data = project_manager.get_session_data("formatted_script")
    if not script_data:
        st.error("❌ No script data found. Please complete script planning first.")
        return
    
    # Check if locations already exist
    existing_locations = project_manager.get_session_data("locations")
    
    if existing_locations and not st.session_state.get("regenerate_locations", False):
        st.subheader("🏢 Generated Locations")
        locations_list = existing_locations.get("locations", [])
        render_location_display([LocationInfo(**loc) for loc in locations_list], show_regenerate=True)
        
        if st.button("🔄 Regenerate All Locations", type="secondary"):
            st.session_state["regenerate_locations"] = True
            st.rerun()
    else:
        # Get locations from formatted script
        script_locations = script_data.get("locations", [])
        
        if not script_locations:
            st.error("❌ No locations found in script data. Please complete script planning first.")
            return
        
        st.subheader("🏢 Extracted Locations")
        st.write(f"Found {len(script_locations)} locations from script:")
        for loc in script_locations:
            st.write(f"  - {loc.get('name', 'Unknown')} ({loc.get('location_id', 'Unknown')})")
        
        if st.button("🏢 Generate Location Images", type="primary"):
            with st.spinner("Generating location images..."):
                try:
                    # Initialize location generator
                    from location_generation.location_generator import LocationGenerator
                    location_generator = LocationGenerator()
                    
                    # Convert script locations to the format expected by location generator
                    locations_for_generation = []
                    for loc in script_locations:
                        location_data = {
                            'location_id': loc.get('location_id', ''),
                            'name': loc.get('name', ''),
                            'location_type': loc.get('location_type', ''),
                            'environment': loc.get('environment', ''),
                            'time_of_day': loc.get('time_of_day', 'Day'),
                            'lighting': loc.get('lighting', ''),
                            'atmosphere': loc.get('atmosphere', ''),
                            'background_sfx': loc.get('background_sfx', []),
                            'set_details': loc.get('set_details', ''),
                            'mood': loc.get('mood', 'neutral')
                        }
                        locations_for_generation.append(location_data)
                    
                    # Generate location images
                    session_path = project_manager.session_dir
                    locations_with_images = location_generator.generate_location_images(locations_for_generation, session_path)
                    
                    # Save locations
                    project_manager.save_data("locations", {
                        "locations": [location.model_dump(by_alias=True) for location in locations_with_images]
                    })
                    
                    # Also save to location_generation directory
                    location_generator.save_locations(locations_with_images, "locations.json", session_path)
                    
                    st.success("✅ Location generation completed!")
                    if "regenerate_locations" in st.session_state:
                        del st.session_state["regenerate_locations"]
                    
                    # Display locations
                    render_location_display(locations_with_images, show_regenerate=True)
                    
                except Exception as e:
                    st.error(f"❌ Error generating locations: {e}")

def render_location_display(locations, show_regenerate: bool = False):
    """Render location display with images"""
    if not locations:
        st.info("No locations generated yet.")
        return
    
    # Create columns for location display
    cols = st.columns(2)
    
    for i, location in enumerate(locations):
        with cols[i % 2]:
            st.markdown(f"### {location.name}")
            st.markdown(f"**Type:** {location.location_type}")
            st.markdown(f"**Environment:** {location.environment}")
            st.markdown(f"**Time:** {location.time_of_day}")
            st.markdown(f"**Lighting:** {location.lighting}")
            st.markdown(f"**Mood:** {location.mood}")
            
            # Display main location image
            if location.image_path and os.path.exists(location.image_path):
                st.image(location.image_path, caption=f"{location.name} - Main View", width=300)
            else:
                st.info("No main image available")
            
            
            # Background SFX
            if location.background_sfx:
                st.markdown("**Background SFX:**")
                for sfx in location.background_sfx:
                    st.markdown(f"  - {sfx}")
            
            st.markdown("---")
    
    if show_regenerate:
        if st.button("🔄 Regenerate All Locations", type="secondary"):
            st.session_state["regenerate_locations"] = True
            st.rerun()

def scene_creation_step(project_manager: ProjectManager):
    """Handle scene creation step"""
    render_step_header("Scene Creation", 3)
    
    st.info("🚧 Scene creation functionality coming soon! This will include scene description generation and video creation.")
    
    # Placeholder for scene creation
    st.subheader("📋 Current Scenes")
    
    script_data = project_manager.get_session_data("formatted_script")
    if script_data:
        scenes = script_data.get("scenes", [])
        
        for i, scene in enumerate(scenes):
            with st.expander(f"Scene {i+1}: {scene.get('scene_info', {}).get('title', 'Unknown')}"):
                scene_info = scene.get('scene_info', {})
                shots = scene.get('shots', [])
                
                st.write(f"**Location:** {scene_info.get('location', 'N/A')}")
                st.write(f"**Tone:** {scene_info.get('scene_tone', 'N/A')}")
                st.write(f"**Plot:** {scene_info.get('plot', {}).get('summary', 'N/A')}")
                
                st.write(f"**Shots ({len(shots)}):**")
                for j, shot in enumerate(shots):
                    st.write(f"  {j+1}. {shot.get('description', 'N/A')}")

def video_assembly_step(project_manager: ProjectManager):
    """Handle video assembly step"""
    render_step_header("Video Assembly", 4)
    
    st.info("🚧 Video assembly functionality coming soon! This will include final video generation and export.")
    
    # Project summary
    st.subheader("📊 Project Summary")
    
    script_data = project_manager.get_session_data("formatted_script")
    character_data = project_manager.get_session_data("characters")
    
    if script_data:
        scenes = script_data.get("scenes", [])
        total_shots = sum(len(scene.get('shots', [])) for scene in scenes)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Scenes", len(scenes))
        
        with col2:
            st.metric("Total Shots", total_shots)
        
        with col3:
            characters_count = len(character_data.get("characters", [])) if character_data else 0
            st.metric("Characters", characters_count)
