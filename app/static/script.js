const sensorTable = document.getElementById('sensorTable');
const sensorTableBody = sensorTable.querySelector('tbody');
const logDiv = document.getElementById('apiLogs');

let ws = null;
let lastTimestamp = null;

// Fungsi untuk log aktivitas
function log(message) {
    const logEntry = document.createElement('div');
    logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    logDiv.prepend(logEntry);
    logDiv.scrollTop = 0;
}

// Fungsi untuk menambahkan baris ke tabel
function addTableRow(data) {
    // Lewati data jika tidak ada sensor aktif atau timestamp sama dengan yang terakhir
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

    // Tambahkan log
    if (data.log) {
        log(data.log);
    }
}

// Fungsi untuk menghubungkan WebSocket
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

// Fungsi untuk memulai sensor
function startSensor(sensor) {
    fetch(`/sensor/start/${sensor}`, { method: 'POST' })
        .then(response => {
            if (!response.ok) throw new Error(`Gagal start sensor ${sensor}`);
            return response.json();
        })
        .then(data => {
            log(data.message);
            startWebSocket();
        })
        .catch(err => {
            console.error(`Gagal memulai sensor ${sensor}:`, err);
            log(`Error: ${err.message}`);
        });
}

// Fungsi untuk menghentikan sensor
function stopSensor() {
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
        })
        .catch(err => {
            console.error("Gagal menghentikan sensor:", err);
            log(`Error: ${err.message}`);
        });
}

// Tombol-tombol sensor
document.getElementById('startMQ135Btn').onclick = () => startSensor('mq135');
document.getElementById('startMQ2Btn').onclick = () => startSensor('mq2');
document.getElementById('startMQ4Btn').onclick = () => startSensor('mq4');
document.getElementById('startMQ7Btn').onclick = () => startSensor('mq7');
document.getElementById('startAllBtn').onclick = () => startSensor('all');
document.getElementById('stopBtn').onclick = stopSensor;

// Inisialisasi tampilan awal
sensorTableBody.innerHTML = '';

// document.addEventListener('DOMContentLoaded', () => {
//     // Inisialisasi elemen
//     const startMQ135Btn = document.getElementById('startMQ135Btn');
//     const startMQ2Btn = document.getElementById('startMQ2Btn');
//     const startMQ4Btn = document.getElementById('startMQ4Btn');
//     const startMQ7Btn = document.getElementById('startMQ7Btn');
//     const startAllBtn = document.getElementById('startAllBtn');
//     const stopBtn = document.getElementById('stopBtn');
//     const tableBody = document.getElementById('sensorTable').getElementsByTagName('tbody')[0];
//     const apiLogs = document.getElementById('apiLogs');
//     let ws;
//     let chart;

//     // Verifikasi elemen
//     if (!startMQ135Btn || !startMQ2Btn || !startMQ4Btn || !startMQ7Btn || !startAllBtn || !stopBtn) {
//         console.error('One or more button elements not found');
//         return;
//     }

//     // Inisialisasi grafik
//     const ctx = document.getElementById('sensorChart').getContext('2d');
//     if (!ctx) {
//         console.error('Canvas element not found');
//         return;
//     }
//     chart = new Chart(ctx, {
//         type: 'line',
//         data: {
//             datasets: [
//                 {
//                     label: 'MQ135',
//                     data: [],
//                     borderColor: 'rgba(255, 99, 132, 1)',
//                     fill: false
//                 },
//                 {
//                     label: 'MQ2',
//                     data: [],
//                     borderColor: 'rgba(54, 162, 235, 1)',
//                     fill: false
//                 },
//                 {
//                     label: 'MQ4',
//                     data: [],
//                     borderColor: 'rgba(75, 192, 192, 1)',
//                     fill: false
//                 },
//                 {
//                     label: 'MQ7',
//                     data: [],
//                     borderColor: 'rgba(255, 206, 86, 1)',
//                     fill: false
//                 }
//             ]
//         },
//         options: {
//             scales: {
//                 x: {
//                     type: 'time',
//                     time: {
//                         unit: 'second'
//                     },
//                     title: {
//                         display: true,
//                         text: 'Waktu'
//                     }
//                 },
//                 y: {
//                     beginAtZero: true,
//                     title: {
//                         display: true,
//                         text: 'Nilai Sensor'
//                     }
//                 }
//             },
//             plugins: {
//                 legend: {
//                     display: true
//                 }
//             }
//         }
//     });

//     function logMessage(message) {
//         const logEntry = document.createElement('div');
//         logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
//         apiLogs.appendChild(logEntry);
//         apiLogs.scrollTop = apiLogs.scrollHeight;
//     }

//     function clearTable() {
//         tableBody.innerHTML = '';
//     }

//     function clearChart() {
//         chart.data.datasets.forEach(dataset => {
//             dataset.data = [];
//         });
//         chart.update();
//     }

//     function showColumns(sensor) {
//         const headers = document.querySelectorAll('#sensorTable th');
//         headers.forEach(header => {
//             const col = header.getAttribute('data-column');
//             if (sensor === 'all') {
//                 header.style.display = '';
//             } else {
//                 header.style.display = (col === 'timestamp' || col === 'kualitas' || col === sensor) ? '' : 'none';
//             }
//         });

