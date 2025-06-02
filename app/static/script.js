const sensorTable = document.getElementById('sensorTable');
const sensorTableBody = sensorTable ? sensorTable.querySelector('tbody') : null;
const logDiv = document.getElementById('apiLogs');
const sensorChartCanvas = document.getElementById('sensorChart');
const intervalSelect = document.getElementById('intervalSelect');
const aiResult = document.getElementById('aiResult');
const startAIBtn = document.getElementById('startAIBtn');

let ws = null;
let lastTimestamp = null;
let activeSensors = new Set();
let isAIRunning = false;

function formatTimestampWIB(isoTimestamp) {
    try {
        const date = new Date(isoTimestamp);
        if (isNaN(date.getTime())) throw new Error("Invalid timestamp");
        const options = {
            timeZone: 'Asia/Jakarta',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        };
        const formatter = new Intl.DateTimeFormat('id-ID', options);
        const parts = formatter.formatToParts(date);
        return `${parts[4].value}/${parts[2].value}/${parts[0].value} ${parts[6].value}:${parts[8].value}:${parts[10].value} WIB`;
    } catch (err) {
        console.error('Error formatting timestamp:', err);
        return '-';
    }
}

function formatTimeWIB(isoTimestamp) {
    try {
        const time = new Date(isoTimestamp);
        if (isNaN(time.getTime())) throw new Error("Invalid timestamp");
        const options = {
            timeZone: 'Asia/Jakarta',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        };
        const formatter = new Intl.DateTimeFormat('id-ID', options);
        const parts = formatter.formatToParts(time);
        return `${parts[0].value}:${parts[2].value}:${parts[4].value} WIB`;
    } catch (err) {
        console.error('Error formatting time:', err);
        return '-';
    }
}

function initializeIntervalSelect() {
    if (!intervalSelect) {
        console.error('Interval select not found');
        return;
    }
    const expectedOptions = [
        { value: '3s', text: '3 detik' },
        { value: '10s', text: '10 detik' },
        { value: '30s', text: '30 detik' },
        { value: '1min', text: '1 menit' },
        { value: '5min', text: '5 menit' }
    ];
    const currentOptions = Array.from(intervalSelect.options).map(opt => opt.value);
    if (currentOptions.length < expectedOptions.length || !currentOptions.includes('10s')) {
        intervalSelect.innerHTML = '';
        expectedOptions.forEach(opt => {
            const option = document.createElement('option');
            option.value = opt.value;
            option.textContent = opt.text;
            if (opt.value === '3s') option.selected = true;
            intervalSelect.appendChild(option);
        });
        log('Initialized interval options: 3s, 10s, 30s, 1min, 5min');
    }
}

const maxDataPoints = 1200;
const chartData = {
    labels: [],
    datasets: [
        { label: 'MQ135', data: [], borderColor: '#3498db', backgroundColor: 'rgba(52, 152, 219, 0.2)', fill: false, tension: 0.3, pointRadius: 3, hidden: false },
        { label: 'MQ2', data: [], borderColor: '#e74c3c', backgroundColor: 'rgba(231, 76, 60, 0.2)', fill: false, tension: 0.3, pointRadius: 3, hidden: false },
        { label: 'MQ4', data: [], borderColor: '#2ecc71', backgroundColor: 'rgba(46, 204, 113, 0.2)', fill: false, tension: 0.3, pointRadius: 3, hidden: false },
        { label: 'MQ7', data: [], borderColor: '#f1c40f', backgroundColor: 'rgba(241, 196, 15, 0.2)', fill: false, tension: 0.3, pointRadius: 3, hidden: false },
    ]
};

const sensorChart = new Chart(sensorChartCanvas, {
    type: 'line',
    data: chartData,
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: {
                title: { display: true, text: 'Time (WIB)', color: '#2c3e50', font: { size: 14, weight: 'bold' } },
                ticks: { color: '#34495e', maxRotation: 45, minRotation: 45, maxTicksLimit: 20, callback: function(value) { return formatTimeWIB(chartData.labels[value]); } },
                grid: { display: false }
            },
            y: {
                title: { display: true, text: 'Sensor Value', color: '#2c3e50', font: { size: 14, weight: 'bold' } },
                ticks: { color: '#34495e' },
                grid: { color: '#e0e0e0' },
                beginAtZero: true,
                max: 5,
                ticks: { stepSize: 0.5 }
            }
        },
        plugins: {
            legend: { display: true, position: 'top', labels: { color: '#2c3e50', font: { size: 12 }, usePointStyle: true } },
            tooltip: {
                backgroundColor: '#2c3e50',
                titleColor: '#ffffff',
                bodyColor: '#ffffff',
                borderColor: '#3498db',
                borderWidth: 1,
                callbacks: { title: function(tooltipItems) { return formatTimeWIB(chartData.labels[tooltipItems[0].dataIndex]); } }
            }
        },
        animation: { duration: 500 }
    }
});

