/**
 * F1 Live Timing Module
 * Real-time timing tower and race data visualization
 */

class F1LiveTiming {
    constructor() {
        this.isLive = false;
        this.updateInterval = null;
        this.currentSessionData = null;
        this.sortBy = 'position';
        this.lastUpdateTime = 0;
        this.initializeEventListeners();
    }

    /**
     * Initialize all event listeners
     */
    initializeEventListeners() {
        // Season change
        const seasonSelect = document.getElementById('liveSeasonSelect');
        if (seasonSelect) {
            seasonSelect.addEventListener('change', () => this.loadEvents());
        }

        // Start/Stop timing
        const startBtn = document.getElementById('startLiveTimingBtn');
        const stopBtn = document.getElementById('stopLiveTimingBtn');
        
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startLiveTiming());
        }
        
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopLiveTiming());
        }

        // Sort controls
        document.querySelectorAll('.sort-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.setSortMode(e.target.dataset.sort);
            });
        });
    }

    /**
     * Load events for selected season
     */
    async loadEvents() {
        const seasonSelect = document.getElementById('liveSeasonSelect');
        const eventSelect = document.getElementById('liveEventSelect');
        
        if (!seasonSelect || !eventSelect) return;

        const year = seasonSelect.value;
        if (!year) return;

        try {
            const response = await fetch(`/api/seasons/${year}/events`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const data = await response.json();
            
            eventSelect.innerHTML = '<option value="">Select Grand Prix...</option>';
            
            // Add recent races first (last 5)
            const recentEvents = data.events.slice(-5).reverse();
            const otherEvents = data.events.slice(0, -5);
            
            // Recent races group
            if (recentEvents.length > 0) {
                const recentGroup = document.createElement('optgroup');
                recentGroup.label = 'Recent Races';
                recentEvents.forEach(event => {
                    const option = document.createElement('option');
                    option.value = event.round;
                    option.textContent = `${event.name} (${event.country})`;
                    recentGroup.appendChild(option);
                });
                eventSelect.appendChild(recentGroup);
            }
            
            // All other races
            if (otherEvents.length > 0) {
                const allGroup = document.createElement('optgroup');
                allGroup.label = 'All Races';
                otherEvents.forEach(event => {
                    const option = document.createElement('option');
                    option.value = event.round;
                    option.textContent = `${event.name} (${event.country})`;
                    allGroup.appendChild(option);
                });
                eventSelect.appendChild(allGroup);
            }
            
        } catch (error) {
            console.error('Error loading events:', error);
            this.showError('Failed to load events for selected season');
        }
    }

    /**
     * Start live timing updates
     */
    async startLiveTiming() {
        const seasonSelect = document.getElementById('liveSeasonSelect');
        const eventSelect = document.getElementById('liveEventSelect');
        const sessionSelect = document.getElementById('liveSessionSelect');
        
        if (!seasonSelect?.value || !eventSelect?.value || !sessionSelect?.value) {
            this.showError('Please select season, event, and session');
            return;
        }

        try {
            this.showLoading();
            this.updateStatus('connecting', 'Connecting to live timing...');
            
            // Load initial session data
            await this.loadSessionData();
            
            this.isLive = true;
            this.updateStatus('live', 'Live Timing Active');
            this.showLiveContent();
            this.hideLoading();
            
            // Toggle buttons
            document.getElementById('startLiveTimingBtn').style.display = 'none';
            document.getElementById('stopLiveTimingBtn').style.display = 'flex';
            
            // Start update interval (every 2 seconds for demo)
            this.updateInterval = setInterval(() => {
                this.updateLiveData();
            }, 2000);
            
        } catch (error) {
            console.error('Error starting live timing:', error);
            this.showError('Failed to start live timing');
            this.hideLoading();
        }
    }

    /**
     * Stop live timing updates
     */
    stopLiveTiming() {
        this.isLive = false;
        
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
        
        this.updateStatus('paused', 'Live Timing Paused');
        
        // Toggle buttons
        document.getElementById('startLiveTimingBtn').style.display = 'flex';
        document.getElementById('stopLiveTimingBtn').style.display = 'none';
    }

    /**
     * Load session data
     */
    async loadSessionData() {
        const seasonSelect = document.getElementById('liveSeasonSelect');
        const eventSelect = document.getElementById('liveEventSelect');
        const sessionSelect = document.getElementById('liveSessionSelect');
        
        const year = seasonSelect.value;
        const round = eventSelect.value;
        const session = sessionSelect.value;
        
        try {
            // Get session summary for live timing
            const response = await fetch(`/api/session-summary/${year}/${round}?session_type=${session}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            this.currentSessionData = await response.json();
            
            // Initial render
            this.renderTimingTower();
            this.renderSectorTimes();
            this.updateRaceStats();
            
        } catch (error) {
            console.error('Error loading session data:', error);
            throw new Error('Failed to load session data');
        }
    }

    /**
     * Update live data (simulated for now)
     */
    async updateLiveData() {
        if (!this.isLive || !this.currentSessionData) return;
        
        try {
            // In a real implementation, this would fetch fresh data
            // For now, we'll simulate updates by modifying existing data
            this.simulateDataUpdates();
            
            // Re-render components
            this.renderTimingTower();
            this.renderSectorTimes();
            this.updateRaceStats();
            
            this.lastUpdateTime = Date.now();
            
        } catch (error) {
            console.error('Error updating live data:', error);
        }
    }

    /**
     * Simulate live data updates for demonstration
     */
    simulateDataUpdates() {
        if (!this.currentSessionData?.drivers) return;
        
        // Simulate small random changes to lap times and positions
        this.currentSessionData.drivers.forEach(driver => {
            // Simulate new lap time (±0.5 seconds variation)
            if (driver.last_lap_time && Math.random() > 0.7) {
                const variation = (Math.random() - 0.5) * 1.0;
                driver.last_lap_time += variation;
                driver.last_lap_time = Math.max(driver.last_lap_time, 60); // Minimum 1 minute
                
                // Mark as updated for animation
                driver.updated = true;
                setTimeout(() => delete driver.updated, 1000);
            }
            
            // Simulate sector times
            if (Math.random() > 0.8) {
                driver.sector1_time = 20 + Math.random() * 10;
                driver.sector2_time = 25 + Math.random() * 15;
                driver.sector3_time = 22 + Math.random() * 12;
            }
        });
        
        // Simulate position changes (rarely)
        if (Math.random() > 0.95 && this.currentSessionData.drivers.length > 1) {
            const driver1Index = Math.floor(Math.random() * this.currentSessionData.drivers.length);
            const driver2Index = Math.floor(Math.random() * this.currentSessionData.drivers.length);
            
            if (driver1Index !== driver2Index) {
                const temp = this.currentSessionData.drivers[driver1Index];
                this.currentSessionData.drivers[driver1Index] = this.currentSessionData.drivers[driver2Index];
                this.currentSessionData.drivers[driver2Index] = temp;
            }
        }
    }

    /**
     * Render timing tower
     */
    renderTimingTower() {
        const timingTower = document.getElementById('timingTower');
        if (!timingTower || !this.currentSessionData?.drivers) return;
        
        // Sort drivers based on current sort mode
        let sortedDrivers = [...this.currentSessionData.drivers];
        
        switch (this.sortBy) {
            case 'position':
                sortedDrivers.sort((a, b) => (a.position || 999) - (b.position || 999));
                break;
            case 'gap':
                sortedDrivers.sort((a, b) => (a.gap_to_leader || 999) - (b.gap_to_leader || 999));
                break;
            case 'lastlap':
                sortedDrivers.sort((a, b) => (a.last_lap_time || 999) - (b.last_lap_time || 999));
                break;
        }
        
        timingTower.innerHTML = '';
        
        // Create header row
        const headerRow = document.createElement('div');
        headerRow.className = 'timing-row-header';
        headerRow.innerHTML = `
            <div style="display: grid; grid-template-columns: 50px 60px 200px 1fr 100px 100px 100px 80px; gap: var(--space-md); padding: var(--space-sm) var(--space-md); font-weight: 700; color: var(--f1-light-gray); border-bottom: 1px solid rgba(255,255,255,0.2); margin-bottom: var(--space-sm);">
                <div>POS</div>
                <div>NUM</div>
                <div>DRIVER</div>
                <div>GAP</div>
                <div>LAST LAP</div>
                <div>SECTORS</div>
                <div>BEST LAP</div>
                <div>TYRE</div>
            </div>
        `;
        timingTower.appendChild(headerRow);
        
        // Create driver rows
        sortedDrivers.forEach((driver, index) => {
            const row = document.createElement('div');
            row.className = `timing-row ${driver.updated ? 'updated' : ''}`;
            
            if (index === 0) row.classList.add('leader');
            
            const gapText = index === 0 ? 'LEADER' : 
                           driver.gap_to_leader ? `+${F1Utils.formatTime(driver.gap_to_leader)}` : '--';
            
            const lastLapClass = driver.is_personal_best ? 'personal-best' : '';
            const lastLapText = driver.last_lap_time ? F1Utils.formatTime(driver.last_lap_time) : '--:--.---';
            
            const sectorTimes = `
                <div class="sector-times">
                    <span class="sector-time ${driver.sector1_best ? 'personal-best' : ''}">${driver.sector1_time ? F1Utils.formatSectorTime(driver.sector1_time) : '--'}</span>
                    <span class="sector-time ${driver.sector2_best ? 'personal-best' : ''}">${driver.sector2_time ? F1Utils.formatSectorTime(driver.sector2_time) : '--'}</span>
                    <span class="sector-time ${driver.sector3_best ? 'personal-best' : ''}">${driver.sector3_time ? F1Utils.formatSectorTime(driver.sector3_time) : '--'}</span>
                </div>
            `;
            
            const tyreCompound = driver.compound || 'MEDIUM';
            const tyreAge = driver.tyre_life || 0;
            
            row.innerHTML = `
                <div class="position">${driver.position || index + 1}</div>
                <div class="driver-number">${driver.driver_number || '00'}</div>
                <div class="driver-info">
                    <div class="driver-name">${driver.full_name || 'Unknown Driver'}</div>
                    <div class="driver-team">${driver.team_name || 'Unknown Team'}</div>
                </div>
                <div class="gap-time ${index === 0 ? 'leader' : ''}">${gapText}</div>
                <div class="last-lap ${lastLapClass}">${lastLapText}</div>
                ${sectorTimes}
                <div class="best-lap">${driver.best_lap_time ? F1Utils.formatTime(driver.best_lap_time) : '--:--.---'}</div>
                <div class="tyre-info">
                    <div class="tyre-compound ${tyreCompound.toLowerCase()}">${tyreCompound.charAt(0)}</div>
                    <span>${tyreAge}</span>
                </div>
            `;
            
            timingTower.appendChild(row);
        });
    }

    /**
     * Render sector times
     */
    renderSectorTimes() {
        const sector1Times = document.getElementById('sector1Times');
        const sector2Times = document.getElementById('sector2Times');
        const sector3Times = document.getElementById('sector3Times');
        
        if (!sector1Times || !sector2Times || !sector3Times || !this.currentSessionData?.drivers) return;
        
        // Get fastest times for each sector
        const drivers = this.currentSessionData.drivers;
        
        const sector1Data = drivers
            .filter(d => d.sector1_time)
            .sort((a, b) => a.sector1_time - b.sector1_time)
            .slice(0, 10);
            
        const sector2Data = drivers
            .filter(d => d.sector2_time)
            .sort((a, b) => a.sector2_time - b.sector2_time)
            .slice(0, 10);
            
        const sector3Data = drivers
            .filter(d => d.sector3_time)
            .sort((a, b) => a.sector3_time - b.sector3_time)
            .slice(0, 10);
        
        // Render each sector
        this.renderSectorColumn(sector1Times, sector1Data, 'sector1_time');
        this.renderSectorColumn(sector2Times, sector2Data, 'sector2_time');
        this.renderSectorColumn(sector3Times, sector3Data, 'sector3_time');
    }

    /**
     * Render individual sector column
     */
    renderSectorColumn(container, data, timeField) {
        container.innerHTML = '';
        
        data.forEach((driver, index) => {
            const entry = document.createElement('div');
            entry.className = `sector-time-entry ${index === 0 ? 'fastest' : ''}`;
            
            entry.innerHTML = `
                <span class="driver-name">${driver.full_name || 'Unknown'}</span>
                <span class="sector-time">${F1Utils.formatSectorTime(driver[timeField])}</span>
            `;
            
            container.appendChild(entry);
        });
    }

    /**
     * Update race statistics
     */
    updateRaceStats() {
        if (!this.currentSessionData) return;
        
        const drivers = this.currentSessionData.drivers;
        const currentLapEl = document.getElementById('currentLap');
        const fastestLapEl = document.getElementById('fastestLap');
        const raceLeaderEl = document.getElementById('raceLeader');
        const trackTempEl = document.getElementById('trackTemp');
        
        // Current lap (simulated)
        if (currentLapEl) {
            const currentLap = Math.floor(Math.random() * 50) + 1;
            currentLapEl.textContent = currentLap;
        }
        
        // Fastest lap
        if (fastestLapEl && drivers.length > 0) {
            const fastestDriver = drivers.reduce((fastest, driver) => {
                if (!fastest.best_lap_time || (driver.best_lap_time && driver.best_lap_time < fastest.best_lap_time)) {
                    return driver;
                }
                return fastest;
            }, drivers[0]);
            
            fastestLapEl.textContent = fastestDriver.best_lap_time ? 
                F1Utils.formatTime(fastestDriver.best_lap_time) : '--:--.---';
        }
        
        // Race leader
        if (raceLeaderEl && drivers.length > 0) {
            const leader = drivers.find(d => d.position === 1) || drivers[0];
            raceLeaderEl.textContent = leader.full_name || 'Unknown';
        }
        
        // Track temperature (simulated)
        if (trackTempEl) {
            const temp = Math.floor(Math.random() * 20) + 25; // 25-45°C
            trackTempEl.textContent = `${temp}°C`;
        }
    }

    /**
     * Set sort mode for timing tower
     */
    setSortMode(sortBy) {
        this.sortBy = sortBy;
        
        // Update active button
        document.querySelectorAll('.sort-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        document.querySelector(`[data-sort="${sortBy}"]`)?.classList.add('active');
        
        // Re-render timing tower
        this.renderTimingTower();
    }

    /**
     * Update status indicator
     */
    updateStatus(status, text) {
        const statusIndicator = document.getElementById('liveStatus');
        const statusText = document.getElementById('statusText');
        
        if (statusIndicator && statusText) {
            statusIndicator.className = `status-indicator ${status}`;
            statusText.textContent = text;
        }
    }

    /**
     * Show live content
     */
    showLiveContent() {
        const content = document.getElementById('liveTimingContent');
        if (content) {
            content.style.display = 'block';
        }
    }

    /**
     * Show loading state
     */
    showLoading() {
        const loading = document.getElementById('liveTimingLoading');
        if (loading) {
            loading.style.display = 'block';
        }
    }

    /**
     * Hide loading state
     */
    hideLoading() {
        const loading = document.getElementById('liveTimingLoading');
        if (loading) {
            loading.style.display = 'none';
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        const errorContainer = document.getElementById('liveTimingError');
        const errorText = document.querySelector('#liveTimingError .error-text');
        
        if (errorContainer && errorText) {
            errorText.textContent = message;
            errorContainer.style.display = 'block';
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                errorContainer.style.display = 'none';
            }, 5000);
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname === '/live-timing') {
        window.F1LiveTiming = new F1LiveTiming();
        
        // Auto-load events for current season
        if (window.F1LiveTiming) {
            window.F1LiveTiming.loadEvents();
        }
    }
});