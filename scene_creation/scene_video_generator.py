#!/usr/bin/env python3
"""
Scene Video Generator using FAL Veo3 Image-to-Video
Generates videos from scene images with detailed prompts
"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
import fal_client
from pathlib import Path

load_dotenv()

class SceneVideoGenerator:
    def __init__(self, session_dir: str):
        """Initialize the Scene Video Generator"""
        self.session_dir = session_dir
        self.videos_dir = os.path.join(session_dir, "scene_creation", "videos")
        os.makedirs(self.videos_dir, exist_ok=True)
        
        # Initialize FAL client
        self.fal_api_key = os.getenv('FAL_KEY')
        if not self.fal_api_key:
            raise ValueError("FAL_KEY environment variable not found. Please set your FAL API key.")
    
    def load_script_with_descriptions(self) -> Optional[Dict[str, Any]]:
        """Load the script with scene descriptions"""
        script_path = os.path.join(self.session_dir, "scene_creation", "script_with_descriptions.json")
        
        if os.path.exists(script_path):
            with open(script_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def create_video_prompt(self, shot_info: Dict[str, Any], scene_description: Dict[str, Any]) -> str:
        """Create detailed video prompt for Veo3 from shot and scene description"""
        
        # Get the scene video prompt from scene description
        base_video_prompt = ""
        if scene_description and 'scene_video_prompt' in scene_description:
            video_info = scene_description['scene_video_prompt']
            if isinstance(video_info, dict):
                # Build detailed video prompt from components
                components = []
                
                if video_info.get('camera_angle'):
                    components.append(f"Camera: {video_info['camera_angle']}")
                
                if video_info.get('scene_description'):
                    components.append(f"Scene: {video_info['scene_description']}")
                
                if video_info.get('character_visual_description'):
                    components.append(f"Characters: {video_info['character_visual_description']}")
                
                if video_info.get('mood_emotion'):
                    components.append(f"Mood: {video_info['mood_emotion']}")
                
                if video_info.get('lighting'):
                    components.append(f"Lighting: {video_info['lighting']}")
                
                base_video_prompt = ". ".join(components)
            else:
                base_video_prompt = str(video_info)
        
        # Enhance with shot-specific details
        shot_enhancements = []
        
        if shot_info.get('Camera'):
            shot_enhancements.append(f"Camera movement: {shot_info['Camera']}")
        
        if shot_info.get('Shot_Tone'):
            shot_enhancements.append(f"Tone: {shot_info['Shot_Tone']}")
        
        if shot_info.get('Description'):
            shot_enhancements.append(f"Action: {shot_info['Description']}")
        
        # Character-specific actions
        if shot_info.get('Shot_Characters'):
            char_actions = []
            for char in shot_info['Shot_Characters']:
                if char.get('character_action'):
                    char_actions.append(f"{char['character_name']} {char['character_action']}")
            if char_actions:
                shot_enhancements.append(f"Character actions: {', '.join(char_actions)}")
        
        # Combine base prompt with enhancements
        enhanced_prompt = base_video_prompt
        if shot_enhancements:
            enhanced_prompt += ". " + ". ".join(shot_enhancements)
        
        # Add video-specific instructions
        video_instructions = [
            "Smooth natural motion",
            "Cinematic camera movement",
            "Realistic character animations",
            "Maintain visual consistency",
            "Professional film quality"
        ]
        
        final_prompt = f"{enhanced_prompt}. {'. '.join(video_instructions)}."
        
        return final_prompt.strip()
    
    def upload_image_to_fal(self, image_path: str) -> str:
        """Upload image to FAL and return URL"""
        try:
            print(f"📤 Uploading image to FAL: {os.path.basename(image_path)}")
            url = fal_client.upload_file(image_path)
            print(f"✅ Image uploaded successfully: {url}")
            return url
        except Exception as e:
            print(f"❌ Error uploading image to FAL: {e}")
            raise
    
    def generate_video(self, shot_info: Dict[str, Any], scene_image_path: str, 
                      scene_description: Dict[str, Any], scene_id: str = "unknown") -> Optional[str]:
        """Generate video for a single shot using FAL Veo3"""
        
        shot_id = shot_info.get('Shot_ID', 'unknown')
        print(f"🎬 Generating video for {shot_id}...")
        
        try:
            # Check if scene image exists
            if not os.path.exists(scene_image_path):
                print(f"❌ Scene image not found: {scene_image_path}")
                return None
            
            # Upload image to FAL
            image_url = self.upload_image_to_fal(scene_image_path)
            
            # Create video prompt
            video_prompt = self.create_video_prompt(shot_info, scene_description)
            print(f"📝 Video prompt: {video_prompt[:100]}...")
            
            # Prepare FAL request
            request_args = {
                "prompt": video_prompt,
                "image_url": image_url,
                "duration": "8s",
                "generate_audio": True,
                "resolution": "720p"
            }
            
            print(f"🚀 Submitting video generation request...")
            
            # Submit request with progress tracking
            def on_queue_update(update):
                if isinstance(update, fal_client.InProgress):
                    for log in update.logs:
                        print(f"   📋 {log['message']}")
            
            result = fal_client.subscribe(
                "fal-ai/veo3/image-to-video",
                arguments=request_args,
                with_logs=True,
                on_queue_update=on_queue_update,
            )
            
            # Save video
            if result and 'video' in result and 'url' in result['video']:
                video_url = result['video']['url']
                video_filename = f"{scene_id}_{shot_id}_video.mp4"
                video_path = os.path.join(self.videos_dir, video_filename)
                
                # Download video
                print(f"💾 Downloading video...")
                import requests
                response = requests.get(video_url)
                response.raise_for_status()
                
                with open(video_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"✅ Video saved: {video_path}")
                return video_path
            else:
                print(f"❌ No video URL in result: {result}")
                return None
                
        except Exception as e:
            print(f"❌ Error generating video for {shot_id}: {e}")
            return None
    
    def generate_scene_videos(self, scene_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate videos for all shots in a scene"""
        scene_id = scene_info.get('scene_info', {}).get('Scene_ID', 'unknown')
        shots = scene_info.get('shots', [])
        
        print(f"\n🎬 Generating videos for scene {scene_id} ({len(shots)} shots)")
        
        results = {
            "scene_id": scene_id,
            "videos": [],
            "total_shots": len(shots),
            "successful_videos": 0,
            "failed_videos": 0
        }
        
        for shot in shots:
            shot_id = shot.get('Shot_ID', 'unknown')
            
            # Find corresponding scene image
            scene_image_path = os.path.join(
                self.session_dir, 
                "scene_creation", 
                "images", 
                f"{scene_id}_{shot_id}_scene.png"
            )
            
            # Get scene description
            scene_description = shot.get('scene_description', {})
            
            # Generate video
            video_path = self.generate_video(shot, scene_image_path, scene_description, scene_id)
            
            video_result = {
                "shot_id": shot_id,
                "scene_image_path": scene_image_path,
                "video_path": video_path,
                "status": "success" if video_path else "failed"
            }
            
            results["videos"].append(video_result)
            
            if video_path:
                results["successful_videos"] += 1
            else:
                results["failed_videos"] += 1
        
        print(f"✅ Scene {scene_id} video generation complete:")
        print(f"   📊 Successful: {results['successful_videos']}/{results['total_shots']}")
        print(f"   ❌ Failed: {results['failed_videos']}/{results['total_shots']}")
        
        return results
    
    def regenerate_single_shot_video(self, shot_info: Dict, scene_image_path: str, 
                                   scene_description: Dict, scene_id: str = "unknown") -> Optional[str]:
        """Regenerate video for a single shot"""
        print(f"🔄 Regenerating video for shot...")
        return self.generate_video(shot_info, scene_image_path, scene_description, scene_id)
    
    def list_generated_videos(self) -> List[Dict[str, Any]]:
        """List all generated videos with metadata"""
        videos = []
        
        if not os.path.exists(self.videos_dir):
            return videos
        
        for filename in os.listdir(self.videos_dir):
            if filename.endswith('_video.mp4'):
                # Parse filename: SC_ID_SH_ID_video.mp4
                parts = filename.replace('_video.mp4', '').split('_')
                if len(parts) >= 2:
                    scene_id = parts[0]
                    shot_id = '_'.join(parts[1:])
                    
                    video_path = os.path.join(self.videos_dir, filename)
                    file_size = os.path.getsize(video_path)
                    
                    videos.append({
                        "scene_id": scene_id,
                        "shot_id": shot_id,
                        "filename": filename,
                        "filepath": video_path,
                        "file_size": file_size,
                        "created_time": os.path.getctime(video_path)
                    })
        
        # Sort by creation time (newest first)
        videos.sort(key=lambda x: x['created_time'], reverse=True)
        return videos
    
    def load_existing_generation_results(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load existing video generation results grouped by scene"""
        videos = self.list_generated_videos()
        grouped_videos = {}
        
        for video in videos:
            scene_id = video['scene_id']
            if scene_id not in grouped_videos:
                grouped_videos[scene_id] = []
            grouped_videos[scene_id].append(video)
        
        return grouped_videos
    
    def save_generation_results(self, results: Dict[str, Any]):
        """Save video generation results to JSON"""
        results_file = os.path.join(self.videos_dir, "generation_results.json")
        
        existing_results = []
        if os.path.exists(results_file):
            with open(results_file, 'r', encoding='utf-8') as f:
                existing_results = json.load(f)
        
        existing_results.append(results)
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(existing_results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Video generation results saved: {results_file}")
