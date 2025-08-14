"""
Map and Geography System for CampusLifeBench
All natural language communications/returns MUST use English only
"""

import json
import heapq
import itertools
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

from ..tools import ToolResult, ensure_english_message


@dataclass
class GeographyState:
    """Current geography state of the agent"""
    current_location_id: str
    current_location_name: str
    walk_history: List[List[str]]


class MapLookupSystem:
    """
    Static map information lookup system
    Provides read-only access to campus map data
    """
    
    def __init__(self, map_data_path: Path):
        """
        Initialize map lookup system
        
        Args:
            map_data_path: Path to map data JSON file
        """
        self.map_data_path = map_data_path
        self._map_data: Optional[Dict[str, Any]] = None
        self._load_map_data()
    
    def _load_map_data(self):
        """Load map data from JSON file"""
        try:
            with open(self.map_data_path, 'r', encoding='utf-8') as f:
                self._map_data = json.load(f)
        except FileNotFoundError:
            # Create minimal map data if file doesn't exist
            self._map_data = {
                "nodes": [
                    {
                        "id": "B083",
                        "name": "Lakeside Dormitory",
                        "aliases": ["Dorm", "Dormitory"],
                        "type": "Residential",
                        "zone": "Residential Area",
                        "internal_amenities": {
                            "floor_1": ["Lobby", "Common Room"],
                            "floor_2": ["Student Rooms (201-220)"]
                        }
                    }
                ],
                "edges": [],
                "building_complexes": []
            }
    
    def find_building_id(self, building_name: str) -> ToolResult:
        """
        Find building ID by name or alias
        
        Args:
            building_name: Building name or alias to search for
            
        Returns:
            ToolResult with building ID or error message
        """
        try:
            if not building_name:
                return ToolResult.failure("Building name is required.")
            
            building_name_lower = building_name.lower()
            
            for node in self._map_data["nodes"]:
                # Check exact name match
                if node["name"].lower() == building_name_lower:
                    message = f"Found building '{node['name']}' with ID '{node['id']}'."
                    return ToolResult.success(ensure_english_message(message), {
                        "building_id": node["id"],
                        "building_name": node["name"]
                    })
                
                # Check aliases
                for alias in node.get("aliases", []):
                    if alias.lower() == building_name_lower:
                        message = f"Found building '{node['name']}' with ID '{node['id']}' (matched alias '{alias}')."
                        return ToolResult.success(ensure_english_message(message), {
                            "building_id": node["id"],
                            "building_name": node["name"]
                        })
            
            return ToolResult.failure(f"Building '{building_name}' not found.")
            
        except Exception as e:
            return ToolResult.error(f"Failed to find building ID: {str(e)}")
    
    def get_building_details(self, building_id: str) -> ToolResult:
        """
        Get detailed information about a building
        
        Args:
            building_id: Building ID to get details for
            
        Returns:
            ToolResult with building details
        """
        try:
            if not building_id:
                return ToolResult.failure("Building ID is required.")
            
            for node in self._map_data["nodes"]:
                if node["id"] == building_id:
                    # Format amenities for display
                    amenities_text = ""
                    for floor, items in node.get("internal_amenities", {}).items():
                        amenities_text += f"\n  {floor}: {', '.join(items)}"
                    
                    message = f"Building Details for {node['name']} (ID: {building_id}):"
                    message += f"\n- Type: {node.get('type', 'Unknown')}"
                    message += f"\n- Zone: {node.get('zone', 'Unknown')}"
                    message += f"\n- Aliases: {', '.join(node.get('aliases', []))}"
                    if amenities_text:
                        message += f"\n- Internal Amenities:{amenities_text}"
                    
                    return ToolResult.success(ensure_english_message(message), node)
            
            return ToolResult.failure(f"Building with ID '{building_id}' not found.")
            
        except Exception as e:
            return ToolResult.error(f"Failed to get building details: {str(e)}")
    
    def find_room_location(self, room_query: str, building_id: Optional[str] = None, zone: Optional[str] = None) -> ToolResult:
        """
        Find room location within campus or specified area
        
        Args:
            room_query: Room name or number to search for
            building_id: Optional building ID to limit search
            zone: Optional zone to limit search
            
        Returns:
            ToolResult with room location information
        """
        try:
            if not room_query:
                return ToolResult.failure("Room query is required.")
            
            room_query_lower = room_query.lower()
            found_rooms = []
            
            for node in self._map_data["nodes"]:
                # Apply filters
                if building_id and node["id"] != building_id:
                    continue
                if zone and node.get("zone") != zone:
                    continue
                
                # Search in internal amenities
                for floor, items in node.get("internal_amenities", {}).items():
                    for item in items:
                        if room_query_lower in item.lower():
                            found_rooms.append({
                                "building_id": node["id"],
                                "building_name": node["name"],
                                "floor": floor,
                                "room_name": item
                            })
            
            if not found_rooms:
                return ToolResult.failure(f"No rooms found matching '{room_query}'.")
            
            if len(found_rooms) == 1:
                room = found_rooms[0]
                message = f"Found room '{room['room_name']}' on {room['floor']} of {room['building_name']} (ID: {room['building_id']})."
            else:
                message = f"Found {len(found_rooms)} rooms matching '{room_query}':"
                for room in found_rooms:
                    message += f"\n- {room['room_name']} on {room['floor']} of {room['building_name']} (ID: {room['building_id']})"
            
            return ToolResult.success(ensure_english_message(message), {"rooms": found_rooms})
            
        except Exception as e:
            return ToolResult.error(f"Failed to find room location: {str(e)}")
    
    def find_optimal_path(self, source_building_id: str, target_building_id: str, constraints: Optional[Dict[str, Any]] = None) -> ToolResult:
        """
        Find optimal path between two buildings using deterministic algorithm
        
        Args:
            source_building_id: Starting building ID
            target_building_id: Target building ID
            constraints: Optional path constraints
            
        Returns:
            ToolResult with optimal path information
        """
        try:
            if not all([source_building_id, target_building_id]):
                return ToolResult.failure("Both source and target building IDs are required.")
            
            if constraints is None:
                constraints = {}
            
            # Use the deterministic path finding algorithm
            result = self._find_optimal_path_algorithm(self._map_data, source_building_id, target_building_id, constraints)
            
            if "error" in result:
                return ToolResult.failure(result["error"])
            
            path = result["path"]

            # Format path for display
            path_names = []
            for building_id in path:
                for node in self._map_data["nodes"]:
                    if node["id"] == building_id:
                        path_names.append(node["name"])
                        break
                else:
                    path_names.append(building_id)  # Fallback to ID if name not found

            message = f"Optimal path found: {' -> '.join(path_names)}."

            return ToolResult.success(ensure_english_message(message), {
                "path": path,
                "path_names": path_names
            })
            
        except Exception as e:
            return ToolResult.error(f"Failed to find optimal path: {str(e)}")
    
    def _find_optimal_path_algorithm(self, map_data, source_id, target_id, constraints=None):
        """
        Deterministic path finding algorithm (from find_optimal_path.py)
        """
        if constraints is None:
            constraints = {}

        nodes = {node['id']: node for node in map_data['nodes']}
        
        if source_id not in nodes:
            return {"error": f"No path could be found from {source_id} to {target_id}."}
        if target_id not in nodes:
            return {"error": f"No path could be found from {source_id} to {target_id}."}

        graph = {node_id: [] for node_id in nodes}
        for edge in map_data.get('edges', []):
            source, target = edge.get('source'), edge.get('target')
            if source in nodes and target in nodes:
                properties = edge.get('properties', {})
                time_cost = edge.get('time_cost', 0)
                properties['is_complex_path'] = False 
                graph[source].append((target, time_cost, properties))
                graph[target].append((source, time_cost, properties))

        for complex_group in map_data.get('building_complexes', []):
            member_ids = complex_group.get('member_ids', [])
            for u, v in itertools.combinations(member_ids, 2):
                if u in nodes and v in nodes:
                    properties = {'is_complex_path': True}
                    time_cost = 0
                    graph[u].append((v, time_cost, properties))
                    graph[v].append((u, time_cost, properties))

        # Core algorithm with dynamic penalty logic
        PENALTY_MULTIPLIER = 0.5 

        priority_queue = [(0, 1, 0, source_id, [source_id])]
        visited_costs = {}

        while priority_queue:
            priority_cost, path_len, real_time_cost, current_node, path = heapq.heappop(priority_queue)

            if current_node in visited_costs and visited_costs[current_node] <= (priority_cost, path_len):
                continue
            
            visited_costs[current_node] = (priority_cost, path_len)

            if current_node == target_id:
                return {"path": path, "total_time_cost": real_time_cost}

            for neighbor, edge_time, properties in graph.get(current_node, []):
                
                unmet_constraints = 0
                if not properties.get('is_complex_path', False):
                    for key, required_value in constraints.items():
                        edge_value = properties.get(key)
                        
                        is_violated = False
                        if edge_value is None:
                            is_violated = True
                        elif key == 'rain_exposure' and required_value == 'Covered' and 'Exposed' in edge_value:
                            is_violated = True
                        elif key != 'rain_exposure' and edge_value != required_value:
                            is_violated = True
                        
                        if is_violated:
                            unmet_constraints += 1

                base_cost = edge_time if edge_time > 0 else 0.01 
                cost_multiplier = 1 + (unmet_constraints * PENALTY_MULTIPLIER)
                effective_edge_cost = base_cost * cost_multiplier

                new_priority_cost = priority_cost + effective_edge_cost
                new_real_time_cost = real_time_cost + edge_time
                new_path_len = path_len + 1

                if neighbor not in visited_costs or (new_priority_cost, new_path_len) < visited_costs[neighbor]:
                    heapq.heappush(priority_queue, (new_priority_cost, new_path_len, new_real_time_cost, neighbor, path + [neighbor]))

        return {"error": f"No path could be found from {source_id} to {target_id}."}
    
    def query_buildings_by_property(self, zone: Optional[str] = None, building_type: Optional[str] = None, amenity: Optional[str] = None) -> ToolResult:
        """
        Query buildings by properties
        
        Args:
            zone: Zone to filter by
            building_type: Building type to filter by
            amenity: Amenity to filter by
            
        Returns:
            ToolResult with matching buildings
        """
        try:
            matching_buildings = []
            
            for node in self._map_data["nodes"]:
                # Apply filters
                if zone and node.get("zone") != zone:
                    continue
                if building_type and node.get("type") != building_type:
                    continue
                if amenity:
                    # Search in internal amenities
                    found_amenity = False
                    for floor, items in node.get("internal_amenities", {}).items():
                        if any(amenity.lower() in item.lower() for item in items):
                            found_amenity = True
                            break
                    if not found_amenity:
                        continue
                
                matching_buildings.append({
                    "id": node["id"],
                    "name": node["name"],
                    "type": node.get("type"),
                    "zone": node.get("zone")
                })
            
            if not matching_buildings:
                return ToolResult.failure("No buildings found matching the specified criteria.")
            
            message = f"Found {len(matching_buildings)} building(s) matching criteria:"
            for building in matching_buildings:
                message += f"\n- {building['name']} (ID: {building['id']}, Type: {building['type']}, Zone: {building['zone']})"
            
            return ToolResult.success(ensure_english_message(message), {"buildings": matching_buildings})
            
        except Exception as e:
            return ToolResult.error(f"Failed to query buildings: {str(e)}")
    
    def get_building_complex_info(self, building_id: str) -> ToolResult:
        """
        Get building complex information
        
        Args:
            building_id: Building ID to check for complex membership
            
        Returns:
            ToolResult with complex information
        """
        try:
            if not building_id:
                return ToolResult.failure("Building ID is required.")
            
            for complex_group in self._map_data.get("building_complexes", []):
                if building_id in complex_group.get("member_ids", []):
                    message = f"Building {building_id} is part of the '{complex_group.get('name', 'Unnamed')}' complex."
                    message += f" Complex members: {', '.join(complex_group['member_ids'])}."
                    
                    return ToolResult.success(ensure_english_message(message), complex_group)
            
            return ToolResult.success(f"Building {building_id} is not part of any building complex.", {
                "is_complex_member": False
            })
            
        except Exception as e:
            return ToolResult.error(f"Failed to get building complex info: {str(e)}")
    
    def list_valid_query_properties(self) -> ToolResult:
        """
        List all valid query properties
        
        Returns:
            ToolResult with available properties
        """
        try:
            # Extract unique properties from map data
            zones = set()
            types = set()
            
            for node in self._map_data["nodes"]:
                if "zone" in node:
                    zones.add(node["zone"])
                if "type" in node:
                    types.add(node["type"])
            
            message = "Available query properties:"
            message += f"\n- Zones: {', '.join(sorted(zones))}"
            message += f"\n- Building Types: {', '.join(sorted(types))}"
            
            return ToolResult.success(ensure_english_message(message), {
                "zones": sorted(zones),
                "building_types": sorted(types)
            })
            
        except Exception as e:
            return ToolResult.error(f"Failed to list valid properties: {str(e)}")


