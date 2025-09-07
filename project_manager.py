import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import streamlit as st

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