function updateChartVisibility() {
    chartData.datasets.forEach(dataset => {
        dataset.hidden = !activeSensors.has(dataset.label.toLowerCase()) && !activeSensors.has('all');
    });
    sensorChart.update();
    console.log(`Chart visibility updated, active sensors: ${Array.from(activeSensors)}`);
}

function log(message) {
    if (!logDiv) {
        console.error('Log div not found');
        return;
    }
    const logEntry = document.createElement('div');
    logEntry.textContent = `[${formatTimestampWIB(new Date())}] ${message}`;
    logDiv.prepend(logEntry);
    logDiv.scrollTop = 0;
}

function showColumns() {
    if (!sensorTable) {
        console.error('Sensor table not found');
        return;
    }
    const headers = sensorTable.querySelectorAll('th');
    headers.forEach(th => th.style.display = '');
    sensorTableBody?.querySelectorAll('tr').forEach(row => {
        row.querySelectorAll('td').forEach(td => td.style.display = '');
    });
}

async function fetchChartData(interval) {
    try {
        chartData.labels = [];
        chartData.datasets.forEach(dataset => dataset.data = []);
        if (sensorTableBody) sensorTableBody.innerHTML = '';
        sensorChart.update();

        const response = await fetch(`/sensor/data/db/${interval}`);
        if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
        const data = await response.json();
        if (data.length === 0) {
            log(`No data for interval ${interval}`);
            return;
        }

        chartData.labels = data.map(d => d.timestamp);
        chartData.datasets[0].data = data.map(d => ({ x: d.timestamp, y: d.mq135 || 0 }));
        chartData.datasets[1].data = data.map(d => ({ x: d.timestamp, y: d.mq2 || 0 }));
        chartData.datasets[2].data = data.map(d => ({ x: d.timestamp, y: d.mq4 || 0 }));
        chartData.datasets[3].data = data.map(d => ({ x: d.timestamp, y: d.mq7 || 0 }));

        updateChartVisibility();
        sensorChart.update();
        log(`Chart updated for interval ${interval}`);
    } catch (err) {
        console.error('Error fetching chart data:', err);
        log(`Error fetching chart data: ${err.message}`);
    }
}

function formatComposition(composition) {
    if (!composition) {
        console.log('No composition data');
        return '-';
    }
    if (typeof composition === 'string') return composition;
    if (composition.Arabika !== undefined && composition.Robusta !== undefined) {
        const arabikaPercent = (composition.Arabika * 100).toFixed(2);
        const robustaPercent = (composition.Robusta * 100).toFixed(2);
        return `${arabikaPercent}% Arabika, ${robustaPercent}% Robusta`;
    }
    console.log('Invalid composition:', composition);
    return '-';
}

function addTableRow(data) {
    if (data.timestamp === lastTimestamp) return;
    lastTimestamp = data.timestamp;

    console.log('Adding row:', data);
    const row = document.createElement('tr');
    row.innerHTML = `
        <td>${formatTimestampWIB(data.timestamp)}</td>
        <td>${data.mq135 !== null ? data.mq135.toFixed(4) : '-'}</td>
        <td>${data.mq2 !== null ? data.mq2.toFixed(4) : '-'}</td>
        <td>${data.mq4 !== null ? data.mq4.toFixed(4) : '-'}</td>
        <td>${data.mq7 !== null ? data.mq7.toFixed(4) : '-'}</td>
        <td>${data.jenis || '-'}</td>
        <td>${data.ai_classification?.composition ? formatComposition(data.ai_classification.composition) : '-'}</td>
    `;
    sensorTableBody?.prepend(row);

    chartData.labels.push(data.timestamp);
    chartData.datasets[0].data.push({ x: data.timestamp, y: data.mq135 || 0 });
    chartData.datasets[1].data.push({ x: data.timestamp, y: data.mq2 || 0 });
    chartData.datasets[2].data.push({ x: data.timestamp, y: data.mq4 || 0 });
    chartData.datasets[3].data.push({ x: data.timestamp, y: data.mq7 || 0 });

    if (chartData.labels.length > maxDataPoints) {
        chartData.labels.shift();
        chartData.datasets.forEach(dataset => dataset.data.shift());
    }
    sensorChart.update();
    showColumns();
}

