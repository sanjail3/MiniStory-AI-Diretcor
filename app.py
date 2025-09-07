import streamlit as st
import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

# Import your existing modules
from script_planning.script_formater import ScriptFormatter
from script_planning.shot_formater import ShotFormatter
from character_generation.character_generator import CharacterGenerator, FullCharacter
from models.pydantic_model import AllScenesInfo, FormattedScript, SceneInfo, FullCharacter as PydanticFullCharacter
from location_generation_step import location_generation_step

# Page configuration
st.set_page_config(
    page_title="MiniStory - AI Short Film Director & Generator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .step-container {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 5px solid #667eea;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .character-card {
        background-color: white;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .scene-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #28a745;
    }
</style>
""", unsafe_allow_html=True)

class ProjectManager:
    """Manages project sessions and data storage"""
    
    def __init__(self):
        self.base_dir = "story_generation_pipeline"
        self.session_dir = None
        
    def create_session(self, project_name: str) -> str:
        """Create a new project session"""
        session_id = f"{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        self.session_dir = os.path.join(self.base_dir, "sessions", session_id)
        
        # Create directory structure
        directories = [
            "script_planning",
            "character_generation",
            "location_generation", 
            "scene_creation",
            "video_editing",
            "metadata"
        ]
        
        for dir_name in directories:
            os.makedirs(os.path.join(self.session_dir, dir_name), exist_ok=True)
            
        # Save project metadata
        metadata = {
            "project_name": project_name,
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "status": "created",
            "steps_completed": [],
            "current_step": 0
        }
        
        with open(os.path.join(self.session_dir, "metadata", "project_info.json"), "w") as f:
            json.dump(metadata, f, indent=2)
            
        return session_id
    
    def load_session(self, session_id: str) -> bool:
        """Load an existing session"""
        session_path = os.path.join(self.base_dir, "sessions", session_id)
        if os.path.exists(session_path):
            self.session_dir = session_path
            return True
        return False
    
    def get_available_sessions(self) -> List[Dict[str, Any]]:
        """Get list of available sessions"""
        sessions = []
        sessions_dir = os.path.join(self.base_dir, "sessions")
        
        if not os.path.exists(sessions_dir):
            return sessions
            
        for session_id in os.listdir(sessions_dir):
            session_path = os.path.join(sessions_dir, session_id)
            metadata_path = os.path.join(session_path, "metadata", "project_info.json")
            
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                    sessions.append({
                        "session_id": session_id,
                        "project_name": metadata.get("project_name", session_id),
                        "created_at": metadata.get("created_at", ""),
                        "current_step": metadata.get("current_step", 0),
                        "steps_completed": metadata.get("steps_completed", [])
                    })
                except:
                    continue
                    
        # Sort by creation date (newest first)
        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return sessions
    
    def save_script_data(self, script_data: Any, filename: str = "scenes_info.json"):
        """Save script planning data"""
        if not self.session_dir:
            raise ValueError("No active session")
            
        filepath = os.path.join(self.session_dir, "script_planning", filename)
        script_dict = script_data.model_dump(by_alias=True) if hasattr(script_data, 'model_dump') else script_data
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(script_dict, f, indent=2, ensure_ascii=False)
            
        # Update metadata
        self._update_metadata("script_planning_completed", True)
        
    def save_formatted_script(self, formatted_script: Any, filename: str = "formatted_script.json"):
        """Save formatted script with shots"""
        if not self.session_dir:
            raise ValueError("No active session")
            
        filepath = os.path.join(self.session_dir, "script_planning", filename)
        script_dict = formatted_script.model_dump(by_alias=True) if hasattr(formatted_script, 'model_dump') else formatted_script
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(script_dict, f, indent=2, ensure_ascii=False)
            
        # Update metadata
        self._update_metadata("shot_planning_completed", True)
    
    def save_characters(self, characters: List[Any], filename: str = "characters.json"):
        """Save character data"""
        if not self.session_dir:
            raise ValueError("No active session")
            
        filepath = os.path.join(self.session_dir, "character_generation", filename)
        characters_dict = {"characters": [char.model_dump() if hasattr(char, 'model_dump') else char for char in characters]}
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(characters_dict, f, indent=2, ensure_ascii=False)
            
        # Update metadata
        self._update_metadata("character_generation_completed", True)
    
    def save_data(self, data_type: str, data: Any):
        """Save data to session"""
        if not self.session_dir:
            raise ValueError("No active session")
        
        file_mapping = {
            "locations": os.path.join(self.session_dir, "location_generation", "locations.json")
        }
        
        filepath = file_mapping.get(data_type)
        if filepath:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _update_metadata(self, key: str, value: Any):
        """Update project metadata"""
        metadata_path = os.path.join(self.session_dir, "metadata", "project_info.json")
        
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
        else:
            metadata = {}
            
        metadata[key] = value
        metadata["last_updated"] = datetime.now().isoformat()
        
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
    
    def get_session_data(self, data_type: str) -> Optional[Dict]:
        """Get data from current session"""
        if not self.session_dir:
            return None
            
        file_mapping = {
            "script": os.path.join(self.session_dir, "script_planning", "scenes_info.json"),
            "formatted_script": os.path.join(self.session_dir, "script_planning", "formatted_script.json"),
            "characters": os.path.join(self.session_dir, "character_generation", "characters.json"),
            "locations": os.path.join(self.session_dir, "location_generation", "locations.json")
        }
        
        filepath = file_mapping.get(data_type)
        if filepath and os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    
    def get_current_step(self) -> int:
        """Get current step from metadata"""
        if not self.session_dir:
            return 0
            
        metadata_path = os.path.join(self.session_dir, "metadata", "project_info.json")
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                return metadata.get("current_step", 0)
            except:
                pass
        return 0
    
    def set_current_step(self, step: int):
        """Set current step in metadata"""
        self._update_metadata("current_step", step)
    
    def get_project_name(self) -> str:
        """Get project name from metadata"""
        if not self.session_dir:
            return "Unknown Project"
            
        metadata_path = os.path.join(self.session_dir, "metadata", "project_info.json")
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                return metadata.get("project_name", "Unknown Project")
            except:
                pass
        return "Unknown Project"

def extract_characters_from_scenes_and_shots(script_data, scenes_data):
    """Extract character information from scenes and shots data"""
    characters = []
    character_info = {}
    
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

def main():
    # Initialize session state
    if "project_manager" not in st.session_state:
        st.session_state.project_manager = ProjectManager()
    if "current_step" not in st.session_state:
        st.session_state.current_step = 0
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    
    # Header
    st.markdown('<h1 class="main-header">🎬 MiniStory - AI Short Film Director & Generator</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar for project management
    with st.sidebar:
        st.header("📁 Project Management")
        
        # Get available sessions
        sessions = st.session_state.project_manager.get_available_sessions()
        
        if sessions:
            st.subheader("📂 Available Projects")
            
            # Create session options
            session_options = {f"{s['project_name']} ({s['session_id'][:8]})": s['session_id'] for s in sessions}
            session_options["➕ Create New Project"] = "new"
            
            # Session selector
            selected_option = st.selectbox(
                "Select Project:",
                list(session_options.keys()),
                index=0 if not st.session_state.current_session_id else None
            )
            
            selected_session_id = session_options[selected_option]
            
            if selected_option == "➕ Create New Project":
                # New project creation
                st.subheader("Create New Project")
                project_name = st.text_input("Project Name", placeholder="Enter your project name")
                
                if st.button("🚀 Create Project", type="primary"):
                    if project_name:
                        session_id = st.session_state.project_manager.create_session(project_name)
                        st.session_state.current_session_id = session_id
                        st.session_state.current_step = 0
                        st.success(f"Project '{project_name}' created!")
                        st.rerun()
                    else:
                        st.error("Please enter a project name")
            else:
                # Load existing session
                if selected_session_id != st.session_state.current_session_id:
                    if st.session_state.project_manager.load_session(selected_session_id):
                        st.session_state.current_session_id = selected_session_id
                        st.session_state.current_step = st.session_state.project_manager.get_current_step()
                        st.success(f"Loaded project: {st.session_state.project_manager.get_project_name()}")
                        st.rerun()
                    else:
                        st.error("Failed to load project")
        else:
            # No projects exist, create new one
            st.subheader("Create New Project")
            project_name = st.text_input("Project Name", placeholder="Enter your project name")
            
            if st.button("🚀 Create Project", type="primary"):
                if project_name:
                    session_id = st.session_state.project_manager.create_session(project_name)
                    st.session_state.current_session_id = session_id
                    st.session_state.current_step = 0
                    st.success(f"Project '{project_name}' created!")
                    st.rerun()
                else:
                    st.error("Please enter a project name")
        
        # Progress tracking
        st.subheader("📊 Progress")
        steps = [
            "Script Planning",
            "Character Generation",
            "Location Generation",
            "Scene Creation",
            "Video Assembly"
        ]
        
        for i, step in enumerate(steps):
            if i <= st.session_state.current_step:
                st.success(f"✅ {step}")
            else:
                st.info(f"⏳ {step}")
        
        # Step navigation
        st.subheader("🧭 Navigation")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.session_state.current_step > 0:
                if st.button("⬅️ Previous Step"):
                    st.session_state.current_step -= 1
                    st.session_state.project_manager.set_current_step(st.session_state.current_step)
                    st.rerun()
        
        with col2:
            if st.session_state.current_step < len(steps) - 1:
                if st.button("➡️ Next Step"):
                    st.session_state.current_step += 1
                    st.session_state.project_manager.set_current_step(st.session_state.current_step)
                    st.rerun()
    
    # Main content area
    if not st.session_state.project_manager.session_dir:
        st.info("👈 Please create or select a project using the sidebar to get started!")
        return
    
    # Step 1: Script Planning
    if st.session_state.current_step == 0:
        script_planning_step(st.session_state.project_manager)
    elif st.session_state.current_step == 1:
        character_generation_step(st.session_state.project_manager)
    elif st.session_state.current_step == 2:
        location_generation_step(st.session_state.project_manager)
    elif st.session_state.current_step == 3:
        scene_creation_step(st.session_state.project_manager)
    elif st.session_state.current_step == 4:
        video_assembly_step(st.session_state.project_manager)

def script_planning_step(project_manager):
    st.markdown('<div class="step-container">', unsafe_allow_html=True)
    st.header("📝 Step 1: Script Planning")
    st.markdown("</div>", unsafe_allow_html=True)
    
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
                display_script_results(formatted_script)
                
            except Exception as e:
                st.error(f"Error generating script: {str(e)}")
    
    # Display existing script if available
    existing_script = project_manager.get_session_data("formatted_script")
    if existing_script:
        st.subheader("📋 Current Script")
        display_script_results(FormattedScript(**existing_script))

def character_generation_step(project_manager):
    st.markdown('<div class="step-container">', unsafe_allow_html=True)
    st.header("👥 Step 2: Character Generation")
    st.markdown("</div>", unsafe_allow_html=True)
    
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
    
    # Check if characters already exist
    existing_characters = project_manager.get_session_data("characters")
    
    if existing_characters and not st.session_state.get("regenerate_characters", False):
        # Display existing characters
        st.subheader("🎭 Generated Characters")
        characters_list = existing_characters.get("characters", [])
        display_character_results([FullCharacter(**char) for char in characters_list])
        
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
                    display_character_results(characters_with_images)
                    
                except Exception as e:
                    st.error(f"Error generating characters: {str(e)}")

def scene_creation_step(project_manager):
    st.markdown('<div class="step-container">', unsafe_allow_html=True)
    st.header("🎬 Step 4: Scene Creation")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Initialize scene creator
    try:
        from scene_creation.scene_creator import SceneCreator
        scene_creator = SceneCreator(project_manager.session_dir)
    except ImportError as e:
        st.error(f"❌ Could not import SceneCreator: {e}")
        return
    
    # Check prerequisites
    script_data = project_manager.get_session_data("formatted_script")
    character_data = project_manager.get_session_data("characters")
    location_data = project_manager.get_session_data("locations")
    
    if not script_data:
        st.error("❌ No script data found. Please complete script planning first.")
        return
    
    if not character_data:
        st.error("❌ No character data found. Please complete character generation first.")
        return
    
    if not location_data:
        st.error("❌ No location data found. Please complete location generation first.")
        return
    
    # Scene Creation Workflow
    st.subheader("🎭 Scene Creation Workflow")
    
    # Step 1: Scene Description Generation
    st.markdown("### Step 1: Scene Description Generation")
    
    status = scene_creator.get_scene_creation_status()
    
    if not status["descriptions_generated"]:
        st.info("📝 Scene descriptions need to be generated first.")
        
        if st.button("🎭 Generate Scene Descriptions", type="primary"):
            with st.spinner("Generating scene descriptions for all shots..."):
                try:
                    script_with_descriptions = scene_creator.generate_scene_descriptions(
                        script_data, character_data, location_data
                    )
                    st.success("✅ Scene descriptions generated successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error generating scene descriptions: {e}")
    else:
        st.success("✅ Scene descriptions already generated")
        
        # Load and display script with descriptions
        script_with_descriptions = scene_creator.load_script_with_descriptions()
        
        if script_with_descriptions:
            # Step 2: Scene Image Generation
            st.markdown("### Step 2: Scene Image Generation")
            
            scenes = script_with_descriptions.get("scenes", [])
            total_scenes = len(scenes)
            
            st.info(f"🎬 Ready to generate images for {total_scenes} scenes")
            
            # Check for existing generated images
            existing_images = scene_creator.image_generator.list_generated_images()
            generated_scenes = set()
            
            # Group existing images by scene
            scene_image_map = {}
            for image_info in existing_images:
                scene_id = image_info.get('scene_id', 'unknown')
                if scene_id not in scene_image_map:
                    scene_image_map[scene_id] = []
                scene_image_map[scene_id].append(image_info)
                generated_scenes.add(scene_id)
            
            # Display existing images summary if any
            if existing_images:
                st.success(f"✅ Found {len(existing_images)} previously generated images across {len(generated_scenes)} scenes")
                
                with st.expander("📸 View Previously Generated Images", expanded=False):
                    display_existing_scene_images(scene_image_map, scenes)
            
            # Scene completion tracking
            scene_completion_status = {}
            images_dir = os.path.join(project_manager.session_dir, "scene_creation", "images")
            
            for i, scene in enumerate(scenes):
                scene_id = scene.get('scene_info', {}).get('Scene_ID', f'Scene_{i+1}')
                shots = scene.get('shots', [])
                
                # Check how many shots are completed for this scene by checking actual files
                completed_shots = 0
                if os.path.exists(images_dir):
                    for shot in shots:
                        shot_id = shot.get('Shot_ID', 'unknown')
                        image_filename = f"{scene_id}_{shot_id}_scene.png"
                        image_path = os.path.join(images_dir, image_filename)
                        if os.path.exists(image_path):
                            completed_shots += 1
                
                scene_completion_status[scene_id] = {
                    'total_shots': len(shots),
                    'completed_shots': completed_shots,
                    'is_complete': completed_shots >= len(shots)
                }
            
            # Display scene completion overview
            st.markdown("### 📊 Scene Completion Status")
            completion_cols = st.columns(min(4, total_scenes))
            
            for i, scene in enumerate(scenes[:4]):  # Show first 4 scenes
                scene_id = scene.get('scene_info', {}).get('Scene_ID', f'Scene_{i+1}')
                status = scene_completion_status[scene_id]
                
                with completion_cols[i]:
                    if status['is_complete']:
                        st.success(f"✅ {scene_id}")
                        st.write(f"{status['completed_shots']}/{status['total_shots']} shots")
                    else:
                        st.info(f"⏳ {scene_id}")
                        st.write(f"{status['completed_shots']}/{status['total_shots']} shots")
            
            if total_scenes > 4:
                st.write(f"... and {total_scenes - 4} more scenes")
            
            # Scene-by-scene image generation
            current_scene = st.session_state.get("current_scene_generation", 0)
            
            if current_scene < total_scenes:
                scene = scenes[current_scene]
                scene_id = scene.get('scene_info', {}).get('Scene_ID', f'Scene_{current_scene+1}')
                shots = scene.get('shots', [])
                current_status = scene_completion_status[scene_id]
                
                st.markdown(f"#### 🎬 Scene {current_scene + 1}/{total_scenes}: {scene_id}")
                
                # Show completion status for current scene
                if current_status['is_complete']:
                    st.success(f"✅ Scene completed! ({current_status['completed_shots']}/{current_status['total_shots']} shots)")
                else:
                    st.info(f"⏳ In progress: {current_status['completed_shots']}/{current_status['total_shots']} shots completed")
                
                st.markdown(f"**Total shots in scene:** {len(shots)}")
                
                # Display scene info
                with st.expander("📋 Scene Details", expanded=True):
                    scene_info = scene.get('scene_info', {})
                    st.write(f"**Location:** {scene_info.get('Location', 'N/A')}")
                    st.write(f"**Tone:** {scene_info.get('Scene_Tone', 'N/A')}")
                    if scene_info.get('Plot', {}).get('summary'):
                        st.write(f"**Plot:** {scene_info['Plot']['summary']}")
                
                # Scene selector
                st.markdown("#### 🎯 Scene Navigation")
                scene_options = []
                for i, s in enumerate(scenes):
                    s_id = s.get('scene_info', {}).get('Scene_ID', f'Scene_{i+1}')
                    status = scene_completion_status[s_id]
                    status_icon = "✅" if status['is_complete'] else "⏳"
                    scene_options.append(f"{status_icon} Scene {i+1}: {s_id} ({status['completed_shots']}/{status['total_shots']})")
                
                selected_scene_idx = st.selectbox(
                    "Jump to Scene:",
                    range(len(scene_options)),
                    index=current_scene,
                    format_func=lambda x: scene_options[x]
                )
                
                if selected_scene_idx != current_scene:
                    st.session_state["current_scene_generation"] = selected_scene_idx
                    st.rerun()
                
                # Display existing images for current scene if any
                if scene_id in scene_image_map:
                    st.markdown("#### 📸 Existing Images for This Scene")
                    existing_scene_images = {scene_id: scene_image_map[scene_id]}
                    display_existing_scene_images(existing_scene_images, [scene])
                else:
                    # Check if there are any images in the file system for this scene
                    images_dir = os.path.join(project_manager.session_dir, "scene_creation", "images")
                    if os.path.exists(images_dir):
                        scene_images = []
                        for filename in os.listdir(images_dir):
                            if filename.startswith(f"{scene_id}_") and filename.endswith("_scene.png"):
                                shot_id = filename.replace("_scene.png", "")
                                scene_images.append({
                                    "shot_id": shot_id,
                                    "filepath": os.path.join(images_dir, filename),
                                    "scene_id": scene_id
                                })
                        
                        if scene_images:
                            st.markdown("#### 📸 Found Existing Images for This Scene")
                            existing_scene_images = {scene_id: scene_images}
                            display_existing_scene_images(existing_scene_images, [scene])
                
                # Generate images for current scene
                col1, col2 = st.columns(2)
                
                with col1:
                    if current_status['is_complete']:
                        button_text = f"🔄 Regenerate All Images for {scene_id}"
                        button_type = "secondary"
                    else:
                        button_text = f"🎨 Generate Images for {scene_id}"
                        button_type = "primary"
                    
                    if st.button(button_text, type=button_type):
                        with st.spinner(f"Generating images for {scene_id}..."):
                            try:
                                # Generate images for this scene only
                                scene_results = scene_creator.image_generator.generate_scene_images(scene)
                                
                                st.success(f"✅ Generated {len(scene_results['generated_shots'])} images for {scene_id}")
                                
                                # Display generated images
                                display_scene_images(scene_results)
                                
                                # Refresh the page to update the status
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"❌ Error generating images for {scene_id}: {e}")
                
                with col2:
                    if st.button("⏭️ Skip to Next Scene"):
                        st.session_state["current_scene_generation"] = current_scene + 1
                        st.rerun()
                
                # Navigation buttons
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if current_scene > 0:
                        if st.button("⬅️ Previous Scene"):
                            st.session_state["current_scene_generation"] = current_scene - 1
                            st.rerun()
                
                with col2:
                    if st.button("🔄 Regenerate Scene Descriptions"):
                        # Delete existing descriptions and regenerate
                        desc_path = os.path.join(project_manager.session_dir, "scene_creation", "script_with_descriptions.json")
                        if os.path.exists(desc_path):
                            os.remove(desc_path)
                        st.rerun()
                
                with col3:
                    if current_scene < total_scenes - 1:
                        if st.button("➡️ Next Scene"):
                            st.session_state["current_scene_generation"] = current_scene + 1
                            st.rerun()
            
            else:
                # All scenes completed
                st.success("🎉 All scene images have been generated!")
                
                # Display summary
                generated_images = scene_creator.image_generator.list_generated_images()
                st.metric("Generated Images", len(generated_images))
                
                # Step 3: Video Generation
                st.markdown("### Step 3: Video Generation")
                
                # Add navigation back to image generation
                col1, col2 = st.columns([3, 1])
                
                with col2:
                    if st.button("⬅️ Back to Image Generation", type="secondary"):
                        # Reset video generation state and go back to image generation
                        if "current_scene_video_generation" in st.session_state:
                            del st.session_state["current_scene_video_generation"]
                        st.rerun()
                
                with col1:
                    st.info("💡 You can go back to generate missing scene images if needed")
                
                # Check for existing videos
                existing_videos = scene_creator.load_existing_video_results()
                
                if existing_videos:
                    st.success(f"✅ Found previously generated videos for {len(existing_videos)} scenes")
                    
                    with st.expander("🎬 View Previously Generated Videos", expanded=False):
                        display_existing_scene_videos(existing_videos, scenes)
                
                # Video generation controls
                video_scene_generation_step(scene_creator, scenes, project_manager)
                
                # Option to proceed to final assembly
                if st.button("🎬 Proceed to Final Assembly", type="primary"):
                    st.session_state.current_step = 4
                    project_manager.set_current_step(4)
                    st.rerun()
                
                # Reset option
                if st.button("🔄 Start Over"):
                    st.session_state["current_scene_generation"] = 0
                    st.rerun()

def display_scene_images(scene_results: Dict):
    """Display generated scene images"""
    if not scene_results.get("images"):
        st.info("No images generated yet.")
        return
    
    st.subheader("🖼️ Generated Scene Images")
    
    for shot_id, image_info in scene_results["images"].items():
        with st.expander(f"📸 {shot_id}", expanded=True):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                if os.path.exists(image_info["image_path"]):
                    try:
                        # Use unique key to avoid cache conflicts
                        image_key = f"current_scene_image_{shot_id}"
                        st.image(
                            image_info["image_path"], 
                            caption=f"Scene Image - {shot_id}", 
                            width="stretch",
                            key=image_key
                        )
                    except Exception as e:
                        st.error(f"Error displaying image: {str(e)}")
                        st.text(f"Image path: {image_info['image_path']}")
                else:
                    st.error("Image file not found")
                    st.text(f"Expected path: {image_info.get('image_path', 'No path provided')}")
            
            with col2:
                shot_info = image_info.get("shot_info", {})
                st.write(f"**Shot ID:** {shot_id}")
                st.write(f"**Description:** {shot_info.get('Description', 'N/A')}")
                st.write(f"**Camera:** {shot_info.get('Camera', 'N/A')}")
                st.write(f"**Emotion:** {shot_info.get('Emotion', 'N/A')}")
                
                # Regenerate button for individual shots
                if st.button(f"🔄 Regenerate {shot_id}", key=f"regen_{shot_id}"):
                    with st.spinner(f"Regenerating image for {shot_id}..."):
                        try:
                            # Get the scene creator
                            from scene_creation.scene_creator import SceneCreator
                            scene_creator = SceneCreator(st.session_state.project_manager.session_dir)
                            
                            # Get scene_id from shot_id (e.g., SC1_SH1 -> SC_01)
                            scene_id = shot_id.split('_')[0] + "_" + shot_id.split('_')[1][:2]
                            
                            # Get character and location references
                            character_refs = image_info.get("character_refs", [])
                            location_ref = image_info.get("location_ref")
                            
                            # Regenerate the image
                            new_image_path = scene_creator.regenerate_single_shot_image(
                                shot_info, character_refs, location_ref, scene_id
                            )
                            
                            if new_image_path:
                                st.success(f"✅ Successfully regenerated {shot_id}")
                                st.rerun()
                            else:
                                st.error(f"❌ Failed to regenerate {shot_id}")
                                
                        except Exception as e:
                            st.error(f"❌ Error regenerating {shot_id}: {e}")

def display_character_voices(characters: List[Dict]):
    """Display character voices with audio previews"""
    
    for char in characters:
        name = char.get('name', 'Unknown')
        voice_id = char.get('generated_voice_id')
        voice_preview_path = char.get('voice_preview_path')
        voice_description = char.get('voice_description', '')
        
        st.markdown(f"#### 🎭 {name}")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if voice_description:
                st.markdown(f"**Voice Description:** {voice_description[:200]}...")
            
            if voice_id:
                st.success(f"**Voice ID:** {voice_id}")
            else:
                st.error("**Voice ID:** Not generated")
        
        with col2:
            if voice_preview_path and os.path.exists(voice_preview_path):
                st.audio(voice_preview_path, format='audio/mp3')
            else:
                st.info("No audio preview available")

def generate_dialog_mapping_workflow(video_assembly_manager, script_data, character_data):
    """Generate dialog mapping workflow"""
    from video_editing.dialog_mapper import DialogMapper
    
    # Initialize dialog mapper
    dialog_mapper = DialogMapper()
    
    # Load script with descriptions
    script_with_descriptions = video_assembly_manager.load_script_with_descriptions()
    if not script_with_descriptions:
        st.error("❌ Could not load script with descriptions")
        return
    
    # Generate dialog mappings
    dialog_mappings = dialog_mapper.generate_all_dialog_mappings(
        script_with_descriptions, character_data.get('characters', [])
    )
    
    if dialog_mappings:
        # Save dialog mappings
        dialog_file = os.path.join(video_assembly_manager.dialog_dir, "shot_dialog_mapping.json")
        success = dialog_mapper.save_dialog_mappings(dialog_mappings, dialog_file)
        
        if success:
            # Get statistics
            stats = dialog_mapper.get_dialog_statistics(dialog_mappings)
            
            st.success(f"✅ Generated dialog mapping for {stats['total_scenes']} scenes")
            st.info(f"📊 {stats['shots_with_dialog']} shots with dialog, {stats['shots_with_narration']} with narration")
        else:
            st.error("❌ Failed to save dialog mappings")
    else:
        st.error("❌ Failed to generate dialog mappings")

def display_dialog_mapping_summary(video_assembly_manager):
    """Display dialog mapping summary"""
    from video_editing.dialog_mapper import DialogMapper
    
    dialog_file = os.path.join(video_assembly_manager.dialog_dir, "shot_dialog_mapping.json")
    
    if os.path.exists(dialog_file):
        dialog_mapper = DialogMapper()
        dialog_mappings = dialog_mapper.load_dialog_mappings(dialog_file)
        
        if dialog_mappings:
            stats = dialog_mapper.get_dialog_statistics(dialog_mappings)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Scenes", stats['total_scenes'])
                st.metric("Total Shots", stats['total_shots'])
            
            with col2:
                st.metric("Shots with Dialog", stats['shots_with_dialog'])
                st.metric("Shots with Narration", stats['shots_with_narration'])
            
            with col3:
                st.metric("Silent Shots", stats['shots_without_audio'])
            
            # Character dialog count
            if stats['character_dialog_count']:
                st.markdown("**Dialog Distribution by Character:**")
                for char_name, count in stats['character_dialog_count'].items():
                    st.write(f"- {char_name}: {count} dialogs")

def generate_audio_workflow(video_assembly_manager, character_data):
    """Generate audio workflow"""
    from video_editing.audio_generator import AudioGenerator
    from video_editing.dialog_mapper import DialogMapper
    
    # Initialize audio generator
    audio_generator = AudioGenerator()
    
    # Load dialog mappings
    dialog_file = os.path.join(video_assembly_manager.dialog_dir, "shot_dialog_mapping.json")
    dialog_mapper = DialogMapper()
    dialog_mappings = dialog_mapper.load_dialog_mappings(dialog_file)
    
    if not dialog_mappings:
        st.error("❌ Could not load dialog mappings")
        return
    
    # Generate audio for all scenes (with intelligent voice assignment fallback)
    characters_file_path = video_assembly_manager.get_characters_file_path()
    audio_results = audio_generator.generate_all_audio(
        dialog_mappings, 
        character_data.get('characters', []), 
        video_assembly_manager.audio_dir,
        characters_file_path
    )
    
    # Save results
    results_file = os.path.join(video_assembly_manager.audio_dir, "audio_generation_results.json")
    audio_generator.save_audio_results(audio_results, results_file)
    
    # Display statistics
    stats = audio_generator.get_audio_statistics(audio_results)
    
    st.success(f"✅ Generated {stats['total_audio_files']} audio files")
    st.info(f"📊 {stats['audio_by_type']['dialog']} dialog files, {stats['audio_by_type']['narration']} narration files")
    
    # Show voice assignment information if applied
    if audio_results.get('voice_assignments_applied', False):
        st.info("🤖 Intelligent voice assignment was applied during audio generation")
        st.caption("Character voice IDs were automatically assigned using AI matching")

def display_audio_files(video_assembly_manager):
    """Display generated audio files"""
    audio_files = []
    
    if os.path.exists(video_assembly_manager.audio_dir):
        for filename in os.listdir(video_assembly_manager.audio_dir):
            if filename.endswith(('.mp3', '.wav')):
                audio_files.append(filename)
    
    if audio_files:
        st.markdown(f"**Found {len(audio_files)} audio files:**")
        
        # Group by shot
        audio_by_shot = {}
        for filename in audio_files:
            if '_' in filename:
                shot_id = '_'.join(filename.split('_')[:2])  # Get SC_01_SC1_SH1 part
                if shot_id not in audio_by_shot:
                    audio_by_shot[shot_id] = []
                audio_by_shot[shot_id].append(filename)
        
        # Display by shot
        for shot_id, files in audio_by_shot.items():
            with st.expander(f"🎬 {shot_id} ({len(files)} files)"):
                for filename in files:
                    file_path = os.path.join(video_assembly_manager.audio_dir, filename)
                    st.markdown(f"**{filename}**")
                    st.audio(file_path, format='audio/mp3')
    else:
        st.info("No audio files found")

def display_existing_scene_videos(scene_video_map: Dict, scenes: List[Dict]):
    """Display previously generated scene videos organized by scene"""
    
    for i, scene in enumerate(scenes):
        scene_id = scene.get('scene_info', {}).get('Scene_ID', f'Scene_{i+1}')
        
        if scene_id in scene_video_map:
            videos = scene_video_map[scene_id]
            
            st.markdown(f"### 🎬 {scene_id} ({len(videos)} videos)")
            
            # Display videos in a grid
            cols = st.columns(min(2, len(videos)))
            
            for idx, video_info in enumerate(videos):
                col_idx = idx % 2
                
                with cols[col_idx]:
                    shot_id = video_info.get('shot_id', f'shot_{idx}')
                    filepath = video_info.get('filepath', '')
                    
                    if filepath and os.path.exists(filepath):
                        try:
                            st.markdown(f"**{shot_id}**")
                            st.video(filepath)
                            
                            # Add regenerate and modify options for videos
                            col_video1, col_video2 = st.columns(2)
                            
                            with col_video1:
                                if st.button(f"🔄 Regenerate Video", key=f"regen_video_{scene_id}_{shot_id}"):
                                    # Regenerate this specific video
                                    with st.spinner(f"Regenerating video for {shot_id}..."):
                                        
                                            # Get the scene creator
                                        from scene_creation.scene_creator import SceneCreator
                                        scene_creator = SceneCreator(st.session_state.project_manager.session_dir)
                                        
                                        # Load script with descriptions to get shot info
                                        script_with_descriptions = scene_creator.load_script_with_descriptions()
                                        if script_with_descriptions:
                                            # Find the specific shot
                                            shot_info = None
                                            scene_description = None
                                            scene_image_path = None
                                            
                                            for scene in script_with_descriptions.get('scenes', []):
                                                if scene.get('scene_info', {}).get('Scene_ID') == scene_id:
                                                    for shot in scene.get('shots', []):
                                                        if shot.get('Shot_ID') == shot_id:
                                                            shot_info = shot
                                                            scene_description = shot.get('scene_description', {})
                                                            # Get corresponding scene image
                                                            scene_image_path = os.path.join(
                                                                st.session_state.project_manager.session_dir,
                                                                "scene_creation", "images",
                                                                f"{scene_id}_{shot_id}_scene.png"
                                                            )
                                                            break
                                                    break
                                            
                                            if shot_info and scene_image_path and os.path.exists(scene_image_path):
                                                new_video_path = scene_creator.regenerate_single_shot_video(
                                                    shot_info, scene_image_path, scene_description, scene_id
                                                )
                                                if new_video_path:
                                                    st.success(f"✅ Successfully regenerated video for {shot_id}")
                                                    st.rerun()
                                                else:
                                                    st.error(f"❌ Failed to regenerate video for {shot_id}")
                                            else:
                                                st.error(f"❌ Could not find required data for {shot_id}")
                                        else:
                                            st.error("❌ Could not load script with descriptions")
                                        
                            
                            with col_video2:
                                if st.button(f"✏️ Modify Video Prompt", key=f"modify_video_prompt_{scene_id}_{shot_id}"):
                                    st.session_state[f"modify_video_prompt_{scene_id}_{shot_id}"] = True
                                    st.rerun()
                            
                            # Show video prompt modification dialog if requested
                            if st.session_state.get(f"modify_video_prompt_{scene_id}_{shot_id}", False):
                                with st.expander(f"✏️ Modify Video Prompt for {shot_id}", expanded=True):
                                    try:
                                        from scene_creation.scene_creator import SceneCreator
                                        scene_creator = SceneCreator(st.session_state.project_manager.session_dir)
                                        script_with_descriptions = scene_creator.load_script_with_descriptions()
                                        
                                        current_video_prompt = ""
                                        if script_with_descriptions:
                                            for scene in script_with_descriptions.get('scenes', []):
                                                if scene.get('scene_info', {}).get('Scene_ID') == scene_id:
                                                    for shot in scene.get('shots', []):
                                                        if shot.get('Shot_ID') == shot_id:
                                                            scene_desc = shot.get('scene_description', {})
                                                            video_info = scene_desc.get('scene_video_prompt', {})
                                                            if isinstance(video_info, dict):
                                                                current_video_prompt = f"Camera: {video_info.get('camera_angle', '')}\nScene: {video_info.get('scene_description', '')}\nCharacters: {video_info.get('character_visual_description', '')}\nMood: {video_info.get('mood_emotion', '')}\nLighting: {video_info.get('lighting', '')}"
                                                            else:
                                                                current_video_prompt = str(video_info)
                                                            break
                                                    break
                                        
                                        # Text area for video prompt modification
                                        modified_video_prompt = st.text_area(
                                            "Modify the video generation prompt:",
                                            value=current_video_prompt,
                                            height=150,
                                            key=f"video_prompt_input_{scene_id}_{shot_id}"
                                        )
                                        
                                        col_save, col_cancel = st.columns(2)
                                        
                                        with col_save:
                                            if st.button("🎬 Generate Video with Modified Prompt", key=f"save_video_prompt_{scene_id}_{shot_id}"):
                                                with st.spinner(f"Generating video with modified prompt..."):
                                                    # Implementation for modified video prompt generation would go here
                                                    st.info("Modified video prompt generation will be implemented")
                                                    st.session_state[f"modify_video_prompt_{scene_id}_{shot_id}"] = False
                                                    st.rerun()
                                        
                                        with col_cancel:
                                            if st.button("❌ Cancel", key=f"cancel_video_prompt_{scene_id}_{shot_id}"):
                                                st.session_state[f"modify_video_prompt_{scene_id}_{shot_id}"] = False
                                                st.rerun()
                                    
                                    except Exception as e:
                                        st.error(f"❌ Error loading video prompt: {e}")
                        
                        except Exception as e:
                            st.error(f"Error displaying video for {shot_id}: {str(e)}")
                    else:
                        st.error(f"Video not found: {shot_id}")

def video_scene_generation_step(scene_creator, scenes: List[Dict], project_manager):
    """Handle video generation for scenes"""
    
    if "current_scene_video_generation" not in st.session_state:
        st.session_state["current_scene_video_generation"] = 0
    
    current_scene = st.session_state["current_scene_video_generation"]
    total_scenes = len(scenes)
    
    if current_scene >= total_scenes:
        st.success("🎉 All scene videos have been generated!")
        return
    
    # Current scene info
    scene = scenes[current_scene]
    scene_id = scene.get('scene_info', {}).get('Scene_ID', f'Scene_{current_scene+1}')
    shots = scene.get('shots', [])
    
    st.subheader(f"🎬 Video Generation: {scene_id} ({current_scene + 1}/{total_scenes})")
    
    # Add quick navigation to image generation
    col_info, col_nav = st.columns([3, 1])
    
    with col_info:
        st.info(f"Scene has {len(shots)} shots to convert to videos")
    
    with col_nav:
        if st.button("🖼️ Go to Image Generation", key=f"goto_images_{scene_id}"):
            # Set the current scene for image generation and switch
            st.session_state["current_scene_generation"] = current_scene
            if "current_scene_video_generation" in st.session_state:
                del st.session_state["current_scene_video_generation"]
            st.rerun()
    
    # Check if scene images exist
    missing_images = []
    available_shots = []
    
    for shot in shots:
        shot_id = shot.get('Shot_ID', 'unknown')
        scene_image_path = os.path.join(
            project_manager.session_dir,
            "scene_creation", "images",
            f"{scene_id}_{shot_id}_scene.png"
        )
        
        if os.path.exists(scene_image_path):
            available_shots.append({
                'shot': shot,
                'image_path': scene_image_path
            })
        else:
            missing_images.append(shot_id)
    
    if missing_images:
        st.warning(f"⚠️ Missing scene images for: {', '.join(missing_images)}")
        st.info(f"✅ {len(available_shots)} shots are ready for video generation")
        
        # Show detailed status
        with st.expander("📋 Detailed Shot Status", expanded=True):
            shot_cols = st.columns(min(3, len(shots)))
            
            for i, shot in enumerate(shots):
                shot_id = shot.get('Shot_ID', f'shot_{i+1}')
                col_idx = i % 3
                
                with shot_cols[col_idx]:
                    if shot_id in [s['shot'].get('Shot_ID') for s in available_shots]:
                        st.success(f"✅ {shot_id}")
                        st.caption("Image available")
                    else:
                        st.error(f"❌ {shot_id}")
                        st.caption("Image missing")
                        
                        # Add quick regenerate button for missing images
                        if st.button(f"🔄 Generate Image", key=f"quick_gen_{scene_id}_{shot_id}"):
                            with st.spinner(f"Generating image for {shot_id}..."):
                                try:
                                    from scene_creation.scene_creator import SceneCreator
                                    scene_creator = SceneCreator(project_manager.session_dir)
                                    
                                    # Load script and find shot info
                                    script_with_descriptions = scene_creator.load_script_with_descriptions()
                                    if script_with_descriptions:
                                        for scene_data in script_with_descriptions.get('scenes', []):
                                            if scene_data.get('scene_info', {}).get('Scene_ID') == scene_id:
                                                for shot_data in scene_data.get('shots', []):
                                                    if shot_data.get('Shot_ID') == shot_id:
                                                        character_refs = shot_data.get('focus_character_images', [])
                                                        location_ref = shot_data.get('location_reference')
                                                        
                                                        new_image_path = scene_creator.regenerate_single_shot_image(
                                                            shot_data, character_refs, location_ref, scene_id
                                                        )
                                                        
                                                        if new_image_path:
                                                            st.success(f"✅ Generated image for {shot_id}")
                                                            st.rerun()
                                                        else:
                                                            st.error(f"❌ Failed to generate image for {shot_id}")
                                                        break
                                                break
                                    else:
                                        st.error("Could not load script data")
                                except Exception as e:
                                    st.error(f"Error generating image: {e}")
        
        if len(available_shots) == 0:
            st.error("❌ No scene images available. Please generate scene images first.")
            return
    
    # Check for existing videos for this scene
    existing_videos = scene_creator.load_existing_video_results()
    scene_videos = existing_videos.get(scene_id, [])
    
    if scene_videos:
        st.markdown("#### 🎬 Existing Videos for This Scene")
        display_existing_scene_videos({scene_id: scene_videos}, [scene])
    
    # Video generation controls
    st.markdown("#### 🎥 Generate Videos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        button_text = f"🎬 Generate Videos for Available Shots ({len(available_shots)})"
        if st.button(button_text, type="primary"):
            with st.spinner(f"Generating videos for available shots in {scene_id}... This may take several minutes."):
                try:
                    # Create a modified scene with only available shots
                    available_scene = {
                        'scene_info': scene.get('scene_info', {}),
                        'shots': [shot_data['shot'] for shot_data in available_shots]
                    }
                    
                    # Generate videos for available shots only
                    video_results = scene_creator.generate_scene_videos(available_scene)
                    
                    successful = video_results.get('successful_videos', 0)
                    failed = video_results.get('failed_videos', 0)
                    
                    if successful > 0:
                        st.success(f"✅ Generated {successful} videos for {scene_id}")
                        
                        if failed > 0:
                            st.warning(f"⚠️ {failed} videos failed to generate")
                        
                        # Display generated videos
                        if video_results.get('videos'):
                            st.markdown("#### 🎬 Generated Videos")
                            for video_info in video_results['videos']:
                                if video_info['status'] == 'success':
                                    st.markdown(f"**{video_info['shot_id']}**")
                                    st.video(video_info['video_path'])
                        
                        # Refresh to update status
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to generate any videos for {scene_id}")
                        
                except Exception as e:
                    st.error(f"❌ Error generating videos for {scene_id}: {e}")
    
    with col2:
        if st.button("⏭️ Skip to Next Scene"):
            st.session_state["current_scene_video_generation"] = current_scene + 1
            st.rerun()
    
    # Single shot video generation and management
    st.markdown("#### 🎯 Individual Shot Management")
    
    # Only show shots that have scene images
    available_shot_options = [shot_data['shot'].get('Shot_ID', f'Shot_{i+1}') for i, shot_data in enumerate(available_shots)]
    
    if available_shot_options:
        col_select, col_actions = st.columns([2, 3])
        
        with col_select:
            selected_shot = st.selectbox("Select shot:", available_shot_options)
        
        with col_actions:
            if selected_shot:
                # Check if video already exists for this shot
                video_exists = False
                existing_video_path = os.path.join(
                    project_manager.session_dir,
                    "scene_creation", "videos",
                    f"{scene_id}_{selected_shot}_video.mp4"
                )
                
                if os.path.exists(existing_video_path):
                    video_exists = True
                
                col_gen, col_regen, col_img = st.columns(3)
                
                with col_gen:
                    button_text = "🔄 Regenerate Video" if video_exists else "🎬 Generate Video"
                    if st.button(button_text, key=f"single_video_{selected_shot}"):
                        with st.spinner(f"{'Regenerating' if video_exists else 'Generating'} video for {selected_shot}..."):
                            try:
                                # Find the selected shot
                                selected_shot_info = None
                                scene_image_path = None
                                
                                for shot in shots:
                                    if shot.get('Shot_ID') == selected_shot:
                                        selected_shot_info = shot
                                        scene_image_path = os.path.join(
                                            project_manager.session_dir,
                                            "scene_creation", "images",
                                            f"{scene_id}_{selected_shot}_scene.png"
                                        )
                                        break
                                
                                if selected_shot_info and scene_image_path and os.path.exists(scene_image_path):
                                    scene_description = selected_shot_info.get('scene_description', {})
                                    video_path = scene_creator.video_generator.generate_video(
                                        selected_shot_info, scene_image_path, scene_description, scene_id
                                    )
                                    
                                    if video_path:
                                        st.success(f"✅ Successfully {'regenerated' if video_exists else 'generated'} video for {selected_shot}")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Failed to {'regenerate' if video_exists else 'generate'} video for {selected_shot}")
                                else:
                                    st.error(f"❌ Could not find scene image for {selected_shot}")
                                    
                            except Exception as e:
                                st.error(f"❌ Error {'regenerating' if video_exists else 'generating'} video for {selected_shot}: {e}")
                
                with col_regen:
                    if st.button("🖼️ Regenerate Image", key=f"regen_img_{selected_shot}"):
                        with st.spinner(f"Regenerating image for {selected_shot}..."):
                            try:
                                from scene_creation.scene_creator import SceneCreator
                                scene_creator_temp = SceneCreator(project_manager.session_dir)
                                
                                # Load script and find shot info
                                script_with_descriptions = scene_creator_temp.load_script_with_descriptions()
                                if script_with_descriptions:
                                    for scene_data in script_with_descriptions.get('scenes', []):
                                        if scene_data.get('scene_info', {}).get('Scene_ID') == scene_id:
                                            for shot_data in scene_data.get('shots', []):
                                                if shot_data.get('Shot_ID') == selected_shot:
                                                    character_refs = shot_data.get('focus_character_images', [])
                                                    location_ref = shot_data.get('location_reference')
                                                    
                                                    new_image_path = scene_creator_temp.regenerate_single_shot_image(
                                                        shot_data, character_refs, location_ref, scene_id
                                                    )
                                                    
                                                    if new_image_path:
                                                        st.success(f"✅ Regenerated image for {selected_shot}")
                                                        st.rerun()
                                                    else:
                                                        st.error(f"❌ Failed to regenerate image for {selected_shot}")
                                                    break
                                            break
                                else:
                                    st.error("Could not load script data")
                            except Exception as e:
                                st.error(f"Error regenerating image: {e}")
                
                with col_img:
                    if st.button("✏️ Modify Prompts", key=f"modify_prompts_{selected_shot}"):
                        st.session_state[f"modify_prompts_{scene_id}_{selected_shot}"] = True
                        st.rerun()
        
        # Show existing video if available
        if selected_shot and os.path.exists(existing_video_path):
            st.markdown(f"#### 🎬 Current Video for {selected_shot}")
            st.video(existing_video_path)
        
        # Show prompt modification dialog
        if selected_shot and st.session_state.get(f"modify_prompts_{scene_id}_{selected_shot}", False):
            with st.expander(f"✏️ Modify Prompts for {selected_shot}", expanded=True):
                # Image and Video prompt modification tabs
                tab1, tab2 = st.tabs(["🖼️ Image Prompt", "🎬 Video Prompt"])
                
                with tab1:
                    st.markdown("**Modify Scene Image Prompt**")
                    # Implementation for image prompt modification
                    st.text_area("Image prompt:", height=100, key=f"img_prompt_{scene_id}_{selected_shot}")
                    
                    col_save_img, col_cancel = st.columns(2)
                    with col_save_img:
                        if st.button("💾 Regenerate Image with New Prompt", key=f"save_img_prompt_{scene_id}_{selected_shot}"):
                            st.info("Image prompt modification will be implemented")
                    
                with tab2:
                    st.markdown("**Modify Video Generation Prompt**")
                    # Implementation for video prompt modification  
                    st.text_area("Video prompt:", height=100, key=f"vid_prompt_{scene_id}_{selected_shot}")
                    
                    col_save_vid, col_cancel2 = st.columns(2)
                    with col_save_vid:
                        if st.button("🎬 Regenerate Video with New Prompt", key=f"save_vid_prompt_{scene_id}_{selected_shot}"):
                            st.info("Video prompt modification will be implemented")
                
                # Cancel button
                if st.button("❌ Cancel Modifications", key=f"cancel_mods_{scene_id}_{selected_shot}"):
                    st.session_state[f"modify_prompts_{scene_id}_{selected_shot}"] = False
                    st.rerun()
    else:
        st.info("No shots available for video generation. Please generate scene images first.")
    
    # Navigation buttons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if current_scene > 0:
            if st.button("⬅️ Previous Scene"):
                st.session_state["current_scene_video_generation"] = current_scene - 1
                st.rerun()
    
    with col2:
        if st.button("🖼️ Generate Missing Images"):
            # Go back to image generation for this scene
            st.session_state["current_scene_generation"] = current_scene
            if "current_scene_video_generation" in st.session_state:
                del st.session_state["current_scene_video_generation"]
            st.rerun()
    
    with col3:
        st.markdown(f"**Scene {current_scene + 1} of {total_scenes}**")
    
    with col4:
        if current_scene < total_scenes - 1:
            if st.button("➡️ Next Scene"):
                st.session_state["current_scene_video_generation"] = current_scene + 1
                st.rerun()

def display_existing_scene_images(scene_image_map: Dict, scenes: List[Dict]):
    """Display previously generated scene images organized by scene"""
    
    for i, scene in enumerate(scenes):
        scene_id = scene.get('scene_info', {}).get('Scene_ID', f'Scene_{i+1}')
        
        if scene_id in scene_image_map:
            images = scene_image_map[scene_id]
            
            st.markdown(f"### 🎬 {scene_id} ({len(images)} images)")
            
            # Display images in a grid
            cols = st.columns(min(3, len(images)))
            
            for idx, image_info in enumerate(images):
                col_idx = idx % 3
                
                with cols[col_idx]:
                    shot_id = image_info.get('shot_id', f'shot_{idx}')
                    filepath = image_info.get('filepath', '')
                    
                    if filepath and os.path.exists(filepath):
                        try:
                            # Use a unique key for each image to avoid cache conflicts
                            image_key = f"scene_image_{scene_id}_{shot_id}"
                            
                            # Display image with error handling
                            st.image(
                                filepath, 
                                caption=f"{shot_id}", 
                                width="stretch",
                                # key=image_key
                            )
                            
                            # Add regenerate options
                            col_regen1, col_regen2 = st.columns(2)
                            
                            with col_regen1:
                                if st.button(f"🔄 Regenerate", key=f"regen_existing_{scene_id}_{shot_id}"):
                                    # Regenerate this specific shot
                                    with st.spinner(f"Regenerating {shot_id}..."):
                                    
                                            # Get the scene creator
                                        from scene_creation.scene_creator import SceneCreator
                                        scene_creator = SceneCreator(st.session_state.project_manager.session_dir)
                                        
                                        # Load script with descriptions to get shot info
                                        script_with_descriptions = scene_creator.load_script_with_descriptions()
                                        if script_with_descriptions:
                                            # Find the specific shot
                                            shot_info = None
                                            character_refs = []
                                            location_ref = None
                                            
                                            for scene in script_with_descriptions.get('scenes', []):
                                                if scene.get('scene_info', {}).get('Scene_ID') == scene_id:
                                                    for shot in scene.get('shots', []):
                                                        if shot.get('Shot_ID') == shot_id:
                                                            shot_info = shot
                                                            character_refs = shot.get('focus_character_images', [])
                                                            location_ref = shot.get('location_reference')
                                                            break
                                                    break
                                            
                                            if shot_info:
                                                new_image_path = scene_creator.regenerate_single_shot_image(
                                                    shot_info, character_refs, location_ref, scene_id
                                                )
                                                
                                                if new_image_path:
                                                    st.success(f"✅ Successfully regenerated {shot_id}")
                                                    st.rerun()
                                                else:
                                                    st.error(f"❌ Failed to regenerate {shot_id}")
                                            else:
                                                st.error(f"❌ Could not find shot info for {shot_id}")
                                        else:
                                            st.error("❌ Could not load script with descriptions")
                                            
                                            
                            
                            with col_regen2:
                                if st.button(f"✏️ Modify Prompt", key=f"modify_prompt_{scene_id}_{shot_id}"):
                                    st.session_state[f"modify_image_prompt_{scene_id}_{shot_id}"] = True
                                    st.rerun()
                            
                            # Show prompt modification dialog if requested
                            if st.session_state.get(f"modify_image_prompt_{scene_id}_{shot_id}", False):
                                with st.expander(f"✏️ Modify Prompt for {shot_id}", expanded=True):
                                    # Get current prompt
                                    try:
                                        from scene_creation.scene_creator import SceneCreator
                                        scene_creator = SceneCreator(st.session_state.project_manager.session_dir)
                                        script_with_descriptions = scene_creator.load_script_with_descriptions()
                                        
                                        current_prompt = ""
                                        if script_with_descriptions:
                                            for scene in script_with_descriptions.get('scenes', []):
                                                if scene.get('scene_info', {}).get('Scene_ID') == scene_id:
                                                    for shot in scene.get('shots', []):
                                                        if shot.get('Shot_ID') == shot_id:
                                                            scene_desc = shot.get('scene_description', {})
                                                            current_prompt = scene_desc.get('scene_image_prompt', '')
                                                            break
                                                    break
                                        
                                        # Text area for prompt modification
                                        modified_prompt = st.text_area(
                                            "Modify the scene image prompt:",
                                            value=current_prompt,
                                            height=100,
                                            key=f"prompt_input_{scene_id}_{shot_id}"
                                        )
                                        
                                        col_save, col_cancel = st.columns(2)
                                        
                                        with col_save:
                                            if st.button("💾 Generate with Modified Prompt", key=f"save_prompt_{scene_id}_{shot_id}"):
                                                with st.spinner(f"Generating with modified prompt..."):
                                                    # Implementation for modified prompt generation would go here
                                                    st.info("Modified prompt generation will be implemented")
                                                    st.session_state[f"modify_image_prompt_{scene_id}_{shot_id}"] = False
                                                    st.rerun()
                                        
                                        with col_cancel:
                                            if st.button("❌ Cancel", key=f"cancel_prompt_{scene_id}_{shot_id}"):
                                                st.session_state[f"modify_image_prompt_{scene_id}_{shot_id}"] = False
                                                st.rerun()
                                    
                                    except Exception as e:
                                        st.error(f"❌ Error loading prompt: {e}")
                        
                        except Exception as e:
                            st.error(f"Error displaying image for {shot_id}: {str(e)}")
                            st.text(f"Image path: {filepath}")
                    else:
                        st.error(f"Image not found: {shot_id}")
                        if filepath:
                            st.text(f"Expected path: {filepath}")
            
            st.markdown("---")

def video_assembly_step(project_manager):
    st.markdown('<div class="step-container">', unsafe_allow_html=True)
    st.header("🎞️ Step 5: Video Assembly")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Initialize video assembly manager
    try:
        from video_editing.video_assembly_manager import VideoAssemblyManager
        video_assembly_manager = VideoAssemblyManager(project_manager.session_dir)
    except ImportError as e:
        st.error(f"❌ Could not import VideoAssemblyManager: {e}")
        return
    
    # Check prerequisites
    script_data = project_manager.get_session_data("formatted_script")
    character_data = project_manager.get_session_data("characters")
    
    if not script_data:
        st.error("❌ No script data found. Please complete script planning first.")
        return
    
    if not character_data:
        st.error("❌ No character data found. Please complete character generation first.")
        return
    
    # Get video assembly status
    assembly_status = video_assembly_manager.get_video_assembly_status()
    
    # Display overall progress
    st.subheader("📋 Video Assembly Pipeline")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        voice_status = assembly_status["voice_generation"]
        if voice_status["voices_generated"]:
            st.success("✅ Voice Generation Complete")
            st.metric("Characters with Voices", f"{voice_status['characters_with_voices']}/{voice_status['characters_count']}")
        else:
            st.warning("⚠️ Voice Generation Pending")
            st.metric("Characters with Voices", f"{voice_status['characters_with_voices']}/{voice_status['characters_count']}")
    
    with col2:
        if assembly_status["dialog_mapping_exists"]:
            st.success("✅ Dialog Mapping Complete")
        else:
            st.warning("⚠️ Dialog Mapping Pending")
        st.metric("Dialog Mapping", "✅" if assembly_status["dialog_mapping_exists"] else "❌")
    
    with col3:
        st.metric("Audio Files", assembly_status["audio_files_count"])
        if assembly_status["audio_files_count"] > 0:
            st.success("✅ Audio Files Generated")
        else:
            st.info("📝 No Audio Files Yet")
    
    # Step 1: Voice Generation
    st.markdown("### Step 1: Character Voice Generation")
    
    if not voice_status["voices_generated"]:
        st.info("🎤 Generate unique voices for each character using AI voice design")
        
        if st.button("🎭 Generate Character Voices", type="primary"):
            with st.spinner("Generating voices for all characters... This may take a few minutes."):
                try:
                    voice_results = video_assembly_manager.generate_character_voices()
                    
                    if voice_results["success"]:
                        st.success(f"✅ Generated voices for {voice_results['successful_voices']}/{voice_results['characters_processed']} characters")
                        
                        if voice_results["failed_voices"] > 0:
                            st.warning(f"⚠️ {voice_results['failed_voices']} voices failed to generate")
                        
                        st.rerun()
                    else:
                        st.error(f"❌ Voice generation failed: {voice_results['error']}")
                except Exception as e:
                    st.error(f"❌ Error during voice generation: {e}")
    else:
        st.success("✅ Character voices have been generated!")
        
        # Display character voices
        with st.expander("🎤 View Character Voices", expanded=False):
            display_character_voices(voice_status["characters"])
    
    # Step 2: Dialog Mapping
    st.markdown("### Step 2: Shot Dialog Mapping")
    
    if voice_status["voices_generated"]:
        if not assembly_status["dialog_mapping_exists"]:
            st.info("🎭 Map dialog and narration to characters for each shot")
            
            if st.button("🎬 Generate Dialog Mapping", type="primary"):
                with st.spinner("Analyzing script and mapping dialog to characters..."):
                    try:
                        generate_dialog_mapping_workflow(video_assembly_manager, script_data, character_data)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error generating dialog mapping: {e}")
        else:
            st.success("✅ Dialog mapping has been generated!")
            
            # Display dialog mapping summary
            with st.expander("📋 View Dialog Mapping", expanded=False):
                display_dialog_mapping_summary(video_assembly_manager)
    else:
        st.info("⚠️ Complete voice generation first")
    
    # Step 3: Audio Generation
    st.markdown("### Step 3: Audio Generation")
    
    if voice_status["voices_generated"] and assembly_status["dialog_mapping_exists"]:
        if assembly_status["audio_files_count"] == 0:
            st.info("🎵 Generate audio files for all shots using character voices")
            
            if st.button("🎤 Generate All Audio", type="primary"):
                with st.spinner("Generating audio files for all shots... This may take several minutes."):
                    try:
                        generate_audio_workflow(video_assembly_manager, character_data)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error generating audio: {e}")
        else:
            st.success(f"✅ Generated {assembly_status['audio_files_count']} audio files!")
            
            # Display audio files
            with st.expander("🎵 View Generated Audio", expanded=False):
                display_audio_files(video_assembly_manager)
    else:
        st.info("⚠️ Complete voice generation and dialog mapping first")
    
    # Final Assembly Status
    if assembly_status["ready_for_assembly"]:
        st.markdown("### 🎞️ Final Video Assembly")
        
        # Get comprehensive assembly status including video files
        try:
            comprehensive_status = video_assembly_manager.get_comprehensive_assembly_status()
            video_assembly_info = comprehensive_status.get("video_assembly", {})
            
            # Show assembly readiness
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Scene Videos", video_assembly_info.get("scene_videos_count", 0))
            with col2:
                st.metric("Audio Files", comprehensive_status.get("audio_files_count", 0))
            with col3:
                assembled_videos = video_assembly_info.get("assembled_videos", [])
                st.metric("Assembled Videos", len(assembled_videos))
            
            if comprehensive_status.get("ready_for_final_assembly", False):
                st.success("✅ All components ready for final video assembly!")
                
                # Assembly options
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("🎬 Create Preview Video", type="secondary"):
                        with st.spinner("Creating preview video (2 scenes)..."):
                            try:
                                preview_result = video_assembly_manager.create_preview_video(max_scenes=2)
                                
                                if preview_result["success"]:
                                    st.success("✅ Preview video created!")
                                    stats = preview_result.get("stats", {})
                                    st.info(f"📊 {stats.get('processed_scenes', 0)} scenes, {stats.get('final_duration', 0):.1f}s")
                                    
                                    # Display preview
                                    if os.path.exists(preview_result["output_path"]):
                                        st.video(preview_result["output_path"])
                                        
                                        with open(preview_result["output_path"], "rb") as f:
                                            st.download_button(
                                                label="📥 Download Preview",
                                                data=f.read(),
                                                file_name=os.path.basename(preview_result["output_path"]),
                                                mime="video/mp4"
                                            )
                                else:
                                    st.error(f"❌ Preview failed: {preview_result.get('error', 'Unknown error')}")
                            except Exception as e:
                                st.error(f"❌ Error creating preview: {e}")
                
                with col2:
                    if st.button("🎞️ Assemble Full Video", type="primary"):
                        with st.spinner("Assembling full video... This may take several minutes."):
                            try:
                                assembly_result = video_assembly_manager.assemble_final_video()
                                
                                if assembly_result["success"]:
                                    st.success("🎉 Full video assembled successfully!")
                                    stats = assembly_result.get("stats", {})
                                    
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric("Scenes", f"{stats.get('processed_scenes', 0)}/{stats.get('total_scenes', 0)}")
                                    with col2:
                                        st.metric("Duration", f"{stats.get('final_duration', 0):.1f}s")
                                    with col3:
                                        st.metric("File Size", f"{stats.get('file_size_mb', 0)} MB")
                                    
                                    # Display final video
                                    if os.path.exists(assembly_result["output_path"]):
                                        st.video(assembly_result["output_path"])
                                        
                                        with open(assembly_result["output_path"], "rb") as f:
                                            st.download_button(
                                                label="📥 Download Final Video",
                                                data=f.read(),
                                                file_name=os.path.basename(assembly_result["output_path"]),
                                                mime="video/mp4"
                                            )
                                else:
                                    st.error(f"❌ Assembly failed: {assembly_result.get('error', 'Unknown error')}")
                            except Exception as e:
                                st.error(f"❌ Error assembling video: {e}")
                
                # Show existing assembled videos
                if assembled_videos:
                    st.markdown("#### 📹 Previously Assembled Videos")
                    for video_file in assembled_videos:
                        video_path = os.path.join(video_assembly_info["assembly_dir"], video_file)
                        if os.path.exists(video_path):
                            with st.expander(f"🎬 {video_file}"):
                                st.video(video_path)
                                with open(video_path, "rb") as f:
                                    st.download_button(
                                        label="📥 Download",
                                        data=f.read(),
                                        file_name=video_file,
                                        mime="video/mp4",
                                        key=f"download_{video_file}"
                                    )
                
                # Cleanup option
                if st.button("🧹 Clean Temporary Files"):
                    video_assembly_manager.cleanup_assembly_temp_files()
                    st.success("✅ Temporary files cleaned up")
            
            else:
                st.warning("⚠️ Missing components for final assembly")
                missing_components = []
                if video_assembly_info.get("scene_videos_count", 0) == 0:
                    missing_components.append("Scene videos")
                if comprehensive_status.get("audio_files_count", 0) == 0:
                    missing_components.append("Audio files")
                if not comprehensive_status.get("dialog_mapping_exists", False):
                    missing_components.append("Dialog mapping")
                
                if missing_components:
                    st.error(f"❌ Missing: {', '.join(missing_components)}")
                    st.info("💡 Complete video generation (Step 3) and audio generation first")
        
        except Exception as e:
            st.error(f"❌ Error checking assembly status: {e}")
            st.info("🚧 Basic assembly ready - advanced features may need additional setup")
    
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

def display_script_results(formatted_script: FormattedScript):
    """Display script planning results"""
    st.subheader("📋 Generated Script Structure")
    
    # Summary
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Scenes", len(formatted_script.scenes))
    
    with col2:
        total_shots = sum(len(scene.shots) for scene in formatted_script.scenes)
        st.metric("Total Shots", total_shots)
    
    with col3:
        st.metric("Characters", len(formatted_script.characters))
    
    # Scenes breakdown
    st.subheader("🎬 Scenes Breakdown")
    
    for i, scene in enumerate(formatted_script.scenes):
        with st.expander(f"Scene {i+1}: {scene.scene_info.title}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Location:** {scene.scene_info.location}")
                st.write(f"**Tone:** {scene.scene_info.scene_tone}")
                st.write(f"**Characters:** {len(scene.scene_info.scene_characters)}")
                
            with col2:
                st.write(f"**Shots:** {len(scene.shots)}")
                st.write(f"**Environment:** {scene.scene_info.set_info.environment if scene.scene_info.set_info else 'N/A'}")
            
            # Shots details
            st.write("**Shots:**")
            for j, shot in enumerate(scene.shots):
                st.write(f"  {j+1}. {shot.description}")

def display_character_results(characters: List[FullCharacter]):
    """Display character generation results"""
    st.subheader("👥 Generated Characters")
    
    for i, character in enumerate(characters):
        with st.expander(f"Character {i+1}: {character.name}", expanded=True):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.write(f"**ID:** {character.id}")
                st.write(f"**Age:** {character.age}")
                st.write(f"**Role:** {character.role}")
                st.write(f"**Gender:** {character.gender}")
                st.write(f"**Voice:** {character.voice_information}")
                st.write(f"**Description:** {character.overall_description}")
            
            with col2:
                if character.image_path and os.path.exists(character.image_path):
                    # Centered image display
                    col_img1, col_img2, col_img3 = st.columns([1, 2, 1])
                    with col_img2:
                        st.image(
                            character.image_path, 
                            caption=f"{character.name} - Reference Image", 
                            width=400
                        )
                else:
                    st.warning("No image available for this character")

if __name__ == "__main__":
    main()
