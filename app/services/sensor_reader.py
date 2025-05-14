import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from datetime import datetime
import logging
from collections import deque

logger = logging.getLogger(__name__)

# Konstanta
VCC = 5.0  # Tegangan referensi sensor

# Setup I2C
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
except Exception as e:
    logger.error(f"❌ Gagal menghubungkan ke I2C: {e}")
    raise

# Sensor Channels
channel_mq135 = AnalogIn(ads, ADS.P0)
channel_mq2 = AnalogIn(ads, ADS.P1)
channel_mq4 = AnalogIn(ads, ADS.P2)
channel_mq7 = AnalogIn(ads, ADS.P3)

# Konstanta Kalibrasi sensor
SENSORS = {
    "mq135": {"channel": channel_mq135, "A": 100, "B": -2.5, "gas": "CO2", "max_ppm": 1000},
    "mq2": {"channel": channel_mq2, "A": 50, "B": -3.0, "gas": "LPG, Smoke", "max_ppm": 500},
    "mq4": {"channel": channel_mq4, "A": 600, "B": -3.5, "gas": "Methane", "max_ppm": 200},
    "mq7": {"channel": channel_mq7, "A": 200, "B": -2.0, "gas": "CO", "max_ppm": 150}
}

# PPM udara bersih
PPM_UDARA_BERSIH = {
    "CO2": 400,
    "LPG, Smoke": 200,
    "Methane": 150,
    "CO": 50
}

# Sensor aktif
active_sensors = set()

# Moving average buffer
MOVING_AVG_BUFFERS = {
    "mq4": deque(maxlen=10),
    "mq7": deque(maxlen=10)
}

# Fungsi kalibrasi
def kalibrasi_sensor(sensor, A, B, gas):
    total = 0
    n = 50
    for _ in range(n):
        try:
            voltage = sensor["channel"].voltage
            if voltage <= 0:
                continue
            Rs = (voltage * 10000) / (VCC - voltage)
            total += Rs
        except ZeroDivisionError:
            continue
        time.sleep(0.05)
    
    Rs_mean = total / n if total > 0 else 1.0
    try:
        Ro = Rs_mean / ((PPM_UDARA_BERSIH[gas] / A) ** (1 / B))
    except ZeroDivisionError:
        Ro = 1.0
    return Ro

# Kalibrasi semua sensor
for sensor_name, sensor in SENSORS.items():
    sensor["Ro"] = kalibrasi_sensor(sensor, sensor["A"], sensor["B"], sensor["gas"])

logger.info("✅ Kalibrasi selesai.")

# Fungsi moving average untuk MQ4 dan MQ7
def moving_average(sensor_name, new_value):
    if sensor_name in MOVING_AVG_BUFFERS:
        buffer = MOVING_AVG_BUFFERS[sensor_name]
        buffer.append(new_value)
        return sum(buffer) / len(buffer)
    return new_value

# Fungsi hitung PPM dan normalisasi
def hitung_ppm(sensor, sensor_name=None):
    try:
        voltage = sensor["channel"].voltage
        if voltage <= 0:
            return 0.0
        Rs = (voltage * 10000) / (VCC - voltage)
        ppm = sensor["A"] * ((Rs / sensor["Ro"]) ** sensor["B"])
        max_ppm = sensor["max_ppm"]
        normalized_value = (ppm / max_ppm) * 5
        normalized_value = max(0, min(5, normalized_value))
        if sensor_name in ["mq4", "mq7"]:
            normalized_value = moving_average(sensor_name, normalized_value)
        return normalized_value
    except ZeroDivisionError:
        return 0.0

# Fungsi membaca sensor
def baca_sensor(sensor_name=None):
    """
    Membaca data dari sensor tertentu atau semua sensor aktif.
    sensor_name: 'mq135', 'mq2', 'mq4', 'mq7', atau None (untuk semua sensor).
    Mengembalikan dict dengan nilai sensor.
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Format datetime lengkap
    sensor_data = {
        "timestamp": timestamp,
        "mq135": None,
        "mq2": None,
        "mq4": None,
        "mq7": None
    }
    try:
        if sensor_name is None:
            for s_name in active_sensors:
                ppm = hitung_ppm(SENSORS[s_name], s_name)
                sensor_data[s_name] = format(ppm, ".4f")
        elif sensor_name in SENSORS:
            if sensor_name in active_sensors:
                ppm = hitung_ppm(SENSORS[sensor_name], sensor_name)
                sensor_data[sensor_name] = format(ppm, ".4f")
            else:
                logger.warning(f"Sensor {sensor_name} tidak aktif")
        else:
            logger.error(f"Sensor {sensor_name} tidak valid")
        return sensor_data
    except Exception as e:
        logger.error(f"Gagal membaca sensor {sensor_name}: {e}")
        return sensor_data

# Fungsi mengaktifkan sensor
def start_sensor(sensor_name: str):
    try:
        if sensor_name in SENSORS or sensor_name == "all":
            if sensor_name == "all":
                active_sensors.update(SENSORS.keys())
            else:
                active_sensors.add(sensor_name)
            logger.info(f"Sensor {sensor_name} diaktifkan")
    except Exception as e:
        logger.error(f"Error starting sensor {sensor_name}: {str(e)}")

# Fungsi menghentikan sensor
def stop_sensor(sensor_name: str):
    try:
        if sensor_name in active_sensors:
            active_sensors.remove(sensor_name)
            logger.info(f"Sensor {sensor_name} dihentikan")
    except Exception as e:
        logger.error(f"Error stopping sensor {sensor_name}: {str(e)}")

def stop_all_sensors():
    try:
        active_sensors.clear()
        logger.info("Semua sensor dihentikan")
    except Exception as e:
        logger.error(f"Error stopping all sensors: {str(e)}")

# Jalankan jika file ini dieksekusi langsung
if __name__ == "__main__":
    try:
        start_sensor("all")
        while True:
            data = baca_sensor()
            print(f"[{data['timestamp']}] MQ135: {data['mq135']} ppm | MQ2: {data['mq2']} ppm | MQ4: {data['mq4']} ppm | MQ7: {data['mq7']} ppm")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️ Pembacaan dihentikan oleh pengguna.")