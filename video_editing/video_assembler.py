#!/usr/bin/env python3
"""
Video Assembler - Combines scene videos with generated audio using MoviePy
"""

import os
import json
from typing import Dict, List, Any, Optional, Tuple
from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeAudioClip, 
    concatenate_videoclips, concatenate_audioclips
)
import tempfile
from datetime import datetime

class VideoAssembler:
    """Assembles final video by combining scene videos with generated audio"""
    
    def __init__(self, session_path: str):
        self.session_path = session_path
        self.video_editing_dir = os.path.join(session_path, "video_editing")
        self.assembly_dir = os.path.join(self.video_editing_dir, "assembly")
        os.makedirs(self.assembly_dir, exist_ok=True)
        
        # Paths to various components
        self.scene_videos_dir = os.path.join(session_path, "scene_creation", "videos")
        self.audio_dir = os.path.join(self.video_editing_dir, "audio")
        self.dialog_mapping_dir = os.path.join(self.video_editing_dir, "dialog_mapping")
        
        # Default audio settings
        self.default_audio_fade_duration = 0.5  # seconds
        self.background_audio_volume = 0.3  # 30% of original volume when dialog is present
        
    def load_dialog_mappings(self) -> Optional[List[Dict[str, Any]]]:
        """Load dialog mappings for shots"""
        dialog_file = os.path.join(self.dialog_mapping_dir, "shot_dialog_mapping.json")
        
        if not os.path.exists(dialog_file):
            print("❌ Dialog mapping file not found")
            return None
        
        try:
            with open(dialog_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('scenes', [])
        except Exception as e:
            print(f"❌ Error loading dialog mappings: {e}")
            return None
    
    def get_scene_video_path(self, scene_id: str, shot_id: str) -> Optional[str]:
        """Get path to scene video file"""
        video_filename = f"{shot_id}_video.mp4"
        video_path = os.path.join(self.scene_videos_dir, video_filename)
        
        if os.path.exists(video_path):
            return video_path
        
        # Try alternative naming
        alt_filename = f"{scene_id}_{shot_id}_video.mp4"
        alt_path = os.path.join(self.scene_videos_dir, alt_filename)
        
        if os.path.exists(alt_path):
            return alt_path
        
        return None
    
    def get_shot_audio_files(self, shot_id: str) -> List[str]:
        """Get all audio files for a shot"""
        audio_files = []
        
        if not os.path.exists(self.audio_dir):
            return audio_files
        
        # Find all audio files that start with the shot_id
        for filename in os.listdir(self.audio_dir):
            if filename.startswith(shot_id) and filename.endswith(('.mp3', '.wav')):
                audio_path = os.path.join(self.audio_dir, filename)
                audio_files.append(audio_path)
        
        return sorted(audio_files)  # Sort for consistent ordering
    
    def create_shot_audio_track(self, shot_audio_files: List[str]) -> Optional[AudioFileClip]:
        """Create composite audio track for a shot by concatenating all audio files"""
        if not shot_audio_files:
            return None
        
        try:
            audio_clips = []
            
            for audio_file in shot_audio_files:
                print(f"   📢 Adding audio: {os.path.basename(audio_file)}")
                audio_clip = AudioFileClip(audio_file)
                audio_clips.append(audio_clip)
            
            if len(audio_clips) == 1:
                return audio_clips[0]
            else:
                # Concatenate multiple audio clips
                return concatenate_audioclips(audio_clips)
                
        except Exception as e:
            print(f"❌ Error creating audio track: {e}")
            return None
    
    def process_shot_video(self, scene_id: str, shot_id: str, shot_info: Dict[str, Any]) -> Optional[VideoFileClip]:
        """Process a single shot video with audio replacement/overlay"""
        
        print(f"🎬 Processing shot {shot_id}...")
        
        # Get scene video path
        video_path = self.get_scene_video_path(scene_id, shot_id)
        if not video_path:
            print(f"❌ Video not found for shot {shot_id}")
            return None
        
        try:
            # Load video clip
            video_clip = VideoFileClip(video_path)
            print(f"   📹 Loaded video: {os.path.basename(video_path)} ({video_clip.duration:.2f}s)")
            
            # Get generated audio files for this shot
            shot_audio_files = self.get_shot_audio_files(shot_id)
            
            if shot_audio_files:
                print(f"   🔊 Found {len(shot_audio_files)} audio files for shot")
                
                # Create composite audio track from generated audio
                generated_audio = self.create_shot_audio_track(shot_audio_files)
                
                if generated_audio:
                    # Check if video has original audio
                    if video_clip.audio is not None:
                        print("   🎵 Video has original audio - mixing with generated audio")
                        
                        # Reduce background audio volume
                        background_audio = video_clip.audio.volumex(self.background_audio_volume)
                        
                        # Ensure generated audio fits video duration
                        if generated_audio.duration > video_clip.duration:
                            print(f"   ✂️ Trimming audio from {generated_audio.duration:.2f}s to {video_clip.duration:.2f}s")
                            generated_audio = generated_audio.subclip(0, video_clip.duration)
                        elif generated_audio.duration < video_clip.duration:
                            print(f"   ⏱️ Audio shorter than video ({generated_audio.duration:.2f}s vs {video_clip.duration:.2f}s)")
                            # Keep audio as is, video will continue with background audio
                        
                        # Create composite audio (background + generated)
                        try:
                            composite_audio = CompositeAudioClip([
                                background_audio,
                                generated_audio.set_start(0)
                            ])
                            video_clip = video_clip.set_audio(composite_audio)
                            print("   ✅ Created composite audio track")
                        except Exception as e:
                            print(f"   ⚠️ Failed to create composite audio, using generated only: {e}")
                            video_clip = video_clip.set_audio(generated_audio)
                    else:
                        print("   🔇 Video has no original audio - using generated audio only")
                        video_clip = video_clip.set_audio(generated_audio)
                else:
                    print("   ❌ Failed to create generated audio track")
            else:
                print("   📢 No generated audio found - keeping original audio")
            
            return video_clip
            
        except Exception as e:
            print(f"❌ Error processing shot {shot_id}: {e}")
            return None
    
    def assemble_scene(self, scene_mapping: Dict[str, Any]) -> Optional[VideoFileClip]:
        """Assemble all shots in a scene into a single video"""
        
        scene_id = scene_mapping.get('scene_id', 'unknown')
        shots = scene_mapping.get('shots', [])
        
        print(f"🎭 Assembling scene {scene_id} with {len(shots)} shots...")
        
        if not shots:
            print(f"❌ No shots found for scene {scene_id}")
            return None
        
        processed_shots = []
        
        for shot_info in shots:
            shot_id = shot_info.get('shot_id', 'unknown')
            
            # Process individual shot
            shot_video = self.process_shot_video(scene_id, shot_id, shot_info)
            
            if shot_video:
                processed_shots.append(shot_video)
                print(f"   ✅ Shot {shot_id} processed successfully")
            else:
                print(f"   ❌ Failed to process shot {shot_id}")
        
        if not processed_shots:
            print(f"❌ No shots could be processed for scene {scene_id}")
            return None
        
        try:
            # Concatenate all shots in the scene
            scene_video = concatenate_videoclips(processed_shots, method="compose")
            print(f"✅ Scene {scene_id} assembled: {len(processed_shots)} shots, {scene_video.duration:.2f}s total")
            return scene_video
            
        except Exception as e:
            print(f"❌ Error assembling scene {scene_id}: {e}")
            return None
    
    def assemble_full_video(self, output_filename: Optional[str] = None) -> Dict[str, Any]:
        """Assemble the complete video from all scenes"""
        
        print("🎬 Starting full video assembly...")
        
        # Load dialog mappings to get scene structure
        dialog_mappings = self.load_dialog_mappings()
        if not dialog_mappings:
            return {"success": False, "error": "Could not load dialog mappings"}
        
        # Generate output filename if not provided
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"final_video_{timestamp}.mp4"
        
        output_path = os.path.join(self.assembly_dir, output_filename)
        
        try:
            assembled_scenes = []
            assembly_stats = {
                "total_scenes": len(dialog_mappings),
                "processed_scenes": 0,
                "failed_scenes": 0,
                "total_shots": 0,
                "processed_shots": 0,
                "scene_details": []
            }
            
            # Process each scene
            for scene_mapping in dialog_mappings:
                scene_id = scene_mapping.get('scene_id', 'unknown')
                shots_count = len(scene_mapping.get('shots', []))
                assembly_stats["total_shots"] += shots_count
                
                scene_video = self.assemble_scene(scene_mapping)
                
                if scene_video:
                    assembled_scenes.append(scene_video)
                    assembly_stats["processed_scenes"] += 1
                    assembly_stats["processed_shots"] += shots_count
                    
                    scene_detail = {
                        "scene_id": scene_id,
                        "duration": scene_video.duration,
                        "shots_count": shots_count,
                        "status": "success"
                    }
                else:
                    assembly_stats["failed_scenes"] += 1
                    scene_detail = {
                        "scene_id": scene_id,
                        "duration": 0,
                        "shots_count": shots_count,
                        "status": "failed"
                    }
                
                assembly_stats["scene_details"].append(scene_detail)
            
            if not assembled_scenes:
                return {
                    "success": False, 
                    "error": "No scenes could be assembled",
                    "stats": assembly_stats
                }
            
            print(f"🎞️ Concatenating {len(assembled_scenes)} scenes...")
            
            # Concatenate all scenes into final video
            final_video = concatenate_videoclips(assembled_scenes, method="compose")
            
            # Write final video
            print(f"💾 Writing final video to: {output_path}")
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                verbose=False,
                logger=None
            )
            
            # Close all clips to free memory
            for scene_video in assembled_scenes:
                scene_video.close()
            final_video.close()
            
            # Calculate final stats
            final_duration = sum(detail["duration"] for detail in assembly_stats["scene_details"])
            assembly_stats.update({
                "final_duration": final_duration,
                "output_path": output_path,
                "output_filename": output_filename,
                "file_size_mb": round(os.path.getsize(output_path) / (1024 * 1024), 2) if os.path.exists(output_path) else 0
            })
            
            print(f"🎉 Video assembly complete!")
            print(f"   📹 Final video: {output_filename}")
            print(f"   ⏱️ Total duration: {final_duration:.2f} seconds")
            print(f"   📊 Scenes: {assembly_stats['processed_scenes']}/{assembly_stats['total_scenes']}")
            print(f"   🎬 Shots: {assembly_stats['processed_shots']}/{assembly_stats['total_shots']}")
            print(f"   📁 File size: {assembly_stats['file_size_mb']} MB")
            
            return {
                "success": True,
                "output_path": output_path,
                "stats": assembly_stats
            }
            
        except Exception as e:
            print(f"❌ Error in video assembly: {e}")
            return {
                "success": False,
                "error": str(e),
                "stats": assembly_stats if 'assembly_stats' in locals() else {}
            }
    
    def get_assembly_status(self) -> Dict[str, Any]:
        """Get status of video assembly components"""
        
        # Check for scene videos
        scene_videos = []
        if os.path.exists(self.scene_videos_dir):
            scene_videos = [f for f in os.listdir(self.scene_videos_dir) if f.endswith('.mp4')]
        
        # Check for audio files
        audio_files = []
        if os.path.exists(self.audio_dir):
            audio_files = [f for f in os.listdir(self.audio_dir) if f.endswith(('.mp3', '.wav'))]
        
        # Check for dialog mappings
        dialog_mapping_exists = os.path.exists(
            os.path.join(self.dialog_mapping_dir, "shot_dialog_mapping.json")
        )
        
        # Check for existing assembled videos
        assembled_videos = []
        if os.path.exists(self.assembly_dir):
            assembled_videos = [f for f in os.listdir(self.assembly_dir) if f.endswith('.mp4')]
        
        return {
            "scene_videos_count": len(scene_videos),
            "scene_videos": scene_videos,
            "audio_files_count": len(audio_files),
            "audio_files": audio_files,
            "dialog_mapping_exists": dialog_mapping_exists,
            "assembled_videos_count": len(assembled_videos),
            "assembled_videos": assembled_videos,
            "ready_for_assembly": len(scene_videos) > 0 and dialog_mapping_exists,
            "assembly_dir": self.assembly_dir
        }
    
    def create_assembly_preview(self, max_scenes: int = 2) -> Dict[str, Any]:
        """Create a preview video with limited scenes for testing"""
        
        print(f"🎬 Creating assembly preview (max {max_scenes} scenes)...")
        
        # Load dialog mappings
        dialog_mappings = self.load_dialog_mappings()
        if not dialog_mappings:
            return {"success": False, "error": "Could not load dialog mappings"}
        
        # Limit to first few scenes for preview
        preview_mappings = dialog_mappings[:max_scenes]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        preview_filename = f"preview_{max_scenes}scenes_{timestamp}.mp4"
        
        # Temporarily replace dialog mappings for preview
        original_mappings = dialog_mappings
        try:
            # Create a temporary method to return limited mappings
            def limited_load_dialog_mappings():
                return preview_mappings
            
            # Replace the method temporarily
            original_method = self.load_dialog_mappings
            self.load_dialog_mappings = limited_load_dialog_mappings
            
            # Assemble preview
            result = self.assemble_full_video(preview_filename)
            
            # Restore original method
            self.load_dialog_mappings = original_method
            
            if result["success"]:
                result["is_preview"] = True
                result["preview_scenes"] = max_scenes
                result["total_available_scenes"] = len(original_mappings)
            
            return result
            
        except Exception as e:
            # Restore original method in case of error
            self.load_dialog_mappings = original_method
            return {"success": False, "error": str(e)}
    
    def cleanup_temp_files(self):
        """Clean up temporary files created during assembly"""
        temp_patterns = ["temp-audio.m4a", "temp-video.mp4"]
        
        for pattern in temp_patterns:
            temp_path = os.path.join(self.assembly_dir, pattern)
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    print(f"🧹 Cleaned up: {pattern}")
                except Exception as e:
                    print(f"⚠️ Could not clean up {pattern}: {e}")
