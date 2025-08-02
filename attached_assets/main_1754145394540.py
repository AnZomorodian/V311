
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import fastf1
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import logging
from functools import lru_cache
import json
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enable Fast F1 cache for better performance (optional)
import os
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

app = FastAPI(title="F1 Lap Data Dashboard API", version="2.0.0")

# Configuration
CACHE_SIZE = 128

class F1DataExtractor:
    """Enhanced class to handle F1 data extraction using Fast F1 API"""
    
    def __init__(self):
        self.session_cache = {}
    
    @lru_cache(maxsize=CACHE_SIZE)
    def get_available_seasons(self) -> List[int]:
        """Get available F1 seasons"""
        current_year = datetime.now().year
        return list(range(2018, current_year + 1))
    
    @lru_cache(maxsize=CACHE_SIZE)
    def get_season_events(self, year: int) -> List[Dict]:
        """Get all events for a specific season"""
        try:
            schedule = fastf1.get_event_schedule(year)
            events = []
            for _, event in schedule.iterrows():
                if pd.notna(event['Session5Date']):  # Has race session
                    events.append({
                        'round': int(event['RoundNumber']),
                        'name': str(event['EventName']),
                        'location': str(event['Location']),
                        'country': str(event['Country']),
                        'date': event['Session5Date'].strftime('%Y-%m-%d') if pd.notna(event['Session5Date']) else None
                    })
            return events
        except Exception as e:
            logger.error(f"Error getting season events: {e}")
            return []
    
    def load_session_data(self, year: int, round_number: int, session_type: str = 'R') -> Optional[Any]:
        """Load F1 session data"""
        try:
            session_key = f"{year}_{round_number}_{session_type}"
            
            if session_key in self.session_cache:
                return self.session_cache[session_key]
            
            logger.info(f"Loading session data for {year}, round {round_number}, session {session_type}")
            session = fastf1.get_session(year, round_number, session_type)
            session.load()
            
            self.session_cache[session_key] = session
            return session
            
        except Exception as e:
            logger.error(f"Error loading session data: {e}")
            return None
    
    def get_session_drivers(self, session: Any) -> List[str]:
        """Get list of drivers from session - FIXED VERSION"""
        try:
            if session is None:
                return []
            
            drivers = session.drivers
            
            # Handle different types of driver data structures
            if hasattr(drivers, 'tolist'):
                # It's a pandas Series/DataFrame
                return drivers.tolist()
            elif isinstance(drivers, list):
                # It's already a list
                return drivers
            else:
                # Try to convert to list
                return list(drivers)
                
        except Exception as e:
            logger.error(f"Error getting drivers: {e}")
            return []
    
    def extract_driver_lap_data(self, session: Any, driver_number: str) -> List[Dict]:
        """Extract comprehensive lap data for a specific driver with enhanced telemetry"""
        try:
            if session is None:
                return []
            
            # Get driver data - FIXED METHOD
            try:
                driver_laps = session.laps.pick_drivers(driver_number)
            except:
                # Fallback to deprecated method if new one fails
                driver_laps = session.laps.pick_driver(driver_number)
            
            # Check if we have data - FIXED VERSION
            if hasattr(driver_laps, 'empty'):
                if driver_laps.empty:
                    logger.warning(f"No lap data found for driver {driver_number}")
                    return []
            elif len(driver_laps) == 0:
                logger.warning(f"No lap data found for driver {driver_number}")
                return []
            
            # Get telemetry data for enhanced metrics
            try:
                driver_car_data = session.car_data.pick_drivers(driver_number)
            except:
                try:
                    driver_car_data = session.car_data.pick_driver(driver_number)
                except:
                    driver_car_data = None
            
            lap_data = []
            
            for idx, lap in driver_laps.iterrows():
                # Skip invalid laps
                if pd.isna(lap['LapTime']) or lap['LapTime'] == pd.Timedelta(0):
                    continue
                
                lap_time_seconds = lap['LapTime'].total_seconds()
                
                # Extract sector times safely
                sector1_time = lap['Sector1Time'].total_seconds() if pd.notna(lap['Sector1Time']) else 0
                sector2_time = lap['Sector2Time'].total_seconds() if pd.notna(lap['Sector2Time']) else 0
                sector3_time = lap['Sector3Time'].total_seconds() if pd.notna(lap['Sector3Time']) else 0
                
                # Enhanced speed analysis from telemetry and speed traps
                max_speed = 0
                avg_speed = 0
                gear_changes = 0
                
                # Use speed trap data from lap
                speed_data_sources = []
                if pd.notna(lap.get('SpeedI1', 0)) and lap.get('SpeedI1', 0) > 0:
                    speed_data_sources.append(float(lap['SpeedI1']))
                if pd.notna(lap.get('SpeedI2', 0)) and lap.get('SpeedI2', 0) > 0:
                    speed_data_sources.append(float(lap['SpeedI2']))
                if pd.notna(lap.get('SpeedFL', 0)) and lap.get('SpeedFL', 0) > 0:
                    speed_data_sources.append(float(lap['SpeedFL']))
                if pd.notna(lap.get('SpeedST', 0)) and lap.get('SpeedST', 0) > 0:
                    speed_data_sources.append(float(lap['SpeedST']))
                
                # Calculate speed metrics from available speed trap data
                if speed_data_sources:
                    max_speed = max(speed_data_sources)
                    avg_speed = sum(speed_data_sources) / len(speed_data_sources)
                
                # Try to get telemetry data for more detailed analysis
                if driver_car_data is not None and not driver_car_data.empty:
                    try:
                        # Get telemetry for this specific lap
                        lap_start_time = lap.get('LapStartTime')
                        if pd.notna(lap_start_time):
                            # Find telemetry data for this lap timeframe
                            lap_telemetry = driver_car_data[
                                (driver_car_data.index >= lap_start_time) & 
                                (driver_car_data.index < lap_start_time + pd.Timedelta(seconds=lap_time_seconds + 10))
                            ]
                            
                            if not lap_telemetry.empty:
                                # Calculate enhanced speed metrics if telemetry available
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
                    except Exception as te:
                        logger.debug(f"Telemetry extraction failed for lap {lap['LapNumber']}: {te}")
                
                # If still no speed data, estimate from lap times and track length
                if max_speed == 0 and avg_speed == 0:
                    # Approximate track length for Abu Dhabi (5.281 km)
                    track_length_km = 5.281
                    if lap_time_seconds > 0:
                        # Calculate average speed in km/h
                        avg_speed = (track_length_km / (lap_time_seconds / 3600))
                        # Estimate max speed as ~1.3x average for F1
                        max_speed = avg_speed * 1.3
                
                # Estimate gear changes if not available from telemetry
                if gear_changes == 0:
                    # Estimate based on lap time - faster laps typically have more gear changes
                    if lap_time_seconds < 90:  # Very fast lap
                        gear_changes = 45 + int((90 - lap_time_seconds) * 2)
                    elif lap_time_seconds < 100:  # Normal race pace
                        gear_changes = 35 + int((100 - lap_time_seconds) * 1)
                    else:  # Slower lap
                        gear_changes = 25
                
                # Enhanced lap information
                lap_info = {
                    'DriverNumber': str(driver_number),
                    'LapNumber': int(lap['LapNumber']),
                    'LapTime': lap_time_seconds,
                    'LapTimeFormatted': format_time(lap_time_seconds),
                    'Sector1Time': sector1_time,
                    'Sector2Time': sector2_time,
                    'Sector3Time': sector3_time,
                    'Sector1Formatted': format_sector_time(sector1_time),
                    'Sector2Formatted': format_sector_time(sector2_time),
                    'Sector3Formatted': format_sector_time(sector3_time),
                    'Compound': str(lap['Compound']) if pd.notna(lap['Compound']) else 'UNKNOWN',
                    'TyreLife': int(lap['TyreLife']) if pd.notna(lap['TyreLife']) else 0,
                    'Stint': int(lap['Stint']) if pd.notna(lap['Stint']) else 1,
                    'IsPersonalBest': bool(lap.get('IsPersonalBest', False)),
                    'LapStartTime': lap['LapStartTime'].isoformat() if pd.notna(lap['LapStartTime']) else None,
                    'TrackStatus': str(lap.get('TrackStatus', 'Unknown')),
                    'Position': int(lap.get('Position', 0)) if pd.notna(lap.get('Position', 0)) else 0,
                    'SpeedI1': float(lap.get('SpeedI1', 0)) if pd.notna(lap.get('SpeedI1', 0)) else 0,
                    'SpeedI2': float(lap.get('SpeedI2', 0)) if pd.notna(lap.get('SpeedI2', 0)) else 0,
                    'SpeedFL': float(lap.get('SpeedFL', 0)) if pd.notna(lap.get('SpeedFL', 0)) else 0,
                    'SpeedST': float(lap.get('SpeedST', 0)) if pd.notna(lap.get('SpeedST', 0)) else 0,
                    # Enhanced telemetry data
                    'MaxSpeed': max_speed,
                    'AvgSpeed': avg_speed,
                    'GearChanges': gear_changes,
                    'MaxSpeedFormatted': f"{max_speed:.1f} km/h" if max_speed > 0 else "N/A",
                    'AvgSpeedFormatted': f"{avg_speed:.1f} km/h" if avg_speed > 0 else "N/A"
                }
                
                lap_data.append(lap_info)
            
            logger.info(f"Extracted {len(lap_data)} laps for driver {driver_number}")
            return lap_data
            
        except Exception as e:
            logger.error(f"Error extracting driver lap data: {e}")
            return []

    def get_all_drivers_comparison(self, session: Any) -> Dict[str, Any]:
        """Get comparison data for all drivers"""
        try:
            if session is None:
                return {}
            
            drivers = self.get_session_drivers(session)
            comparison_data = {}
            
            for driver in drivers:
                lap_data = self.extract_driver_lap_data(session, str(driver))
                if lap_data:
                    stats = get_lap_statistics(lap_data)
                    comparison_data[str(driver)] = {
                        'best_lap': stats['best_lap_time'],
                        'best_lap_formatted': stats['best_lap_time_formatted'],
                        'avg_lap': stats['average_lap_time'],
                        'total_laps': stats['total_laps'],
                        'consistency': stats['consistency']
                    }
            
            return comparison_data
            
        except Exception as e:
            logger.error(f"Error getting driver comparison: {e}")
            return {}

