"""
Production IoT Sensor Simulator with Historical Data Generation
Generates realistic agricultural data with known patterns for ML training
"""

import json
import random
import time
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Literal, Tuple
from pymongo import MongoClient
from hdfs import InsecureClient
import os
import requests

# ==========================================
# 1. RBAC - Role Manager
# ==========================================

class RoleManager:
    """Manages User Roles and Permissions"""
    
    ROLES = {
        'ADMIN': ['create_field', 'delete_field', 'manage_users', 'run_simulation', 'view_all_data'],
        'FARMER': ['view_own_data', 'view_field', 'export_data'],
        'RESEARCHER': ['view_all_data', 'run_simulation', 'access_hdfs']
    }
    
    def __init__(self, db):
        self.users = db['users']
        
    def create_user(self, user_id: str, role: str, name: str):
        """Create a new user with specific role"""
        if role not in self.ROLES:
            raise ValueError(f"Invalid role: {role}")
            
        self.users.update_one(
            {'user_id': user_id},
            {'$set': {
                'role': role,
                'name': name,
                'created_at': datetime.now(timezone.utc),
                'permissions': self.ROLES[role]
            }},
            upsert=True
        )
        print(f"👤 User {user_id} created as {role}")

    def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specific permission"""
        user = self.users.find_one({'user_id': user_id})
        if not user:
            return False
        return permission in user.get('permissions', [])


# ==========================================
# 2. Data Router - Hot/Cold Storage
# ==========================================

class DataRouter:
    """
    Smart data routing:
    - Real-time -> MongoDB (Hot - Dashboard access)
    - Historical -> HDFS (Cold - ML training/Spark analytics)
    """
    
    def __init__(self, mongo_db, hdfs_client):
        self.mongo_db = mongo_db
        self.hdfs = hdfs_client
        self.buffer = []
        self.BATCH_SIZE = 100
        
    def route_sensor_data(self, data: List[Dict], data_type: Literal['realtime', 'historical', 'ml_training']):
        """Route data to appropriate storage"""
        
        if not data:
            return

        # Real-time path: MongoDB for immediate dashboard access
        if data_type == 'realtime':
            self.mongo_db['sensor_data'].insert_many(data)
            self.buffer.extend(data)
            
            if len(self.buffer) >= self.BATCH_SIZE:
                self._archive_to_hdfs(self.buffer, "realtime_archive")
                self.buffer = []
                
        # Historical/ML training path: Primary to HDFS
        elif data_type in ['historical', 'ml_training']:
            self._write_batch_to_hdfs(data, prefix=data_type)
            
            # Log metadata to MongoDB
            self.mongo_db['data_generation_logs'].insert_one({
                'type': data_type,
                'record_count': len(data),
                'timestamp': datetime.now(timezone.utc),
                'hdfs_status': 'stored'
            })

    def _write_batch_to_hdfs(self, data: List[Dict], prefix: str):
        """Write batch to HDFS with partitioning"""
        try:
            # Create date-based partitions
            current_date = datetime.now().strftime('%Y%m%d')
            timestamp = datetime.now().strftime('%H%M%S')
            
            # HDFS path: /agriculture/data_type/year/month/day/
            hdfs_path = f"/agriculture/{prefix}/{current_date}/"
            filename = f"{hdfs_path}data_{timestamp}.json"
            
            # Ensure directory exists
            try:
                self.hdfs.makedirs(hdfs_path)
            except:
                pass  # Directory might already exist
            
            # Write data
            json_data = json.dumps(data, default=str, indent=2)
            self.hdfs.write(filename, data=json_data, encoding='utf-8', overwrite=True)
            
            print(f"📦 HDFS: {len(data)} records → {filename}")
            
        except Exception as e:
            print(f"⚠️ HDFS Error: {e}")
            # Fallback: Write to local file
            self._fallback_to_local(data, prefix)

    def _fallback_to_local(self, data: List[Dict], prefix: str):
        """Fallback to local storage if HDFS fails"""
        local_dir = f"/app/data/hdfs_fallback/{prefix}"
        os.makedirs(local_dir, exist_ok=True)
        
        filename = f"{local_dir}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, default=str, indent=2)
        print(f"💾 Fallback: Saved to {filename}")

    def _archive_to_hdfs(self, data: List[Dict], prefix: str):
        """Archive buffered data"""
        self._write_batch_to_hdfs(data, prefix)


# ==========================================
# 3. Advanced Weather Simulator
# ==========================================

class WeatherSimulator:
    """
    Generates realistic weather patterns based on:
    - Geographic location (climate zones)
    - Seasonal variations
    - Day/night cycles
    - Weather events (rain, storms)
    """
    
    # Climate zone definitions
    CLIMATE_ZONES = {
        'tropical': {'lat_range': (-23.5, 23.5), 'base_temp': 27, 'temp_variation': 5},
        'subtropical': {'lat_range': (23.5, 35), 'base_temp': 22, 'temp_variation': 10},
        'temperate': {'lat_range': (35, 55), 'base_temp': 15, 'temp_variation': 15},
        'continental': {'lat_range': (40, 60), 'base_temp': 10, 'temp_variation': 20},
        'polar': {'lat_range': (60, 90), 'base_temp': -5, 'temp_variation': 25}
    }
    


    def __init__(self):
        self.weather_cache = {}
        self.active_weather_events = {}  # Track storms, droughts, etc.
        self.api_key = os.getenv('WEATHER_API_KEY')
        self.use_api = os.getenv('USE_WEATHER_API', 'false').lower() == 'true'
        
    def get_climate_zone(self, lat: float) -> str:
        """Determine climate zone from latitude"""
        abs_lat = abs(lat)
        
        if abs_lat <= 23.5:
            return 'tropical'
        elif abs_lat <= 35:
            return 'subtropical'
        elif abs_lat <= 55:
            return 'temperate'
        elif abs_lat <= 60:
            return 'continental'
        else:
            return 'polar'
            
    def _fetch_real_weather(self, lat: float, lon: float) -> Optional[Dict]:
        """Fetch real-time weather from OpenWeatherMap"""
        if not self.api_key:
            return None
            
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                main = data['main']
                wind = data['wind']
                clouds = data['clouds']
                
                # Determine rain
                rainfall = 0
                is_raining = False
                if 'rain' in data:
                    rainfall = data['rain'].get('1h', 0)
                    is_raining = rainfall > 0
                
                print(f"  🌦️  Fetched live weather for ({lat}, {lon}): {main['temp']}°C, {main['humidity']}%")
                
                return {
                    'temperature': main['temp'],
                    'humidity': main['humidity'],
                    'pressure': main['pressure'],
                    'wind_speed': wind['speed'],
                    'wind_direction': wind.get('deg', 0),
                    'rainfall': rainfall,
                    'clouds': clouds.get('all', 0),
                    'climate_zone': self.get_climate_zone(lat), # Keep this for compatibility
                    'is_raining': is_raining,
                    'season': self._get_season(datetime.now().timetuple().tm_yday, lat),
                    'source': 'openweathermap'
                }
            else:
                print(f"⚠️ Weather API Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"⚠️ Weather API Exception: {e}")
            return None
    
    def generate_weather(self, lat: float, lon: float, timestamp: datetime) -> Dict:
        """
        Generate realistic weather for a location and time
        Includes seasonal patterns, daily cycles, and weather events
        """
        
        # Check if we should use real API data
        # Only use API if usage is enabled AND timestamp is close to now (real-time stream)
        time_diff = abs((datetime.now(timezone.utc) - timestamp).total_seconds())
        if self.use_api and time_diff < 3600:
            real_data = self._fetch_real_weather(lat, lon)
            if real_data:
                real_data['timestamp'] = timestamp.isoformat()
                return real_data

        # Fallback to Simulation Logic
        
        # Get climate parameters
        climate = self.get_climate_zone(lat)
        params = self.CLIMATE_ZONES[climate]
        
        # Seasonal factor (Northern hemisphere)
        day_of_year = timestamp.timetuple().tm_yday
        seasonal_factor = math.sin(2 * math.pi * (day_of_year - 80) / 365)  # Peak in summer
        
        # South hemisphere: invert seasons
        if lat < 0:
            seasonal_factor = -seasonal_factor
        
        # Base temperature with seasonal variation
        base_temp = params['base_temp']
        seasonal_variation = params['temp_variation'] * seasonal_factor
        
        # Daily cycle (cooler at night)
        hour = timestamp.hour
        daily_cycle = 8 * (1 - abs(12 - hour) / 12) - 4  # -4°C at night, +4°C at noon
        
        # Calculate temperature
        temperature = base_temp + seasonal_variation + daily_cycle + random.gauss(0, 2)
        
        # Humidity (inversely related to temperature, higher in tropics)
        base_humidity = 70 if climate == 'tropical' else 60
        humidity = base_humidity - (temperature - 20) * 1.5 + random.gauss(0, 5)
        humidity = max(20, min(95, humidity))
        
        # Rainfall probability (higher in tropics, seasonal patterns)
        rain_base_prob = 0.15 if climate == 'tropical' else 0.08
        rain_prob = rain_base_prob * (1 + 0.3 * seasonal_factor)
        
        # Check for active weather events
        event_key = f"{lat:.2f},{lon:.2f}"
        is_raining = False
        rainfall = 0
        
        if event_key in self.active_weather_events:
            event = self.active_weather_events[event_key]
            if timestamp < event['end_time']:
                is_raining = True
                rainfall = random.uniform(1, event['intensity'])
        elif random.random() < rain_prob:
            # Start new rain event
            duration_hours = random.randint(2, 12)
            self.active_weather_events[event_key] = {
                'end_time': timestamp + timedelta(hours=duration_hours),
                'intensity': random.uniform(2, 15)  # mm/hour
            }
            is_raining = True
            rainfall = random.uniform(1, self.active_weather_events[event_key]['intensity'])
        
        # Wind (stronger in certain conditions)
        base_wind = 3 if climate == 'tropical' else 5
        wind_speed = base_wind + random.gauss(0, 2) + (5 if is_raining else 0)
        wind_speed = max(0, wind_speed)
        
        # Cloud cover
        if is_raining:
            clouds = random.randint(80, 100)
        else:
            clouds = random.randint(0, 60)
        
        # Atmospheric pressure
        pressure = 1013 + random.gauss(0, 10) - (5 if is_raining else 0)
        
        return {
            'timestamp': timestamp.isoformat(),
            'temperature': round(temperature, 2),
            'humidity': round(humidity, 2),
            'pressure': round(pressure, 1),
            'wind_speed': round(wind_speed, 2),
            'wind_direction': random.randint(0, 359),
            'rainfall': round(rainfall, 2),
            'clouds': clouds,
            'climate_zone': climate,
            'is_raining': is_raining,
            'season': self._get_season(day_of_year, lat),
            'source': 'simulated'
        }
    
    def _get_season(self, day_of_year: int, lat: float) -> str:
        """Determine season based on day of year and hemisphere"""
        # Northern hemisphere
        if lat >= 0:
            if 80 <= day_of_year < 172:
                return 'spring'
            elif 172 <= day_of_year < 264:
                return 'summer'
            elif 264 <= day_of_year < 355:
                return 'fall'
            else:
                return 'winter'
        # Southern hemisphere (inverted)
        else:
            if 80 <= day_of_year < 172:
                return 'fall'
            elif 172 <= day_of_year < 264:
                return 'winter'
            elif 264 <= day_of_year < 355:
                return 'spring'
            else:
                return 'summer'


# ==========================================
# 4. Disease Pattern Generator
# ==========================================

class DiseaseSimulator:
    """
    Simulates disease patterns for ML training
    Creates realistic disease outbreaks based on environmental conditions
    """
    
    DISEASES = {
        # Potato Diseases
        'Potato___Early_blight': {
            'optimal_temp': (20, 28), 'optimal_humidity': (80, 95), 'rainfall_trigger': 5,
            'soil_moisture_range': (60, 85), 'severity_progression': 'exponential'
        },
        'Potato___Late_blight': {
            'optimal_temp': (15, 22), 'optimal_humidity': (85, 100), 'rainfall_trigger': 10,
            'soil_moisture_range': (70, 90), 'severity_progression': 'fast_exponential'
        },
        
        # Tomato Diseases
        'Tomato_Bacterial_spot': {
            'optimal_temp': (25, 30), 'optimal_humidity': (85, 100), 'rainfall_trigger': 2,
            'soil_moisture_range': (50, 75), 'severity_progression': 'linear'
        },
        'Tomato_Early_blight': {
            'optimal_temp': (24, 29), 'optimal_humidity': (80, 90), 'rainfall_trigger': 5,
            'soil_moisture_range': (60, 80), 'severity_progression': 'exponential'
        },
        'Tomato_Late_blight': {
            'optimal_temp': (17, 22), 'optimal_humidity': (85, 95), 'rainfall_trigger': 10,
            'soil_moisture_range': (70, 90), 'severity_progression': 'fast_exponential'
        },
        'Tomato_Leaf_Mold': {
            'optimal_temp': (21, 24), 'optimal_humidity': (85, 100), 'rainfall_trigger': 0,
            'soil_moisture_range': (50, 70), 'severity_progression': 'slow'
        },
        'Tomato_Septoria_leaf_spot': {
            'optimal_temp': (20, 25), 'optimal_humidity': (60, 80), 'rainfall_trigger': 5,
            'soil_moisture_range': (50, 70), 'severity_progression': 'linear'
        },
        'Tomato_Spider_mites_Two_spotted_spider_mite': {
            'optimal_temp': (27, 32), 'optimal_humidity': (30, 50), 'rainfall_trigger': 0,
            'soil_moisture_range': (30, 50), 'severity_progression': 'exponential'
        },
        'Tomato__Target_Spot': {
            'optimal_temp': (24, 28), 'optimal_humidity': (80, 90), 'rainfall_trigger': 2,
            'soil_moisture_range': (50, 70), 'severity_progression': 'linear'
        },
        'Tomato__Tomato_YellowLeaf__Curl_Virus': {
            'optimal_temp': (25, 32), 'optimal_humidity': (50, 70), 'rainfall_trigger': 0,
            'soil_moisture_range': (40, 60), 'severity_progression': 'slow'
        },
        'Tomato__Tomato_mosaic_virus': {
            'optimal_temp': (20, 28), 'optimal_humidity': (40, 70), 'rainfall_trigger': 0,
            'soil_moisture_range': (50, 70), 'severity_progression': 'slow'
        },

        # Pepper Diseases
        'Pepper__bell___Bacterial_spot': {
            'optimal_temp': (25, 30), 'optimal_humidity': (85, 100), 'rainfall_trigger': 2,
            'soil_moisture_range': (50, 75), 'severity_progression': 'linear'
        }
    }
    
    def __init__(self):
        self.active_infections = {}  # Track ongoing infections
        
    def check_disease_risk(
        self, 
        field_id: str,
        crop_type: str,
        weather: Dict, 
        soil_conditions: Dict,
        timestamp: datetime
    ) -> Tuple[str, float, str]:
        """
        Determine disease risk based on conditions
        Returns: (disease_name, severity, status)
        """
        
        # Check each disease
        risks = []
        
        for disease_name, conditions in self.DISEASES.items():
            # Filter by crop type to ensure realistic diseases
            if crop_type.lower() not in disease_name.lower():
                continue

            risk_score = self._calculate_risk(disease_name, conditions, weather, soil_conditions)
            
            if risk_score > 0.6:  # Threshold for infection
                risks.append((disease_name, risk_score))
        
        if not risks:
            return ('healthy', 0.0, 'healthy')
        
        # Select most likely disease
        disease_name, base_severity = max(risks, key=lambda x: x[1])
        
        # Check if infection already exists (disease progression)
        infection_key = f"{field_id}_{disease_name}"
        
        if infection_key in self.active_infections:
            infection = self.active_infections[infection_key]
            days_since_start = (timestamp - infection['start_date']).days
            
            # Progress severity based on disease type
            progression = self.DISEASES[disease_name]['severity_progression']
            severity = self._progress_severity(base_severity, days_since_start, progression)
            
            # Update infection
            infection['severity'] = severity
            infection['days_active'] = days_since_start
            
            status = 'active_infection'
        else:
            # New infection
            severity = base_severity
            self.active_infections[infection_key] = {
                'start_date': timestamp,
                'severity': severity,
                'days_active': 0
            }
            status = 'new_infection'
        
        return (disease_name, round(severity, 3), status)
    
    def _calculate_risk(
        self, 
        disease_name: str,
        conditions: Dict, 
        weather: Dict, 
        soil: Dict
    ) -> float:
        """Calculate disease risk score (0-1)"""
        
        risk = 0.0
        factors = 0
        
        # Temperature match
        if conditions['optimal_temp'][0] <= weather['temperature'] <= conditions['optimal_temp'][1]:
            risk += 0.3
        factors += 1
        
        # Humidity match
        if conditions['optimal_humidity'][0] <= weather['humidity'] <= conditions['optimal_humidity'][1]:
            risk += 0.3
        factors += 1
        
        # Rainfall trigger
        if weather['rainfall'] >= conditions['rainfall_trigger']:
            risk += 0.2
        factors += 1
        
        # Soil moisture match
        soil_moisture = soil.get('moisture', 50)
        if conditions['soil_moisture_range'][0] <= soil_moisture <= conditions['soil_moisture_range'][1]:
            risk += 0.2
        factors += 1
        
        return risk
    
    def _progress_severity(self, base: float, days: int, progression_type: str) -> float:
        """Progress disease severity over time"""
        
        if progression_type == 'exponential':
            return min(1.0, base * (1.1 ** days))
        elif progression_type == 'fast_exponential':
            return min(1.0, base * (1.2 ** days))
        elif progression_type == 'linear':
            return min(1.0, base + 0.05 * days)
        elif progression_type == 'slow':
            return min(1.0, base + 0.02 * days)
        
        return base


# ==========================================
# 5. Field & Sensor Manager
# ==========================================

class FieldManager:
    """Manages fields and sensors"""
    
    def __init__(self, db):
        self.db = db
        self.fields = db['fields']
        self.sensors = db['sensors']
        
    def create_field(self, user_id: str, field_data: Dict) -> str:
        """Create a new field with sensors"""
        field_id = f"FIELD_{user_id}_{random.randint(1000,9999)}"
        
        field = {
            'field_id': field_id,
            'user_id': user_id,
            'name': field_data['name'],
            'location': {
                'lat': field_data['latitude'],
                'lon': field_data['longitude']
            },
            'area_hectares': field_data.get('area_hectares', 1.0),
            'crop_type': field_data.get('crop_type', 'mixed'),
            'soil_type': field_data.get('soil_type', 'loam'),
            'created_at': datetime.now(timezone.utc),
            'active': True
        }
        
        self.fields.insert_one(field)
        self._create_sensors(field_id, field['location'])
        
        print(f"🌾 Field created: {field_id} at ({field['location']['lat']}, {field['location']['lon']})")
        return field_id
    
    def _create_sensors(self, field_id: str, location: Dict):
        """Create sensors for a field"""
        sensors = []
        
        # Create 5 soil sensors (distributed across field)
        for i in range(5):
            sensors.append({
                'sensor_id': f'SOIL_{field_id}_{i+1:03d}',
                'field_id': field_id,
                'sensor_type': 'soil',
                'location': {
                    'lat': location['lat'] + random.uniform(-0.01, 0.01),
                    'lon': location['lon'] + random.uniform(-0.01, 0.01)
                },
                'status': 'active',
                'created_at': datetime.now(timezone.utc)
            })
        
        # Create 1 atmospheric sensor
        sensors.append({
            'sensor_id': f'ATM_{field_id}_001',
            'field_id': field_id,
            'sensor_type': 'atmospheric',
            'location': location,
            'status': 'active',
            'created_at': datetime.now(timezone.utc)
        })
        
        self.sensors.insert_many(sensors)
        print(f"  📡 Created {len(sensors)} sensors")
        return sensors
    
    def get_field_sensors(self, field_id: str) -> List[Dict]:
        """Get all sensors for a field"""
        return list(self.sensors.find({'field_id': field_id, 'status': 'active'}))


# ==========================================
# 6. Main Sensor Simulator
# ==========================================

class ProductionSensorSimulator:
    """
    Main simulation engine with:
    - Realistic weather patterns
    - Disease simulation
    - ML training data generation
    - Smart data routing
    """
    
    def __init__(self):
        # MongoDB connection
        self.mongo_uri = os.getenv('MONGODB_URI', 'mongodb://admin:admin123@mongodb:27017/')
        self.mongo_client = MongoClient(self.mongo_uri)
        self.db = self.mongo_client['agriculture']
        
        # HDFS connection
        hdfs_url = os.getenv('HDFS_NAMENODE', 'http://namenode:9870')
        try:
            self.hdfs_client = InsecureClient(hdfs_url, user='root')
        except Exception as e:
            print(f"⚠️ HDFS connection warning: {e}")
            self.hdfs_client = None
        
        # Initialize components
        self.role_manager = RoleManager(self.db)
        self.router = DataRouter(self.db, self.hdfs_client)
        self.weather_sim = WeatherSimulator()
        self.disease_sim = DiseaseSimulator()
        self.field_manager = FieldManager(self.db)
        
        print("✅ Simulator initialized")
    
    def generate_soil_reading(
        self, 
        sensor: Dict, 
        weather: Dict, 
        timestamp: datetime
    ) -> Dict:
        """Generate realistic soil sensor reading"""
        
        # Soil temperature follows air temp with lag
        soil_temp = weather['temperature'] * 0.85 + random.gauss(0, 1)
        
        # Soil moisture affected by rainfall and evaporation
        base_moisture = 45
        rain_effect = weather['rainfall'] * 5
        humidity_effect = (weather['humidity'] - 50) * 0.2
        evap_effect = (weather['temperature'] - 20) * -0.5  # Higher temp = more evaporation
        
        moisture = base_moisture + rain_effect + humidity_effect + evap_effect + random.gauss(0, 5)
        moisture = max(15, min(95, moisture))
        
        # pH slightly affected by moisture
        ph = 6.8 + (moisture - 45) * -0.01 + random.gauss(0, 0.2)
        ph = max(5.5, min(8.0, ph))
        
        # Electrical conductivity
        ec = (moisture / 50) * random.gauss(0.5, 0.1)
        
        # Nutrients (NPK) - slow-changing
        nitrogen = random.gauss(50, 10)
        phosphorus = random.gauss(30, 5)
        potassium = random.gauss(40, 8)
        
        return {
            'sensor_id': sensor['sensor_id'],
            'field_id': sensor['field_id'],
            'sensor_type': 'soil',
            'timestamp': timestamp,
            'location': sensor['location'],
            'readings': {
                'moisture': round(moisture, 2),
                'temperature': round(soil_temp, 2),
                'ph': round(ph, 2),
                'electrical_conductivity': round(max(0, ec), 3),
                'nitrogen': round(max(0, nitrogen), 1),
                'phosphorus': round(max(0, phosphorus), 1),
                'potassium': round(max(0, potassium), 1)
            },
            'weather_context': weather
        }
    
    def generate_atmospheric_reading(
        self,
        sensor: Dict,
        weather: Dict,
        timestamp: datetime
    ) -> Dict:
        """Generate atmospheric sensor reading"""
        
        hour = timestamp.hour
        
        # Sensor variations (calibration differences)
        temp_var = random.gauss(0, 0.3)
        humidity_var = random.gauss(0, 1.5)
        
        # Light intensity calculation
        if 6 <= hour <= 18:
            sun_position = 1 - abs(12 - hour) / 6
            cloud_reduction = (100 - weather['clouds']) / 100
            light = 80000 * sun_position * cloud_reduction * random.gauss(1, 0.08)
        else:
            light = random.uniform(0, 100)
        
        return {
            'sensor_id': sensor['sensor_id'],
            'field_id': sensor['field_id'],
            'sensor_type': 'atmospheric',
            'timestamp': timestamp,
            'location': sensor['location'],
            'readings': {
                'temperature': round(weather['temperature'] + temp_var, 2),
                'humidity': round(max(10, min(100, weather['humidity'] + humidity_var)), 2),
                'light_intensity': round(max(0, light), 0),
                'wind_speed': round(weather['wind_speed'] + random.gauss(0, 0.2), 2),
                'wind_direction': (weather['wind_direction'] + random.randint(-10, 10)) % 360,
                'rainfall': weather['rainfall'],
                'atmospheric_pressure': round(weather['pressure'], 1),
                'cloud_coverage': weather['clouds']
            },
            'weather_context': weather
        }
    
    def generate_historical_batch(
        self, 
        requester_id: str, 
        target_user_id: str = None, 
        days: int = 365,
        include_diseases: bool = True
    ):
        """
        Generate historical dataset with realistic patterns
        Perfect for ML training with labeled disease data
        """
        
        # Permission check
        if not self.role_manager.check_permission(requester_id, 'run_simulation'):
            print(f"⛔ Access Denied: {requester_id} lacks 'run_simulation' permission")
            return
        
        # Get target fields
        query = {'active': True}
        if target_user_id:
            query['user_id'] = target_user_id
        
        fields = list(self.db['fields'].find(query))
        
        if not fields:
            print(f"⚠️ No fields found for user: {target_user_id}")
            return
        
        print(f"\n{'='*60}")
        print(f"📊 GENERATING HISTORICAL KNOWLEDGE BASE")
        print(f"{'='*60}")
        print(f"Fields: {len(fields)}")
        print(f"Period: {days} days")
        print(f"Diseases: {'Enabled' if include_diseases else 'Disabled'}")
        print(f"{'='*60}\n")
        
        all_sensor_data = []
        all_disease_data = []
        
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        for field_idx, field in enumerate(fields, 1):
            print(f"🌾 Field {field_idx}/{len(fields)}: {field['field_id']}")
            
            field_id = field['field_id']
            lat = field['location']['lat']
            lon = field['location']['lon']
            
            sensors = self.field_manager.get_field_sensors(field_id)
            field_sensor_count = 0
            field_disease_count = 0
            
            # Generate daily data
            for day in range(days):
                current_date = start_date + timedelta(days=day)
                
                # Generate weather for this day (hourly)
                for hour in range(0, 24, 3):  # Every 3 hours to reduce volume
                    timestamp = current_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                    weather = self.weather_sim.generate_weather(lat, lon, timestamp)
                    
                    # Generate sensor readings
                    soil_readings = []
                    for sensor in sensors:
                        if sensor['sensor_type'] == 'soil':
                            reading = self.generate_soil_reading(sensor, weather, timestamp)
                            soil_readings.append(reading)
                            all_sensor_data.append(reading)
                            field_sensor_count += 1
                        else:
                            reading = self.generate_atmospheric_reading(sensor, weather, timestamp)
                            all_sensor_data.append(reading)
                            field_sensor_count += 1
                    
                    # Check for diseases (once per day)
                    if include_diseases and hour == 12 and soil_readings:
                        avg_soil = {
                            'moisture': sum(r['readings']['moisture'] for r in soil_readings) / len(soil_readings),
                            'temperature': sum(r['readings']['temperature'] for r in soil_readings) / len(soil_readings)
                        }
                        
                        disease, severity, status = self.disease_sim.check_disease_risk(
                            field_id, 
                            field['crop_type'],
                            weather, 
                            avg_soil, 
                            timestamp
                        )
                        
                        if disease != 'healthy':
                            disease_record = {
                                'field_id': field_id,
                                'disease': disease,
                                'severity': severity,
                                'status': status,
                                'detection_date': timestamp,
                                'environmental_conditions': {
                                    'temperature': weather['temperature'],
                                    'humidity': weather['humidity'],
                                    'rainfall': weather['rainfall'],
                                    'soil_moisture': avg_soil['moisture']
                                },
                                'season': weather['season'],
                                'climate_zone': weather['climate_zone']
                            }
                            all_disease_data.append(disease_record)
                            field_disease_count += 1
                
                # Progress indicator
                if (day + 1) % 30 == 0:
                    progress = ((day + 1) / days) * 100
                    print(f"  📅 Progress: {progress:.0f}% ({day + 1}/{days} days)")
            
            print(f"  ✓ Generated: {field_sensor_count:,} sensor readings, {field_disease_count} disease events\n")
        
        # Route to storage
        print(f"\n{'='*60}")
        print(f"📦 STORING DATA")
        print(f"{'='*60}")
        
        if all_sensor_data:
            print(f"Sensor readings: {len(all_sensor_data):,}")
            self.router.route_sensor_data(all_sensor_data, data_type='ml_training')
        
        if all_disease_data:
            print(f"Disease records: {len(all_disease_data):,}")
            self.db['disease_records'].insert_many(all_disease_data)
            print("✓ Disease data stored in MongoDB")
        
        print(f"{'='*60}\n")
        print("✅ Historical data generation complete!")
        print(f"\n📊 Summary:")
        print(f"  Total readings: {len(all_sensor_data):,}")
        print(f"  Disease events: {len(all_disease_data):,}")
        print(f"  Storage: HDFS + MongoDB")
        print(f"  Ready for: ML training & Spark analytics\n")
    
    def start_realtime_stream(self, user_id: str, interval_seconds: int = 60):
        """
        Real-time data stream (Hot path)
        Continuously generates current sensor readings
        """
        
        print(f"\n{'='*60}")
        print(f"🚀 STARTING REAL-TIME STREAM")
        print(f"{'='*60}")
        print(f"User: {user_id}")
        print(f"Interval: {interval_seconds}s")
        print(f"Press Ctrl+C to stop\n")
        
        try:
            iteration = 0
            while True:
                iteration += 1
                fields = list(self.db['fields'].find({'user_id': user_id, 'active': True}))
                
                if not fields:
                    print(f"⚠️ No active fields for {user_id}")
                    time.sleep(interval_seconds)
                    continue
                
                batch = []
                current_time = datetime.now(timezone.utc)
                
                for field in fields:
                    lat = field['location']['lat']
                    lon = field['location']['lon']
                    
                    weather = self.weather_sim.generate_weather(lat, lon, current_time)
                    sensors = self.field_manager.get_field_sensors(field['field_id'])
                    
                    for sensor in sensors:
                        if sensor['sensor_type'] == 'soil':
                            reading = self.generate_soil_reading(sensor, weather, current_time)
                        else:
                            reading = self.generate_atmospheric_reading(sensor, weather, current_time)
                        
                        batch.append(reading)
                
                # Route to MongoDB (hot path)
                if batch:
                    self.router.route_sensor_data(batch, data_type='realtime')
                    print(f"[{iteration:04d}] {current_time.strftime('%H:%M:%S')} | {len(batch)} readings | {len(fields)} fields")
                
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Real-time stream stopped by user")
            print(f"Total iterations: {iteration}")


# ==========================================
# 7. Setup & Entry Point
# ==========================================

def setup_demo_environment():
    """Setup demo users and fields"""
    sim = ProductionSensorSimulator()
    
    print("\n🔧 Setting up demo environment...")
    
    # Create users
    sim.role_manager.create_user('ADMIN_01', 'ADMIN', 'System Administrator')
    sim.role_manager.create_user('FARMER_ALICE', 'FARMER', 'Alice Johnson')
    sim.role_manager.create_user('RESEARCHER_BOB', 'RESEARCHER', 'Dr. Bob Smith')
    
    # Create fields
    fields = [
        {'name': 'North Tomato Field', 'latitude': 36.8065, 'longitude': 10.1815, 
         'area_hectares': 5.5, 'crop_type': 'tomato', 'soil_type': 'clay_loam'},
        
        {'name': 'South pepper Field', 'latitude': 40.7128, 'longitude': -74.0060,
         'area_hectares': 8.2, 'crop_type': 'pepper', 'soil_type': 'sandy_loam'},
        
        {'name': 'East potato Field', 'latitude': 51.5074, 'longitude': -0.1278,
         'area_hectares': 12.0, 'crop_type': 'potato', 'soil_type': 'silt_loam'}
    ]
    
    for field_data in fields:
        sim.field_manager.create_field('FARMER_ALICE', field_data)
    
    print("✅ Demo environment ready!\n")
    return sim


def main():
    """Entry point"""
    import sys
    
    sim = setup_demo_environment()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'history':
            # Generate historical ML training data
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 365
            user = sys.argv[3] if len(sys.argv) > 3 else 'FARMER_ALICE'
            
            sim.generate_historical_batch(
                requester_id='ADMIN_01',
                target_user_id=user,
                days=days,
                include_diseases=True
            )
        
        elif command == 'stream':
            # Start real-time monitoring
            user = sys.argv[2] if len(sys.argv) > 2 else 'FARMER_ALICE'
            interval = int(sys.argv[3]) if len(sys.argv) > 3 else 60
            
            sim.start_realtime_stream(user, interval_seconds=interval)
        
        else:
            print("Unknown command. Use: history [days] [user] | stream [user] [interval]")
    
    else:
        # Default: Generate 30 days of training data
        print("No command specified. Running default: 30 days historical generation")
        sim.generate_historical_batch(
            requester_id='ADMIN_01',
            target_user_id='FARMER_ALICE',
            days=30,
            include_diseases=True
        )


if __name__ == '__main__':
    main()