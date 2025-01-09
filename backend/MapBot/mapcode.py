import os
import sys
import requests
import folium
import google.generativeai as genai
from dotenv import load_dotenv
from typing import List, Dict, Tuple, Optional
import webbrowser
from pathlib import Path
from time import sleep
from datetime import datetime

class SafetyRouter:
    def __init__(self):
        """Initialize SafetyRouter with Geoapify configuration."""
        if not self._load_environment():
            sys.exit(1)
            
        # Base URLs for Geoapify APIs
        self.geocode_url = "https://api.geoapify.com/v1/geocode/search"
        self.autocomplete_url = "https://api.geoapify.com/v1/geocode/autocomplete"
        self.routing_url = "https://api.geoapify.com/v1/routing"
        
        # Configure Gemini
        genai.configure(api_key=self.gemini_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Define risk colors for visualization
        self.risk_colors = {
            'low': '#00ff00',    # Green
            'medium': '#ffff00',  # Yellow
            'high': '#ff0000'    # Red
        }
        
        # South Asian country codes for location bias
        self.south_asian_countries = [
            'in',  # India
            'pk',  # Pakistan
            'bd',  # Bangladesh
            'np',  # Nepal
            'lk',  # Sri Lanka
            'bt',  # Bhutan
            'mv',  # Maldives
            'af'   # Afghanistan
        ]

    def _load_environment(self) -> bool:
        """Load and validate environment variables with better error checking."""
        try:
            load_dotenv()
            
            self.gemini_key = os.getenv('GOOGLE_API_KEY')
            self.geoapify_key = os.getenv('GEOAPIFY_API_KEY')
            
            missing_keys = []
            if not self.gemini_key:
                missing_keys.append('GOOGLE_API_KEY')
            if not self.geoapify_key:
                missing_keys.append('GEOAPIFY_API_KEY')
            
            if missing_keys:
                print("\nError: Missing required API keys in .env file:")
                for key in missing_keys:
                    print(f"- {key}")
                print("\nPlease create a .env file with the following format:")
                print("GOOGLE_API_KEY=your_google_api_key")
                print("GEOAPIFY_API_KEY=your_geoapify_api_key")
                return False
            
            # Validate API key format
            if len(self.geoapify_key) < 32:  # Basic validation
                print("Warning: Geoapify API key appears to be invalid")
                return False
            
            return True
            
        except Exception as e:
            print(f"Error loading environment: {str(e)}")
            return False

    def get_location_suggestions(self, query: str, country: Optional[str] = None) -> List[Dict]:
        """Get location suggestions with South Asian bias."""
        try:
            # Clean the query
            cleaned_query = query.strip().replace("  ", " ")
            
            # Base parameters
            params = {
                'text': cleaned_query,
                'format': 'json',
                'apiKey': self.geoapify_key,
                'limit': 5,
                'type': 'street,amenity,locality,city,county,district',
                'fuzzy': 0.8
            }
            
            # Add bias towards South Asian countries
            if not country:
                bias_countries = ','.join(f'countrycode:{c}' for c in self.south_asian_countries)
                params['bias'] = bias_countries
            else:
                params['filter'] = f'country:{country}'
            
            response = requests.get(self.autocomplete_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            suggestions = []
            
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                
                # Build comprehensive address
                address_parts = []
                
                # Add building number and street
                if props.get('housenumber') and props.get('street'):
                    address_parts.append(f"{props['housenumber']} {props['street']}")
                elif props.get('street'):
                    address_parts.append(props['street'])
                
                # Add local details
                for key in ['district', 'suburb', 'city', 'state', 'country']:
                    if props.get(key):
                        address_parts.append(props[key])
                
                # Add local language name if available
                local_name = props.get('local_name')
                if local_name and local_name != props.get('name'):
                    address_parts.append(f"(Local: {local_name})")
                
                formatted_address = ', '.join(filter(None, address_parts))
                
                suggestions.append({
                    'formatted': formatted_address,
                    'coordinates': feature['geometry']['coordinates'],
                    'type': props.get('result_type', 'location').replace('_', ' ').title(),
                    'confidence': props.get('rank', {}).get('confidence', 0),
                    'details': props
                })
            
            # Sort by confidence score
            return sorted(suggestions, key=lambda x: x['confidence'], reverse=True)
            
        except Exception as e:
            print(f"Error getting location suggestions: {str(e)}")
            return []

    def geocode_location(self, location: str) -> Optional[Tuple[float, float]]:
        """Convert a location string into coordinates with improved error handling."""
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                print(f"\nGeocoding location: {location}")
                
                # Prepare parameters with South Asian bias
                params = {
                    'text': location,
                    'format': 'json',
                    'apiKey': self.geoapify_key,
                    'bias': ','.join(f'countrycode:{c}' for c in self.south_asian_countries),
                    'fuzzy': 0.8
                }
                
                response = requests.get(self.geocode_url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                if not data.get('features'):
                    if attempt < max_retries - 1:
                        print(f"Location not found, retrying... ({attempt + 1}/{max_retries})")
                        sleep(retry_delay)
                        continue
                    print(f"Location not found: {location}")
                    return None
                
                # Extract coordinates (Geoapify returns [longitude, latitude])
                coordinates = data['features'][0]['geometry']['coordinates']
                # Convert to (latitude, longitude) format
                coordinates = (coordinates[1], coordinates[0])
                
                print(f"✓ Found coordinates: {coordinates}")
                return coordinates
                
            except requests.exceptions.Timeout:
                print(f"Request timed out, retrying... ({attempt + 1}/{max_retries})")
                sleep(retry_delay)
            except Exception as e:
                print(f"Attempt {attempt + 1}/{max_retries}: {str(e)}")
                if attempt < max_retries - 1:
                    sleep(retry_delay)
                else:
                    print("Failed to geocode location after all attempts")
                    return None
        
        return None

    def get_route(self, start: Tuple[float, float], end: Tuple[float, float]) -> Optional[List[Dict]]:
        """Get route segments from Geoapify Routing API with improved error handling."""
        try:
            print(f"\nGetting route from {start} to {end}...")
            
            params = {
                'waypoints': f"{start[1]},{start[0]}|{end[1]},{end[0]}",
                'mode': 'drive',
                'apiKey': self.geoapify_key
            }
            
            response = requests.get(f"{self.routing_url}", params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            if not data.get('features'):
                print("No route found")
                return None
            
            segments = self._extract_segments(data['features'][0])
            
            if not segments:
                print("No route segments found in the response")
                return None
            
            print(f"✓ Retrieved {len(segments)} route segments")
            return segments
            
        except requests.exceptions.Timeout:
            print("Route request timed out. Please try again.")
            return None
        except Exception as e:
            print(f"Error getting route: {str(e)}")
            return None

    def _extract_segments(self, route_data: Dict) -> List[Dict]:
        """Extract route segments with validation."""
        segments = []
        try:
            coordinates = route_data['geometry']['coordinates']
            
            # Validate coordinates
            for coord in coordinates:
                if len(coord) >= 2:
                    segments.append({
                        'lat': float(coord[1]),
                        'lon': float(coord[0])
                    })
            
            return segments
            
        except Exception as e:
            print(f"Error extracting segments: {str(e)}")
            return segments

    def assess_safety(self, segment: Dict) -> Dict:
        """Assess safety risk for a route segment using Gemini Pro."""
        try:
            prompt = f"""
            Assess the safety risk level for a route segment at coordinates:
            Latitude: {segment['lat']}, Longitude: {segment['lon']}
            
            Respond with exactly one word (low, medium, or high):
            """
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.model.generate_content(prompt)
                    risk_level = response.text.strip().lower()
                    
                    if risk_level in ['low', 'medium', 'high']:
                        segment['risk_level'] = risk_level
                        return segment
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        sleep(1)
                    else:
                        print(f"Error assessing safety: {str(e)}")
            
            segment['risk_level'] = 'medium'
            return segment
            
        except Exception as e:
            print(f"Unexpected error in safety assessment: {str(e)}")
            segment['risk_level'] = 'medium'
            return segment

    def create_safety_map(self, segments: List[Dict], start_location: str, end_location: str) -> Optional[str]:
        """Create an interactive map showing route segments with risk levels."""
        try:
            print("\nCreating safety map...")
            
            if not segments:
                print("No segments provided for map creation")
                return None
            
            # Calculate map center
            start_coords = (float(segments[0]['lat']), float(segments[0]['lon']))
            end_coords = (float(segments[-1]['lat']), float(segments[-1]['lon']))
            center_lat = (start_coords[0] + end_coords[0]) / 2
            center_lon = (start_coords[1] + end_coords[1]) / 2
            
            # Create base map with Geoapify tiles
            m = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=10,
                tiles=f'https://maps.geoapify.com/v1/tile/osm-bright/{{z}}/{{x}}/{{y}}.png?apiKey={self.geoapify_key}',
                attr='Geoapify'
            )
            
            # Add route segments
            for i in range(len(segments)-1):
                try:
                    start = [segments[i]['lat'], segments[i]['lon']]
                    end = [segments[i+1]['lat'], segments[i+1]['lon']]
                    risk_level = segments[i].get('risk_level', 'medium')
                    
                    folium.PolyLine(
                        locations=[start, end],
                        color=self.risk_colors[risk_level],
                        weight=4,
                        opacity=0.8,
                        popup=f"Risk Level: {risk_level.capitalize()}"
                    ).add_to(m)
                    
                except (KeyError, ValueError) as e:
                    print(f"Warning: Skipping segment {i} due to error: {e}")
                    continue
            
            # Add markers
            folium.Marker(
                start_coords,
                popup=f"Start: {start_location}",
                icon=folium.Icon(color='green')
            ).add_to(m)
            
            folium.Marker(
                end_coords,
                popup=f"End: {end_location}",
                icon=folium.Icon(color='red')
            ).add_to(m)
            
            # Add legend
            legend_html = '''
                <div style="position: fixed; 
                            bottom: 50px; right: 50px; 
                            border:2px solid grey; z-index:9999; 
                            background-color:white;
                            padding:10px;
                            font-size:14px;">
                    <p><strong>Risk Levels</strong></p>
                    <p>
                        <span style="color:#00ff00;">■</span> Low Risk<br>
                        <span style="color:#ffff00;">■</span> Medium Risk<br>
                        <span style="color:#ff0000;">■</span> High Risk
                    </p>
                </div>
            '''
            m.get_root().html.add_child(folium.Element(legend_html))
            
            # Save map
            output_dir = Path('safety_routes')
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / 'safety_route.html'
            m.save(str(output_file))
            
            print(f"✓ Map saved as {output_file}")
            return str(output_file)
            
        except Exception as e:
            print(f"Error creating map: {str(e)}")
            return None

def get_location_input(prompt_text: str, router: SafetyRouter) -> Optional[str]:
    """Get and validate location input with improved suggestions."""
    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts:
        try:
            print("\n" + prompt_text)
            query = input("Enter location (or 'q' to quit): ").strip()
            
            if query.lower() == 'q':
                return None
            
            if len(query) < 3:
                print("Please enter at least 3 characters for the search.")
                continue
            
            print("\nSearching for locations...")
            suggestions = router.get_location_suggestions(query)
            
            if not suggestions:
                print("\nNo locations found. Tips:")
                print("- Try entering the location in local language")
                print("- Include city or state name")
                print("- Check spelling")
                print("- Try adding country name (e.g., 'Mumbai, India')")
                
                # Offer country-specific search
                country = input("\nEnter country code for specific search (e.g., in, pk, bd) or press Enter to skip: ").strip().lower()
                if country:
                    suggestions = router.get_location_suggestions(query, country)
                
                if not suggestions:
                    attempt += 1
                    if attempt < max_attempts:
                        print(f"\n{max_attempts - attempt} attempts remaining")
                    continue
            
            print("\nFound these locations:")
            for i, suggestion in enumerate(suggestions, 1):
                confidence = suggestion['confidence']
                stars = "★" * int((confidence / 100) * 5)  # Convert confidence to 0-5 stars
                print(f"{i}. {suggestion['formatted']}")
                print(f"   Type: {suggestion['type']}")
                print(f"   Confidence: {stars}")
            
            print("\nOptions:")
            print("0. Search again with a different query")
            choice = input("\nEnter number (1-5) to select, 0 to search again: ").strip()
            
            if choice == "0":
                attempt = 0  # Reset attempts for new search
                continue
            
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(suggestions):
                    return suggestions[choice_num - 1]['formatted']
            except ValueError:
                print("Invalid input. Please enter a number.")
            
        except KeyboardInterrupt:
            print("\nSearch cancelled by user")
            return None
        except Exception as e:
            print(f"Error during location input: {e}")
            attempt += 1
    
    print("\nMaximum search attempts reached. Please try again later.")
    return None

def main():
    """Main function with improved error handling and user experience."""
    try:
        print("\nSafety Router - Route Risk Assessment Tool")
        print("==========================================")
        print("Optimized for South Asian locations")
        print("Supported countries: India, Pakistan, Bangladesh, Nepal, Sri Lanka, Bhutan, Maldives, Afghanistan")
        print("==========================================")
        
        # Initialize SafetyRouter
        router = SafetyRouter()
        
        # Get location inputs with improved suggestions
        start_location = get_location_input("\nEnter starting location (e.g., 'Connaught Place, Delhi' or 'Gulshan, Dhaka'): ", router)
        if not start_location:
            print("\nOperation cancelled.")
            return
        
        end_location = get_location_input("Enter destination location: ", router)
        if not end_location:
            print("\nOperation cancelled.")
            return
        
        # Convert locations to coordinates
        print("\nProcessing locations...")
        start_coords = router.geocode_location(start_location)
        if not start_coords:
            print("\nCould not find starting location. Please try:")
            print("- Adding more location details (city, state, country)")
            print("- Using local language names")
            print("- Checking for spelling errors")
            return
            
        end_coords = router.geocode_location(end_location)
        if not end_coords:
            print("\nCould not find destination location. Please try:")
            print("- Adding more location details (city, state, country)")
            print("- Using local language names")
            print("- Checking for spelling errors")
            return
        
        # Get route segments
        print(f"\nAnalyzing route from {start_location} to {end_location}...")
        segments = router.get_route(start_coords, end_coords)
        if not segments:
            print("\nCould not find a route between the specified locations.")
            print("This could be because:")
            print("- The locations are not connected by roads")
            print("- The route crosses unsupported regions")
            print("- One or both locations are not accessible by road")
            return
        
        # Assess safety for each segment
        print("\nAssessing safety risks...")
        safe_segments = []
        total_segments = len(segments)
        
        for i, segment in enumerate(segments, 1):
            print(f"\rProgress: {i}/{total_segments} segments assessed", end='', flush=True)
            safe_segments.append(router.assess_safety(segment))
        print("\n✓ Safety assessment complete")
        
        # Create and display visualization
        map_file = router.create_safety_map(safe_segments, start_location, end_location)
        if not map_file:
            print("\nFailed to create safety map.")
            print("Please check if you have write permissions in the current directory.")
            return
            
        print("\nOpening map in your default web browser...")
        webbrowser.open(f'file://{os.path.abspath(map_file)}')
        
        print("\nProcess completed successfully! 🎉")
        print(f"\nThe route map has been saved to: {map_file}")
        print("You can reopen it any time in your web browser.")
        
        # Offer to analyze another route
        if input("\nWould you like to analyze another route? (y/n): ").lower().strip() == 'y':
            main()
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        print("Please try again or report this issue if it persists.")

if __name__ == "__main__":
    main()