class GeographySystem:
    """
    Agent location tracking and movement system
    Maintains current location state and movement history
    """
    
    def __init__(self, map_lookup_system: MapLookupSystem):
        """
        Initialize geography system
        
        Args:
            map_lookup_system: Reference to map lookup system
        """
        self.map_lookup_system = map_lookup_system
        
        # Initialize at dormitory
        self._state = GeographyState(
            current_location_id="B083",
            current_location_name="Lakeside Dormitory",
            walk_history=[]
        )
    
    def daily_reset(self) -> None:
        """
        Reset agent location to dormitory at start of new day
        Called by CampusEnvironment during daily_reset
        """
        self._state.current_location_id = "B083"
        self._state.current_location_name = "Lakeside Dormitory"
        self._state.walk_history = []
    
    def set_location(self, building_id: str) -> ToolResult:
        """
        Set agent location (used for source_building_id)
        Called by CampusEnvironment during task initialization
        
        Args:
            building_id: Building ID to set as current location
            
        Returns:
            ToolResult indicating success or failure
        """
        try:
            # Get building details to validate and get name
            result = self.map_lookup_system.get_building_details(building_id)
            if not result.is_success():
                return ToolResult.failure(f"Cannot set location to unknown building '{building_id}'.")
            
            building_name = result.data["name"]
            self._state.current_location_id = building_id
            self._state.current_location_name = building_name
            
            message = f"You are now located at {building_name}."
            return ToolResult.success(ensure_english_message(message))
            
        except Exception as e:
            return ToolResult.error(f"Failed to set location: {str(e)}")
    
    def walk_to(self, path_info: Dict[str, Any]) -> ToolResult:
        """
        Walk to a location using path information from find_optimal_path
        
        Args:
            path_info: Path information dictionary with 'path' key
            
        Returns:
            ToolResult indicating movement success or failure
        """
        try:
            # Validate path_info format
            if not isinstance(path_info, dict) or "path" not in path_info:
                return ToolResult.failure("Invalid path_info format. Must be a dictionary with 'path' key.")
            
            path = path_info["path"]
            if not isinstance(path, list) or len(path) < 2:
                return ToolResult.failure("Invalid path. Must be a list with at least 2 locations.")
            
            # Validate starting location
            if path[0] != self._state.current_location_id:
                return ToolResult.failure(f"Path starting location '{path[0]}' does not match current location '{self._state.current_location_id}'.")
            
            # Update location to destination
            destination_id = path[-1]
            result = self.map_lookup_system.get_building_details(destination_id)
            if not result.is_success():
                return ToolResult.failure(f"Invalid destination building '{destination_id}'.")
            
            destination_name = result.data["name"]
            
            # Update state
            self._state.current_location_id = destination_id
            self._state.current_location_name = destination_name
            self._state.walk_history.append(path)
            
            message = f"Successfully walked to {destination_name}. You are now at {destination_name}."
            return ToolResult.success(ensure_english_message(message), {
                "new_location_id": destination_id,
                "new_location_name": destination_name,
                "path_taken": path
            })
            
        except Exception as e:
            return ToolResult.error(f"Failed to walk to location: {str(e)}")
    
    def get_current_location(self) -> ToolResult:
        """
        Get current location information
        
        Returns:
            ToolResult with current location details
        """
        try:
            message = f"You are currently at {self._state.current_location_name} (ID: {self._state.current_location_id})."
            return ToolResult.success(ensure_english_message(message), {
                "building_id": self._state.current_location_id,
                "building_name": self._state.current_location_name
            })
            
        except Exception as e:
            return ToolResult.error(f"Failed to get current location: {str(e)}")
    
    def get_state_for_evaluation(self) -> GeographyState:
        """
        Get current geography state for evaluation
        Used by CampusTask during evaluation
        
        Returns:
            Current GeographyState object
        """
        return self._state
