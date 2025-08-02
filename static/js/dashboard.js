/**
 * F1 Analytics Dashboard - Main JavaScript Module
 * Handles data loading, UI interactions, and dashboard functionality
 */

class F1Dashboard {
    constructor() {
        this.currentData = null;
        this.charts = {};
        this.initializeEventListeners();
        this.loadInitialData();
    }

    /**
     * Initialize all event listeners
     */
    initializeEventListeners() {
        // Season change event
        const seasonSelect = document.getElementById('seasonSelect');
        if (seasonSelect) {
            seasonSelect.addEventListener('change', () => this.loadEvents());
        }

        // Load data button
        const loadDataBtn = document.getElementById('loadDataBtn');
        if (loadDataBtn) {
            loadDataBtn.addEventListener('click', () => this.loadDriverData());
        }

        // Export button
        const exportBtn = document.getElementById('exportBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportData());
        }

        // Event change to load drivers
        const eventSelect = document.getElementById('eventSelect');
        const sessionSelect = document.getElementById('sessionSelect');
        if (eventSelect && sessionSelect) {
            eventSelect.addEventListener('change', () => this.loadDrivers());
            sessionSelect.addEventListener('change', () => this.loadDrivers());
        }
    }

    /**
     * Load initial data when page loads
     */
    async loadInitialData() {
        try {
            await this.loadEvents();
        } catch (error) {
            console.error('Error loading initial data:', error);
            this.showError('Failed to load initial data');
        }
    }

    /**
     * Load events for selected season
     */
    async loadEvents() {
        const seasonSelect = document.getElementById('seasonSelect');
        const eventSelect = document.getElementById('eventSelect');
        
        if (!seasonSelect || !eventSelect) return;

        const year = seasonSelect.value;
        if (!year) return;

        try {
            this.showLoading();
            
            const response = await fetch(`/api/seasons/${year}/events`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Clear existing options
            eventSelect.innerHTML = '<option value="">Select Grand Prix...</option>';
            
            // Add new options
            data.events.forEach(event => {
                const option = document.createElement('option');
                option.value = event.round;
                option.textContent = `${event.name} (${event.country})`;
                eventSelect.appendChild(option);
            });

            this.hideLoading();
            this.hideError();
            
        } catch (error) {
            console.error('Error loading events:', error);
            this.showError('Failed to load events for selected season');
            this.hideLoading();
        }
    }

    /**
     * Load drivers for selected session
     */
    async loadDrivers() {
        const seasonSelect = document.getElementById('seasonSelect');
        const eventSelect = document.getElementById('eventSelect');
        const sessionSelect = document.getElementById('sessionSelect');
        const driverSelect = document.getElementById('driverSelect');
        
        if (!seasonSelect || !eventSelect || !sessionSelect || !driverSelect) return;

        const year = seasonSelect.value;
        const round = eventSelect.value;
        const session = sessionSelect.value;
        
        if (!year || !round || !session) {
            driverSelect.innerHTML = '<option value="">Select Driver...</option>';
            return;
        }

        try {
            const response = await fetch(`/api/sessions/${year}/${round}/drivers?session_type=${session}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Clear existing options
            driverSelect.innerHTML = '<option value="">Select Driver...</option>';
            
            // Add new options
            data.drivers.forEach(driver => {
                const option = document.createElement('option');
                option.value = driver;
                option.textContent = `Driver #${driver}`;
                driverSelect.appendChild(option);
            });
            
        } catch (error) {
            console.error('Error loading drivers:', error);
            this.showError('Failed to load drivers for selected session');
        }
    }

