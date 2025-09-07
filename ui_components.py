import streamlit as st
import os
from typing import List, Dict, Any
from character_generation.character_generator import FullCharacter
from models.pydantic_model import FormattedScript

def render_project_selector(project_manager, current_session_id: str = None):
    """Render project selection sidebar"""
    with st.sidebar:
        st.header("📁 Project Management")
        
        # Get available sessions
        sessions = project_manager.get_available_sessions()
        
        if sessions:
            st.subheader("📂 Available Projects")
            
            # Create session options
            session_options = {f"{s['project_name']} ({s['session_id'][:8]})": s['session_id'] for s in sessions}
            session_options["➕ Create New Project"] = "new"
            
            # Session selector
            selected_option = st.selectbox(
                "Select Project:",
                list(session_options.keys()),
                index=0 if not current_session_id else None
            )
            
            selected_session_id = session_options[selected_option]
            
            if selected_option == "➕ Create New Project":
                # New project creation
                st.subheader("Create New Project")
                project_name = st.text_input("Project Name", placeholder="Enter your project name")
                
                if st.button("🚀 Create Project", type="primary"):
                    if project_name:
                        session_id = project_manager.create_session(project_name)
                        st.success(f"Project '{project_name}' created!")
                        st.rerun()
                    else:
                        st.error("Please enter a project name")
                return None
            else:
                # Load existing session
                if selected_session_id != current_session_id:
                    if project_manager.load_session(selected_session_id):
                        st.success(f"Loaded project: {project_manager.get_project_name()}")
                        st.rerun()
                    else:
                        st.error("Failed to load project")
                return selected_session_id
        else:
            # No projects exist, create new one
            st.subheader("Create New Project")
            project_name = st.text_input("Project Name", placeholder="Enter your project name")
            
            if st.button("🚀 Create Project", type="primary"):
                if project_name:
                    session_id = project_manager.create_session(project_name)
                    st.success(f"Project '{project_name}' created!")
                    st.rerun()
                else:
                    st.error("Please enter a project name")
            return None

def render_progress_tracker(current_step: int, project_manager):
    """Render progress tracking sidebar"""
    with st.sidebar:
        st.subheader("📊 Progress")
        steps = [
            "Script Planning",
            "Character Generation",
            "Location Generation",
            "Scene Creation",
            "Video Assembly"
        ]
        
        for i, step in enumerate(steps):
            if i <= current_step:
                st.success(f"✅ {step}")
            else:
                st.info(f"⏳ {step}")
        
        # Step navigation
        st.subheader("🧭 Navigation")
        col1, col2 = st.columns(2)
        
        with col1:
            if current_step > 0:
                if st.button("⬅️ Previous Step"):
                    project_manager.set_current_step(current_step - 1)
                    st.rerun()
        
        with col2:
            if current_step < len(steps) - 1:
                if st.button("➡️ Next Step"):
                    project_manager.set_current_step(current_step + 1)
                    st.rerun()

def render_character_display(characters: List[FullCharacter], show_regenerate: bool = True):
    """Render character display with images"""
    st.subheader(f"🎭 Generated Characters ({len(characters)})")
    
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
                            width=400,
                            use_column_width=True
                        )
                else:
                    st.warning("No image available for this character")
                
                if show_regenerate:
                    if st.button(f"🔄 Regenerate {character.name}", key=f"regen_char_{i}"):
                        st.session_state[f"regenerate_character_{i}"] = True
                        st.rerun()

def render_script_display(formatted_script: FormattedScript, show_regenerate: bool = True):
    """Render script display with regeneration option"""
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
    
    # Regeneration buttons
    if show_regenerate:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Regenerate Script Structure", type="secondary"):
                st.session_state["regenerate_script"] = True
                st.rerun()
        with col2:
            if st.button("🔄 Regenerate Shots", type="secondary"):
                st.session_state["regenerate_shots"] = True
                st.rerun()
    
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

def render_debug_info(script_data, scenes_data, characters):
    """Render debug information"""
    with st.expander("🔍 Debug Information", expanded=False):
        st.write("**Script Data Available:**", "formatted_script" in (script_data or {}))
        st.write("**Scenes Data Available:**", "scenes" in (scenes_data or {}))
        if script_data:
            st.write("**Script Data Keys:**", list(script_data.keys()))
        if scenes_data:
            st.write("**Scenes Data Keys:**", list(scenes_data.keys()))
        st.write("**Characters Found:**", len(characters))
        
        # Show session info
        if hasattr(st.session_state, 'project_manager') and st.session_state.project_manager.session_dir:
            st.write("**Session Directory:**", st.session_state.project_manager.session_dir)
            st.write("**Current Step:**", st.session_state.project_manager.get_current_step())

def render_step_header(step_name: str, step_number: int):
    """Render step header with consistent styling"""
    st.markdown(f'<div class="step-container">', unsafe_allow_html=True)
    st.header(f"📝 Step {step_number}: {step_name}")
    st.markdown("</div>", unsafe_allow_html=True)
