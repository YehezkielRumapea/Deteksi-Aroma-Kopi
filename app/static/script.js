const sensorTable = document.getElementById('sensorTable');
const sensorTableBody = sensorTable.querySelector('tbody');
const logDiv = document.getElementById('apiLogs');
const sensorChartCanvas = document.getElementById('sensorChart');
const intervalSelect = document.getElementById('intervalSelect');

let ws = null;
let lastTimestamp = null;
let activeSensor = 'all';

// Chart.js configuration
const maxDataPoints = 1200; // Sesuai 1 jam data untuk 3s
const chartData = {
    labels: [],
    datasets: [
        {
            label: 'MQ135',
            data: [],
            borderColor: '#3498db',
            backgroundColor: 'rgba(52, 152, 219, 0.2)',
            fill: false,
            tension: 0.3,
            pointRadius: 3,
        },
        {
            label: 'MQ2',
            data: [],
            borderColor: '#e74c3c',
            backgroundColor: 'rgba(231, 76, 60, 0.2)',
            fill: false,
            tension: 0.3,
            pointRadius: 3,
        },
        {
            label: 'MQ4',
            data: [],
            borderColor: '#2ecc71',
            backgroundColor: 'rgba(46, 204, 113, 0.2)',
            fill: false,
            tension: 0.3,
            pointRadius: 3,
        },
        {
            label: 'MQ7',
            data: [],
            borderColor: '#f1c40f',
            backgroundColor: 'rgba(241, 196, 15, 0.2)',
            fill: false,
            tension: 0.3,
            pointRadius: 3,
        },
    ],
};

const sensorChart = new Chart(sensorChartCanvas, {
    type: 'line',
    data: chartData,
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: {
                title: {
                    display: true,
                    text: 'Timestamp',
                    color: '#2c3e50',
                    font: { size: 14, weight: 'bold' },
                },
                ticks: {
                    color: '#34495e',
                    maxRotation: 45,
                    minRotation: 45,
                    maxTicksLimit: 10,
                    callback: function (value, index, ticks) {
                        const label = this.getLabelForValue(value);
                        const date = new Date(label);
                        return date.toLocaleTimeString('en-GB');
                    }
                },
                grid: { display: false },
            },
            y: {
                title: {
                    display: true,
                    text: 'Sensor Value',
                    color: '#2c3e50',
                    font: { size: 14, weight: 'bold' },
                },
                ticks: { color: '#34495e' },
                grid: { color: '#e0e0e0' },
                beginAtZero: true,
                max: 5,
                ticks: { stepSize: 0.5 }
            },
        },
        plugins: {
            legend: {
                display: true,
                position: 'top',
                labels: {
                    color: '#2c3e50',
                    font: { size: 12 },
                    usePointStyle: true,
                },
            },
            tooltip: {
                backgroundColor: '#2c3e50',
                titleColor: '#ffffff',
                bodyColor: '#ffffff',
                borderColor: '#3498db',
                borderWidth: 1,
            },
        },
        animation: {
            duration: 500,
        },
    },
});

function log(message) {
    const logEntry = document.createElement('div');
    logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    logDiv.prepend(logEntry);
    logDiv.scrollTop = 0;
}

function showColumns(sensor) {
    const headers = sensorTable.querySelectorAll('th');
    const colIndexes = {
        'mq135': [1],
        'mq2': [2],
        'mq4': [3],
        'mq7': [4],
        'all': [1, 2, 3, 4]
    };

    headers.forEach((th, idx) => {
        if (idx === 0 || idx === 5 || sensor === 'all' || colIndexes[sensor]?.includes(idx)) {
            th.style.display = '';
        } else {
            th.style.display = 'none';
        }
    });

    sensorTableBody.querySelectorAll('tr').forEach(row => {
        row.querySelectorAll('td').forEach((td, idx) => {
            if (idx === 0 || idx === 5 || sensor === 'all' || colIndexes[sensor]?.includes(idx)) {
                td.style.display = '';
            } else {
                td.style.display = 'none';
            }
        });
    });
}

