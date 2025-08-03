# 🏎️ Track.lytix - Professional F1 Data Analysis Platform

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastF1](https://img.shields.io/badge/FastF1-3.6.0-green.svg)](https://github.com/theOehrly/Fast-F1)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39+-red.svg)](https://streamlit.io)
[![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3+-blue.svg)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Track.lytix** is a comprehensive Formula 1 data analysis platform that provides advanced race data visualization and analytics capabilities. Built with modern web technologies and professional-grade design.

## ✨ Features

### 🔧 Core Analytics
- **Real-time Telemetry Analysis** - Speed, throttle, brake, RPM, and gear data visualization
- **Advanced Performance Metrics** - Comprehensive driver and team comparison tools
- **Brake Analysis System** - Efficiency, force analysis, and duration tracking
- **Composite Performance Index** - Multi-factor performance evaluation combining speed, acceleration, and efficiency
- **Tire Strategy Visualization** - Compound performance analysis with degradation tracking
- **Track Dominance Mapping** - Sector-by-sector performance visualization
- **Weather Impact Analysis** - Correlation between weather conditions and performance
- **Race Strategy Analytics** - Pit stop strategy and pace evolution tracking

### 🎨 Modern Interface
- **Dual Interface Options** - Traditional Streamlit and modern Next.js/TypeScript frontend
- **Professional Design** - High-contrast F1-themed styling with glass morphism effects
- **Responsive Layout** - Mobile-first design with dynamic tab system
- **Interactive Visualizations** - Plotly-powered charts with professional styling
- **Real-time Data Updates** - Live session data loading and caching

### 🚀 Technical Stack
- **Backend**: Python 3.11+, FastAPI, FastF1 library
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, Framer Motion
- **Legacy Interface**: Streamlit with custom CSS styling
- **Data Visualization**: Plotly, Recharts
- **Data Processing**: Pandas, NumPy, SciPy
- **API**: RESTful endpoints with automatic OpenAPI documentation

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.11 or higher
- Node.js 18+ (for Next.js frontend)
- Git

### Quick Start with Replit
1. **Fork this repository** on Replit
2. **Install dependencies** automatically via Replit's package manager
3. **Run the application** using the configured workflows

### Local Development Setup

#### 1. Clone the Repository
```bash
git clone https://github.com/your-username/track-lytix.git
cd track-lytix
```

#### 2. Set Up Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

#### 3. Install Node.js Dependencies (for Next.js frontend)
```bash
cd frontend-next
npm install
cd ..
```

#### 4. Configure Environment
Create a `.streamlit/config.toml` file:
```toml
[server]
headless = true
address = "0.0.0.0"
port = 5000

[theme]
base = "dark"
```

## 🚀 Running the Application

### Option 1: Command Line Launch (Easiest)
```bash
# Simply run the main script - handles everything automatically
python main.py
```
This will:
- Check all dependencies
- Create Streamlit configuration
- Launch Track.lytix on `http://localhost:5000`

### Option 2: Direct Streamlit Interface
```bash
# Run the traditional Streamlit interface
streamlit run app.py --server.port 5000 --server.address 0.0.0.0
```
Access at: `http://localhost:5000`

### Option 2: Modern Web Frontend + API Backend
```bash
# Terminal 1: Start the FastAPI backend
python api_server.py

# Terminal 2: Start the Next.js frontend
cd frontend-next
npm run dev
```
- API Documentation: `http://localhost:8000/api/docs`
- Frontend Application: `http://localhost:3000`

### Option 3: Full Stack Development
```bash
# Run all services simultaneously (recommended for development)
# Use the configured Replit workflows or run manually:

# Terminal 1: Streamlit
streamlit run app.py --server.port 5000 --server.address 0.0.0.0

# Terminal 2: FastAPI Backend
python api_server.py

# Terminal 3: Next.js Frontend
cd frontend-next && npm run dev
```

## 📊 Usage Guide

### Getting Started
1. **Select Session Data**:
   - Choose year (2018-2025)
   - Select Grand Prix event
   - Pick session type (Practice, Qualifying, Race, Sprint)

2. **Load Data**: Click "Load Session Data" to fetch telemetry information

3. **Choose Drivers**: Select drivers for comparison analysis

4. **Explore Analytics**:
   - **Telemetry**: Speed, throttle, brake, and gear analysis
   - **Lap Analysis**: Sector times and lap progression
   - **Tire Strategy**: Compound performance and pit stop analysis
   - **Track Dominance**: Fastest sectors visualization
   - **Advanced Analytics**: Performance index and ML clustering
   - **Brake Analysis**: Efficiency and force metrics
   - **Composite Performance**: Multi-factor driver evaluation

### Advanced Features
- **Data Export**: Download charts and analysis data
- **Real-time Updates**: Live session data refresh
- **Professional Styling**: High-contrast design for better visibility
- **Mobile Support**: Responsive design for all devices

## 🔧 API Documentation

### Core Endpoints
- `POST /api/session/load` - Load F1 session data
- `GET /api/drivers` - Get available drivers
- `POST /api/analysis/telemetry` - Telemetry analysis
- `POST /api/analysis/brake` - Brake performance analysis
- `POST /api/analysis/composite` - Composite performance metrics
- `POST /api/analysis/tire` - Tire strategy analysis
- `GET /api/constants/teams` - Team colors and constants

### Example API Usage
```python
import requests

# Load session data
response = requests.post("http://localhost:8000/api/session/load", json={
    "year": 2024,
    "grand_prix": "Monaco",
    "session_type": "R"
})

# Get brake analysis
response = requests.post("http://localhost:8000/api/analysis/brake", json={
    "drivers": ["VER", "HAM", "LEC"]
})
```

## 📁 Project Structure

```
track-lytix/
├── app.py                      # Main Streamlit application
├── api_server.py               # FastAPI backend server
├── requirements.txt            # Python dependencies
├── replit.md                   # Project documentation
├── 
├── utils/                      # Core analysis modules
│   ├── data_loader.py          # F1 data loading and caching
│   ├── brake_analysis.py       # Brake efficiency analysis
│   ├── composite_performance.py # Performance index calculations
│   ├── advanced_analytics.py   # ML-powered analytics
│   ├── tire_performance.py     # Tire strategy analysis
│   ├── visualizations.py       # Plotly chart generation
│   ├── constants.py            # F1 team colors and data
│   └── ...                     # Additional analysis modules
├── 
├── frontend-next/              # Next.js TypeScript frontend
│   ├── app/                    # Next.js 14 app directory
│   │   ├── components/         # React components
│   │   ├── globals.css         # Global styles
│   │   ├── layout.tsx          # Root layout
│   │   └── page.tsx            # Main page
│   ├── package.json            # Node.js dependencies
│   ├── tailwind.config.js      # Tailwind CSS configuration
│   └── next.config.js          # Next.js configuration
└── 
└── .streamlit/                 # Streamlit configuration
    └── config.toml             # Server settings
```

## 🎨 Customization

### Styling
- Modify `app.py` CSS variables for color themes
- Update `frontend-next/tailwind.config.js` for frontend styling
- Customize team colors in `utils/constants.py`

### Adding New Analysis
1. Create new module in `utils/` directory
2. Add corresponding API endpoint in `api_server.py`
3. Import and integrate in `app.py`
4. Add frontend component in `frontend-next/app/components/`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-analysis`
3. Commit changes: `git commit -am 'Add new analysis feature'`
4. Push to branch: `git push origin feature/new-analysis`
5. Submit a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastF1** - Official F1 data access library
- **Streamlit** - Web application framework
- **Next.js** - React framework for production
- **Plotly** - Interactive visualization library
- **Formula 1** - For providing official timing data

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-username/track-lytix/issues)
- **Documentation**: [Project Wiki](https://github.com/your-username/track-lytix/wiki)
- **API Docs**: `http://localhost:8000/api/docs` (when running)

---

<div align="center">
  <h3>🏎️ Built for F1 Enthusiasts, by F1 Enthusiasts</h3>
  <p>Track.lytix - Professional Formula 1 Data Analysis Platform</p>
</div>