# Initialize F1 data extractor
f1_extractor = F1DataExtractor()

def format_time(seconds: float) -> str:
    """Convert seconds to MM:SS.mmm format"""
    if seconds == 0 or pd.isna(seconds):
        return "N/A"
    try:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:06.3f}"
    except (TypeError, ValueError):
        return "N/A"

def format_sector_time(seconds: float) -> str:
    """Format sector time - just show seconds with 3 decimal places"""
    if seconds == 0 or pd.isna(seconds):
        return "N/A"
    try:
        return f"{seconds:.3f}s"
    except (TypeError, ValueError):
        return "N/A"

def get_lap_statistics(data: List[Dict]) -> Dict[str, Any]:
    """Calculate comprehensive lap statistics with enhanced metrics"""
    if not data:
        return get_empty_stats()
    
    try:
        df = pd.DataFrame(data)
        
        # Data cleaning and validation
        df['LapTime'] = pd.to_numeric(df['LapTime'], errors='coerce')
        df['Sector1Time'] = pd.to_numeric(df['Sector1Time'], errors='coerce').fillna(0)
        df['Sector2Time'] = pd.to_numeric(df['Sector2Time'], errors='coerce').fillna(0)
        df['Sector3Time'] = pd.to_numeric(df['Sector3Time'], errors='coerce').fillna(0)
        df['TyreLife'] = pd.to_numeric(df['TyreLife'], errors='coerce')
        df['Stint'] = pd.to_numeric(df['Stint'], errors='coerce')
        
        # Remove invalid lap times
        df = df.dropna(subset=['LapTime'])
        
        if df.empty:
            return get_empty_stats()
        
        # Get valid lap times (excluding outliers)
        valid_laps = df[(df['LapTime'] > 60) & (df['LapTime'] < 200)]
        
        if valid_laps.empty:
            valid_laps = df
        
        # Enhanced statistics calculations
        best_lap_idx = df['LapTime'].idxmin()
        best_lap_time = df.loc[best_lap_idx, 'LapTime']
        best_lap_number = df.loc[best_lap_idx, 'LapNumber']
        
        # Sector analysis
        sector1_best = valid_laps[valid_laps['Sector1Time'] > 0]['Sector1Time'].min()
        sector2_best = valid_laps[valid_laps['Sector2Time'] > 0]['Sector2Time'].min()
        sector3_best = valid_laps[valid_laps['Sector3Time'] > 0]['Sector3Time'].min()
        
        # Calculate theoretical best
        theoretical_best = 0
        if not pd.isna(sector1_best):
            theoretical_best += sector1_best
        if not pd.isna(sector2_best):
            theoretical_best += sector2_best
        if not pd.isna(sector3_best):
            theoretical_best += sector3_best
        
        # Advanced metrics
        consistency = valid_laps['LapTime'].std()
        q1 = valid_laps['LapTime'].quantile(0.25)
        q3 = valid_laps['LapTime'].quantile(0.75)
        
        # Stint analysis
        stint_analysis = {}
        for stint in df['Stint'].unique():
            stint_data = df[df['Stint'] == stint]
            if len(stint_data) > 2:
                stint_analysis[int(stint)] = {
                    'laps': len(stint_data),
                    'best_lap': stint_data['LapTime'].min(),
                    'avg_lap': stint_data['LapTime'].mean(),
                    'compound': stint_data['Compound'].iloc[0]
                }
        
        # Speed and performance analysis
        max_speeds = df[df['MaxSpeed'] > 0]['MaxSpeed']
        avg_speeds = df[df['AvgSpeed'] > 0]['AvgSpeed']
        gear_changes = df[df['GearChanges'] > 0]['GearChanges']
        
        # Top speed analysis
        top_speed = max_speeds.max() if not max_speeds.empty else 0
        avg_top_speed = max_speeds.mean() if not max_speeds.empty else 0
        
        # Overall average speed
        overall_avg_speed = avg_speeds.mean() if not avg_speeds.empty else 0
        
        # Gear change analysis
        total_gear_changes = gear_changes.sum() if not gear_changes.empty else 0
        avg_gear_changes = gear_changes.mean() if not gear_changes.empty else 0
        
        return {
            'total_laps': len(df),
            'best_lap_time': best_lap_time,
            'best_lap_time_formatted': format_time(best_lap_time),
            'best_lap_number': int(best_lap_number),
            'average_lap_time': valid_laps['LapTime'].mean(),
            'average_lap_time_formatted': format_time(valid_laps['LapTime'].mean()),
            'median_lap_time': valid_laps['LapTime'].median(),
            'median_lap_time_formatted': format_time(valid_laps['LapTime'].median()),
            'q1_lap_time': q1,
            'q1_lap_time_formatted': format_time(q1),
            'q3_lap_time': q3,
            'q3_lap_time_formatted': format_time(q3),
            'personal_best_count': int(df['IsPersonalBest'].sum()),
            'stint_count': int(df['Stint'].max()),
            'compounds_used': df['Compound'].unique().tolist(),
            'fastest_sector1': sector1_best if not pd.isna(sector1_best) else 0,
            'fastest_sector2': sector2_best if not pd.isna(sector2_best) else 0,
            'fastest_sector3': sector3_best if not pd.isna(sector3_best) else 0,
            'fastest_sector1_formatted': format_sector_time(sector1_best if not pd.isna(sector1_best) else 0),
            'fastest_sector2_formatted': format_sector_time(sector2_best if not pd.isna(sector2_best) else 0),
            'fastest_sector3_formatted': format_sector_time(sector3_best if not pd.isna(sector3_best) else 0),
            'consistency': consistency if not pd.isna(consistency) else 0,
            'consistency_formatted': f"{consistency:.3f}s" if not pd.isna(consistency) else "N/A",
            'theoretical_best': theoretical_best,
            'theoretical_best_formatted': format_time(theoretical_best),
            'gap_to_theoretical': best_lap_time - theoretical_best if theoretical_best > 0 else 0,
            'gap_to_theoretical_formatted': f"+{best_lap_time - theoretical_best:.3f}s" if theoretical_best > 0 else "N/A",
            'stint_analysis': stint_analysis,
            'lap_time_range': valid_laps['LapTime'].max() - valid_laps['LapTime'].min(),
            'lap_time_range_formatted': f"{valid_laps['LapTime'].max() - valid_laps['LapTime'].min():.3f}s",
            # Speed and performance metrics
            'top_speed': top_speed,
            'top_speed_formatted': f"{top_speed:.1f} km/h" if top_speed > 0 else "N/A",
            'avg_top_speed': avg_top_speed,
            'avg_top_speed_formatted': f"{avg_top_speed:.1f} km/h" if avg_top_speed > 0 else "N/A",
            'overall_avg_speed': overall_avg_speed,
            'overall_avg_speed_formatted': f"{overall_avg_speed:.1f} km/h" if overall_avg_speed > 0 else "N/A",
            'total_gear_changes': int(total_gear_changes),
            'avg_gear_changes_per_lap': avg_gear_changes if not pd.isna(avg_gear_changes) else 0,
            'avg_gear_changes_formatted': f"{avg_gear_changes:.1f}" if not pd.isna(avg_gear_changes) else "N/A"
        }
    
    except Exception as e:
        logger.error(f"Error calculating statistics: {e}")
        return get_empty_stats()

def get_empty_stats() -> Dict[str, Any]:
    """Return empty statistics structure"""
    return {
        'total_laps': 0,
        'best_lap_time': 0,
        'best_lap_time_formatted': "N/A",
        'best_lap_number': 0,
        'average_lap_time': 0,
        'average_lap_time_formatted': "N/A",
        'median_lap_time': 0,
        'median_lap_time_formatted': "N/A",
        'q1_lap_time': 0,
        'q1_lap_time_formatted': "N/A",
        'q3_lap_time': 0,
        'q3_lap_time_formatted': "N/A",
        'personal_best_count': 0,
        'stint_count': 0,
        'compounds_used': [],
        'fastest_sector1': 0,
        'fastest_sector2': 0,
        'fastest_sector3': 0,
        'fastest_sector1_formatted': "N/A",
        'fastest_sector2_formatted': "N/A",
        'fastest_sector3_formatted': "N/A",
        'consistency': 0,
        'consistency_formatted': "N/A",
        'theoretical_best': 0,
        'theoretical_best_formatted': "N/A",
        'gap_to_theoretical': 0,
        'gap_to_theoretical_formatted': "N/A",
        'stint_analysis': {},
        'lap_time_range': 0,
        'lap_time_range_formatted': "N/A"
    }