function startWebSocket() {
    if (ws) {
        ws.close();
        ws = null;
    }

    ws = new WebSocket('ws://192.168.129.215:8000/sensor/ws');

    ws.onopen = () => {
        console.log('WebSocket connected');
        log('WebSocket connected');
        // Minta data awal setelah koneksi
        fetchChartData(intervalSelect.value).then(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ action: "request_initial_data" })); // Opsional
            }
        });
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log('WebSocket data:', data);
            if (!data.timestamp) return;
            addTableRow(data);
            if (data.ai_classification && data.ai_classification.composition && isAIRunning) {
                aiResult.textContent = formatComposition(data.ai_classification.composition);
            }
        } catch (err) {
            console.error('WebSocket parse error:', err);
            log('Error parsing WebSocket data');
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        log('WebSocket error');
        fetchChartData('3s'); // Fallback
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        log('WebSocket disconnected');
        ws = null;
        setTimeout(startWebSocket, 5000); // Retry setelah 5 detik
    };
}

async function startSensor(sensor) {
    try {
        if (sensor === 'all') {
            for (const s of ['mq135', 'mq2', 'mq4', 'mq7']) {
                if (activeSensors.has(s)) {
                    await fetch(`/sensor/stop/${s}`, { method: 'POST' })
                        .then(response => response.json())
                        .then(data => log(data.message))
                        .catch(err => log(`Error: ${err.message}`));
                }
            }
            activeSensors.clear();
            activeSensors.add('all');
        } else {
            if (!activeSensors.has('all') && !activeSensors.has(sensor)) {
                activeSensors.add(sensor);
            }
            if (activeSensors.has('all')) {
                await fetch('/sensor/stop', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => log(data.message))
                    .catch(err => log(`Error: ${err.message}`));
                activeSensors.clear();
                activeSensors.add(sensor);
            }
        }

        const response = await fetch(`/sensor/start/${sensor}`, { method: 'POST' });
        if (!response.ok) throw new Error(`Failed to start ${sensor}`);
        const data = await response.json();
        log(data.message);

        // Pastikan WebSocket aktif dan minta data awal
        if (!ws || ws.readyState === WebSocket.CLOSED) {
            startWebSocket();
        } else {
            await fetchChartData(intervalSelect.value);
        }
        updateChartVisibility();
        console.log(`Started sensor: ${sensor}, active sensors: ${Array.from(activeSensors)}`);
    } catch (err) {
        console.error(`Error starting ${sensor}:`, err);
        log(`Error: ${err.message}`);
        activeSensors.delete(sensor);
    }
}

function stopSensor() {
    activeSensors.clear();
    fetch('/sensor/stop', { method: 'POST' })
        .then(response => {
            if (!response.ok) throw new Error('Failed to stop sensors');
            return response.json();
        })
        .then(data => {
            log(data.message);
            if (ws) {
                ws.close();
                ws = null;
            }
            chartData.labels = [];
            chartData.datasets.forEach(ds => ds.data = []);
            updateChartVisibility();
            sensorChart.update();
            aiResult.textContent = isAIRunning ? 'Waiting...' : 'AI NOT ACTIVE';
        })
        .catch(err => {
            console.error('Error stopping sensors:', err);
            log('Error:', err.message);
        });
}

async function toggleAI() {
    const url = isAIRunning ? '/sensor/stop-ai' : '/sensor/start-ai';
    try {
        const response = await fetch(url, { method: 'POST' });
        if (!response.ok) throw new Error(`Failed to ${isAIRunning ? 'stop' : 'start'} AI`);
        const data = await response.json();
        log(data.message);
        isAIRunning = !isAIRunning;
        startAIBtn.textContent = isAIRunning ? 'Stop AI' : 'Start AI';
        startAIBtn.style.backgroundColor = isAIRunning ? '#e74c3c' : '#27ae60';
        aiResult.textContent = isAIRunning ? 'Waiting...' : 'AI NOT ACTIVE';
    } catch (err) {
        console.error(`Error ${isAIRunning ? 'stopping' : 'starting'} AI:`, err);
        log(`Error: ${err.message}`);
    }
}

intervalSelect?.addEventListener('change', () => {
    console.log('Interval changed:', intervalSelect.value);
    fetchChartData(intervalSelect.value);
});

document.addEventListener('DOMContentLoaded', () => {
    if (!sensorTableBody) {
        console.error('Sensor table body not found');
        log('Error: Sensor table not found');
    }
    initializeIntervalSelect();
    fetchChartData('3s');
    aiResult.textContent = 'AI NOT ACTIVE';
    startWebSocket();
});

document.getElementById('startMQ135Btn')?.addEventListener('click', () => startSensor('mq135'));
document.getElementById('startMQ2Btn')?.addEventListener('click', () => startSensor('mq2'));
document.getElementById('startMQ4Btn')?.addEventListener('click', () => startSensor('mq4'));
document.getElementById('startMQ7Btn')?.addEventListener('click', () => startSensor('mq7'));
document.getElementById('startAllBtn')?.addEventListener('click', () => startSensor('all'));
document.getElementById('startAIBtn')?.addEventListener('click', toggleAI);
document.getElementById('stopBtn')?.addEventListener('click', stopSensor);

if (sensorTableBody) {
    sensorTableBody.innerHTML = '';
}