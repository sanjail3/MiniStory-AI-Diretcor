from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from openai import OpenAI
import json
import os


class CharacterOutfit(BaseModel):
    """Detailed outfit information for a character"""
    outfit_description: str = Field(..., description="Detailed outfit description")
    outfit_type: str = Field(..., description="Type of outfit (casual, formal, uniform, etc.)")
    clothing_items: List[str] = Field(default_factory=list, description="Specific clothing items")
    colors: List[str] = Field(default_factory=list, description="Primary colors of the outfit")
    accessories: List[str] = Field(default_factory=list, description="Accessories worn")
    outfit_context: str = Field(..., description="Why this outfit fits the scene/situation")

class SceneCharacter(BaseModel):
    character_id: str
    character_name: str
    emotion: Optional[str] = None
    outfit: Optional[str] = None  # Keep for backward compatibility
    detailed_outfit: Optional[CharacterOutfit] = None  # New detailed outfit info
    scene_description: Optional[str] = None  

class FullCharacter(BaseModel):
    name: str
    id: str
    age: Optional[int] = None
    role: Optional[str] = None
    voice_information: Optional[str] = None
    gender: Optional[str] = None
    overall_description: Optional[str] = None
    image_path: Optional[str] = None  # Only one image path needed

class SetInfo(BaseModel):
    environment: Optional[str] = None
    time: Optional[str] = None
    lighting: Optional[str] = None
    background_sfx: Optional[List[str]] = None

class Plot(BaseModel):
    summary: str
    theme: Optional[str] = None

class Transition(BaseModel):
    transition_to: str = Field(..., alias="Transition_To")
    type: Optional[str] = "hard_cut"

class SceneInfo(BaseModel):
    scene_id: str = Field(..., alias="Scene_ID")
    title: str = Field(..., alias="Title")
    location: str = Field(..., alias="Location")
    narration: bool = Field(default=True, alias="Narration")
    scene_tone: Optional[str] = Field(None, alias="Scene_Tone")
    set_info: Optional[SetInfo] = Field(None, alias="Set_Info")
    scene_characters: List[SceneCharacter] = Field(default_factory=list, alias="Scene_Characters")
    plot: Optional[Plot] = Field(None, alias="Plot")
    given_script: str = Field(..., alias="Given_Script")

class LocationInfo(BaseModel):
    location_id: str = Field(..., alias="location_id")
    name: str = Field(..., alias="name")
    location_type: str = Field(..., alias="location_type")
    environment: str = Field(..., alias="environment")
    time_of_day: str = Field(..., alias="time_of_day")
    lighting: str = Field(..., alias="lighting")
    atmosphere: str = Field(..., alias="atmosphere")
    background_sfx: List[str] = Field(default=[], alias="background_sfx")
    set_details: str = Field(..., alias="set_details")
    mood: str = Field(..., alias="mood")
    image_path: Optional[str] = Field(None, alias="image_path")  # Only one image path needed
    location_image_prompt: Optional[str] = Field(None, alias="location_image_prompt")  # Location image prompt

class AllScenesInfo(BaseModel):
    scenes: List[SceneInfo]
    characters: List[FullCharacter]
    locations: List[LocationInfo] = Field(default_factory=list)

class ShotCharacter(BaseModel):
    """Character information specific to a shot"""
    character_id: str = Field(..., description="Character ID")
    character_name: str = Field(..., description="Character name")
    outfit_description: str = Field(..., description="Specific outfit for this shot")
    outfit_continuity: str = Field(..., description="Outfit continuity note (same as previous/changed)")
    character_action: str = Field(..., description="What the character is doing in this shot")

class Shot(BaseModel):
    shot_id: str = Field(..., alias="Shot_ID")
    description: str = Field(..., alias="Description")
    focus_characters: List[str] = Field(default_factory=list, alias="Focus_Characters")
    shot_characters: Optional[List[ShotCharacter]] = Field(default_factory=list, alias="Shot_Characters")  # New detailed character info
    camera: Optional[str] = Field(None, alias="Camera")
    emotion: Optional[str] = Field(None, alias="Emotion")
    narration: Optional[str] = Field(None, alias="Narration")
    background_sfx: Optional[List[str]] = Field(None, alias="Background_SFX")
    lighting: Optional[str] = Field(None, alias="Lighting")
    shot_tone: Optional[str] = Field(None, alias="Shot_Tone")
    set_details: Optional[str] = Field(None, alias="Set_Details")
    dialog: Optional[List[Dict[str, str]]] = Field(default_factory=list, alias="Dialog")
    focus_character_images: Optional[List[Dict[str, str]]] = Field(default_factory=list, alias="focus_character_images")
    location_reference: Optional[Dict[str, Any]] = Field(None, alias="location_reference")

class Scene(BaseModel):
    scene_info: SceneInfo
    shots: List[Shot] = Field(default_factory=list)

class FormattedScript(BaseModel):
    scenes: List[Scene]
    characters: List[FullCharacter]
    locations: List[LocationInfo] = Field(default_factory=list) 