async function fetchChartData(interval) {
    try {
        const response = await fetch(`/sensor/data/db/${interval}`);
        const data = await response.json();
        console.log("Chart data:", data);
        chartData.labels = data.map(d => d.timestamp);
        chartData.datasets[0].data = data.map(d => d.mq135);
        chartData.datasets[1].data = data.map(d => d.mq2);
        chartData.datasets[2].data = data.map(d => d.mq4);
        chartData.datasets[3].data = data.map(d => d.mq7);
        sensorChart.update();
        log(`Grafik diperbarui untuk interval ${interval}`);
    } catch (err) {
        console.error("Error fetching chart data:", err);
        log(`Error fetching chart data: ${err}`);
    }
}

function addTableRow(data) {
    if (data.sensor === "unknown" || data.timestamp === lastTimestamp) return;

    lastTimestamp = data.timestamp;

    const row = document.createElement('tr');
    row.innerHTML = `
        <td>${data.timestamp}</td>
        <td>${data.mq135 !== null ? data.mq135.toFixed(4) : '-'}</td>
        <td>${data.mq2 !== null ? data.mq2.toFixed(4) : '-'}</td>
        <td>${data.mq4 !== null ? data.mq4.toFixed(4) : '-'}</td>
        <td>${data.mq7 !== null ? data.mq7.toFixed(4) : '-'}</td>
        <td>${data.kualitas || '-'}</td>
    `;
    sensorTableBody.prepend(row);

    if (intervalSelect.value === '3s') {
        chartData.labels.push(data.timestamp);
        chartData.datasets[0].data.push(data.mq135);
        chartData.datasets[1].data.push(data.mq2);
        chartData.datasets[2].data.push(data.mq4);
        chartData.datasets[3].data.push(data.mq7);

        if (chartData.labels.length > maxDataPoints) {
            chartData.labels.shift();
            chartData.datasets.forEach(dataset => dataset.data.shift());
        }
        sensorChart.update();
    }

    if (data.log) {
        log(data.log);
    }

    showColumns(activeSensor);
}

function startWebSocket() {
    if (ws) {
        ws.close();
        ws = null;
    }

    ws = new WebSocket('ws://' + window.location.host + '/sensor/ws');

    ws.onopen = function () {
        console.log("WebSocket connected");
        log("WebSocket terhubung");
    };

    ws.onmessage = function (event) {
        try {
            const data = JSON.parse(event.data);
            if (!data.timestamp || !data.sensor) return;
            addTableRow(data);
        } catch (err) {
            console.error("Gagal parsing data WebSocket:", err);
            log(`Error: ${err.message}`);
        }
    };

    ws.onerror = function () {
        console.error("WebSocket error");
        log("Error WebSocket");
    };

    ws.onclose = function () {
        console.log("WebSocket disconnected");
        log("WebSocket terputus");
        ws = null;
    };
}

function startSensor(sensor) {
    activeSensor = sensor;
    fetch(`/sensor/start/${sensor}`, { method: 'POST' })
        .then(response => {
            if (!response.ok) throw new Error(`Gagal start sensor ${sensor}`);
            return response.json();
        })
        .then(data => {
            log(data.message);
            startWebSocket();
            fetchChartData(intervalSelect.value);
        })
        .catch(err => {
            console.error(`Gagal memulai sensor ${sensor}:`, err);
            log(`Error: ${err.message}`);
        });
}

function stopSensor() {
    activeSensor = 'none';
    fetch('/sensor/stop', { method: 'POST' })
        .then(response => {
            if (!response.ok) throw new Error("Gagal stop sensor");
            return response.json();
        })
        .then(data => {
            log(data.message);
            if (ws) {
                ws.close();
                ws = null;
            }
            chartData.labels = [];
            chartData.datasets.forEach(dataset => dataset.data = []);
            sensorChart.update();
        })
        .catch(err => {
            console.error("Gagal menghentikan sensor:", err);
            log(`Error: ${err.message}`);
        });
}

intervalSelect.onchange = () => {
    fetchChartData(intervalSelect.value);
};

document.getElementById('startMQ135Btn').onclick = () => startSensor('mq135');
document.getElementById('startMQ2Btn').onclick = () => startSensor('mq2');
document.getElementById('startMQ4Btn').onclick = () => startSensor('mq4');
document.getElementById('startMQ7Btn').onclick = () => startSensor('mq7');
document.getElementById('startAllBtn').onclick = () => startSensor('all');
document.getElementById('stopBtn').onclick = stopSensor;

sensorTableBody.innerHTML = '';
fetchChartData('3s');