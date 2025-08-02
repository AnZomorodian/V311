from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging
from f1_data_extractor import F1DataExtractor

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize F1 data extractor
f1_extractor = F1DataExtractor()

@router.get("/seasons")
async def get_seasons() -> Dict[str, List[int]]:
    """Get available F1 seasons"""
    try:
        seasons = f1_extractor.get_available_seasons()
        return {"seasons": seasons}
    except Exception as e:
        logger.error(f"Error getting seasons: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve seasons")

@router.get("/seasons/{year}/events")
async def get_season_events(year: int) -> Dict[str, List[Dict]]:
    """Get all events for a specific season"""
    try:
        if year < 2018 or year > 2030:
            raise HTTPException(status_code=400, detail="Invalid year. Must be between 2018 and 2030")
        
        events = f1_extractor.get_season_events(year)
        return {"events": events}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting events for season {year}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve events for season {year}")

@router.get("/sessions/{year}/{round_number}/drivers")
async def get_session_drivers(
    year: int, 
    round_number: int, 
    session_type: str = Query(default="R", description="Session type (FP1, FP2, FP3, Q, R)")
) -> Dict[str, List[str]]:
    """Get drivers for a specific session"""
    try:
        # Validate parameters
        if year < 2018 or year > 2030:
            raise HTTPException(status_code=400, detail="Invalid year")
        if round_number < 1 or round_number > 30:
            raise HTTPException(status_code=400, detail="Invalid round number")
        if session_type not in ['FP1', 'FP2', 'FP3', 'Q', 'R']:
            raise HTTPException(status_code=400, detail="Invalid session type")
        
        # Load session data
        session = f1_extractor.load_session_data(year, round_number, session_type)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get drivers
        drivers = f1_extractor.get_session_drivers(session)
        return {"drivers": drivers}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting drivers for session {year}/{round_number}/{session_type}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve drivers")

@router.get("/driver-info/{year}/{round_number}/{driver_number}")
async def get_driver_info(
    year: int,
    round_number: int,
    driver_number: str,
    session_type: str = Query(default="R", description="Session type")
) -> Dict[str, Any]:
    """Get detailed driver information"""
    try:
        # Load session data
        session = f1_extractor.load_session_data(year, round_number, session_type)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get driver info
        driver_info = f1_extractor.get_driver_info(session, driver_number)
        return {"driver_info": driver_info}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting driver info: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve driver information")