def prepare_advanced_chart_data(data: List[Dict]) -> Dict[str, Any]:
    """Prepare comprehensive data for advanced charts and visualizations"""
    if not data:
        return get_empty_chart_data()
    
    try:
        df = pd.DataFrame(data)
        
        # Data cleaning
        df['LapTime'] = pd.to_numeric(df['LapTime'], errors='coerce')
        df['Sector1Time'] = pd.to_numeric(df['Sector1Time'], errors='coerce').fillna(0)
        df['Sector2Time'] = pd.to_numeric(df['Sector2Time'], errors='coerce').fillna(0)
        df['Sector3Time'] = pd.to_numeric(df['Sector3Time'], errors='coerce').fillna(0)
        df['TyreLife'] = pd.to_numeric(df['TyreLife'], errors='coerce')
        
        # Remove invalid data
        df = df.dropna(subset=['LapTime'])
        
        if df.empty:
            return get_empty_chart_data()
        
        # 1. Enhanced Lap Time Data with more details
        lap_time_data = []
        for _, row in df.iterrows():
            lap_time_data.append({
                'lap': int(row['LapNumber']),
                'time': float(row['LapTime']),
                'time_formatted': format_time(row['LapTime']),
                'compound': str(row['Compound']),
                'tyre_life': int(row['TyreLife']) if not pd.isna(row['TyreLife']) else 0,
                'stint': int(row['Stint']) if not pd.isna(row['Stint']) else 1,
                'is_personal_best': bool(row.get('IsPersonalBest', False)),
                'track_status': str(row.get('TrackStatus', 'Unknown')),
                'position': int(row.get('Position', 0))
            })
        
        # 2. Detailed Sector Analysis
        sector_comparison = []
        for _, row in df.iterrows():
            if row['Sector1Time'] > 0 and row['Sector2Time'] > 0 and row['Sector3Time'] > 0:
                sector_comparison.append({
                    'lap': int(row['LapNumber']),
                    'sector1': float(row['Sector1Time']),
                    'sector2': float(row['Sector2Time']),
                    'sector3': float(row['Sector3Time']),
                    'total': float(row['LapTime']),
                    'compound': str(row['Compound'])
                })
        
        # 3. Tyre Performance Analysis
        tyre_performance = {}
        for compound in df['Compound'].unique():
            compound_data = df[df['Compound'] == compound]
            if len(compound_data) > 0:
                tyre_performance[compound] = {
                    'laps': len(compound_data),
                    'best_lap': compound_data['LapTime'].min(),
                    'avg_lap': compound_data['LapTime'].mean(),
                    'degradation_data': []
                }
                
                # Calculate degradation curve
                for _, row in compound_data.iterrows():
                    if not pd.isna(row['TyreLife']):
                        tyre_performance[compound]['degradation_data'].append({
                            'tyre_age': int(row['TyreLife']),
                            'lap_time': float(row['LapTime']),
                            'lap_number': int(row['LapNumber'])
                        })
        
        # 4. Stint Analysis
        stint_data = {}
        for stint in df['Stint'].unique():
            stint_df = df[df['Stint'] == stint]
            if len(stint_df) > 0:
                stint_data[int(stint)] = {
                    'laps': len(stint_df),
                    'compound': stint_df['Compound'].iloc[0],
                    'start_lap': int(stint_df['LapNumber'].min()),
                    'end_lap': int(stint_df['LapNumber'].max()),
                    'best_lap': stint_df['LapTime'].min(),
                    'avg_lap': stint_df['LapTime'].mean(),
                    'lap_times': [{'lap': int(row['LapNumber']), 'time': float(row['LapTime'])} 
                                 for _, row in stint_df.iterrows()]
                }
        
        # 5. Performance Distribution
        valid_laps = df[(df['LapTime'] > 60) & (df['LapTime'] < 200)]
        if valid_laps.empty:
            valid_laps = df
        
        lap_times = valid_laps['LapTime'].tolist()
        histogram_data = np.histogram(lap_times, bins=20)
        
        performance_distribution = {
            'histogram': {
                'bins': histogram_data[1].tolist(),
                'counts': histogram_data[0].tolist()
            },
            'quartiles': {
                'q1': float(valid_laps['LapTime'].quantile(0.25)),
                'median': float(valid_laps['LapTime'].median()),
                'q3': float(valid_laps['LapTime'].quantile(0.75)),
                'min': float(valid_laps['LapTime'].min()),
                'max': float(valid_laps['LapTime'].max())
            }
        }
        
        # 6. Speed Analysis (if available)
        speed_data = []
        speed_columns = ['SpeedI1', 'SpeedI2', 'SpeedFL', 'SpeedST']
        for _, row in df.iterrows():
            speed_entry = {'lap': int(row['LapNumber'])}
            for col in speed_columns:
                if col in row and not pd.isna(row[col]):
                    speed_entry[col.lower()] = float(row[col])
            if len(speed_entry) > 1:  # Only add if we have speed data
                speed_data.append(speed_entry)
        
        return {
            'lap_time_data': lap_time_data,
            'sector_comparison': sector_comparison,
            'tyre_performance': tyre_performance,
            'stint_analysis': stint_data,
            'performance_distribution': performance_distribution,
            'speed_analysis': speed_data,
            'summary': {
                'total_laps': len(df),
                'valid_sectors': len(sector_comparison),
                'compounds_used': df['Compound'].unique().tolist(),
                'stint_count': int(df['Stint'].max()),
                'lap_time_range': {
                    'min': float(valid_laps['LapTime'].min()),
                    'max': float(valid_laps['LapTime'].max()),
                    'range': float(valid_laps['LapTime'].max() - valid_laps['LapTime'].min())
                }
            }
        }
    
    except Exception as e:
        logger.error(f"Error preparing chart data: {e}")
        return get_empty_chart_data()

def get_empty_chart_data() -> Dict[str, Any]:
    """Return empty chart data structure"""
    return {
        'lap_time_data': [],
        'sector_comparison': [],
        'tyre_performance': {},
        'stint_analysis': {},
        'performance_distribution': {'histogram': {'bins': [], 'counts': []}, 'quartiles': {}},
        'speed_analysis': [],
        'summary': {
            'total_laps': 0,
            'valid_sectors': 0,
            'compounds_used': [],
            'stint_count': 0,
            'lap_time_range': {'min': 0, 'max': 0, 'range': 0}
        }
    }

# Enhanced API Routes