//         const cells = tableBody.querySelectorAll('td');
//         cells.forEach(cell => {
//             const col = cell.getAttribute('data-column');
//             if (sensor === 'all') {
//                 cell.style.display = '';
//             } else {
//                 cell.style.display = (col === 'timestamp' || col === 'kualitas' || col === sensor) ? '' : 'none';
//             }
//         });
//     }

//     function addTableRow(data) {
//         const row = tableBody.insertRow();
//         const timestampCell = row.insertCell();
//         const mq135Cell = row.insertCell();
//         const mq2Cell = row.insertCell();
//         const mq4Cell = row.insertCell();
//         const mq7Cell = row.insertCell();
//         const kualitasCell = row.insertCell();

//         timestampCell.textContent = new Date(data.timestamp).toLocaleString();
//         timestampCell.setAttribute('data-column', 'timestamp');
//         mq135Cell.textContent = data.mq135 != null ? data.mq135.toFixed(4) : '';
//         mq135Cell.setAttribute('data-column', 'mq135');
//         mq2Cell.textContent = data.mq2 != null ? data.mq2.toFixed(4) : '';
//         mq2Cell.setAttribute('data-column', 'mq2');
//         mq4Cell.textContent = data.mq4 != null ? data.mq4.toFixed(4) : '';
//         mq4Cell.setAttribute('data-column', 'mq4');
//         mq7Cell.textContent = data.mq7 != null ? data.mq7.toFixed(4) : '';
//         mq7Cell.setAttribute('data-column', 'mq7');
//         kualitasCell.textContent = data.kualitas || '';
//         kualitasCell.setAttribute('data-column', 'kualitas');

//         showColumns(data.sensor);
//     }

//     function updateChart(data) {
//         const timestamp = new Date(data.timestamp);
//         if (data.sensor === 'all') {
//             chart.data.datasets[0].data.push({ x: timestamp, y: data.mq135 });
//             chart.data.datasets[1].data.push({ x: timestamp, y: data.mq2 });
//             chart.data.datasets[2].data.push({ x: timestamp, y: data.mq4 });
//             chart.data.datasets[3].data.push({ x: timestamp, y: data.mq7 });
//         } else {
//             const sensorMap = {
//                 'mq135': 0,
//                 'mq2': 1,
//                 'mq4': 2,
//                 'mq7': 3
//             };
//             const datasetIndex = sensorMap[data.sensor];
//             chart.data.datasets[datasetIndex].data.push({ x: timestamp, y: data[data.sensor] });
//         }
//         // Batasi jumlah data
//         chart.data.datasets.forEach(dataset => {
//             if (dataset.data.length > 50) {
//                 dataset.data.shift();
//             }
//         });
//         chart.update();
//     }

//     async function startSensor(sensor) {
//         try {
//             console.log(`Starting sensor: ${sensor}`);
//             const response = await fetch(`/sensor/start/${sensor}`, { method: 'POST' });
//             const data = await response.json();
//             logMessage(data.message);
//             if (sensor === 'all') {
//                 clearChart();
//                 clearTable();
//             }
//         } catch (error) {
//             logMessage(`Error starting ${sensor}: ${error.message}`);
//             console.error(`Error starting ${sensor}:`, error);
//         }
//     }

//     async function stopSensors() {
//         try {
//             console.log('Stopping all sensors');
//             const response = await fetch('/sensor/stop', { method: 'POST' });
//             const data = await response.json();
//             logMessage(data.message);
//             clearTable();
//             clearChart();
//             document.querySelectorAll('#sensorTable th').forEach(header => header.style.display = '');
//         } catch (error) {
//             logMessage(`Error stopping sensors: ${error.message}`);
//             console.error('Error stopping sensors:', error);
//         }
//     }

//     function connectWebSocket() {
//         ws = new WebSocket(`ws://${window.location.host}/sensor/ws`);
//         ws.onmessage = (event) => {
//             const data = JSON.parse(event.data);
//             if (data.message) {
//                 logMessage(data.message);
//             } else {
//                 addTableRow(data);
//                 updateChart(data);
//                 if (data.log) logMessage(data.log);
//             }
//         };
//         ws.onclose = () => {
//             logMessage('WebSocket disconnected');
//             setTimeout(connectWebSocket, 1000);
//         };
//         ws.onerror = (error) => {
//             logMessage(`WebSocket error: ${error}`);
//             console.error('WebSocket error:', error);
//         };
//     }

//     // Tambah event listener
//     startMQ135Btn.addEventListener('click', () => startSensor('mq135'));
//     startMQ2Btn.addEventListener('click', () => startSensor('mq2'));
//     startMQ4Btn.addEventListener('click', () => startSensor('mq4'));
//     startMQ7Btn.addEventListener('click', () => startSensor('mq7'));
//     startAllBtn.addEventListener('click', () => startSensor('all'));
//     stopBtn.addEventListener('click', stopSensors);

//     // Inisialisasi WebSocket
//     connectWebSocket();
// });