    /**
     * Load comprehensive driver data
     */
    async loadDriverData() {
        const seasonSelect = document.getElementById('seasonSelect');
        const eventSelect = document.getElementById('eventSelect');
        const sessionSelect = document.getElementById('sessionSelect');
        const driverSelect = document.getElementById('driverSelect');
        
        if (!seasonSelect || !eventSelect || !sessionSelect || !driverSelect) return;

        const year = seasonSelect.value;
        const round = eventSelect.value;
        const session = sessionSelect.value;
        const driver = driverSelect.value;
        
        if (!year || !round || !session || !driver) {
            this.showError('Please select all required options');
            return;
        }

        try {
            this.showLoading();
            this.hideError();
            this.hideDashboard();

            const response = await fetch(`/api/lap-data/${year}/${round}/${driver}?session_type=${session}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (!data.lap_data || data.lap_data.length === 0) {
                this.showError(data.message || 'No lap data found for selected driver');
                this.hideLoading();
                return;
            }

            this.currentData = data;
            this.displayDriverData(data);
            this.showDashboard();
            this.hideLoading();
            
        } catch (error) {
            console.error('Error loading driver data:', error);
            this.showError('Failed to load driver data. Please try again.');
            this.hideLoading();
        }
    }

    /**
     * Display driver data in the dashboard
     */
    displayDriverData(data) {
        // Update driver info
        this.updateDriverInfo(data.driver_info);
        
        // Update statistics
        this.updateStatistics(data.statistics);
        
        // Update data table
        this.updateDataTable(data.lap_data);
        
        // Create charts
        if (window.F1Charts) {
            window.F1Charts.createLapTimesChart(data.lap_data);
            window.F1Charts.createSectorTimesChart(data.lap_data);
            window.F1Charts.createSpeedChart(data.lap_data);
            window.F1Charts.createTyreChart(data.lap_data);
        }
    }

    /**
     * Update driver information display
     */
    updateDriverInfo(driverInfo) {
        const elements = {
            driverName: document.getElementById('driverName'),
            driverNumber: document.getElementById('driverNumber'),
            driverTeam: document.getElementById('driverTeam'),
            driverPosition: document.getElementById('driverPosition'),
            driverStatus: document.getElementById('driverStatus')
        };

        if (elements.driverName) {
            elements.driverName.textContent = driverInfo.full_name || 'Unknown Driver';
        }
        
        if (elements.driverNumber) {
            elements.driverNumber.textContent = `#${driverInfo.driver_number || '00'}`;
        }
        
        if (elements.driverTeam) {
            elements.driverTeam.textContent = driverInfo.team_name || 'Unknown Team';
        }
        
        if (elements.driverPosition) {
            elements.driverPosition.textContent = driverInfo.position ? `P${driverInfo.position}` : '-';
        }
        
        if (elements.driverStatus) {
            elements.driverStatus.textContent = driverInfo.status || 'Unknown';
        }
    }

    /**
     * Update statistics display
     */
    updateStatistics(stats) {
        const elements = {
            bestLapTime: document.getElementById('bestLapTime'),
            bestLapNumber: document.getElementById('bestLapNumber'),
            avgLapTime: document.getElementById('avgLapTime'),
            totalLaps: document.getElementById('totalLaps'),
            consistency: document.getElementById('consistency'),
            theoreticalBest: document.getElementById('theoreticalBest')
        };

        if (elements.bestLapTime) {
            elements.bestLapTime.textContent = stats.best_lap_time_formatted || '--:--.---';
        }
        
        if (elements.bestLapNumber) {
            elements.bestLapNumber.textContent = stats.best_lap_number || '-';
        }
        
        if (elements.avgLapTime) {
            elements.avgLapTime.textContent = stats.average_lap_time_formatted || '--:--.---';
        }
        
        if (elements.totalLaps) {
            elements.totalLaps.textContent = stats.total_laps || '0';
        }
        
        if (elements.consistency) {
            elements.consistency.textContent = stats.consistency_formatted || '-.---s';
        }
        
        if (elements.theoreticalBest) {
            elements.theoreticalBest.textContent = stats.theoretical_best_formatted || '--:--.---';
        }
    }

    /**
     * Update data table with lap information
     */
    updateDataTable(lapData) {
        const tableBody = document.querySelector('#lapDataTable tbody');
        if (!tableBody) return;

        tableBody.innerHTML = '';

        lapData.forEach(lap => {
            const row = document.createElement('tr');
            
            // Add personal best class if applicable
            if (lap.IsPersonalBest) {
                row.classList.add('personal-best');
            }

            row.innerHTML = `
                <td>${lap.LapNumber}</td>
                <td>${lap.LapTimeFormatted}</td>
                <td>${lap.Sector1Formatted}</td>
                <td>${lap.Sector2Formatted}</td>
                <td>${lap.Sector3Formatted}</td>
                <td>${lap.Compound}</td>
                <td>${lap.TyreLife}</td>
                <td>${lap.MaxSpeedFormatted}</td>
                <td>${lap.Position || '-'}</td>
            `;

            tableBody.appendChild(row);
        });
    }

    /**
     * Export data to CSV
     */
    exportData() {
        if (!this.currentData || !this.currentData.lap_data) {
            this.showError('No data available to export');
            return;
        }

        try {
            const csv = this.convertToCSV(this.currentData.lap_data);
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', `f1_lap_data_${Date.now()}.csv`);
            link.style.visibility = 'hidden';
            
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
        } catch (error) {
            console.error('Error exporting data:', error);
            this.showError('Failed to export data');
        }
    }

    /**
     * Convert lap data to CSV format
     */
    convertToCSV(lapData) {
        const headers = [
            'Lap Number', 'Lap Time', 'Sector 1', 'Sector 2', 'Sector 3',
            'Compound', 'Tyre Life', 'Max Speed', 'Avg Speed', 'Position'
        ];

        const rows = lapData.map(lap => [
            lap.LapNumber,
            lap.LapTimeFormatted,
            lap.Sector1Formatted,
            lap.Sector2Formatted,
            lap.Sector3Formatted,
            lap.Compound,
            lap.TyreLife,
            lap.MaxSpeedFormatted,
            lap.AvgSpeedFormatted,
            lap.Position || ''
        ]);

        const csvContent = [headers, ...rows]
            .map(row => row.map(field => `"${field}"`).join(','))
            .join('\n');

        return csvContent;
    }

    /**
     * Show loading indicator
     */
    showLoading() {
        const loadingIndicator = document.getElementById('loadingIndicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
        }
    }

    /**
     * Hide loading indicator
     */
    hideLoading() {
        const loadingIndicator = document.getElementById('loadingIndicator');
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        const errorContainer = document.getElementById('errorMessage');
        const errorText = document.querySelector('#errorMessage .error-text');
        
        if (errorContainer && errorText) {
            errorText.textContent = message;
            errorContainer.style.display = 'block';
        }
    }

    /**
     * Hide error message
     */
    hideError() {
        const errorContainer = document.getElementById('errorMessage');
        if (errorContainer) {
            errorContainer.style.display = 'none';
        }
    }

    /**
     * Show dashboard content
     */
    showDashboard() {
        const dashboardContent = document.getElementById('dashboardContent');
        if (dashboardContent) {
            dashboardContent.style.display = 'block';
        }
    }

    /**
     * Hide dashboard content
     */
    hideDashboard() {
        const dashboardContent = document.getElementById('dashboardContent');
        if (dashboardContent) {
            dashboardContent.style.display = 'none';
        }
    }
}

// Utility functions for formatting
const F1Utils = {
    /**
     * Format time in seconds to MM:SS.mmm
     */
    formatTime(seconds) {
        if (!seconds || seconds <= 0) return '--:--.---';
        
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        
        return `${minutes}:${remainingSeconds.toFixed(3).padStart(6, '0')}`;
    },

    /**
     * Format sector time
     */
    formatSectorTime(seconds) {
        if (!seconds || seconds <= 0) return '---.---';
        return `${seconds.toFixed(3)}s`;
    },

    /**
     * Get tyre compound color
     */
    getTyreColor(compound) {
        const colors = {
            'SOFT': '#ff0000',
            'MEDIUM': '#ffff00',
            'HARD': '#ffffff',
            'INTERMEDIATE': '#00ff00',
            'WET': '#0000ff'
        };
        return colors[compound] || '#cccccc';
    },

    /**
     * Debounce function for API calls
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.F1Dashboard = new F1Dashboard();
});

// Make utilities globally available
window.F1Utils = F1Utils;
