/**
 * F1 Analytics Charts - Chart.js Implementation
 * Handles all chart visualizations for the F1 dashboard
 */

class F1Charts {
    constructor() {
        this.charts = {};
        this.defaultOptions = this.getDefaultChartOptions();
    }

    /**
     * Get default Chart.js options with F1 styling
     */
    getDefaultChartOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#ffffff',
                        font: {
                            family: 'Inter, sans-serif',
                            size: 12,
                            weight: '600'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#cccccc',
                    borderColor: '#ff0000',
                    borderWidth: 1,
                    cornerRadius: 8,
                    titleFont: {
                        family: 'Inter, sans-serif',
                        size: 14,
                        weight: '700'
                    },
                    bodyFont: {
                        family: 'Fira Code, monospace',
                        size: 12
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: '#cccccc',
                        font: {
                            family: 'Fira Code, monospace',
                            size: 11
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)',
                        borderColor: 'rgba(255, 255, 255, 0.2)'
                    }
                },
                y: {
                    ticks: {
                        color: '#cccccc',
                        font: {
                            family: 'Fira Code, monospace',
                            size: 11
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)',
                        borderColor: 'rgba(255, 255, 255, 0.2)'
                    }
                }
            }
        };
    }

    /**
     * Create lap times evolution chart
     */
    createLapTimesChart(lapData) {
        const ctx = document.getElementById('lapTimesChart');
        if (!ctx || !lapData || lapData.length === 0) return;

        // Destroy existing chart
        if (this.charts.lapTimes) {
            this.charts.lapTimes.destroy();
        }

        // Prepare data
        const validLaps = lapData.filter(lap => lap.LapTime > 0);
        const labels = validLaps.map(lap => lap.LapNumber);
        const lapTimes = validLaps.map(lap => lap.LapTime);
        const personalBests = validLaps.map(lap => lap.IsPersonalBest ? lap.LapTime : null);

        // Color points based on tyre compound
        const pointColors = validLaps.map(lap => this.getTyreColor(lap.Compound));
        const borderColors = validLaps.map(lap => lap.IsPersonalBest ? '#ffd700' : this.getTyreColor(lap.Compound));

        const config = {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Lap Times',
                        data: lapTimes,
                        borderColor: '#ff0000',
                        backgroundColor: pointColors,
                        pointBackgroundColor: pointColors,
                        pointBorderColor: borderColors,
                        pointBorderWidth: 2,
                        pointRadius: 6,
                        pointHoverRadius: 8,
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'Personal Bests',
                        data: personalBests,
                        borderColor: '#ffd700',
                        backgroundColor: '#ffd700',
                        pointBackgroundColor: '#ffd700',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        pointRadius: 8,
                        pointHoverRadius: 10,
                        borderWidth: 0,
                        fill: false,
                        showLine: false
                    }
                ]
            },
            options: {
                ...this.defaultOptions,
                plugins: {
                    ...this.defaultOptions.plugins,
                    title: {
                        display: false
                    },
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: {
                            title: (context) => `Lap ${context[0].label}`,
                            label: (context) => {
                                const lap = validLaps[context.dataIndex];
                                if (context.datasetIndex === 0) {
                                    return [
                                        `Time: ${lap.LapTimeFormatted}`,
                                        `Compound: ${lap.Compound}`,
                                        `Tyre Age: ${lap.TyreLife} laps`,
                                        `Position: ${lap.Position || 'N/A'}`
                                    ];
                                } else {
                                    return `Personal Best: ${lap.LapTimeFormatted}`;
                                }
                            }
                        }
                    }
                },
                scales: {
                    ...this.defaultOptions.scales,
                    x: {
                        ...this.defaultOptions.scales.x,
                        title: {
                            display: true,
                            text: 'Lap Number',
                            color: '#ffffff',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 14,
                                weight: '600'
                            }
                        }
                    },
                    y: {
                        ...this.defaultOptions.scales.y,
                        title: {
                            display: true,
                            text: 'Lap Time (seconds)',
                            color: '#ffffff',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 14,
                                weight: '600'
                            }
                        },
                        ticks: {
                            ...this.defaultOptions.scales.y.ticks,
                            callback: function(value) {
                                return F1Utils.formatTime(value);
                            }
                        }
                    }
                }
            }
        };

        this.charts.lapTimes = new Chart(ctx, config);
    }

    /**
     * Create sector times analysis chart
     */
    createSectorTimesChart(lapData) {
        const ctx = document.getElementById('sectorTimesChart');
        if (!ctx || !lapData || lapData.length === 0) return;

        // Destroy existing chart
        if (this.charts.sectorTimes) {
            this.charts.sectorTimes.destroy();
        }

        // Prepare data - get best sector times
        const validLaps = lapData.filter(lap => 
            lap.Sector1Time > 0 && lap.Sector2Time > 0 && lap.Sector3Time > 0
        );

        if (validLaps.length === 0) return;

        const bestS1 = Math.min(...validLaps.map(lap => lap.Sector1Time));
        const bestS2 = Math.min(...validLaps.map(lap => lap.Sector2Time));
        const bestS3 = Math.min(...validLaps.map(lap => lap.Sector3Time));
        
        const avgS1 = validLaps.reduce((sum, lap) => sum + lap.Sector1Time, 0) / validLaps.length;
        const avgS2 = validLaps.reduce((sum, lap) => sum + lap.Sector2Time, 0) / validLaps.length;
        const avgS3 = validLaps.reduce((sum, lap) => sum + lap.Sector3Time, 0) / validLaps.length;

        const config = {
            type: 'bar',
            data: {
                labels: ['Sector 1', 'Sector 2', 'Sector 3'],
                datasets: [
                    {
                        label: 'Best Times',
                        data: [bestS1, bestS2, bestS3],
                        backgroundColor: ['#ff0000', '#ff3333', '#ff6666'],
                        borderColor: ['#cc0000', '#cc0000', '#cc0000'],
                        borderWidth: 2,
                        borderRadius: 8,
                        borderSkipped: false
                    },
                    {
                        label: 'Average Times',
                        data: [avgS1, avgS2, avgS3],
                        backgroundColor: ['rgba(255, 0, 0, 0.3)', 'rgba(255, 51, 51, 0.3)', 'rgba(255, 102, 102, 0.3)'],
                        borderColor: ['#ff0000', '#ff3333', '#ff6666'],
                        borderWidth: 1,
                        borderRadius: 8,
                        borderSkipped: false
                    }
                ]
            },
            options: {
                ...this.defaultOptions,
                plugins: {
                    ...this.defaultOptions.plugins,
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: {
                            label: (context) => {
                                const value = context.raw;
                                const label = context.dataset.label;
                                return `${label}: ${F1Utils.formatSectorTime(value)}`;
                            }
                        }
                    }
                },
                scales: {
                    ...this.defaultOptions.scales,
                    x: {
                        ...this.defaultOptions.scales.x,
                        title: {
                            display: true,
                            text: 'Track Sectors',
                            color: '#ffffff',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 14,
                                weight: '600'
                            }
                        }
                    },
                    y: {
                        ...this.defaultOptions.scales.y,
                        title: {
                            display: true,
                            text: 'Time (seconds)',
                            color: '#ffffff',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 14,
                                weight: '600'
                            }
                        },
                        ticks: {
                            ...this.defaultOptions.scales.y.ticks,
                            callback: function(value) {
                                return F1Utils.formatSectorTime(value);
                            }
                        }
                    }
                }
            }
        };

        this.charts.sectorTimes = new Chart(ctx, config);
    }

    /**
     * Create speed analysis chart
     */
    createSpeedChart(lapData) {
        const ctx = document.getElementById('speedChart');
        if (!ctx || !lapData || lapData.length === 0) return;

        // Destroy existing chart
        if (this.charts.speed) {
            this.charts.speed.destroy();
        }

        // Prepare data
        const validLaps = lapData.filter(lap => lap.MaxSpeed > 0 && lap.AvgSpeed > 0);
        
        if (validLaps.length === 0) return;

        const labels = validLaps.map(lap => lap.LapNumber);
        const maxSpeeds = validLaps.map(lap => lap.MaxSpeed);
        const avgSpeeds = validLaps.map(lap => lap.AvgSpeed);

        const config = {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Max Speed',
                        data: maxSpeeds,
                        borderColor: '#ff0000',
                        backgroundColor: 'rgba(255, 0, 0, 0.1)',
                        pointBackgroundColor: '#ff0000',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        borderWidth: 3,
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'Average Speed',
                        data: avgSpeeds,
                        borderColor: '#ffff00',
                        backgroundColor: 'rgba(255, 255, 0, 0.1)',
                        pointBackgroundColor: '#ffff00',
                        pointBorderColor: '#000000',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        borderWidth: 2,
                        fill: false,
                        tension: 0.1
                    }
                ]
            },
            options: {
                ...this.defaultOptions,
                plugins: {
                    ...this.defaultOptions.plugins,
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: {
                            title: (context) => `Lap ${context[0].label}`,
                            label: (context) => {
                                const value = context.raw;
                                const label = context.dataset.label;
                                return `${label}: ${value.toFixed(1)} km/h`;
                            }
                        }
                    }
                },
                scales: {
                    ...this.defaultOptions.scales,
                    x: {
                        ...this.defaultOptions.scales.x,
                        title: {
                            display: true,
                            text: 'Lap Number',
                            color: '#ffffff',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 14,
                                weight: '600'
                            }
                        }
                    },
                    y: {
                        ...this.defaultOptions.scales.y,
                        title: {
                            display: true,
                            text: 'Speed (km/h)',
                            color: '#ffffff',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 14,
                                weight: '600'
                            }
                        },
                        ticks: {
                            ...this.defaultOptions.scales.y.ticks,
                            callback: function(value) {
                                return value.toFixed(0) + ' km/h';
                            }
                        }
                    }
                }
            }
        };

        this.charts.speed = new Chart(ctx, config);
    }

    /**
     * Create tyre strategy chart
     */
    createTyreChart(lapData) {
        const ctx = document.getElementById('tyreChart');
        if (!ctx || !lapData || lapData.length === 0) return;

        // Destroy existing chart
        if (this.charts.tyre) {
            this.charts.tyre.destroy();
        }

        // Prepare data - group by stint and compound
        const stints = {};
        lapData.forEach(lap => {
            const stintKey = `${lap.Stint}_${lap.Compound}`;
            if (!stints[stintKey]) {
                stints[stintKey] = {
                    stint: lap.Stint,
                    compound: lap.Compound,
                    laps: [],
                    startLap: lap.LapNumber,
                    endLap: lap.LapNumber
                };
            }
            stints[stintKey].laps.push(lap);
            stints[stintKey].endLap = Math.max(stints[stintKey].endLap, lap.LapNumber);
        });

        // Create datasets for each compound
        const compounds = [...new Set(lapData.map(lap => lap.Compound))];
        const datasets = compounds.map(compound => {
            const compoundLaps = lapData.filter(lap => lap.Compound === compound);
            const data = compoundLaps.map(lap => ({
                x: lap.LapNumber,
                y: lap.TyreLife
            }));

            return {
                label: compound,
                data: data,
                backgroundColor: this.getTyreColor(compound),
                borderColor: this.getTyreColor(compound),
                pointBackgroundColor: this.getTyreColor(compound),
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8,
                borderWidth: 2,
                fill: false,
                tension: 0
            };
        });

        const config = {
            type: 'scatter',
            data: {
                datasets: datasets
            },
            options: {
                ...this.defaultOptions,
                plugins: {
                    ...this.defaultOptions.plugins,
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: {
                            title: (context) => {
                                const point = context[0];
                                return `Lap ${point.parsed.x}`;
                            },
                            label: (context) => {
                                const point = context.parsed;
                                return [
                                    `Compound: ${context.dataset.label}`,
                                    `Tyre Age: ${point.y} laps`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    ...this.defaultOptions.scales,
                    x: {
                        ...this.defaultOptions.scales.x,
                        type: 'linear',
                        position: 'bottom',
                        title: {
                            display: true,
                            text: 'Lap Number',
                            color: '#ffffff',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 14,
                                weight: '600'
                            }
                        }
                    },
                    y: {
                        ...this.defaultOptions.scales.y,
                        title: {
                            display: true,
                            text: 'Tyre Age (laps)',
                            color: '#ffffff',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 14,
                                weight: '600'
                            }
                        },
                        ticks: {
                            ...this.defaultOptions.scales.y.ticks,
                            callback: function(value) {
                                return value + ' laps';
                            }
                        }
                    }
                }
            }
        };

        this.charts.tyre = new Chart(ctx, config);
    }

    /**
     * Create comparison lap times chart for multiple drivers
     */
    createComparisonLapChart(comparisonData) {
        const ctx = document.getElementById('comparisonLapChart');
        if (!ctx || !comparisonData) return;

        // Destroy existing chart
        if (this.charts.comparisonLap) {
            this.charts.comparisonLap.destroy();
        }

        const datasets = [];
        const colors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff'];
        let colorIndex = 0;

        Object.entries(comparisonData).forEach(([driverNumber, data]) => {
            if (data.error || !data.lap_data) return;

            const validLaps = data.lap_data.filter(lap => lap.LapTime > 0);
            const lapTimes = validLaps.map(lap => ({
                x: lap.LapNumber,
                y: lap.LapTime
            }));

            datasets.push({
                label: `#${driverNumber} ${data.driver_info?.abbreviation || ''}`,
                data: lapTimes,
                borderColor: colors[colorIndex % colors.length],
                backgroundColor: colors[colorIndex % colors.length] + '33',
                pointBackgroundColor: colors[colorIndex % colors.length],
                pointBorderColor: '#ffffff',
                pointBorderWidth: 1,
                pointRadius: 4,
                pointHoverRadius: 6,
                borderWidth: 2,
                fill: false,
                tension: 0.1
            });

            colorIndex++;
        });

        const config = {
            type: 'line',
            data: { datasets },
            options: {
                ...this.defaultOptions,
                plugins: {
                    ...this.defaultOptions.plugins,
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: {
                            title: (context) => `Lap ${context[0].parsed.x}`,
                            label: (context) => {
                                const time = context.parsed.y;
                                return `${context.dataset.label}: ${F1Utils.formatTime(time)}`;
                            }
                        }
                    }
                },
                scales: {
                    ...this.defaultOptions.scales,
                    x: {
                        ...this.defaultOptions.scales.x,
                        type: 'linear',
                        position: 'bottom',
                        title: {
                            display: true,
                            text: 'Lap Number',
                            color: '#ffffff',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 14,
                                weight: '600'
                            }
                        }
                    },
                    y: {
                        ...this.defaultOptions.scales.y,
                        title: {
                            display: true,
                            text: 'Lap Time',
                            color: '#ffffff',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 14,
                                weight: '600'
                            }
                        },
                        ticks: {
                            ...this.defaultOptions.scales.y.ticks,
                            callback: function(value) {
                                return F1Utils.formatTime(value);
                            }
                        }
                    }
                }
            }
        };

        this.charts.comparisonLap = new Chart(ctx, config);
    }

    /**
     * Create best lap times comparison bar chart
     */
    createBestLapComparisonChart(comparisonData) {
        const ctx = document.getElementById('bestLapComparisonChart');
        if (!ctx || !comparisonData) return;

        // Destroy existing chart
        if (this.charts.bestLapComparison) {
            this.charts.bestLapComparison.destroy();
        }

        const drivers = [];
        const bestTimes = [];
        const colors = [];

        Object.entries(comparisonData).forEach(([driverNumber, data]) => {
            if (data.error || !data.statistics) return;

            drivers.push(`#${driverNumber} ${data.driver_info?.abbreviation || ''}`);
            bestTimes.push(data.statistics.best_lap_time || 0);
            colors.push(`hsl(${Math.random() * 360}, 70%, 50%)`);
        });

        const config = {
            type: 'bar',
            data: {
                labels: drivers,
                datasets: [{
                    label: 'Best Lap Time',
                    data: bestTimes,
                    backgroundColor: colors,
                    borderColor: colors.map(color => color.replace('50%', '70%')),
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false
                }]
            },
            options: {
                ...this.defaultOptions,
                indexAxis: 'y',
                plugins: {
                    ...this.defaultOptions.plugins,
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: {
                            label: (context) => {
                                const time = context.raw;
                                return `Best Lap: ${F1Utils.formatTime(time)}`;
                            }
                        }
                    }
                },
                scales: {
                    ...this.defaultOptions.scales,
                    x: {
                        ...this.defaultOptions.scales.x,
                        title: {
                            display: true,
                            text: 'Lap Time',
                            color: '#ffffff',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 14,
                                weight: '600'
                            }
                        },
                        ticks: {
                            ...this.defaultOptions.scales.x.ticks,
                            callback: function(value) {
                                return F1Utils.formatTime(value);
                            }
                        }
                    },
                    y: {
                        ...this.defaultOptions.scales.y,
                        title: {
                            display: true,
                            text: 'Drivers',
                            color: '#ffffff',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 14,
                                weight: '600'
                            }
                        }
                    }
                }
            }
        };

        this.charts.bestLapComparison = new Chart(ctx, config);
    }

    /**
     * Create sector comparison chart
     */
    createSectorComparisonChart(comparisonData) {
        const ctx = document.getElementById('sectorComparisonChart');
        if (!ctx || !comparisonData) return;

        // Destroy existing chart
        if (this.charts.sectorComparison) {
            this.charts.sectorComparison.destroy();
        }

        const drivers = [];
        const sector1Data = [];
        const sector2Data = [];
        const sector3Data = [];

        Object.entries(comparisonData).forEach(([driverNumber, data]) => {
            if (data.error || !data.lap_data) return;

            const validLaps = data.lap_data.filter(lap => 
                lap.Sector1Time > 0 && lap.Sector2Time > 0 && lap.Sector3Time > 0
            );

            if (validLaps.length === 0) return;

            drivers.push(`#${driverNumber}`);
            sector1Data.push(Math.min(...validLaps.map(lap => lap.Sector1Time)));
            sector2Data.push(Math.min(...validLaps.map(lap => lap.Sector2Time)));
            sector3Data.push(Math.min(...validLaps.map(lap => lap.Sector3Time)));
        });

        const config = {
            type: 'bar',
            data: {
                labels: drivers,
                datasets: [
                    {
                        label: 'Sector 1',
                        data: sector1Data,
                        backgroundColor: '#ff0000',
                        borderColor: '#cc0000',
                        borderWidth: 2,
                        borderRadius: 8,
                        borderSkipped: false
                    },
                    {
                        label: 'Sector 2',
                        data: sector2Data,
                        backgroundColor: '#ffff00',
                        borderColor: '#cccc00',
                        borderWidth: 2,
                        borderRadius: 8,
                        borderSkipped: false
                    },
                    {
                        label: 'Sector 3',
                        data: sector3Data,
                        backgroundColor: '#00ff00',
                        borderColor: '#00cc00',
                        borderWidth: 2,
                        borderRadius: 8,
                        borderSkipped: false
                    }
                ]
            },
            options: {
                ...this.defaultOptions,
                plugins: {
                    ...this.defaultOptions.plugins,
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: {
                            label: (context) => {
                                const time = context.raw;
                                return `${context.dataset.label}: ${F1Utils.formatSectorTime(time)}`;
                            }
                        }
                    }
                },
                scales: {
                    ...this.defaultOptions.scales,
                    x: {
                        ...this.defaultOptions.scales.x,
                        title: {
                            display: true,
                            text: 'Drivers',
                            color: '#ffffff',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 14,
                                weight: '600'
                            }
                        }
                    },
                    y: {
                        ...this.defaultOptions.scales.y,
                        title: {
                            display: true,
                            text: 'Sector Time (seconds)',
                            color: '#ffffff',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 14,
                                weight: '600'
                            }
                        },
                        ticks: {
                            ...this.defaultOptions.scales.y.ticks,
                            callback: function(value) {
                                return F1Utils.formatSectorTime(value);
                            }
                        }
                    }
                }
            }
        };

        this.charts.sectorComparison = new Chart(ctx, config);
    }

    /**
     * Create speed comparison chart
     */
    createSpeedComparisonChart(comparisonData) {
        const ctx = document.getElementById('speedComparisonChart');
        if (!ctx || !comparisonData) return;

        // Destroy existing chart
        if (this.charts.speedComparison) {
            this.charts.speedComparison.destroy();
        }

        const drivers = [];
        const maxSpeedData = [];
        const avgSpeedData = [];

        Object.entries(comparisonData).forEach(([driverNumber, data]) => {
            if (data.error || !data.lap_data) return;

            const validLaps = data.lap_data.filter(lap => lap.MaxSpeed > 0 && lap.AvgSpeed > 0);
            
            if (validLaps.length === 0) return;

            drivers.push(`#${driverNumber}`);
            maxSpeedData.push(Math.max(...validLaps.map(lap => lap.MaxSpeed)));
            avgSpeedData.push(validLaps.reduce((sum, lap) => sum + lap.AvgSpeed, 0) / validLaps.length);
        });

        const config = {
            type: 'bar',
            data: {
                labels: drivers,
                datasets: [
                    {
                        label: 'Max Speed',
                        data: maxSpeedData,
                        backgroundColor: '#ff0000',
                        borderColor: '#cc0000',
                        borderWidth: 2,
                        borderRadius: 8,
                        borderSkipped: false
                    },
                    {
                        label: 'Average Speed',
                        data: avgSpeedData,
                        backgroundColor: '#ffff00',
                        borderColor: '#cccc00',
                        borderWidth: 2,
                        borderRadius: 8,
                        borderSkipped: false
                    }
                ]
            },
            options: {
                ...this.defaultOptions,
                plugins: {
                    ...this.defaultOptions.plugins,
                    tooltip: {
                        ...this.defaultOptions.plugins.tooltip,
                        callbacks: {
                            label: (context) => {
                                const speed = context.raw;
                                return `${context.dataset.label}: ${speed.toFixed(1)} km/h`;
                            }
                        }
                    }
                },
                scales: {
                    ...this.defaultOptions.scales,
                    x: {
                        ...this.defaultOptions.scales.x,
                        title: {
                            display: true,
                            text: 'Drivers',
                            color: '#ffffff',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 14,
                                weight: '600'
                            }
                        }
                    },
                    y: {
                        ...this.defaultOptions.scales.y,
                        title: {
                            display: true,
                            text: 'Speed (km/h)',
                            color: '#ffffff',
                            font: {
                                family: 'Inter, sans-serif',
                                size: 14,
                                weight: '600'
                            }
                        },
                        ticks: {
                            ...this.defaultOptions.scales.y.ticks,
                            callback: function(value) {
                                return value.toFixed(0) + ' km/h';
                            }
                        }
                    }
                }
            }
        };

        this.charts.speedComparison = new Chart(ctx, config);
    }

    /**
     * Get tyre compound color
     */
    getTyreColor(compound) {
        const colors = {
            'SOFT': '#ff0000',
            'MEDIUM': '#ffff00',
            'HARD': '#ffffff',
            'INTERMEDIATE': '#00ff00',
            'WET': '#0000ff',
            'UNKNOWN': '#cccccc'
        };
        return colors[compound] || '#cccccc';
    }

    /**
     * Destroy all charts
     */
    destroyAllCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};
    }

    /**
     * Resize all charts
     */
    resizeAllCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.resize === 'function') {
                chart.resize();
            }
        });
    }
}

// Make F1Charts globally available
window.F1Charts = new F1Charts();

// Handle window resize
window.addEventListener('resize', F1Utils.debounce(() => {
    window.F1Charts.resizeAllCharts();
}, 250));

// Clean up charts when page unloads
window.addEventListener('beforeunload', () => {
    window.F1Charts.destroyAllCharts();
});