@router.get("/lap-data/{year}/{round_number}/{driver_number}")
async def get_driver_lap_data(
    year: int,
    round_number: int,
    driver_number: str,
    session_type: str = Query(default="R", description="Session type")
) -> Dict[str, Any]:
    """Get comprehensive lap data for a specific driver"""
    try:
        # Validate parameters
        if year < 2018 or year > 2030:
            raise HTTPException(status_code=400, detail="Invalid year")
        if round_number < 1 or round_number > 30:
            raise HTTPException(status_code=400, detail="Invalid round number")
        
        # Load session data
        session = f1_extractor.load_session_data(year, round_number, session_type)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found or no data available")
        
        # Get driver lap data
        lap_data = f1_extractor.extract_driver_lap_data(session, driver_number)
        
        if not lap_data:
            return {
                "lap_data": [],
                "statistics": {},
                "message": f"No lap data found for driver {driver_number}"
            }
        
        # Calculate statistics
        statistics = f1_extractor.calculate_lap_statistics(lap_data)
        
        # Get driver info
        driver_info = f1_extractor.get_driver_info(session, driver_number)
        
        return {
            "lap_data": lap_data,
            "statistics": statistics,
            "driver_info": driver_info,
            "session_info": {
                "year": year,
                "round": round_number,
                "session_type": session_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lap data for driver {driver_number}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve lap data")

@router.get("/lap-comparison/{year}/{round_number}")
async def get_lap_comparison(
    year: int,
    round_number: int,
    drivers: str = Query(..., description="Comma-separated driver numbers"),
    session_type: str = Query(default="R", description="Session type")
) -> Dict[str, Any]:
    """Compare lap data between multiple drivers"""
    try:
        # Parse driver numbers
        driver_list = [d.strip() for d in drivers.split(',') if d.strip()]
        if len(driver_list) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 drivers allowed for comparison")
        
        # Load session data
        session = f1_extractor.load_session_data(year, round_number, session_type)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        comparison_data = {}
        
        for driver_number in driver_list:
            try:
                lap_data = f1_extractor.extract_driver_lap_data(session, driver_number)
                statistics = f1_extractor.calculate_lap_statistics(lap_data)
                driver_info = f1_extractor.get_driver_info(session, driver_number)
                
                comparison_data[driver_number] = {
                    "lap_data": lap_data,
                    "statistics": statistics,
                    "driver_info": driver_info
                }
            except Exception as driver_error:
                logger.warning(f"Error processing driver {driver_number}: {driver_error}")
                comparison_data[driver_number] = {
                    "error": f"Failed to load data for driver {driver_number}"
                }
        
        return {
            "comparison_data": comparison_data,
            "session_info": {
                "year": year,
                "round": round_number,
                "session_type": session_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in lap comparison: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare lap data")

@router.get("/session-summary/{year}/{round_number}")
async def get_session_summary(
    year: int,
    round_number: int,
    session_type: str = Query(default="R", description="Session type")
) -> Dict[str, Any]:
    """Get comprehensive session summary"""
    try:
        # Load session data
        session = f1_extractor.load_session_data(year, round_number, session_type)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get all drivers
        drivers = f1_extractor.get_session_drivers(session)
        
        session_summary = {
            "drivers": [],
            "fastest_lap": None,
            "total_laps": 0
        }
        
        fastest_lap_time = float('inf')
        fastest_lap_driver = None
        
        for driver_number in drivers[:10]:  # Limit to first 10 drivers for performance
            try:
                lap_data = f1_extractor.extract_driver_lap_data(session, driver_number)
                statistics = f1_extractor.calculate_lap_statistics(lap_data)
                driver_info = f1_extractor.get_driver_info(session, driver_number)
                
                driver_summary = {
                    "driver_number": driver_number,
                    "driver_info": driver_info,
                    "lap_count": len(lap_data),
                    "best_lap_time": statistics.get('best_lap_time', 0),
                    "best_lap_time_formatted": statistics.get('best_lap_time_formatted', 'N/A')
                }
                
                session_summary["drivers"].append(driver_summary)
                session_summary["total_laps"] += len(lap_data)
                
                # Track fastest lap
                if statistics.get('best_lap_time', float('inf')) < fastest_lap_time:
                    fastest_lap_time = statistics.get('best_lap_time')
                    fastest_lap_driver = {
                        "driver_number": driver_number,
                        "driver_info": driver_info,
                        "lap_time": fastest_lap_time,
                        "lap_time_formatted": statistics.get('best_lap_time_formatted', 'N/A')
                    }
                    
            except Exception as driver_error:
                logger.warning(f"Error processing driver {driver_number} in summary: {driver_error}")
                continue
        
        session_summary["fastest_lap"] = fastest_lap_driver
        
        return {
            "session_summary": session_summary,
            "session_info": {
                "year": year,
                "round": round_number,
                "session_type": session_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session summary")

@router.get("/telemetry/{year}/{round_number}/{driver_number}")
async def get_driver_telemetry(
    year: int,
    round_number: int,
    driver_number: str,
    session_type: str = Query(default="R", description="Session type"),
    lap_number: Optional[int] = Query(default=None, description="Specific lap number")
) -> Dict[str, Any]:
    """Get detailed telemetry data for a specific driver"""
    try:
        # Validate parameters
        if year < 2018 or year > 2030:
            raise HTTPException(status_code=400, detail="Invalid year")
        if round_number < 1 or round_number > 30:
            raise HTTPException(status_code=400, detail="Invalid round number")
        if session_type not in ['FP1', 'FP2', 'FP3', 'Q', 'R']:
            raise HTTPException(status_code=400, detail="Invalid session type")
        
        # Load session and get telemetry
        session = f1_extractor.load_session_data(year, round_number, session_type)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        telemetry = f1_extractor.get_driver_telemetry(session, driver_number, lap_number)
        if not telemetry:
            raise HTTPException(status_code=404, detail="Telemetry data not found")
        
        return {"telemetry": telemetry}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting telemetry for {year}/{round_number}/{driver_number}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve telemetry data")

@router.get("/weather/{year}/{round_number}")
async def get_session_weather(
    year: int,
    round_number: int,
    session_type: str = Query(default="R", description="Session type")
) -> Dict[str, Any]:
    """Get weather data for a session"""
    try:
        # Validate parameters
        if year < 2018 or year > 2030:
            raise HTTPException(status_code=400, detail="Invalid year")
        if round_number < 1 or round_number > 30:
            raise HTTPException(status_code=400, detail="Invalid round number")
        if session_type not in ['FP1', 'FP2', 'FP3', 'Q', 'R']:
            raise HTTPException(status_code=400, detail="Invalid session type")
        
        # Load session and get weather
        session = f1_extractor.load_session_data(year, round_number, session_type)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        weather_data = f1_extractor.get_session_weather(session)
        return {"weather": weather_data}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting weather for {year}/{round_number}/{session_type}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve weather data")

@router.get("/ai-predictions/{year}/{round_number}")
async def get_ai_predictions(
    year: int,
    round_number: int,
    session_type: str = Query(default="R", description="Session type")
) -> Dict[str, Any]:
    """Get AI-powered performance predictions"""
    try:
        # Validate parameters
        if year < 2018 or year > 2030:
            raise HTTPException(status_code=400, detail="Invalid year")
        if round_number < 1 or round_number > 30:
            raise HTTPException(status_code=400, detail="Invalid round number")
        
        # Load session data
        session = f1_extractor.load_session_data(year, round_number, session_type)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Generate AI predictions based on session data
        predictions = f1_extractor.generate_ai_predictions(session)
        return {"predictions": predictions}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating AI predictions for {year}/{round_number}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate predictions")

@router.get("/pit-strategy/{year}/{round_number}")
async def get_pit_strategy_analysis(
    year: int,
    round_number: int,
    session_type: str = Query(default="R", description="Session type")
) -> Dict[str, Any]:
    """Get pit strategy analysis and recommendations"""
    try:
        # Validate parameters
        if year < 2018 or year > 2030:
            raise HTTPException(status_code=400, detail="Invalid year")
        if round_number < 1 or round_number > 30:
            raise HTTPException(status_code=400, detail="Invalid round number")
        
        # Load session data
        session = f1_extractor.load_session_data(year, round_number, session_type)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Generate pit strategy analysis
        pit_analysis = f1_extractor.analyze_pit_strategies(session)
        return {"pit_strategy": pit_analysis}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing pit strategies for {year}/{round_number}: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze pit strategies")
