#!/usr/bin/env python3
"""
Location Generation Step for Streamlit Pipeline
"""

import streamlit as st
import os
import json
from typing import List, Dict, Any
from location_generation.location_generator import LocationGenerator, LocationInfo
from project_manager import ProjectManager
from ui_components import render_step_header

def location_generation_step(project_manager: ProjectManager):
    """Location Generation Step"""
    render_step_header("Location Generation", 2)
    
    # Check if we have script data
    script_data = project_manager.get_session_data("formatted_script")
    print(script_data)
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
        print(script_locations)
        
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

def render_location_display(locations: List[LocationInfo], show_regenerate: bool = False):
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
