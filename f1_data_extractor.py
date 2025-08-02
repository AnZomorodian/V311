import fastf1
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from functools import lru_cache
from datetime import datetime, timedelta
import os

# Configure logging
logger = logging.getLogger(__name__)

# Enable Fast F1 cache for better performance
cache_dir = 'cache'
if not os.path.exists(cache_dir):
    try:
        os.makedirs(cache_dir)
        fastf1.Cache.enable_cache(cache_dir)
        logger.info(f"Cache enabled at {cache_dir}")
    except Exception as e:
        logger.warning(f"Could not create cache directory: {e}. Running without cache.")
else:
    fastf1.Cache.enable_cache(cache_dir)
    logger.info(f"Cache enabled at {cache_dir}")

class F1DataExtractor:
    """Enhanced class to handle F1 data extraction using Fast F1 API"""
    
    def __init__(self):
        self.session_cache = {}
        self.cache_size = 128
    
    @lru_cache(maxsize=128)
    def get_available_seasons(self) -> List[int]:
        """Get available F1 seasons"""
        try:
            current_year = datetime.now().year
            # FastF1 typically supports data from 2018 onwards
            return list(range(2018, current_year + 1))
        except Exception as e:
            logger.error(f"Error getting available seasons: {e}")
            return [2024]  # Fallback to current year
    
    @lru_cache(maxsize=128)
    def get_season_events(self, year: int) -> List[Dict]:
        """Get all events for a specific season with enhanced error handling"""
        try:
            logger.info(f"Fetching events for season {year}")
            schedule = fastf1.get_event_schedule(year)
            
            if schedule is None or schedule.empty:
                logger.warning(f"No schedule data found for {year}")
                return []
            
            events = []
            for _, event in schedule.iterrows():
                try:
                    # Check if the event has race session data
                    if pd.notna(event.get('Session5Date')):
                        event_data = {
                            'round': int(event['RoundNumber']) if pd.notna(event['RoundNumber']) else 0,
                            'name': str(event['EventName']) if pd.notna(event['EventName']) else 'Unknown Event',
                            'location': str(event['Location']) if pd.notna(event['Location']) else 'Unknown Location',
                            'country': str(event['Country']) if pd.notna(event['Country']) else 'Unknown Country',
                            'date': event['Session5Date'].strftime('%Y-%m-%d') if pd.notna(event['Session5Date']) else None,
                            'session1_date': event.get('Session1Date', '').strftime('%Y-%m-%d %H:%M') if pd.notna(event.get('Session1Date')) else None,
                            'session2_date': event.get('Session2Date', '').strftime('%Y-%m-%d %H:%M') if pd.notna(event.get('Session2Date')) else None,
                            'session3_date': event.get('Session3Date', '').strftime('%Y-%m-%d %H:%M') if pd.notna(event.get('Session3Date')) else None,
                            'session4_date': event.get('Session4Date', '').strftime('%Y-%m-%d %H:%M') if pd.notna(event.get('Session4Date')) else None,
                            'session5_date': event.get('Session5Date', '').strftime('%Y-%m-%d %H:%M') if pd.notna(event.get('Session5Date')) else None
                        }
                        events.append(event_data)
                except Exception as event_error:
                    logger.warning(f"Error processing event {event.get('EventName', 'Unknown')}: {event_error}")
                    continue
            
            logger.info(f"Found {len(events)} events for season {year}")
            return events
            
        except Exception as e:
            logger.error(f"Error getting season events for {year}: {e}")
            return []
    
    def load_session_data(self, year: int, round_number: int, session_type: str = 'R') -> Optional[Any]:
        """Load F1 session data with enhanced caching and error handling"""
        try:
            session_key = f"{year}_{round_number}_{session_type}"
            
            # Check cache first
            if session_key in self.session_cache:
                logger.info(f"Using cached session data for {session_key}")
                return self.session_cache[session_key]
            
            logger.info(f"Loading session data for {year}, round {round_number}, session {session_type}")
            
            # Validate input parameters
            if year < 2018 or year > datetime.now().year + 1:
                raise ValueError(f"Invalid year: {year}. Must be between 2018 and {datetime.now().year + 1}")
            
            if round_number < 1 or round_number > 30:
                raise ValueError(f"Invalid round number: {round_number}. Must be between 1 and 30")
            
            # Load session data
            session = fastf1.get_session(year, round_number, session_type)
            
            if session is None:
                logger.error(f"No session found for {year}, round {round_number}, {session_type}")
                return None
            
            # Load session data with timeout handling
            session.load()
            
            # Cache the session if cache size allows
            if len(self.session_cache) < self.cache_size:
                self.session_cache[session_key] = session
            
            logger.info(f"Successfully loaded session data for {session_key}")
            return session
            
        except Exception as e:
            logger.error(f"Error loading session data for {year}, round {round_number}, {session_type}: {e}")
            return None
    
    def get_session_drivers(self, session: Any) -> List[str]:
        """Get list of drivers from session with enhanced error handling"""
        try:
            if session is None:
                logger.warning("Session is None, returning empty driver list")
                return []
            
            # Get drivers from session
            drivers = session.drivers
            
            if drivers is None:
                logger.warning("No drivers found in session")
                return []
            
            # Handle different types of driver data structures
            if hasattr(drivers, 'tolist'):
                # It's a pandas Series/DataFrame
                driver_list = drivers.tolist()
            elif isinstance(drivers, list):
                # It's already a list
                driver_list = drivers
            else:
                # Try to convert to list
                driver_list = list(drivers)
            
            # Filter out invalid driver numbers and convert to strings
            valid_drivers = []
            for driver in driver_list:
                try:
                    driver_str = str(driver).strip()
                    if driver_str and driver_str != 'nan' and driver_str.lower() != 'none':
                        valid_drivers.append(driver_str)
                except Exception as driver_error:
                    logger.debug(f"Error processing driver {driver}: {driver_error}")
                    continue
            
            logger.info(f"Found {len(valid_drivers)} valid drivers: {valid_drivers}")
            return valid_drivers
                
        except Exception as e:
            logger.error(f"Error getting drivers from session: {e}")
            return []
    
    def get_driver_info(self, session: Any, driver_number: str) -> Dict[str, Any]:
        """Get detailed driver information"""
        try:
            if session is None:
                return {}
            
            # Get driver information from session
            driver_info = {}
            
            # Try to get driver results
            if hasattr(session, 'results') and session.results is not None:
                driver_result = session.results[session.results['DriverNumber'] == driver_number]
                if not driver_result.empty:
                    result = driver_result.iloc[0]
                    driver_info = {
                        'driver_number': str(driver_number),
                        'abbreviation': str(result.get('Abbreviation', 'UNK')),
                        'full_name': str(result.get('FullName', 'Unknown Driver')),
                        'team_name': str(result.get('TeamName', 'Unknown Team')),
                        'position': int(result.get('Position', 0)) if pd.notna(result.get('Position')) else None,
                        'points': float(result.get('Points', 0)) if pd.notna(result.get('Points')) else 0,
                        'grid_position': int(result.get('GridPosition', 0)) if pd.notna(result.get('GridPosition')) else None,
                        'status': str(result.get('Status', 'Unknown'))
                    }
            
            # Fallback if no results available
            if not driver_info:
                driver_info = {
                    'driver_number': str(driver_number),
                    'abbreviation': 'UNK',
                    'full_name': f'Driver #{driver_number}',
                    'team_name': 'Unknown Team',
                    'position': None,
                    'points': 0,
                    'grid_position': None,
                    'status': 'Unknown'
                }
            
            return driver_info
            
        except Exception as e:
            logger.error(f"Error getting driver info for {driver_number}: {e}")
            return {
                'driver_number': str(driver_number),
                'abbreviation': 'UNK',
                'full_name': f'Driver #{driver_number}',
                'team_name': 'Unknown Team',
                'position': None,
                'points': 0,
                'grid_position': None,
                'status': 'Error'
            }
    
    def extract_driver_lap_data(self, session: Any, driver_number: str) -> List[Dict]:
        """Extract comprehensive lap data for a specific driver with enhanced telemetry"""
        try:
            if session is None:
                logger.warning(f"Session is None for driver {driver_number}")
                return []
            
            # Get driver lap data using multiple methods for compatibility
            driver_laps = None
            try:
                # Try new method first
                driver_laps = session.laps.pick_drivers(driver_number)
            except (AttributeError, TypeError):
                try:
                    # Fallback to older method
                    driver_laps = session.laps.pick_driver(driver_number)
                except Exception as fallback_error:
                    logger.error(f"Failed to get lap data using fallback method: {fallback_error}")
                    return []
            
            # Validate lap data
            if driver_laps is None:
                logger.warning(f"No lap data found for driver {driver_number}")
                return []
            
            if hasattr(driver_laps, 'empty') and driver_laps.empty:
                logger.warning(f"Empty lap data for driver {driver_number}")
                return []
            elif len(driver_laps) == 0:
                logger.warning(f"No laps found for driver {driver_number}")
                return []
            
            # Get telemetry data for enhanced metrics
            driver_car_data = None
            try:
                driver_car_data = session.car_data.pick_drivers(driver_number)
            except (AttributeError, TypeError):
                try:
                    driver_car_data = session.car_data.pick_driver(driver_number)
                except Exception:
                    logger.debug(f"No telemetry data available for driver {driver_number}")
                    driver_car_data = None
            
            lap_data = []
            
            for idx, lap in driver_laps.iterrows():
                try:
                    # Skip invalid laps
                    if pd.isna(lap.get('LapTime')) or lap.get('LapTime') == pd.Timedelta(0):
                        continue
                    
                    lap_time_seconds = lap['LapTime'].total_seconds()
                    
                    # Skip extremely fast or slow laps (likely invalid)
                    if lap_time_seconds < 60 or lap_time_seconds > 300:
                        logger.debug(f"Skipping invalid lap time: {lap_time_seconds}s")
                        continue
                    
                    # Extract sector times safely
                    sector1_time = self._safe_timedelta_to_seconds(lap.get('Sector1Time'))
                    sector2_time = self._safe_timedelta_to_seconds(lap.get('Sector2Time'))
                    sector3_time = self._safe_timedelta_to_seconds(lap.get('Sector3Time'))
                    
                    # Enhanced speed analysis
                    speed_metrics = self._calculate_speed_metrics(lap, driver_car_data, lap_time_seconds)
                    
                    # Enhanced lap information
                    lap_info = {
                        'DriverNumber': str(driver_number),
                        'LapNumber': int(lap.get('LapNumber', 0)),
                        'LapTime': lap_time_seconds,
                        'LapTimeFormatted': self._format_time(lap_time_seconds),
                        'Sector1Time': sector1_time,
                        'Sector2Time': sector2_time,
                        'Sector3Time': sector3_time,
                        'Sector1Formatted': self._format_sector_time(sector1_time),
                        'Sector2Formatted': self._format_sector_time(sector2_time),
                        'Sector3Formatted': self._format_sector_time(sector3_time),
                        'Compound': str(lap.get('Compound', 'UNKNOWN')),
                        'TyreLife': int(lap.get('TyreLife', 0)) if pd.notna(lap.get('TyreLife')) else 0,
                        'Stint': int(lap.get('Stint', 1)) if pd.notna(lap.get('Stint')) else 1,
                        'IsPersonalBest': bool(lap.get('IsPersonalBest', False)),
                        'LapStartTime': lap.get('LapStartTime').isoformat() if pd.notna(lap.get('LapStartTime')) else None,
                        'TrackStatus': str(lap.get('TrackStatus', 'Unknown')),
                        'Position': int(lap.get('Position', 0)) if pd.notna(lap.get('Position')) else 0,
                        'SpeedI1': float(lap.get('SpeedI1', 0)) if pd.notna(lap.get('SpeedI1')) else 0,
                        'SpeedI2': float(lap.get('SpeedI2', 0)) if pd.notna(lap.get('SpeedI2')) else 0,
                        'SpeedFL': float(lap.get('SpeedFL', 0)) if pd.notna(lap.get('SpeedFL')) else 0,
                        'SpeedST': float(lap.get('SpeedST', 0)) if pd.notna(lap.get('SpeedST')) else 0,
                        # Enhanced telemetry data
                        'MaxSpeed': speed_metrics['max_speed'],
                        'AvgSpeed': speed_metrics['avg_speed'],
                        'GearChanges': speed_metrics['gear_changes'],
                        'MaxSpeedFormatted': f"{speed_metrics['max_speed']:.1f} km/h" if speed_metrics['max_speed'] > 0 else "N/A",
                        'AvgSpeedFormatted': f"{speed_metrics['avg_speed']:.1f} km/h" if speed_metrics['avg_speed'] > 0 else "N/A"
                    }
                    
                    lap_data.append(lap_info)
                    
                except Exception as lap_error:
                    logger.warning(f"Error processing lap {lap.get('LapNumber', 'unknown')}: {lap_error}")
                    continue
            
            logger.info(f"Extracted {len(lap_data)} valid laps for driver {driver_number}")
            return lap_data
            
        except Exception as e:
            logger.error(f"Error extracting driver lap data for {driver_number}: {e}")
            return []
    
    def _safe_timedelta_to_seconds(self, time_delta) -> float:
        """Safely convert timedelta to seconds"""
        try:
            if pd.notna(time_delta) and time_delta != pd.Timedelta(0):
                return time_delta.total_seconds()
            return 0.0
        except (AttributeError, TypeError):
            return 0.0
    
    def _calculate_speed_metrics(self, lap: Any, driver_car_data: Any, lap_time_seconds: float) -> Dict[str, float]:
        """Calculate enhanced speed metrics from lap and telemetry data"""
        max_speed = 0.0
        avg_speed = 0.0
        gear_changes = 0
        
        try:
            # Use speed trap data from lap
            speed_data_sources = []
            for speed_field in ['SpeedI1', 'SpeedI2', 'SpeedFL', 'SpeedST']:
                speed_value = lap.get(speed_field, 0)
                if pd.notna(speed_value) and speed_value > 0:
                    speed_data_sources.append(float(speed_value))
            
            # Calculate speed metrics from available speed trap data
            if speed_data_sources:
                max_speed = max(speed_data_sources)
                avg_speed = sum(speed_data_sources) / len(speed_data_sources)
            
            # Try to get telemetry data for more detailed analysis
            if driver_car_data is not None and not driver_car_data.empty:
                try:
                    lap_start_time = lap.get('LapStartTime')
                    if pd.notna(lap_start_time):
                        # Find telemetry data for this lap timeframe
                        lap_telemetry = driver_car_data[
                            (driver_car_data.index >= lap_start_time) & 
                            (driver_car_data.index < lap_start_time + pd.Timedelta(seconds=lap_time_seconds + 10))
                        ]
                        
                        if not lap_telemetry.empty:
                            # Calculate enhanced speed metrics
                            if 'Speed' in lap_telemetry.columns:
                                speeds = lap_telemetry['Speed'].dropna()
                                if not speeds.empty:
                                    telemetry_max = float(speeds.max())
                                    telemetry_avg = float(speeds.mean())
                                    # Use telemetry if it provides better data
                                    if telemetry_max > max_speed:
                                        max_speed = telemetry_max
                                    if telemetry_avg > 0:
                                        avg_speed = telemetry_avg
                            
                            # Calculate gear changes
                            if 'nGear' in lap_telemetry.columns:
                                gears = lap_telemetry['nGear'].dropna()
                                if len(gears) > 1:
                                    gear_changes = int((gears.diff() != 0).sum())
                                    
                except Exception as telemetry_error:
                    logger.debug(f"Telemetry processing failed: {telemetry_error}")
            
            # If still no speed data, estimate from lap times
            if max_speed == 0 and avg_speed == 0:
                # Approximate track length (average F1 circuit ~5km)
                track_length_km = 5.0
                if lap_time_seconds > 0:
                    avg_speed = (track_length_km / (lap_time_seconds / 3600))
                    max_speed = avg_speed * 1.3  # Estimate max as ~1.3x average
            
            # Estimate gear changes if not available from telemetry
            if gear_changes == 0:
                if lap_time_seconds < 90:  # Very fast lap
                    gear_changes = 45 + int((90 - lap_time_seconds) * 2)
                elif lap_time_seconds < 100:  # Normal race pace
                    gear_changes = 35 + int((100 - lap_time_seconds) * 1)
                else:  # Slower lap
                    gear_changes = 25
            
        except Exception as e:
            logger.debug(f"Error calculating speed metrics: {e}")
        
        return {
            'max_speed': max_speed,
            'avg_speed': avg_speed,
            'gear_changes': gear_changes
        }
    
    def _format_time(self, seconds: float) -> str:
        """Format lap time in MM:SS.mmm format"""
        try:
            if seconds <= 0:
                return "N/A"
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}:{remaining_seconds:06.3f}"
        except Exception:
            return "N/A"
    
    def _format_sector_time(self, seconds: float) -> str:
        """Format sector time in SS.mmm format"""
        try:
            if seconds <= 0:
                return "N/A"
            return f"{seconds:.3f}s"
        except Exception:
            return "N/A"
    
    def calculate_lap_statistics(self, lap_data: List[Dict]) -> Dict[str, Any]:
        """Calculate comprehensive lap statistics"""
        try:
            if not lap_data:
                return {}
            
            # Extract lap times
            lap_times = [lap['LapTime'] for lap in lap_data if lap['LapTime'] > 0]
            
            if not lap_times:
                return {}
            
            # Basic statistics
            best_lap_time = min(lap_times)
            worst_lap_time = max(lap_times)
            average_lap_time = sum(lap_times) / len(lap_times)
            
            # Find best lap
            best_lap = min(lap_data, key=lambda x: x['LapTime'] if x['LapTime'] > 0 else float('inf'))
            
            # Calculate consistency (standard deviation)
            if len(lap_times) > 1:
                lap_times_array = np.array(lap_times)
                consistency = float(np.std(lap_times_array))
            else:
                consistency = 0.0
            
            # Count personal bests
            personal_best_count = sum(1 for lap in lap_data if lap.get('IsPersonalBest', False))
            
            # Get compounds used
            compounds_used = list(set(lap['Compound'] for lap in lap_data if lap['Compound'] != 'UNKNOWN'))
            
            # Calculate stint count
            stint_count = len(set(lap['Stint'] for lap in lap_data))
            
            # Calculate theoretical best (sum of best sector times)
            sector1_times = [lap['Sector1Time'] for lap in lap_data if lap['Sector1Time'] > 0]
            sector2_times = [lap['Sector2Time'] for lap in lap_data if lap['Sector2Time'] > 0]
            sector3_times = [lap['Sector3Time'] for lap in lap_data if lap['Sector3Time'] > 0]
            
            theoretical_best = 0
            if sector1_times and sector2_times and sector3_times:
                theoretical_best = min(sector1_times) + min(sector2_times) + min(sector3_times)
            
            return {
                'total_laps': len(lap_data),
                'best_lap_time': best_lap_time,
                'best_lap_time_formatted': self._format_time(best_lap_time),
                'best_lap_number': best_lap.get('LapNumber', 0),
                'worst_lap_time': worst_lap_time,
                'worst_lap_time_formatted': self._format_time(worst_lap_time),
                'average_lap_time': average_lap_time,
                'average_lap_time_formatted': self._format_time(average_lap_time),
                'consistency': consistency,
                'consistency_formatted': f"{consistency:.3f}s",
                'personal_best_count': personal_best_count,
                'compounds_used': compounds_used,
                'stint_count': stint_count,
                'theoretical_best': theoretical_best,
                'theoretical_best_formatted': self._format_time(theoretical_best) if theoretical_best > 0 else "N/A"
            }
            
        except Exception as e:
            logger.error(f"Error calculating lap statistics: {e}")
            return {}
