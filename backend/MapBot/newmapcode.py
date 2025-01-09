import requests

class SafetyRouter:
    def __init__(self, overpass_url, safegraph_url, gemini_url, gemini_api_key, safegraph_api_key):
        self.overpass_url = overpass_url
        self.safegraph_url = safegraph_url
        self.gemini_url = gemini_url
        self.gemini_api_key = AIzaSyCN8nZuR22pM6Vuxhz1cCowBSgots5NOBw
        self.safegraph_api_key = 

    # 1. Fetch POIs from Overpass API
    def fetch_overpass_data(self, lat, lon, radius):
        query = f"""
        [out:json];
        (
          node["amenity"="bar"](around:{radius},{lat},{lon});
          node["amenity"="nightclub"](around:{radius},{lat},{lon});
          node["public_transport"](around:{radius},{lat},{lon});
        );
        out body;
        """
        response = requests.get(self.overpass_url, params={'data': query})
        data = response.json()
        pois = [
            {
                'lat': element['lat'],
                'lon': element['lon'],
                'type': element['tags'].get('amenity', 'public_transport'),
                'risk_level': 'high' if element['tags'].get('amenity') in ['bar', 'nightclub'] else 'medium'
            }
            for element in data.get('elements', [])
        ]
        return pois

    # 2. Fetch POI and foot traffic data from SafeGraph API
    def fetch_safegraph_data(self, lat, lon, radius):
        headers = {'Authorization': f'Bearer {self.safegraph_api_key}'}
        headers = {'Authorization': f'Bearer {self.gemini_api_key}'}
        params = {
            'latitude': lat,
            'longitude': lon,
            'radius': radius,
            'categories': 'food,nightlife,entertainment',
        }
        response = requests.get(f"{self.safegraph_url}/places", headers=headers, params=params)
        data = response.json()
        pois = [
            {
                'lat': place['location']['latitude'],
                'lon': place['location']['longitude'],
                'category': place['category'],
                'traffic_level': place.get('foot_traffic', 'low')
            }
            for place in data.get('places', [])
        ]
        return pois

    # 3. Analyze route safety
    def analyze_route_safety(self, route):
        route_score = 0
        segment_scores = []
        for segment in route['segments']:
            segment_lat = segment['start_lat']
            segment_lon = segment['start_lon']
            overpass_pois = self.fetch_overpass_data(segment_lat, segment_lon, 500)
            safegraph_pois = self.fetch_safegraph_data(segment_lat, segment_lon, 500)
            
            poi_count = len(overpass_pois) + len(safegraph_pois)
            traffic_weight = sum(1 for poi in safegraph_pois if poi['traffic_level'] == 'high')
            risk_weight = sum(1 for poi in overpass_pois if poi['risk_level'] == 'high')
            
            segment_score = poi_count + traffic_weight + risk_weight
            segment_scores.append({'segment': segment, 'score': segment_score})
            route_score += segment_score

        return {'segment_scores': segment_scores, 'overall_score': route_score}

    # 4. Generate safety analysis summary with Gemini
    def generate_gemini_safety_analysis(self, segment_data):
        headers = {
            'Authorization': f'Bearer {self.gemini_api_key}',
            'Content-Type': 'application/json'
        }
        response = requests.post(self.gemini_url, headers=headers, json={'data': segment_data})
        analysis = response.json().get('analysis', 'No analysis available')
        return analysis

    # 5. Visualize route with safety information
    def visualize_route_with_safety(self, route):
        for segment_data in self.analyze_route_safety(route)['segment_scores']:
            segment = segment_data['segment']
            score = segment_data['score']
            color = 'green' if score < 2 else 'yellow' if score < 5 else 'red'
            gemini_analysis = self.generate_gemini_safety_analysis(segment_data)
            
            # Example output format
            print(f"Segment {segment} - Score: {score}, Color: {color}, Analysis: {gemini_analysis}")

    # 6. Get the safest route
    def get_safest_route(self, route_options):
        scored_routes = [self.analyze_route_safety(route) for route in route_options]
        safest_route = min(scored_routes, key=lambda r: r['overall_score'])
        
        for segment_data in safest_route['segment_scores']:
            gemini_summary = self.generate_gemini_safety_analysis(segment_data)
            segment_data['gemini_summary'] = gemini_summary
        
        return safest_route

    # 7. Real-time adjustments (optional, placeholder)
    def update_real_time_safety(self):
        # Gemini cannot process real-time data directly, so this function
        # would require external real-time data sources like news or social media APIs
        # with NLP processing to interpret real-time events.
        print("Real-time updates are currently unsupported.")

# Example usage
overpass_url = "https://overpass-api.de/api/interpreter"
safegraph_url = "https://api.safegraph.com/v1"
gemini_url = "https://api.gemini.com/analyze"
gemini_api_key = "your_gemini_api_key"

safety_router = SafetyRouter(overpass_url, safegraph_url, gemini_url, gemini_api_key)
route_example = {
    'segments': [
        {'start_lat': 40.7128, 'start_lon': -74.0060, 'end_lat': 40.7138, 'end_lon': -74.0050},
        {'start_lat': 40.7138, 'start_lon': -74.0050, 'end_lat': 40.7148, 'end_lon': -74.0040},
    ]
}
safest_route = safety_router.get_safest_route([route_example])
safety_router.visualize_route_with_safety(route_example)