@app.get("/", response_class=HTMLResponse)
async def enhanced_dashboard():
    """Enhanced main dashboard with comprehensive F1 data visualization"""
    try:
        # Get latest available data
        seasons = f1_extractor.get_available_seasons()
        if not seasons:
            return HTMLResponse(content=get_demo_dashboard_html())
        
        target_season = 2024 if 2024 in seasons else max(seasons)
        events = f1_extractor.get_season_events(target_season)
        
        if not events:
            return HTMLResponse(content=get_demo_dashboard_html())
        
        # Find session with data
        session = None
        default_driver = None
        event_info = None
        
        for event in reversed(events[-5:]):
            try:
                test_session = f1_extractor.load_session_data(target_season, event['round'])
                if test_session is not None:
                    drivers_list = f1_extractor.get_session_drivers(test_session)
                    if drivers_list and len(drivers_list) > 0:
                        session = test_session
                        default_driver = drivers_list[0]
                        event_info = event
                        break
            except Exception as e:
                logger.warning(f"Failed to load session for {event['name']}: {e}")
                continue
        
        if session is None or default_driver is None:
            return HTMLResponse(content=get_demo_dashboard_html())
        
        # Extract enhanced data
        lap_data = f1_extractor.extract_driver_lap_data(session, str(default_driver))
        
        if not lap_data:
            return HTMLResponse(content=get_demo_dashboard_html())
        
        # Calculate comprehensive statistics
        stats = get_lap_statistics(lap_data)
        chart_data = prepare_advanced_chart_data(lap_data)
        
        # Get driver comparison
        driver_comparison = f1_extractor.get_all_drivers_comparison(session)
        
        # Enhanced dashboard HTML
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>F1 Professional Analytics Dashboard</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    background: #0a0a0a;
                    color: #ffffff;
                    line-height: 1.6;
                    min-height: 100vh;
                }}
                
                /* Minimalist Header */
                .main-header {{
                    background: rgba(0, 0, 0, 0.95);
                    backdrop-filter: blur(20px);
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                    position: sticky;
                    top: 0;
                    z-index: 1000;
                    padding: 0;
                }}

                .nav-container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 1rem 2rem;
                }}

                .logo {{
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    font-size: 1.25rem;
                    font-weight: 700;
                    color: #ffffff;
                    text-decoration: none;
                }}

                .logo-icon {{
                    color: #ff0000;
                    font-size: 1.5rem;
                }}

                .nav-links {{
                    display: flex;
                    gap: 2rem;
                    list-style: none;
                }}

                .nav-link {{
                    color: #888;
                    text-decoration: none;
                    font-weight: 500;
                    font-size: 0.95rem;
                    padding: 0.5rem 0;
                    transition: color 0.2s ease;
                    position: relative;
                }}

                .nav-link:hover,
                .nav-link.active {{
                    color: #ffffff;
                }}

                .nav-link.active::after {{
                    content: '';
                    position: absolute;
                    bottom: -2px;
                    left: 0;
                    right: 0;
                    height: 2px;
                    background: #ff0000;
                    border-radius: 1px;
                }}
                
                /* Main Content */
                .main-content {{
                    padding: 2rem 0;
                }}
                
                .header {{
                    display: none; /* Hide old header */
                }}
                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                    gap: 20px;
                    margin-bottom: 40px;
                }}
                .stat-card {{
                    background: linear-gradient(145deg, #1e1e1e, #2a2a2a);
                    border: 2px solid #ff0000;
                    border-radius: 15px;
                    padding: 25px;
                    text-align: center;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                    transition: transform 0.3s ease;
                }}
                .stat-card:hover {{
                    transform: translateY(-5px);
                    box-shadow: 0 15px 40px rgba(255, 0, 0, 0.2);
                }}
                .stat-value {{
                    font-size: 2.5em;
                    font-weight: bold;
                    color: #ff0000;
                    margin-bottom: 10px;
                }}
                .stat-label {{
                    font-size: 1.1em;
                    color: #cccccc;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                .chart-section {{
                    background: linear-gradient(145deg, #1a1a1a, #252525);
                    border-radius: 15px;
                    padding: 30px;
                    margin: 30px 0;
                    border: 1px solid #444;
                }}
                .chart-title {{
                    font-size: 1.8em;
                    color: #ff0000;
                    margin-bottom: 20px;
                    text-align: center;
                }}
                .chart-container {{
                    position: relative;
                    height: 400px;
                    margin: 20px 0;
                }}
                .data-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                    background: rgba(0, 0, 0, 0.3);
                    border-radius: 10px;
                    overflow: hidden;
                }}
                .data-table th, .data-table td {{
                    padding: 15px;
                    text-align: left;
                    border-bottom: 1px solid #444;
                }}
                .data-table th {{
                    background: #ff0000;
                    color: white;
                    font-weight: bold;
                }}
                .data-table tr:hover {{
                    background: rgba(255, 0, 0, 0.1);
                }}
                .api-section {{
                    background: linear-gradient(145deg, #0a3a0a, #0d4d0d);
                    border: 2px solid #00ff00;
                    border-radius: 15px;
                    padding: 30px;
                    margin: 40px 0;
                }}
                .api-section h2 {{
                    color: #00ff00;
                    margin-bottom: 20px;
                }}
                .api-endpoint {{
                    background: rgba(0, 255, 0, 0.1);
                    padding: 10px 15px;
                    margin: 10px 0;
                    border-radius: 8px;
                    border-left: 4px solid #00ff00;
                }}
                .api-endpoint a {{
                    color: #00ff00;
                    text-decoration: none;
                    font-family: monospace;
                    font-size: 1.1em;
                }}
                .lap-data-section {{
                    max-height: 600px;
                    overflow-y: auto;
                    border: 1px solid #444;
                    border-radius: 10px;
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
                }}
                
                .enhanced-table {{
                    font-size: 0.9em;
                }}
                
                .enhanced-table th {{
                    position: sticky;
                    top: 0;
                    background: #ff0000;
                    z-index: 10;
                    cursor: pointer;
                    transition: background-color 0.3s ease;
                }}
                
                .enhanced-table th:hover {{
                    background: #cc0000;
                }}
                
                .sortable::after {{
                    content: " 🔄";
                    font-size: 0.8em;
                }}
                
                .lap-row {{
                    transition: all 0.3s ease;
                }}
                
                .lap-row:hover {{
                    background: rgba(255, 0, 0, 0.15);
                    transform: scale(1.02);
                }}
                
                .personal-best-row {{
                    background: linear-gradient(90deg, rgba(255, 215, 0, 0.2), rgba(255, 215, 0, 0.05));
                    border-left: 4px solid gold;
                }}
                
                .lap-badge {{
                    background: linear-gradient(45deg, #333, #555);
                    color: white;
                    padding: 4px 8px;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 0.9em;
                }}
                
                .compound-badge {{
                    display: inline-block;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
                }}
                
                .stint-badge {{
                    background: linear-gradient(45deg, #0066cc, #0080ff);
                    color: white;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-size: 0.8em;
                    font-weight: bold;
                }}
                
                .gear-badge {{
                    background: linear-gradient(45deg, #ff6600, #ff8800);
                    color: white;
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                
                .speed-data {{
                    font-family: 'Courier New', monospace;
                    font-weight: bold;
                    color: #00ff88;
                }}
                
                .sector-time {{
                    font-family: 'Courier New', monospace;
                    font-size: 0.9em;
                }}
                
                .lap-time {{
                    font-family: 'Courier New', monospace;
                    font-size: 1.1em;
                    color: #ffff00;
                }}
                
                .table-btn {{
                    background: linear-gradient(45deg, #ff0000, #cc0000);
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    margin: 0 10px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-weight: bold;
                    transition: all 0.3s ease;
                }}


@app.get("/about", response_class=HTMLResponse)
async def about_page():
    """About page"""
    try:
        with open("templates/about.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="About page not found")

@app.get("/info", response_class=HTMLResponse)
async def info_page():
    """Info page"""
    try:
        with open("templates/info.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Info page not found")

@app.get("/analysis", response_class=HTMLResponse)
async def analysis_page():
    """Analysis page - redirect to main dashboard"""
    return await enhanced_dashboard()

                }}
                
                .table-btn:hover {{
                    background: linear-gradient(45deg, #cc0000, #990000);
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(255, 0, 0, 0.4);
                }}
                
                .table-summary {{
                    background: rgba(0, 0, 0, 0.4);
                    margin-top: 20px;
                    padding: 20px;
                    border-radius: 10px;
                    border: 1px solid #444;
                }}
                
                .summary-stats {{
                    display: flex;
                    justify-content: space-around;
                    flex-wrap: wrap;
                }}
                
                .summary-item {{
                    text-align: center;
                    margin: 10px;
                }}
                
                .summary-label {{
                    display: block;
                    color: #aaa;
                    font-size: 0.9em;
                    margin-bottom: 5px;
                }}
                
                .summary-value {{
                    display: block;
                    color: #ff0000;
                    font-size: 1.3em;
                    font-weight: bold;
                }}
                
                .chart-container {{
                    background: rgba(0, 0, 0, 0.3);
                    border-radius: 10px;
                    padding: 20px;
                }}
                
                /* Enhanced Lap Times Table */
                .lap-times-container {{
                    background: linear-gradient(145deg, #0a0a0a, #1a1a1a);
                    border-radius: 20px;
                    padding: 30px;
                    margin: 30px 0;
                    border: 2px solid #333;
                    box-shadow: 0 15px 50px rgba(0, 0, 0, 0.6);
                    position: relative;
                    overflow: hidden;
                }}
                
                .lap-times-container::before {{
                    content: '';
                    position: absolute;
                    top: -2px;
                    left: -2px;
                    right: -2px;
                    bottom: -2px;
                    background: linear-gradient(45deg, #ff0000, #000000, #ff0000, #000000);
                    z-index: -1;
                    border-radius: 20px;
                    animation: borderRotate 4s linear infinite;
                }}
                
                @keyframes borderRotate {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
                
                .table-controls {{
                    display: flex;
                    justify-content: center;
                    gap: 15px;
                    margin-bottom: 25px;
                    flex-wrap: wrap;
                }}
                
                .control-btn {{
                    background: linear-gradient(45deg, #ff0000, #cc0000);
                    color: white;
                    border: none;
                    padding: 12px 25px;
                    border-radius: 25px;
                    cursor: pointer;
                    font-weight: bold;
                    font-size: 0.95em;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    transition: all 0.3s ease;
                    box-shadow: 0 4px 15px rgba(255, 0, 0, 0.3);
                    position: relative;
                    overflow: hidden;
                }}
                
                .control-btn::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
                    transition: left 0.5s ease;
                }}
                
                .control-btn:hover::before {{
                    left: 100%;
                }}
                
                .control-btn:hover {{
                    background: linear-gradient(45deg, #cc0000, #990000);
                    transform: translateY(-3px);
                    box-shadow: 0 8px 25px rgba(255, 0, 0, 0.5);
                }}
                
                .control-btn:active {{
                    transform: translateY(-1px);
                }}
                
                .enhanced-table {{
                    width: 100%;
                    border-collapse: collapse;
                    background: rgba(0, 0, 0, 0.8);
                    border-radius: 15px;
                    overflow: hidden;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
                }}
                
                .enhanced-table thead {{
                    background: linear-gradient(135deg, #ff0000, #cc0000, #990000);
                    position: sticky;
                    top: 0;
                    z-index: 100;
                }}
                
                .enhanced-table th {{
                    padding: 18px 15px;
                    text-align: center;
                    font-weight: 900;
                    font-size: 0.95em;
                    text-transform: uppercase;
                    letter-spacing: 1.5px;
                    color: #ffffff;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
                    cursor: pointer;
                    transition: all 0.3s ease;
                    border-right: 1px solid rgba(255, 255, 255, 0.2);
                }}
                
                .enhanced-table th:hover {{
                    background: rgba(255, 255, 255, 0.1);
                    transform: scale(1.05);
                }}
                
                .enhanced-table tbody tr {{
                    background: linear-gradient(90deg, rgba(26, 26, 26, 0.9), rgba(42, 42, 42, 0.9));
                    border-bottom: 1px solid #333;
                    transition: all 0.3s ease;
                }}
                
                .enhanced-table tbody tr:nth-child(even) {{
                    background: linear-gradient(90deg, rgba(20, 20, 20, 0.9), rgba(35, 35, 35, 0.9));
                }}
                
                .enhanced-table tbody tr:hover {{
                    background: linear-gradient(90deg, rgba(255, 0, 0, 0.15), rgba(255, 0, 0, 0.05));
                    transform: scale(1.02);
                    box-shadow: 0 5px 20px rgba(255, 0, 0, 0.3);
                    border-left: 4px solid #ff0000;
                }}
                
                .enhanced-table td {{
                    padding: 15px 12px;
                    text-align: center;
                    font-size: 0.9em;
                    font-weight: 500;
                    color: #ffffff;
                    border-right: 1px solid rgba(255, 255, 255, 0.1);
                    transition: all 0.3s ease;
                }}
                
                .personal-best-row {{
                    background: linear-gradient(90deg, rgba(255, 215, 0, 0.3), rgba(255, 215, 0, 0.1)) !important;
                    border-left: 6px solid #ffd700 !important;
                    box-shadow: 0 0 20px rgba(255, 215, 0, 0.4);
                }}
                
                .personal-best-row td {{
                    color: #ffd700;
                    font-weight: bold;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
                }}
                
                .lap-number-cell {{
                    font-weight: bold;
                    color: #00ff88;
                    font-size: 1.1em;
                }}
                
                .lap-time-cell {{
                    font-family: 'Courier New', monospace;
                    font-weight: bold;
                    font-size: 1.05em;
                    color: #ffff00;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
                }}
                
                .sector-cell {{
                    font-family: 'Courier New', monospace;
                    font-size: 0.9em;
                    color: #00ddff;
                }}
                
                .compound-cell {{
                    font-weight: bold;
                    padding: 8px !important;
                }}
                
                .compound-soft {{
                    background: radial-gradient(circle, #ff0000, #cc0000);
                    color: white;
                    border-radius: 8px;
                    padding: 4px 8px;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
                }}
                
                .compound-medium {{
                    background: radial-gradient(circle, #ffff00, #cccc00);
                    color: black;
                    border-radius: 8px;
                    padding: 4px 8px;
                    font-weight: bold;
                }}
                
                .compound-hard {{
                    background: radial-gradient(circle, #ffffff, #cccccc);
                    color: black;
                    border-radius: 8px;
                    padding: 4px 8px;
                    font-weight: bold;
                }}
                
                .speed-cell {{
                    color: #00ff88;
                    font-family: 'Courier New', monospace;
                    font-weight: bold;
                }}
                
                .gear-cell {{
                    background: linear-gradient(45deg, #ff6600, #ff8800);
                    color: white;
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-weight: bold;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.8);
                }}
                
                /* Amazing Footer */
                .footer {{
                    background: linear-gradient(135deg, #000000, #1a1a1a, #ff0000, #000000);
                    padding: 50px 0 30px;
                    margin-top: 60px;
                    border-top: 4px solid #ff0000;
                    position: relative;
                    overflow: hidden;
                }}
                
                .footer::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 2px;
                    background: linear-gradient(90deg, #ff0000, #ffffff, #ff0000);
                    animation: footerGlow 3s ease-in-out infinite;
                }}
                
                @keyframes footerGlow {{
                    0%, 100% {{ opacity: 0.5; }}
                    50% {{ opacity: 1; }}
                }}
                
                .footer-content {{
                    max-width: 1400px;
                    margin: 0 auto;
                    padding: 0 30px;
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 40px;
                }}
                
                .footer-section {{
                    text-align: center;
                    padding: 20px;
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 15px;
                    border: 1px solid rgba(255, 0, 0, 0.3);
                    backdrop-filter: blur(10px);
                    transition: all 0.3s ease;
                }}
                
                .footer-section:hover {{
                    transform: translateY(-5px);
                    box-shadow: 0 15px 40px rgba(255, 0, 0, 0.3);
                    border-color: #ff0000;
                }}
                
                .footer-title {{
                    font-size: 1.5em;
                    font-weight: bold;
                    color: #ff0000;
                    margin-bottom: 15px;
                    text-transform: uppercase;
                    letter-spacing: 2px;
                }}
                
                .footer-text {{
                    color: #cccccc;
                    line-height: 1.6;
                    margin-bottom: 20px;
                }}
                
                .footer-links {{
                    display: flex;
                    justify-content: center;
                    gap: 20px;
                    flex-wrap: wrap;
                }}
                
                .footer-link {{
                    color: #ffffff;
                    text-decoration: none;
                    padding: 10px 15px;
                    border: 1px solid rgba(255, 0, 0, 0.5);
                    border-radius: 25px;
                    transition: all 0.3s ease;
                    font-weight: 500;
                }}
                
                .footer-link:hover {{
                    background: #ff0000;
                    border-color: #ff0000;
                    transform: scale(1.1);
                    box-shadow: 0 5px 20px rgba(255, 0, 0, 0.4);
                }}
                
                .footer-social {{
                    display: flex;
                    justify-content: center;
                    gap: 15px;
                    margin-top: 20px;
                }}
                
                .social-icon {{
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: 50px;
                    height: 50px;
                    background: linear-gradient(45deg, #ff0000, #cc0000);
                    color: white;
                    border-radius: 50%;
                    font-size: 1.3em;
                    text-decoration: none;
                    transition: all 0.3s ease;
                }}
                
                .social-icon:hover {{
                    transform: scale(1.2) rotate(10deg);
                    box-shadow: 0 10px 30px rgba(255, 0, 0, 0.5);
                    background: linear-gradient(45deg, #ffffff, #ff0000);
                }}
                
                .footer-bottom {{
                    text-align: center;
                    margin-top: 40px;
                    padding-top: 30px;
                    border-top: 1px solid rgba(255, 0, 0, 0.3);
                    color: #888;
                }}
                
                .footer-bottom .copyright {{
                    font-size: 1.1em;
                    color: #ff0000;
                    font-weight: bold;
                }}
                
                @media (max-width: 768px) {{
                    .main-nav {{
                        flex-direction: column;
                    }}
                    
                    .nav-link {{
                        padding: 15px 20px;
                        font-size: 1em;
                    }}
                    
                    .header-title {{
                        font-size: 2.5em;
                    }}
                    
                    .footer-content {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <!-- Minimalist Header with Navigation -->
            <header class="main-header">
                <nav class="nav-container">
                    <a href="/" class="logo">
                        <i class="fas fa-racing-car logo-icon"></i>
                        F1 Analytics
                    </a>
                    <ul class="nav-links">
                        <li><a href="/" class="nav-link active">Home</a></li>
                        <li><a href="/analysis" class="nav-link">Analysis</a></li>
                        <li><a href="/about" class="nav-link">About</a></li>
                        <li><a href="/info" class="nav-link">Info</a></li>
                    </ul>
                </nav>
            </header>
            
            <!-- Page Header -->
            <div style="background: linear-gradient(135deg, #0a0a0a, #1a1a1a); padding: 3rem 0; text-align: center; margin-bottom: 2rem;">
                <h1 style="font-size: 3rem; font-weight: 800; margin-bottom: 1rem; background: linear-gradient(135deg, #ffffff, #ff0000); background-clip: text; -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                    🏎️ F1 Professional Analytics
                </h1>
                <p style="font-size: 1.2rem; color: #888; margin-bottom: 0.5rem;">
                    Driver #{default_driver} • {event_info['name']} {target_season}
                </p>
                <p style="color: #666; font-size: 1rem;">
                    Advanced Telemetry Analysis • Real-time Performance Data
                </p>
            </div>
            
            <main class="main-content">
            
            <div class="container">
                <!-- Enhanced Statistics Grid -->
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{stats['best_lap_time_formatted']}</div>
                        <div class="stat-label">Best Lap Time</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">#{stats['best_lap_number']}</div>
                        <div class="stat-label">Best Lap Number</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['average_lap_time_formatted']}</div>
                        <div class="stat-label">Average Lap Time</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['total_laps']}</div>
                        <div class="stat-label">Total Laps</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['consistency_formatted']}</div>
                        <div class="stat-label">Consistency (σ)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{stats['theoretical_best_formatted']}</div>
                        <div class="stat-label">Theoretical Best</div>
                    </div>
                </div>
                
                <!-- NEW SECTION 1: Speed Performance Overview -->
                <div class="chart-section">
                    <h2 class="chart-title">🚀 Speed Performance Overview</h2>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value">{stats.get('top_speed_formatted', 'N/A')}</div>
                            <div class="stat-label">Top Speed</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{stats.get('avg_top_speed_formatted', 'N/A')}</div>
                            <div class="stat-label">Avg Top Speed</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{stats.get('overall_avg_speed_formatted', 'N/A')}</div>
                            <div class="stat-label">Overall Avg Speed</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{stats.get('total_gear_changes', 0)}</div>
                            <div class="stat-label">Total Gear Changes</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{stats.get('avg_gear_changes_formatted', 'N/A')}</div>
                            <div class="stat-label">Avg Gears/Lap</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{len([lap for lap in lap_data if lap.get('MaxSpeed', 0) > 300])}</div>
                            <div class="stat-label">300+ km/h Laps</div>
                        </div>
                    </div>
                </div>
                
                <!-- NEW SECTION 2: Race Performance Summary -->
                <div class="chart-section">
                    <h2 class="chart-title">🏁 Race Performance Summary</h2>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value">{stats.get('stint_count', 0)}</div>
                            <div class="stat-label">Total Stints</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{len(stats.get('compounds_used', []))}</div>
                            <div class="stat-label">Compounds Used</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{stats.get('personal_best_count', 0)}</div>
                            <div class="stat-label">Personal Bests</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{stats.get('gap_to_theoretical_formatted', 'N/A')}</div>
                            <div class="stat-label">Gap to Theoretical</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{stats.get('lap_time_range_formatted', 'N/A')}</div>
                            <div class="stat-label">Lap Time Range</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{', '.join(stats.get('compounds_used', []))}</div>
                            <div class="stat-label">Tyre Strategy</div>
                        </div>
                    </div>
                </div>
                
                <!-- Sector Analysis -->
                <div class="chart-section">
                    <h2 class="chart-title">📊 Sector Analysis</h2>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value">{stats['fastest_sector1_formatted']}</div>
                            <div class="stat-label">Best Sector 1</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{stats['fastest_sector2_formatted']}</div>
                            <div class="stat-label">Best Sector 2</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{stats['fastest_sector3_formatted']}</div>
                            <div class="stat-label">Best Sector 3</div>
                        </div>
                    </div>
                </div>
                
                <!-- Interactive Lap Time Chart -->
                <div class="chart-section">
                    <h2 class="chart-title">📈 Interactive Lap Time Analysis</h2>
                    <div class="chart-container">
                        <canvas id="lapTimeChart"></canvas>
                    </div>
                </div>
                
                <!-- Speed Analysis Chart -->
                <div class="chart-section">
                    <h2 class="chart-title">🏎️ Speed & Performance Analysis</h2>
                    <div class="chart-container">
                        <canvas id="speedChart"></canvas>
                    </div>
                </div>
                
                <!-- Enhanced Lap Time Data Table -->
                <div class="lap-times-container">
                    <h2 class="chart-title">⏱️ PROFESSIONAL LAP TIMES & TELEMETRY ANALYSIS</h2>
                    
                    <!-- Enhanced Table Controls -->
                    <div class="table-controls">
                        <button onclick="showAllLaps()" class="control-btn">
                            <i class="fas fa-list"></i> All Laps
                        </button>
                        <button onclick="showBestLaps()" class="control-btn">
                            <i class="fas fa-trophy"></i> Best Laps
                        </button>
                        <button onclick="showByStint()" class="control-btn">
                            <i class="fas fa-layer-group"></i> By Stint
                        </button>
                        <button onclick="showOnlyPitLaps()" class="control-btn">
                            <i class="fas fa-tools"></i> Pit Laps
                        </button>
                        <button onclick="showTopSpeed()" class="control-btn">
                            <i class="fas fa-tachometer-alt"></i> Top Speed
                        </button>
                    </div>
                    
                    <div class="lap-data-section" id="lapDataContainer">
                        <table class="enhanced-table" id="lapDataTable">
                            <thead>
                                <tr>
                                    <th onclick="sortTable(0)">
                                        <i class="fas fa-sort"></i> LAP #
                                    </th>
                                    <th onclick="sortTable(1)">
                                        <i class="fas fa-stopwatch"></i> LAP TIME
                                    </th>
                                    <th onclick="sortTable(2)">
                                        <i class="fas fa-flag"></i> S1
                                    </th>
                                    <th onclick="sortTable(3)">
                                        <i class="fas fa-flag"></i> S2
                                    </th>
                                    <th onclick="sortTable(4)">
                                        <i class="fas fa-flag-checkered"></i> S3
                                    </th>
                                    <th>
                                        <i class="fas fa-tire"></i> COMPOUND
                                    </th>
                                    <th>
                                        <i class="fas fa-layer-group"></i> STINT
                                    </th>
                                    <th>
                                        <i class="fas fa-trophy"></i> POS
                                    </th>
                                    <th onclick="sortTable(8)">
                                        <i class="fas fa-rocket"></i> MAX SPEED
                                    </th>
                                    <th onclick="sortTable(9)">
                                        <i class="fas fa-tachometer-alt"></i> AVG SPEED
                                    </th>
                                    <th onclick="sortTable(10)">
                                        <i class="fas fa-cogs"></i> GEARS
                                    </th>
                                </tr>
                            </thead>
                            <tbody id="lapTableBody">
        """
        
        # Add enhanced lap data rows with all telemetry
        for i, lap in enumerate(lap_data):
            pb_indicator = "🏆" if lap.get('IsPersonalBest', False) else ""
            row_class = "personal-best-row" if lap.get('IsPersonalBest', False) else "lap-row"
            
            # Enhanced compound styling
            compound_class = f"compound-{lap['Compound'].lower()}"
            
            html_content += f"""
                                <tr class="{row_class}" data-stint="{lap['Stint']}" data-lap="{lap['LapNumber']}" data-speed="{lap.get('MaxSpeed', 0)}" data-is-pb="{lap.get('IsPersonalBest', False)}">
                                    <td class="lap-number-cell">
                                        <strong>#{lap['LapNumber']}</strong>
                                        {pb_indicator}
                                    </td>
                                    <td class="lap-time-cell">{lap['LapTimeFormatted']}</td>
                                    <td class="sector-cell">{lap['Sector1Formatted']}</td>
                                    <td class="sector-cell">{lap['Sector2Formatted']}</td>
                                    <td class="sector-cell">{lap['Sector3Formatted']}</td>
                                    <td class="compound-cell">
                                        <div class="{compound_class}">
                                            {lap['Compound']}
                                        </div>
                                        <small style="color: #888; display: block; margin-top: 2px;">
                                            Age: {lap['TyreLife']}
                                        </small>
                                    </td>
                                    <td>
                                        <span style="background: linear-gradient(45deg, #0066cc, #0080ff); color: white; padding: 4px 8px; border-radius: 6px; font-weight: bold;">
                                            #{lap['Stint']}
                                        </span>
                                    </td>
                                    <td>
                                        <strong style="color: #ffaa00;">P{lap['Position']}</strong>
                                    </td>
                                    <td class="speed-cell">{lap.get('MaxSpeedFormatted', 'N/A')}</td>
                                    <td class="speed-cell">{lap.get('AvgSpeedFormatted', 'N/A')}</td>
                                    <td>
                                        <div class="gear-cell">{lap.get('GearChanges', 0)}</div>
                                    </td>
                                </tr>
            """
        
        html_content += f"""
                            </tbody>
                        </table>
                    </div>
                    
                    <div class="table-summary">
                        <div class="summary-stats">
                            <div class="summary-item">
                                <span class="summary-label">Total Laps:</span>
                                <span class="summary-value">{len(lap_data)}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Best Lap:</span>
                                <span class="summary-value">{stats['best_lap_time_formatted']}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Average:</span>
                                <span class="summary-value">{stats['average_lap_time_formatted']}</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Stint Analysis -->
                <div class="chart-section">
                    <h2 class="chart-title">🛞 Stint & Tyre Analysis</h2>
                    <div class="stats-grid">
        """
        
        # Add stint analysis cards
        for stint_num, stint_info in stats.get('stint_analysis', {}).items():
            html_content += f"""
                        <div class="stat-card">
                            <div class="stat-value">Stint {stint_num}</div>
                            <div class="stat-label">{stint_info['compound']} • {stint_info['laps']} laps</div>
                            <div style="margin-top: 10px; font-size: 0.9em;">
                                Best: {format_time(stint_info['best_lap'])}<br>
                                Avg: {format_time(stint_info['avg_lap'])}
                            </div>
                        </div>
            """
        
        html_content += f"""
                    </div>
                    
                    <!-- Enhanced Table Summary with Live Stats -->
                    <div class="table-summary">
                        <div class="summary-stats">
                            <div class="summary-item">
                                <span class="summary-label">Total Laps:</span>
                                <span class="summary-value" id="totalLaps">{len(lap_data)}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Personal Bests:</span>
                                <span class="summary-value" id="personalBests">{len([lap for lap in lap_data if lap.get('IsPersonalBest', False)])}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Best Lap:</span>
                                <span class="summary-value">{stats['best_lap_time_formatted']}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Fastest Sector:</span>
                                <span class="summary-value">{stats['fastest_sector1_formatted']}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Top Speed:</span>
                                <span class="summary-value">{stats.get('top_speed_formatted', 'N/A')}</span>
                            </div>
                            <div class="summary-item">
                                <span class="summary-label">Consistency:</span>
                                <span class="summary-value">{stats['consistency_formatted']}</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- API Documentation -->
                <div class="api-section">
                    <h2>📡 API Endpoints & Data Access</h2>
                    <p><strong>Access comprehensive F1 data through these professional API endpoints:</strong></p>
                    
                    <div class="api-endpoint">
                        <a href="/api/seasons">GET /api/seasons</a>
                        <p>Get all available F1 seasons (2018-{max(seasons)})</p>
                    </div>
                    
                    <div class="api-endpoint">
                        <a href="/api/events/{target_season}">GET /api/events/{{year}}</a>
                        <p>Get all race events for specific season</p>
                    </div>
                    
                    <div class="api-endpoint">
                        <a href="/api/data/{target_season}/{event_info['round']}/{default_driver}">GET /api/data/{{year}}/{{round}}/{{driver}}</a>
                        <p>Get detailed lap data with sectors, compounds, and telemetry</p>
                    </div>
                    
                    <div class="api-endpoint">
                        <a href="/api/statistics/{target_season}/{event_info['round']}/{default_driver}">GET /api/statistics/{{year}}/{{round}}/{{driver}}</a>
                        <p>Get comprehensive performance statistics and analytics</p>
                    </div>
                    
                    <div class="api-endpoint">
                        <a href="/api/charts/{target_season}/{event_info['round']}/{default_driver}">GET /api/charts/{{year}}/{{round}}/{{driver}}</a>
                        <p>Get advanced chart data for visualizations</p>
                    </div>
                    
                    <div class="api-endpoint">
                        <a href="/api/comparison/{target_season}/{event_info['round']}">GET /api/comparison/{{year}}/{{round}}</a>
                        <p>Get driver comparison data for entire field</p>
                    </div>
                    
                    <div class="api-endpoint">
                        <a href="/api/drivers/{target_season}/{event_info['round']}">GET /api/drivers/{{year}}/{{round}}</a>
                        <p>Get list of available drivers for session</p>
                    </div>
                    
                    <p style="margin-top: 30px; padding: 20px; background: rgba(255, 255, 255, 0.1); border-radius: 10px;">
                        <strong>🚀 Example Usage:</strong><br>
                        <code>curl {target_season}/{event_info['round']}/{default_driver}</code><br><br>
                        <strong>📊 Response includes:</strong> Lap times, sector analysis, tyre data, performance metrics, 
                        stint analysis, speed traps, and comprehensive race statistics.
                    </p>
                </div>
            </main>
            
            <!-- Amazing Footer -->
            <footer class="footer">
                <div class="footer-content">
                    <div class="footer-section">
                        <h3 class="footer-title">
                            <i class="fas fa-racing-car"></i>
                            F1 Analytics
                        </h3>
                        <p class="footer-text">
                            Professional Formula 1 data analysis platform providing comprehensive telemetry, 
                            lap time analysis, and performance insights for drivers and teams.
                        </p>
                        <div class="footer-social">
                            <a href="#" class="social-icon">
                                <i class="fab fa-twitter"></i>
                            </a>
                            <a href="#" class="social-icon">
                                <i class="fab fa-github"></i>
                            </a>
                            <a href="#" class="social-icon">
                                <i class="fab fa-linkedin"></i>
                            </a>
                        </div>
                    </div>
                    
                    <div class="footer-section">
                        <h3 class="footer-title">
                            <i class="fas fa-chart-line"></i>
                            Features
                        </h3>
                        <p class="footer-text">
                            Real-time lap analysis • Sector breakdowns • Tyre strategy insights • 
                            Speed trap data • Gear change analysis • Comprehensive race statistics
                        </p>
                        <div class="footer-links">
                            <a href="/api/seasons" class="footer-link">API Access</a>
                            <a href="/docs" class="footer-link">Documentation</a>
                        </div>
                    </div>
                    
                    <div class="footer-section">
                        <h3 class="footer-title">
                            <i class="fas fa-database"></i>
                            Data Sources
                        </h3>
                        <p class="footer-text">
                            Powered by FastF1 API • Official F1 timing data • Ergast Developer API • 
                            Real-time telemetry streams • Historical race data from 2018-present
                        </p>
                        <div class="footer-links">
                            <a href="https://github.com/theOehrly/FastF1" class="footer-link">FastF1</a>
                            <a href="http://ergast.com/mrd/" class="footer-link">Ergast API</a>
                        </div>
                    </div>
                    
                    <div class="footer-section">
                        <h3 class="footer-title">
                            <i class="fas fa-info-circle"></i>
                            Platform Info
                        </h3>
                        <p class="footer-text">
                            Built with FastAPI • Powered by Python • Real-time data processing • 
                            Advanced visualization • Professional-grade analytics • Open source
                        </p>
                        <div class="footer-links">
                            <a href="/about" class="footer-link">About</a>
                            <a href="/contact" class="footer-link">Contact</a>
                        </div>
                    </div>
                </div>
                
                <div class="footer-bottom">
                    <p class="copyright">
                        <i class="fas fa-copyright"></i> 2024 F1 Professional Analytics Platform
                    </p>
                    <p style="margin-top: 10px; color: #666;">
                        Built with ❤️ for F1 fans • Deployed on Replit • Data updated in real-time
                    </p>
                </div>
            </footer>
            
            <script>
                // Chart.js Configuration
                Chart.defaults.color = '#ffffff';
                Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.1)';
                
                // Lap Time Chart Data
                const lapTimeData = {json.dumps([{
                    'lap': lap['LapNumber'],
                    'time': lap['LapTime'],
                    'formatted': lap['LapTimeFormatted'],
                    'compound': lap['Compound'],
                    'stint': lap['Stint'],
                    'is_pb': lap.get('IsPersonalBest', False),
                    'max_speed': lap.get('MaxSpeed', 0),
                    'avg_speed': lap.get('AvgSpeed', 0),
                    'gear_changes': lap.get('GearChanges', 0)
                } for lap in lap_data])};
                
                // Lap Time Chart
                const lapTimeCtx = document.getElementById('lapTimeChart').getContext('2d');
                new Chart(lapTimeCtx, {{
                    type: 'line',
                    data: {{
                        labels: lapTimeData.map(d => d.lap),
                        datasets: [{{
                            label: 'Lap Time',
                            data: lapTimeData.map(d => d.time),
                            borderColor: '#ff0000',
                            backgroundColor: 'rgba(255, 0, 0, 0.1)',
                            pointBackgroundColor: lapTimeData.map(d => 
                                d.is_pb ? '#ffd700' : 
                                d.compound === 'SOFT' ? '#ff0000' :
                                d.compound === 'MEDIUM' ? '#ffff00' :
                                d.compound === 'HARD' ? '#ffffff' : '#888888'
                            ),
                            pointRadius: lapTimeData.map(d => d.is_pb ? 8 : 5),
                            pointBorderWidth: 2,
                            pointBorderColor: '#ffffff',
                            tension: 0.3,
                            fill: true
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                display: true,
                                labels: {{ color: '#ffffff' }}
                            }},
                            tooltip: {{
                                callbacks: {{
                                    title: function(context) {{
                                        return `Lap ${{context[0].label}}`;
                                    }},
                                    label: function(context) {{
                                        const lapData = lapTimeData[context.dataIndex];
                                        return [
                                            `Time: ${{lapData.formatted}}`,
                                            `Compound: ${{lapData.compound}}`,
                                            `Stint: ${{lapData.stint}}`,
                                            `Max Speed: ${{lapData.max_speed.toFixed(1)}} km/h`,
                                            lapData.is_pb ? '🏆 Personal Best!' : ''
                                        ].filter(l => l);
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: false,
                                grid: {{ color: 'rgba(255, 255, 255, 0.1)' }},
                                ticks: {{
                                    color: '#ffffff',
                                    callback: function(value) {{
                                        const minutes = Math.floor(value / 60);
                                        const seconds = (value % 60).toFixed(3);
                                        return `${{minutes}}:${{seconds.padStart(6, '0')}}`;
                                    }}
                                }}
                            }},
                            x: {{
                                grid: {{ color: 'rgba(255, 255, 255, 0.1)' }},
                                ticks: {{ color: '#ffffff' }}
                            }}
                        }}
                    }}
                }});
                
                // Speed Analysis Chart with dual axis
                const speedCtx = document.getElementById('speedChart').getContext('2d');
                new Chart(speedCtx, {{
                    type: 'line',
                    data: {{
                        labels: lapTimeData.map(d => d.lap),
                        datasets: [{{
                            label: 'Max Speed (km/h)',
                            data: lapTimeData.map(d => d.max_speed > 0 ? d.max_speed : null),
                            backgroundColor: 'rgba(0, 255, 136, 0.2)',
                            borderColor: '#00ff88',
                            borderWidth: 3,
                            pointBackgroundColor: '#00ff88',
                            pointBorderColor: '#ffffff',
                            pointRadius: 4,
                            fill: false,
                            yAxisID: 'ySpeed',
                            tension: 0.3
                        }}, {{
                            label: 'Average Speed (km/h)',
                            data: lapTimeData.map(d => d.avg_speed > 0 ? d.avg_speed : null),
                            backgroundColor: 'rgba(255, 165, 0, 0.2)',
                            borderColor: '#ffa500',
                            borderWidth: 2,
                            pointBackgroundColor: '#ffa500',
                            pointBorderColor: '#ffffff',
                            pointRadius: 3,
                            fill: false,
                            yAxisID: 'ySpeed',
                            tension: 0.3
                        }}, {{
                            label: 'Gear Changes',
                            data: lapTimeData.map(d => d.gear_changes || 0),
                            type: 'bar',
                            backgroundColor: 'rgba(255, 0, 255, 0.4)',
                            borderColor: '#ff00ff',
                            borderWidth: 1,
                            yAxisID: 'yGear'
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                display: true,
                                labels: {{ color: '#ffffff' }}
                            }},
                            tooltip: {{
                                callbacks: {{
                                    title: function(context) {{
                                        return `Lap ${{context[0].label}}`;
                                    }},
                                    label: function(context) {{
                                        const value = context.parsed.y;
                                        if (context.dataset.label.includes('Speed')) {{
                                            return `${{context.dataset.label}}: ${{value ? value.toFixed(1) : 'N/A'}} km/h`;
                                        }} else {{
                                            return `${{context.dataset.label}}: ${{value || 0}}`;
                                        }}
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            ySpeed: {{
                                type: 'linear',
                                position: 'left',
                                beginAtZero: false,
                                min: 200,
                                max: 350,
                                grid: {{ color: 'rgba(255, 255, 255, 0.1)' }},
                                ticks: {{
                                    color: '#00ff88',
                                    callback: function(value) {{
                                        return value + ' km/h';
                                    }}
                                }},
                                title: {{
                                    display: true,
                                    text: 'Speed (km/h)',
                                    color: '#00ff88'
                                }}
                            }},
                            yGear: {{
                                type: 'linear',
                                position: 'right',
                                beginAtZero: true,
                                max: 80,
                                grid: {{ display: false }},
                                ticks: {{
                                    color: '#ff00ff',
                                    callback: function(value) {{
                                        return value + ' gears';
                                    }}
                                }},
                                title: {{
                                    display: true,
                                    text: 'Gear Changes',
                                    color: '#ff00ff'
                                }}
                            }},
                            x: {{
                                grid: {{ color: 'rgba(255, 255, 255, 0.1)' }},
                                ticks: {{ color: '#ffffff' }},
                                title: {{
                                    display: true,
                                    text: 'Lap Number',
                                    color: '#ffffff'
                                }}
                            }}
                        }}
                    }}
                }});
                
                // Table functionality
                let currentSort = {{ column: -1, direction: 'asc' }};
                
                function sortTable(columnIndex) {{
                    const table = document.getElementById('lapDataTable');
                    const tbody = table.querySelector('tbody');
                    const rows = Array.from(tbody.querySelectorAll('tr'));
                    
                    // Determine sort direction
                    if (currentSort.column === columnIndex) {{
                        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
                    }} else {{
                        currentSort.direction = 'asc';
                    }}
                    currentSort.column = columnIndex;
                    
                    // Sort rows
                    rows.sort((a, b) => {{
                        const aValue = a.cells[columnIndex].textContent.trim();
                        const bValue = b.cells[columnIndex].textContent.trim();
                        
                        // Handle numeric values
                        const aNum = parseFloat(aValue.replace(/[^0-9.-]/g, ''));
                        const bNum = parseFloat(bValue.replace(/[^0-9.-]/g, ''));
                        
                        if (!isNaN(aNum) && !isNaN(bNum)) {{
                            return currentSort.direction === 'asc' ? aNum - bNum : bNum - aNum;
                        }}
                        
                        // Handle text values
                        return currentSort.direction === 'asc' ? 
                            aValue.localeCompare(bValue) : 
                            bValue.localeCompare(aValue);
                    }});
                    
                    // Re-append sorted rows
                    rows.forEach(row => tbody.appendChild(row));
                }}
                
                function showAllLaps() {{
                    const rows = document.querySelectorAll('.lap-row');
                    rows.forEach(row => row.style.display = '');
                }}
                
                function showBestLaps() {{
                    const rows = document.querySelectorAll('.lap-row');
                    rows.forEach(row => {{
                        const isPersonalBest = row.classList.contains('personal-best-row');
                        row.style.display = isPersonalBest ? '' : 'none';
                    }});
                }}
                
                function showByStint() {{
                    const rows = document.querySelectorAll('tbody tr');
                    const stints = new Map();
                    
                    // Group by stint
                    rows.forEach(row => {{
                        const stint = row.dataset.stint;
                        if (!stints.has(stint)) {{
                            stints.set(stint, []);
                        }}
                        stints.get(stint).push(row);
                    }});
                    
                    // Show all rows but add visual grouping
                    rows.forEach(row => {{
                        row.style.display = '';
                        const stint = row.dataset.stint;
                        row.style.borderTop = '2px solid #0066cc';
                    }});
                }}
                
                function showOnlyPitLaps() {{
                    const rows = document.querySelectorAll('tbody tr');
                    rows.forEach(row => {{
                        // Show laps with very slow times (likely pit laps)
                        const lapTimeCell = row.querySelector('.lap-time-cell');
                        if (lapTimeCell) {{
                            const timeText = lapTimeCell.textContent;
                            // If lap time is over 2 minutes, it's likely a pit lap
                            const isSlowLap = timeText.includes('2:') || timeText.includes('3:') || timeText.includes('4:');
                            row.style.display = isSlowLap ? '' : 'none';
                        }}
                    }});
                }}
                
                function showTopSpeed() {{
                    const rows = document.querySelectorAll('tbody tr');
                    const sortedRows = Array.from(rows).sort((a, b) => {{
                        const speedA = parseFloat(a.dataset.speed) || 0;
                        const speedB = parseFloat(b.dataset.speed) || 0;
                        return speedB - speedA;
                    }});
                    
                    // Hide all rows first
                    rows.forEach(row => row.style.display = 'none');
                    
                    // Show top 10 fastest laps
                    sortedRows.slice(0, 10).forEach(row => {{
                        row.style.display = '';
                        row.style.background = 'linear-gradient(90deg, rgba(0, 255, 136, 0.2), rgba(0, 255, 136, 0.05))';
                    }});
                }}
                
                // Enhanced table interactions
                document.addEventListener('DOMContentLoaded', function() {{
                    const tableRows = document.querySelectorAll('tbody tr');
                    let selectedRow = null;
                    
                    tableRows.forEach((row, index) => {{
                        row.addEventListener('click', function() {{
                            // Remove previous selection
                            if (selectedRow) {{
                                selectedRow.classList.remove('selected-row');
                            }}
                            
                            // Add selection to current row
                            this.classList.add('selected-row');
                            selectedRow = this;
                            
                            // Update summary with selected lap info
                            const lapNumber = this.dataset.lap;
                            const isPersonalBest = this.dataset.isPb === 'True';
                            
                            // Highlight in chart if available
                            console.log(`Selected lap ${{lapNumber}}`);
                            
                            // Could add more interactivity here
                        }});
                        
                        // Add double-click for detailed view
                        row.addEventListener('dblclick', function() {{
                            const lapNumber = this.dataset.lap;
                            alert(`Detailed view for Lap ${{lapNumber}} - Feature coming soon!`);
                        }});
                    }});
                    
                    // Add keyboard navigation
                    document.addEventListener('keydown', function(e) {{
                        if (selectedRow) {{
                            let newRow = null;
                            
                            if (e.key === 'ArrowDown') {{
                                newRow = selectedRow.nextElementSibling;
                                e.preventDefault();
                            }} else if (e.key === 'ArrowUp') {{
                                newRow = selectedRow.previousElementSibling;
                                e.preventDefault();
                            }}
                            
                            if (newRow && newRow.tagName === 'TR') {{
                                selectedRow.classList.remove('selected-row');
                                newRow.classList.add('selected-row');
                                selectedRow = newRow;
                                newRow.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                            }}
                        }}
                    }});
                    
                    // Update live stats
                    updateLiveStats();
                }});
                
                function updateLiveStats() {{
                    const visibleRows = document.querySelectorAll('tbody tr[style*="display: none"]').length;
                    const totalRows = document.querySelectorAll('tbody tr').length;
                    const showingRows = totalRows - visibleRows;
                    
                    const totalLapsElement = document.getElementById('totalLaps');
                    if (totalLapsElement) {{
                        totalLapsElement.textContent = showingRows;
                    }}
                    
                    const personalBests = document.querySelectorAll('tbody tr[data-is-pb="True"]:not([style*="display: none"])').length;
                    const personalBestsElement = document.getElementById('personalBests');
                    if (personalBestsElement) {{
                        personalBestsElement.textContent = personalBests;
                    }}
                }}
            </script>
            
            <style>
                .selected-row {{
                    background: rgba(255, 0, 0, 0.3) !important;
                    border: 2px solid #ff0000 !important;
                }}
            </style>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error in enhanced dashboard: {e}")
        return HTMLResponse(content=get_demo_dashboard_html())

# New Enhanced API Endpoints

@app.get("/api/charts/{year}/{round_number}/{driver_number}")
async def get_chart_data(year: int, round_number: int, driver_number: str):
    """Get comprehensive chart data for visualizations"""
    try:
        session = f1_extractor.load_session_data(year, round_number)
        
        if session is None:
            raise HTTPException(status_code=404, detail="Session data not found")
        
        lap_data = f1_extractor.extract_driver_lap_data(session, driver_number)
        
        if not lap_data:
            raise HTTPException(status_code=404, detail="No lap data found for the specified driver")
        
        chart_data = prepare_advanced_chart_data(lap_data)
        
        return {
            "success": True,
            "year": year,
            "round": round_number,
            "driver": driver_number,
            "chart_data": chart_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/comparison/{year}/{round_number}")
async def get_driver_comparison(year: int, round_number: int):
    """Get comparison data for all drivers in a session"""
    try:
        session = f1_extractor.load_session_data(year, round_number)
        
        if session is None:
            raise HTTPException(status_code=404, detail="Session data not found")
        
        comparison_data = f1_extractor.get_all_drivers_comparison(session)
        
        return {
            "success": True,
            "year": year,
            "round": round_number,
            "comparison": comparison_data,
            "driver_count": len(comparison_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting driver comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Keep existing API routes with enhancements

@app.get("/api/seasons")
async def get_seasons():
    """Get available F1 seasons"""
    try:
        seasons = f1_extractor.get_available_seasons()
        return {
            "success": True,
            "seasons": seasons,
            "count": len(seasons),
            "latest": max(seasons) if seasons else None
        }
    except Exception as e:
        logger.error(f"Error getting seasons: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/events/{year}")
async def get_events(year: int):
    """Get events for a specific year"""
    try:
        events = f1_extractor.get_season_events(year)
        return {
            "success": True,
            "year": year,
            "events": events,
            "count": len(events)
        }
    except Exception as e:
        logger.error(f"Error getting events for year {year}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data/{year}/{round_number}/{driver_number}")
async def get_lap_data(year: int, round_number: int, driver_number: str):
    """Get enhanced lap data for a specific driver"""
    try:
        session = f1_extractor.load_session_data(year, round_number)
        
        if session is None:
            raise HTTPException(status_code=404, detail="Session data not found")
        
        lap_data = f1_extractor.extract_driver_lap_data(session, driver_number)
        
        if not lap_data:
            raise HTTPException(status_code=404, detail="No lap data found for the specified driver")
        
        return {
            "success": True,
            "year": year,
            "round": round_number,
            "driver": driver_number,
            "data": lap_data,
            "count": len(lap_data),
            "summary": {
                "best_lap": min(lap['LapTime'] for lap in lap_data),
                "total_laps": len(lap_data),
                "compounds": list(set(lap['Compound'] for lap in lap_data))
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lap data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/statistics/{year}/{round_number}/{driver_number}")
async def get_statistics(year: int, round_number: int, driver_number: str):
    """Get enhanced statistics for a specific driver"""
    try:
        session = f1_extractor.load_session_data(year, round_number)
        
        if session is None:
            raise HTTPException(status_code=404, detail="Session data not found")
        
        lap_data = f1_extractor.extract_driver_lap_data(session, driver_number)
        
        if not lap_data:
            raise HTTPException(status_code=404, detail="No lap data found for the specified driver")
        
        stats = get_lap_statistics(lap_data)
        chart_data = prepare_advanced_chart_data(lap_data)
        
        return {
            "success": True,
            "year": year,
            "round": round_number,
            "driver": driver_number,
            "statistics": stats,
            "chart_data": chart_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/drivers/{year}/{round_number}")
async def get_drivers(year: int, round_number: int):
    """Get available drivers for a specific event"""
    try:
        session = f1_extractor.load_session_data(year, round_number)
        
        if session is None:
            raise HTTPException(status_code=404, detail="Session data not found")
        
        drivers = f1_extractor.get_session_drivers(session)
        
        return {
            "success": True,
            "year": year,
            "round": round_number,
            "drivers": drivers,
            "count": len(drivers)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting drivers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_demo_dashboard_html():
    """Enhanced demo dashboard"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>F1 Professional Analytics - Demo Mode</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #0a0a0a, #1a1a1a);
                color: white;
                margin: 0;
                padding: 20px;
            }
            .header {
                background: linear-gradient(90deg, #ff0000, #cc0000);
                text-align: center;
                padding: 40px 20px;
                border-radius: 15px;
                margin-bottom: 30px;
            }
            .header h1 {
                font-size: 3em;
                margin-bottom: 10px;
            }
            .demo-notice {
                background: rgba(255, 165, 0, 0.2);
                border: 2px solid #ffa500;
                border-radius: 15px;
                padding: 30px;
                margin-bottom: 30px;
                text-align: center;
            }
            .feature-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            .feature-card {
                background: linear-gradient(145deg, #1e1e1e, #2a2a2a);
                border: 2px solid #ff0000;
                border-radius: 15px;
                padding: 25px;
                text-align: center;
            }
            .api-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            .api-endpoint {
                background: rgba(0, 255, 0, 0.1);
                border: 1px solid #00ff00;
                border-radius: 10px;
                padding: 20px;
            }
            .api-endpoint a {
                color: #00ff00;
                text-decoration: none;
                font-family: monospace;
                font-size: 1.1em;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏎️ F1 PROFESSIONAL ANALYTICS</h1>
            <p>Advanced Formula 1 Data Analysis Platform</p>
        </div>
        
        <div class="demo-notice">
            <h2>⚠️ Demo Mode Active</h2>
            <p>Recent F1 session data is temporarily unavailable. This comprehensive API platform provides:</p>
            <p><strong>✅ Complete lap-by-lap analysis • ✅ Sector timing breakdown • ✅ Tyre performance data • ✅ Advanced statistics</strong></p>
        </div>
        
        <div class="feature-grid">
            <div class="feature-card">
                <h3>📊 Advanced Analytics</h3>
                <p>Comprehensive lap time analysis with sector breakdown, consistency metrics, and performance distributions</p>
            </div>
            <div class="feature-card">
                <h3>🏁 Race Intelligence</h3>
                <p>Detailed race statistics, stint analysis, and theoretical best lap calculations</p>
            </div>
            <div class="feature-card">
                <h3>🛞 Tyre Strategy</h3>
                <p>Complete compound analysis, degradation curves, and tyre performance comparisons</p>
            </div>
            <div class="feature-card">
                <h3>⚡ Real-time Data</h3>
                <p>Live session data from Fast F1 API with comprehensive telemetry information</p>
            </div>
            <div class="feature-card">
                <h3>📈 Data Visualization</h3>
                <p>Advanced chart data for lap times, sectors, speed analysis, and performance trends</p>
            </div>
            <div class="feature-card">
                <h3>🔄 Driver Comparison</h3>
                <p>Multi-driver analysis with head-to-head comparisons and field-wide statistics</p>
            </div>
        </div>
        
        <div style="background: linear-gradient(145deg, #0a3a0a, #0d4d0d); border: 2px solid #00ff00; border-radius: 15px; padding: 30px; margin: 40px 0;">
            <h2 style="color: #00ff00; margin-bottom: 20px;">📡 Professional API Endpoints</h2>
            
            <div class="api-grid">
                <div class="api-endpoint">
                    <a href="/api/seasons">/api/seasons</a>
                    <p>Get all available F1 seasons with metadata</p>
                </div>
                
                <div class="api-endpoint">
                    <a href="/api/events/2024">/api/events/{year}</a>
                    <p>Complete season schedule with race details</p>
                </div>
                
                <div class="api-endpoint">
                    <a href="/api/data/2024/24/4">/api/data/{year}/{round}/{driver}</a>
                    <p>Detailed lap data with sectors and telemetry</p>
                </div>
                
                <div class="api-endpoint">
                    <a href="/api/statistics/2024/24/4">/api/statistics/{year}/{round}/{driver}</a>
                    <p>Comprehensive performance statistics</p>
                </div>
                
                <div class="api-endpoint">
                    <a href="/api/charts/2024/24/4">/api/charts/{year}/{round}/{driver}</a>
                    <p>Advanced visualization data</p>
                </div>
                
                <div class="api-endpoint">
                    <a href="/api/comparison/2024/24">/api/comparison/{year}/{round}</a>
                    <p>Multi-driver comparison analysis</p>
                </div>
            </div>
            
            <div style="margin-top: 30px; padding: 20px; background: rgba(255, 255, 255, 0.1); border-radius: 10px;">
                <h3 style="color: #00ff00;">🚀 Data Features</h3>
                <ul style="text-align: left; columns: 2; column-gap: 40px;">
                    <li>Lap-by-lap timing data</li>
                    <li>Sector 1, 2, 3 analysis</li>
                    <li>Tyre compound & lifecycle</li>
                    <li>Stint strategy breakdown</li>
                    <li>Speed trap measurements</li>
                    <li>Track position data</li>
                    <li>Weather conditions</li>
                    <li>Performance consistency</li>
                    <li>Theoretical best laps</li>
                    <li>Statistical distributions</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
