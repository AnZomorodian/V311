/**
 * F1 Circuit Map Visualization Module
 * Interactive circuit maps with telemetry data and driver tracking
 */

class F1CircuitMap {
    constructor() {
        this.currentSessionData = null;
        this.circuitData = null;
        this.selectedDrivers = new Set();
        this.animationFrame = null;
        this.isAnimating = false;
        this.currentLap = 1;
        this.telemetryMode = 'speed';
        this.svg = null;
        this.scales = { x: null, y: null };
        this.charts = {};
        
        this.initializeEventListeners();
        this.setupSVG();
    }

    /**
     * Initialize all event listeners
     */
    initializeEventListeners() {
        // Season change
        const seasonSelect = document.getElementById('mapSeasonSelect');
        if (seasonSelect) {
            seasonSelect.addEventListener('change', () => this.loadEvents());
        }

        // Load circuit button
        const loadBtn = document.getElementById('loadCircuitBtn');
        if (loadBtn) {
            loadBtn.addEventListener('click', () => this.loadCircuitData());
        }

        // Animation controls
        const playBtn = document.getElementById('playAnimation');
        const pauseBtn = document.getElementById('pauseAnimation');
        const resetBtn = document.getElementById('resetAnimation');
        
        if (playBtn) playBtn.addEventListener('click', () => this.playAnimation());
        if (pauseBtn) pauseBtn.addEventListener('click', () => this.pauseAnimation());
        if (resetBtn) resetBtn.addEventListener('click', () => this.resetAnimation());

        // Lap slider
        const lapSlider = document.getElementById('lapSlider');
        if (lapSlider) {
            lapSlider.addEventListener('input', (e) => this.setAnimationPosition(e.target.value));
        }

        // Telemetry mode
        const telemetrySelect = document.getElementById('telemetryMode');
        if (telemetrySelect) {
            telemetrySelect.addEventListener('change', (e) => {
                this.telemetryMode = e.target.value;
                this.updateTelemetryVisualization();
            });
        }

        // Driver comparison
        const compareBtn = document.getElementById('compareDriversBtn');
        if (compareBtn) {
            compareBtn.addEventListener('click', () => this.compareDrivers());
        }
    }

    /**
     * Setup SVG canvas
     */
    setupSVG() {
        this.svg = d3.select('#circuitSVG');
        
        // Set up scales - will be updated when circuit data is loaded
        this.scales.x = d3.scaleLinear().range([50, 750]);
        this.scales.y = d3.scaleLinear().range([50, 550]);
    }

