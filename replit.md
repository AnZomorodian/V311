# F1 Analytics Dashboard

## Overview

The F1 Analytics Dashboard is a professional Formula 1 data analysis platform built with FastAPI and modern web technologies. It provides comprehensive insights into racing performance through real-time telemetry data, lap-by-lap analysis, and advanced visualization tools. The application leverages the FastF1 library to extract official F1 timing data and presents it through an intuitive web interface with interactive charts and analytics.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates for server-side rendering
- **Styling**: Custom CSS with CSS variables for consistent F1-themed design using racing colors (red, black, white)
- **JavaScript Architecture**: Modular approach with separate files for dashboard functionality (`dashboard.js`) and chart management (`charts.js`)
- **Visualization Library**: Chart.js for interactive data visualization and telemetry charts
- **Responsive Design**: Mobile-first approach with flexbox and grid layouts

### Backend Architecture
- **Web Framework**: FastAPI with async/await pattern for high-performance API endpoints
- **API Design**: RESTful API structure with separate router module (`api_endpoints.py`) for clean separation of concerns
- **Data Processing**: Pandas and NumPy for efficient data manipulation and analysis
- **Caching Strategy**: 
  - LRU cache decorators for frequently accessed data
  - File-based caching via FastF1's built-in cache system
  - In-memory session cache for optimal performance
- **Error Handling**: Comprehensive exception handling with structured HTTP responses and logging

### Data Layer
- **Primary Data Source**: FastF1 library for accessing official F1 timing and telemetry data
- **Data Processing Pipeline**: Extract → Transform → Cache → Serve pattern
- **Session Management**: Intelligent caching of F1 session data to minimize API calls
- **Data Validation**: Input validation for years (2018-2030) and session types

### Core Components
- **F1DataExtractor**: Main data processing class handling all F1 API interactions
- **API Router**: Dedicated FastAPI router for clean endpoint organization
- **Static File Serving**: Efficient serving of CSS, JS, and asset files
- **Template System**: Multi-page template structure with shared navigation and styling

## External Dependencies

### Core Libraries
- **FastAPI**: Modern, fast web framework for building APIs with Python 3.7+
- **FastF1**: Official F1 data access library for telemetry and timing data
- **Pandas**: Data manipulation and analysis library
- **NumPy**: Numerical computing library for data processing
- **Uvicorn**: ASGI server for running the FastAPI application

### Frontend Dependencies
- **Chart.js**: Feature-rich charting library delivered via CDN
- **Font Awesome**: Icon library for UI elements (CDN)
- **Jinja2**: Template engine for server-side HTML generation

### Development Tools
- **Python Logging**: Built-in logging system for debugging and monitoring
- **Type Hints**: Full type annotation support for better code maintainability
- **Async Support**: Native async/await support throughout the application

### Data Sources
- **Formula 1 Official Data**: Accessed through FastF1 library providing:
  - Live timing data
  - Historical race data (2018-present)
  - Telemetry information
  - Session details and driver statistics