    /**
     * Load events for selected season
     */
    async loadEvents() {
        const seasonSelect = document.getElementById('mapSeasonSelect');
        const eventSelect = document.getElementById('mapEventSelect');
        
        if (!seasonSelect || !eventSelect) return;

        const year = seasonSelect.value;
        if (!year) return;

        try {
            const response = await fetch(`/api/seasons/${year}/events`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const data = await response.json();
            
            eventSelect.innerHTML = '<option value="">Select Grand Prix...</option>';
            
            // Popular/famous circuits first
            const famousCircuits = ['Monaco', 'Silverstone', 'Monza', 'Spa-Francorchamps', 'Suzuka'];
            const famousEvents = data.events.filter(event => 
                famousCircuits.some(famous => event.location.includes(famous))
            );
            const otherEvents = data.events.filter(event => 
                !famousCircuits.some(famous => event.location.includes(famous))
            );
            
            if (famousEvents.length > 0) {
                const famousGroup = document.createElement('optgroup');
                famousGroup.label = 'Classic Circuits';
                famousEvents.forEach(event => {
                    const option = document.createElement('option');
                    option.value = event.round;
                    option.textContent = `${event.name} (${event.location})`;
                    famousGroup.appendChild(option);
                });
                eventSelect.appendChild(famousGroup);
            }
            
            if (otherEvents.length > 0) {
                const otherGroup = document.createElement('optgroup');
                otherGroup.label = 'All Other Circuits';
                otherEvents.forEach(event => {
                    const option = document.createElement('option');
                    option.value = event.round;
                    option.textContent = `${event.name} (${event.location})`;
                    otherGroup.appendChild(option);
                });
                eventSelect.appendChild(otherGroup);
            }
            
        } catch (error) {
            console.error('Error loading events:', error);
            this.showError('Failed to load events for selected season');
        }
    }

    /**
     * Load circuit and session data
     */
    async loadCircuitData() {
        const seasonSelect = document.getElementById('mapSeasonSelect');
        const eventSelect = document.getElementById('mapEventSelect');
        const sessionSelect = document.getElementById('mapSessionSelect');
        
        if (!seasonSelect?.value || !eventSelect?.value || !sessionSelect?.value) {
            this.showError('Please select season, event, and session');
            return;
        }

        try {
            this.showLoading();
            
            const year = seasonSelect.value;
            const round = eventSelect.value;
            const session = sessionSelect.value;
            
            // Load session data with telemetry
            const sessionResponse = await fetch(`/api/session-summary/${year}/${round}?session_type=${session}`);
            if (!sessionResponse.ok) throw new Error('Failed to load session data');
            
            this.currentSessionData = await sessionResponse.json();
            
            // Generate circuit layout (simulated since FastF1 doesn't provide track maps)
            this.generateCircuitLayout();
            
            // Update UI
            this.updateCircuitInfo();
            this.setupDriverSelection();
            this.renderCircuitMap();
            this.setupTelemetryCharts();
            this.showContent();
            this.hideLoading();
            
        } catch (error) {
            console.error('Error loading circuit data:', error);
            this.showError('Failed to load circuit data');
            this.hideLoading();
        }
    }

    /**
     * Generate simulated circuit layout
     * In a real implementation, this would use track coordinate data
     */
    generateCircuitLayout() {
        // Generate a realistic circuit shape based on the track name
        const eventSelect = document.getElementById('mapEventSelect');
        const selectedOption = eventSelect.options[eventSelect.selectedIndex];
        const trackName = selectedOption?.text || 'Generic Circuit';
        
        this.circuitData = this.createCircuitShape(trackName);
        
        // Update scales based on circuit bounds
        const bounds = this.getCircuitBounds();
        this.scales.x.domain([bounds.minX - 50, bounds.maxX + 50]);
        this.scales.y.domain([bounds.minY - 50, bounds.maxY + 50]);
    }

    /**
     * Create circuit shape based on track characteristics
     */
    createCircuitShape(trackName) {
        const points = [];
        const sectors = [];
        
        // Different circuit shapes based on famous tracks
        if (trackName.includes('Monaco')) {
            points.push(...this.createMonacoShape());
            sectors.push(
                { name: 'Sector 1', position: 0.2 },
                { name: 'Sector 2', position: 0.6 },
                { name: 'Sector 3', position: 0.9 }
            );
        } else if (trackName.includes('Silverstone')) {
            points.push(...this.createSilverstoneShape());
            sectors.push(
                { name: 'Sector 1', position: 0.25 },
                { name: 'Sector 2', position: 0.65 },
                { name: 'Sector 3', position: 0.9 }
            );
        } else if (trackName.includes('Monza')) {
            points.push(...this.createMonzaShape());
            sectors.push(
                { name: 'Sector 1', position: 0.3 },
                { name: 'Sector 2', position: 0.7 },
                { name: 'Sector 3', position: 0.95 }
            );
        } else {
            // Generic circuit shape
            points.push(...this.createGenericShape());
            sectors.push(
                { name: 'Sector 1', position: 0.33 },
                { name: 'Sector 2', position: 0.66 },
                { name: 'Sector 3', position: 0.9 }
            );
        }
        
        return {
            points,
            sectors,
            length: this.calculateTrackLength(points),
            name: trackName.split('(')[0].trim()
        };
    }

    /**
     * Create Monaco-style circuit (tight, twisty)
     */
    createMonacoShape() {
        return [
            { x: 100, y: 300, speed: 80 },   // Start/finish straight
            { x: 200, y: 280, speed: 120 },  // Slight curve
            { x: 350, y: 200, speed: 60 },   // Casino Square
            { x: 450, y: 150, speed: 40 },   // Tight hairpin
            { x: 550, y: 180, speed: 90 },   // Portier
            { x: 650, y: 250, speed: 200 },  // Tunnel approach
            { x: 700, y: 350, speed: 250 },  // Tunnel straight
            { x: 650, y: 450, speed: 80 },   // Chicane
            { x: 500, y: 480, speed: 160 },  // Swimming pool
            { x: 350, y: 450, speed: 70 },   // Rascasse
            { x: 200, y: 400, speed: 110 },  // Anthony Noghes
            { x: 100, y: 350, speed: 180 }   // Back to start
        ];
    }

    /**
     * Create Silverstone-style circuit (fast, flowing)
     */
    createSilverstoneShape() {
        return [
            { x: 100, y: 300, speed: 280 },  // Main straight
            { x: 300, y: 250, speed: 200 },  // Turn 1
            { x: 450, y: 150, speed: 180 },  // Maggotts
            { x: 600, y: 120, speed: 240 },  // Becketts
            { x: 700, y: 200, speed: 160 },  // Chapel
            { x: 650, y: 350, speed: 140 },  // Stowe
            { x: 500, y: 450, speed: 120 },  // Vale
            { x: 300, y: 480, speed: 100 },  // Club
            { x: 150, y: 400, speed: 200 },  // Abbey
            { x: 100, y: 350, speed: 250 }   // Farm curve
        ];
    }

    /**
     * Create Monza-style circuit (very fast)
     */
    createMonzaShape() {
        return [
            { x: 100, y: 300, speed: 340 },  // Main straight
            { x: 500, y: 280, speed: 300 },  // Flat out
            { x: 650, y: 200, speed: 80 },   // First chicane
            { x: 680, y: 150, speed: 200 },  // Lesmo 1
            { x: 650, y: 100, speed: 180 },  // Lesmo 2
            { x: 500, y: 80, speed: 240 },   // Back straight start
            { x: 200, y: 100, speed: 320 },  // Back straight
            { x: 100, y: 150, speed: 90 },   // Parabolica entry
            { x: 80, y: 250, speed: 160 },   // Parabolica exit
            { x: 100, y: 280, speed: 280 }   // Main straight approach
        ];
    }

    /**
     * Create generic circuit shape
     */
    createGenericShape() {
        return [
            { x: 100, y: 300, speed: 250 },
            { x: 300, y: 200, speed: 180 },
            { x: 500, y: 150, speed: 120 },
            { x: 650, y: 200, speed: 200 },
            { x: 700, y: 350, speed: 160 },
            { x: 600, y: 450, speed: 140 },
            { x: 400, y: 480, speed: 190 },
            { x: 200, y: 400, speed: 220 },
            { x: 100, y: 350, speed: 240 }
        ];
    }

    /**
     * Calculate track length from points
     */
    calculateTrackLength(points) {
        let length = 0;
        for (let i = 1; i < points.length; i++) {
            const dx = points[i].x - points[i-1].x;
            const dy = points[i].y - points[i-1].y;
            length += Math.sqrt(dx * dx + dy * dy);
        }
        // Convert to approximate real distance (scale factor)
        return (length * 0.008).toFixed(3); // Rough km conversion
    }

    /**
     * Get circuit bounds for scaling
     */
    getCircuitBounds() {
        const points = this.circuitData.points;
        return {
            minX: Math.min(...points.map(p => p.x)),
            maxX: Math.max(...points.map(p => p.x)),
            minY: Math.min(...points.map(p => p.y)),
            maxY: Math.max(...points.map(p => p.y))
        };
    }

    /**
     * Update circuit information display
     */
    updateCircuitInfo() {
        const circuitName = document.getElementById('circuitName');
        const circuitLength = document.getElementById('circuitLength');
        const circuitLaps = document.getElementById('circuitLaps');
        const circuitRecord = document.getElementById('circuitRecord');
        
        if (circuitName) circuitName.textContent = this.circuitData.name;
        if (circuitLength) circuitLength.textContent = `${this.circuitData.length} km`;
        if (circuitLaps) {
            // Estimate lap count based on session type
            const sessionSelect = document.getElementById('mapSessionSelect');
            const session = sessionSelect?.value || 'R';
            const laps = session === 'R' ? Math.floor(300 / parseFloat(this.circuitData.length)) : 
                        session === 'Q' ? 15 : 10;
            circuitLaps.textContent = `${laps} laps`;
        }
        
        // Find fastest lap from session data
        if (circuitRecord && this.currentSessionData?.drivers) {
            const fastestDriver = this.currentSessionData.drivers.reduce((fastest, driver) => {
                if (!fastest.best_lap_time || (driver.best_lap_time && driver.best_lap_time < fastest.best_lap_time)) {
                    return driver;
                }
                return fastest;
            }, this.currentSessionData.drivers[0]);
            
            circuitRecord.textContent = fastestDriver.best_lap_time ? 
                F1Utils.formatTime(fastestDriver.best_lap_time) : '--:--.---';
        }
    }

    /**
     * Setup driver selection checkboxes
     */
    setupDriverSelection() {
        const driverCheckboxes = document.getElementById('driverCheckboxes');
        const driver1Select = document.getElementById('driver1Select');
        const driver2Select = document.getElementById('driver2Select');
        
        if (!driverCheckboxes || !this.currentSessionData?.drivers) return;
        
        driverCheckboxes.innerHTML = '';
        driver1Select.innerHTML = '<option value="">Select Driver 1</option>';
        driver2Select.innerHTML = '<option value="">Select Driver 2</option>';
        
        this.currentSessionData.drivers.forEach(driver => {
            // Checkbox for map display
            const checkbox = document.createElement('div');
            checkbox.className = 'driver-checkbox';
            checkbox.innerHTML = `
                <input type="checkbox" id="driver_${driver.driver_number}" value="${driver.driver_number}">
                <label for="driver_${driver.driver_number}">
                    ${driver.driver_number} ${driver.full_name || 'Unknown'}
                </label>
            `;
            
            const input = checkbox.querySelector('input');
            input.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.selectedDrivers.add(driver.driver_number);
                } else {
                    this.selectedDrivers.delete(driver.driver_number);
                }
                this.updateDriverPositions();
            });
            
            driverCheckboxes.appendChild(checkbox);
            
            // Options for comparison selects
            const option1 = document.createElement('option');
            option1.value = driver.driver_number;
            option1.textContent = `${driver.driver_number} ${driver.full_name || 'Unknown'}`;
            driver1Select.appendChild(option1);
            
            const option2 = document.createElement('option');
            option2.value = driver.driver_number;
            option2.textContent = `${driver.driver_number} ${driver.full_name || 'Unknown'}`;
            driver2Select.appendChild(option2);
        });
        
        // Auto-select top 3 drivers
        const topDrivers = this.currentSessionData.drivers
            .sort((a, b) => (a.position || 999) - (b.position || 999))
            .slice(0, 3);
            
        topDrivers.forEach(driver => {
            const checkbox = document.getElementById(`driver_${driver.driver_number}`);
            if (checkbox) {
                checkbox.checked = true;
                this.selectedDrivers.add(driver.driver_number);
            }
        });
    }

    /**
     * Render the circuit map
     */
    renderCircuitMap() {
        if (!this.circuitData) return;
        
        // Clear previous content
        this.svg.selectAll('g > *').remove();
        
        // Draw circuit track
        this.drawCircuitTrack();
        this.drawSectorMarkers();
        this.updateTelemetryVisualization();
        this.updateDriverPositions();
    }

    /**
     * Draw the circuit track
     */
    drawCircuitTrack() {
        const trackGroup = this.svg.select('#circuitTrack');
        const points = this.circuitData.points;
        
        // Create line generator
        const line = d3.line()
            .x(d => this.scales.x(d.x))
            .y(d => this.scales.y(d.y))
            .curve(d3.curveCatmullRom.alpha(0.5));
        
        // Draw main track
        trackGroup.append('path')
            .datum(points.concat([points[0]])) // Close the circuit
            .attr('class', 'circuit-track')
            .attr('d', line);
        
        // Draw center line
        trackGroup.append('path')
            .datum(points.concat([points[0]]))
            .attr('class', 'circuit-centerline')
            .attr('d', line);
        
        // Draw start/finish line
        const startPoint = points[0];
        trackGroup.append('line')
            .attr('class', 'start-finish-line')
            .attr('x1', this.scales.x(startPoint.x) - 20)
            .attr('y1', this.scales.y(startPoint.y))
            .attr('x2', this.scales.x(startPoint.x) + 20)
            .attr('y2', this.scales.y(startPoint.y));
    }

    /**
     * Draw sector markers
     */
    drawSectorMarkers() {
        const sectorGroup = this.svg.select('#sectorMarkers');
        const points = this.circuitData.points;
        
        this.circuitData.sectors.forEach((sector, index) => {
            const pointIndex = Math.floor(sector.position * points.length);
            const point = points[pointIndex];
            
            // Sector marker
            sectorGroup.append('circle')
                .attr('class', 'sector-marker')
                .attr('cx', this.scales.x(point.x))
                .attr('cy', this.scales.y(point.y))
                .attr('r', 6);
            
            // Sector label
            sectorGroup.append('text')
                .attr('class', 'sector-label')
                .attr('x', this.scales.x(point.x))
                .attr('y', this.scales.y(point.y) - 15)
                .text(`S${index + 1}`);
        });
    }

    /**
     * Update telemetry visualization on track
     */
    updateTelemetryVisualization() {
        const telemetryGroup = this.svg.select('#telemetryData');
        telemetryGroup.selectAll('*').remove();
        
        if (!this.circuitData) return;
        
        const points = this.circuitData.points;
        
        // Draw telemetry-colored segments
        for (let i = 0; i < points.length - 1; i++) {
            const current = points[i];
            const next = points[i + 1];
            
            let segmentClass = '';
            let value = 0;
            
            switch (this.telemetryMode) {
                case 'speed':
                    value = current.speed || 0;
                    segmentClass = value > 200 ? 'speed-high' : 
                                  value > 100 ? 'speed-medium' : 'speed-low';
                    break;
                case 'throttle':
                    value = Math.random(); // Simulated
                    segmentClass = value > 0.8 ? 'throttle-full' : 
                                  value > 0.3 ? 'throttle-partial' : 'throttle-none';
                    break;
                case 'brake':
                    value = (250 - (current.speed || 100)) / 250; // Inverse of speed
                    segmentClass = value > 0.7 ? 'brake-heavy' : 
                                  value > 0.3 ? 'brake-light' : 'brake-none';
                    break;
                case 'gear':
                    value = Math.floor((current.speed || 50) / 40) + 1; // Simulated gear
                    segmentClass = `gear-${Math.min(value, 8)}`;
                    break;
            }
            
            telemetryGroup.append('line')
                .attr('class', `telemetry-segment ${segmentClass}`)
                .attr('x1', this.scales.x(current.x))
                .attr('y1', this.scales.y(current.y))
                .attr('x2', this.scales.x(next.x))
                .attr('y2', this.scales.y(next.y));
        }
    }

    /**
     * Update driver positions on track
     */
    updateDriverPositions() {
        const positionGroup = this.svg.select('#driverPositions');
        positionGroup.selectAll('*').remove();
        
        if (!this.selectedDrivers.size || !this.currentSessionData?.drivers) return;
        
        const selectedDriverData = this.currentSessionData.drivers.filter(driver => 
            this.selectedDrivers.has(driver.driver_number)
        );
        
        selectedDriverData.forEach((driver, index) => {
            // Simulate position on track based on lap progress
            const progress = (this.currentLap - 1 + Math.random()) / 50; // Simulated
            const position = this.getTrackPosition(progress);
            
            const driverGroup = positionGroup.append('g')
                .attr('class', 'driver-marker-group')
                .attr('data-driver', driver.driver_number);
            
            // Driver marker
            driverGroup.append('circle')
                .attr('class', 'driver-marker')
                .attr('cx', this.scales.x(position.x))
                .attr('cy', this.scales.y(position.y))
                .attr('r', 8)
                .attr('fill', this.getDriverColor(driver.driver_number));
            
            // Driver number
            driverGroup.append('text')
                .attr('class', 'driver-number')
                .attr('x', this.scales.x(position.x))
                .attr('y', this.scales.y(position.y))
                .text(driver.driver_number);
        });
    }

    /**
     * Get position on track based on progress (0-1)
     */
    getTrackPosition(progress) {
        const points = this.circuitData.points;
        const totalPoints = points.length;
        const index = (progress * totalPoints) % totalPoints;
        const floorIndex = Math.floor(index);
        const ceilIndex = (floorIndex + 1) % totalPoints;
        const fraction = index - floorIndex;
        
        const current = points[floorIndex];
        const next = points[ceilIndex];
        
        return {
            x: current.x + (next.x - current.x) * fraction,
            y: current.y + (next.y - current.y) * fraction
        };
    }

    /**
     * Get driver color based on driver number
     */
    getDriverColor(driverNumber) {
        const colors = [
            '#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff',
            '#00ffff', '#ffa500', '#800080', '#008000', '#000080',
            '#ff69b4', '#dda0dd', '#98fb98', '#f0e68c', '#deb887'
        ];
        return colors[parseInt(driverNumber) % colors.length];
    }

    /**
     * Setup telemetry charts
     */
    setupTelemetryCharts() {
        this.createSpeedChart();
        this.createThrottleBrakeChart();
        this.createGearChart();
        this.updateSectorAnalysis();
    }

    /**
     * Create speed profile chart
     */
    createSpeedChart() {
        const ctx = document.getElementById('speedChart');
        if (!ctx) return;
        
        const data = this.circuitData.points.map((point, index) => ({
            x: index * 100 / this.circuitData.points.length,
            y: point.speed || 0
        }));
        
        this.charts.speed = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Speed (km/h)',
                    data: data,
                    borderColor: '#00ff00',
                    backgroundColor: 'rgba(0, 255, 0, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Track Position (%)' },
                        grid: { color: 'rgba(255, 255, 255, 0.1)' }
                    },
                    y: {
                        title: { display: true, text: 'Speed (km/h)' },
                        grid: { color: 'rgba(255, 255, 255, 0.1)' }
                    }
                }
            }
        });
    }

    /**
     * Create throttle and brake chart
     */
    createThrottleBrakeChart() {
        const ctx = document.getElementById('throttleBrakeChart');
        if (!ctx) return;
        
        const throttleData = this.circuitData.points.map((point, index) => ({
            x: index * 100 / this.circuitData.points.length,
            y: Math.max(0, ((point.speed || 100) - 50) / 200) // Simulated
        }));
        
        const brakeData = this.circuitData.points.map((point, index) => ({
            x: index * 100 / this.circuitData.points.length,
            y: Math.max(0, (200 - (point.speed || 100)) / 150) // Simulated
        }));
        
        this.charts.throttleBrake = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'Throttle %',
                        data: throttleData,
                        borderColor: '#00ff00',
                        backgroundColor: 'rgba(0, 255, 0, 0.2)',
                        fill: true
                    },
                    {
                        label: 'Brake %',
                        data: brakeData,
                        borderColor: '#ff0000',
                        backgroundColor: 'rgba(255, 0, 0, 0.2)',
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'top' }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Track Position (%)' }
                    },
                    y: {
                        title: { display: true, text: 'Input %' },
                        max: 1
                    }
                }
            }
        });
    }

    /**
     * Create gear chart
     */
    createGearChart() {
        const ctx = document.getElementById('gearChart');
        if (!ctx) return;
        
        const gearData = this.circuitData.points.map((point, index) => ({
            x: index * 100 / this.circuitData.points.length,
            y: Math.min(8, Math.max(1, Math.floor((point.speed || 50) / 40) + 1))
        }));
        
        this.charts.gear = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Gear',
                    data: gearData,
                    borderColor: '#ffff00',
                    backgroundColor: 'rgba(255, 255, 0, 0.1)',
                    stepped: true,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Track Position (%)' }
                    },
                    y: {
                        title: { display: true, text: 'Gear' },
                        min: 1,
                        max: 8,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    }

    /**
     * Update sector analysis
     */
    updateSectorAnalysis() {
        const sectorAnalysis = document.getElementById('sectorAnalysis');
        if (!sectorAnalysis || !this.currentSessionData?.drivers) return;
        
        sectorAnalysis.innerHTML = '';
        
        // Find fastest sector times
        const drivers = this.currentSessionData.drivers;
        
        const fastestSector1 = drivers.reduce((fastest, driver) => {
            if (!fastest.sector1_time || (driver.sector1_time && driver.sector1_time < fastest.sector1_time)) {
                return driver;
            }
            return fastest;
        }, drivers[0]);
        
        const fastestSector2 = drivers.reduce((fastest, driver) => {
            if (!fastest.sector2_time || (driver.sector2_time && driver.sector2_time < fastest.sector2_time)) {
                return driver;
            }
            return fastest;
        }, drivers[0]);
        
        const fastestSector3 = drivers.reduce((fastest, driver) => {
            if (!fastest.sector3_time || (driver.sector3_time && driver.sector3_time < fastest.sector3_time)) {
                return driver;
            }
            return fastest;
        }, drivers[0]);
        
        [
            { name: 'Sector 1', driver: fastestSector1, time: fastestSector1.sector1_time },
            { name: 'Sector 2', driver: fastestSector2, time: fastestSector2.sector2_time },
            { name: 'Sector 3', driver: fastestSector3, time: fastestSector3.sector3_time }
        ].forEach(sector => {
            const sectorData = document.createElement('div');
            sectorData.className = 'sector-data';
            sectorData.innerHTML = `
                <div>
                    <div class="sector-name">${sector.name}</div>
                    <div style="font-size: 0.8rem; color: var(--f1-light-gray);">${sector.driver.full_name || 'Unknown'}</div>
                </div>
                <div class="sector-time fastest">${sector.time ? F1Utils.formatSectorTime(sector.time) : '--.-'}</div>
            `;
            sectorAnalysis.appendChild(sectorData);
        });
    }

    /**
     * Animation controls
     */
    playAnimation() {
        this.isAnimating = true;
        document.getElementById('playAnimation').style.display = 'none';
        document.getElementById('pauseAnimation').style.display = 'flex';
        
        const animate = () => {
            if (!this.isAnimating) return;
            
            this.currentLap += 0.02; // Slow progression
            const maxLaps = 50;
            
            if (this.currentLap > maxLaps) {
                this.currentLap = 1;
            }
            
            this.updateAnimationDisplay();
            this.updateDriverPositions();
            
            this.animationFrame = requestAnimationFrame(animate);
        };
        
        animate();
    }

    pauseAnimation() {
        this.isAnimating = false;
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
        
        document.getElementById('playAnimation').style.display = 'flex';
        document.getElementById('pauseAnimation').style.display = 'none';
    }

    resetAnimation() {
        this.pauseAnimation();
        this.currentLap = 1;
        this.updateAnimationDisplay();
        this.updateDriverPositions();
    }

    setAnimationPosition(value) {
        this.currentLap = 1 + (value / 100) * 49; // Scale to 1-50 laps
        this.updateAnimationDisplay();
        this.updateDriverPositions();
    }

    updateAnimationDisplay() {
        const lapSlider = document.getElementById('lapSlider');
        const currentLapNumber = document.getElementById('currentLapNumber');
        const lapProgress = document.getElementById('lapProgress');
        
        if (lapSlider) {
            lapSlider.value = ((this.currentLap - 1) / 49) * 100;
        }
        
        if (currentLapNumber) {
            currentLapNumber.textContent = Math.floor(this.currentLap);
        }
        
        if (lapProgress) {
            const progress = ((this.currentLap % 1) * 100).toFixed(1);
            lapProgress.textContent = `${progress}%`;
        }
    }

    /**
     * Compare drivers
     */
    async compareDrivers() {
        const driver1Select = document.getElementById('driver1Select');
        const driver2Select = document.getElementById('driver2Select');
        const comparisonResults = document.getElementById('comparisonResults');
        
        if (!driver1Select?.value || !driver2Select?.value) {
            this.showError('Please select two drivers to compare');
            return;
        }
        
        const driver1Data = this.currentSessionData.drivers.find(d => d.driver_number === driver1Select.value);
        const driver2Data = this.currentSessionData.drivers.find(d => d.driver_number === driver2Select.value);
        
        if (!driver1Data || !driver2Data) {
            this.showError('Driver data not found');
            return;
        }
        
        // Update comparison display
        document.getElementById('driver1Name').textContent = driver1Data.full_name || 'Driver 1';
        document.getElementById('driver2Name').textContent = driver2Data.full_name || 'Driver 2';
        
        document.getElementById('driver1BestLap').textContent = 
            driver1Data.best_lap_time ? F1Utils.formatTime(driver1Data.best_lap_time) : '--:--.---';
        document.getElementById('driver2BestLap').textContent = 
            driver2Data.best_lap_time ? F1Utils.formatTime(driver2Data.best_lap_time) : '--:--.---';
        
        // Simulated additional metrics
        document.getElementById('driver1AvgSpeed').textContent = `${Math.floor(180 + Math.random() * 40)} km/h`;
        document.getElementById('driver2AvgSpeed').textContent = `${Math.floor(180 + Math.random() * 40)} km/h`;
        
        document.getElementById('driver1TopSpeed').textContent = `${Math.floor(300 + Math.random() * 50)} km/h`;
        document.getElementById('driver2TopSpeed').textContent = `${Math.floor(300 + Math.random() * 50)} km/h`;
        
        comparisonResults.style.display = 'block';
        
        // Create comparison chart
        this.createComparisonChart(driver1Data, driver2Data);
    }

    /**
     * Create driver comparison chart
     */
    createComparisonChart(driver1, driver2) {
        const ctx = document.getElementById('comparisonChart');
        if (!ctx) return;
        
        if (this.charts.comparison) {
            this.charts.comparison.destroy();
        }
        
        const sectors = ['Sector 1', 'Sector 2', 'Sector 3'];
        const driver1Times = [
            driver1.sector1_time || 25 + Math.random() * 5,
            driver1.sector2_time || 30 + Math.random() * 8,
            driver1.sector3_time || 28 + Math.random() * 6
        ];
        const driver2Times = [
            driver2.sector1_time || 25 + Math.random() * 5,
            driver2.sector2_time || 30 + Math.random() * 8,
            driver2.sector3_time || 28 + Math.random() * 6
        ];
        
        this.charts.comparison = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: sectors,
                datasets: [
                    {
                        label: driver1.full_name || 'Driver 1',
                        data: driver1Times,
                        backgroundColor: 'rgba(255, 0, 0, 0.6)',
                        borderColor: '#ff0000',
                        borderWidth: 2
                    },
                    {
                        label: driver2.full_name || 'Driver 2',
                        data: driver2Times,
                        backgroundColor: 'rgba(0, 0, 255, 0.6)',
                        borderColor: '#0000ff',
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'top' },
                    title: { display: true, text: 'Sector Time Comparison' }
                },
                scales: {
                    y: {
                        title: { display: true, text: 'Time (seconds)' },
                        beginAtZero: false
                    }
                }
            }
        });
    }

    /**
     * Utility methods
     */
    showContent() {
        const content = document.getElementById('circuitMapContent');
        if (content) content.style.display = 'block';
    }

    showLoading() {
        const loading = document.getElementById('circuitMapLoading');
        if (loading) loading.style.display = 'block';
    }

    hideLoading() {
        const loading = document.getElementById('circuitMapLoading');
        if (loading) loading.style.display = 'none';
    }

    showError(message) {
        const errorContainer = document.getElementById('circuitMapError');
        const errorText = document.querySelector('#circuitMapError .error-text');
        
        if (errorContainer && errorText) {
            errorText.textContent = message;
            errorContainer.style.display = 'block';
            
            setTimeout(() => {
                errorContainer.style.display = 'none';
            }, 5000);
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname === '/circuit-map') {
        window.F1CircuitMap = new F1CircuitMap();
        
        // Auto-load events for current season
        if (window.F1CircuitMap) {
            window.F1CircuitMap.loadEvents();
        }
    }
});