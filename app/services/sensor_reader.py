import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from datetime import datetime
import logging

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

# Konstanta Kalibrasi untuk tiap sensor berdasarkan gas utama
SENSORS = {
    "mq135": {"channel": channel_mq135, "A": 116.6020682, "B": -2.769034857, "gas": "CO2", "max_ppm": 1000},
    "mq2": {"channel": channel_mq2, "A": 37.6, "B": -3.2, "gas": "LPG, Smoke", "max_ppm": 500},
    "mq4": {"channel": channel_mq4, "A": 330.63, "B": -2.63, "gas": "Methane", "max_ppm": 500},
    "mq7": {"channel": channel_mq7, "A": 99.042, "B": -1.518, "gas": "CO", "max_ppm": 500}
}

PPM_UDARA_BERSIH = {
    "CO2": 400,
    "LPG, Smoke": 200,
    "Methane": 150,
    "CO": 50
}

# Set untuk melacak sensor aktif
active_sensors = set()

# Fungsi kalibrasi sensor
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
    
    Rs_mean = total / n if total > 0 else 1.0  # Hindari pembagian dengan nol
    try:
        Ro = Rs_mean / ((PPM_UDARA_BERSIH[gas] / A) ** (1 / B))
    except ZeroDivisionError:
        Ro = 1.0  # Set nilai default agar tidak menyebabkan error

    return Ro

# Kalibrasi masing-masing sensor
for sensor_name, sensor in SENSORS.items():
    sensor["Ro"] = kalibrasi_sensor(sensor, sensor["A"], sensor["B"], sensor["gas"])

logger.info("✅ Kalibrasi selesai.")

# Fungsi untuk menghitung PPM dari sensor dan menormalkan ke 0-5
def hitung_ppm(sensor):
    try:
        voltage = sensor["channel"].voltage
        if voltage <= 0:
            return 0.0
        Rs = (voltage * 10000) / (VCC - voltage)
        ppm = sensor["A"] * ((Rs / sensor["Ro"]) ** sensor["B"])
        # Normalisasi ke 0-5 berdasarkan max_ppm
        max_ppm = sensor["max_ppm"]
        normalized_value = (ppm / max_ppm) * 5  # Skala ke 0-5
        # Batasi ke 0-5 tanpa pembulatan dini
        normalized_value = max(0, min(5, normalized_value))
        return normalized_value
    except ZeroDivisionError:
        return 0.0

# Fungsi untuk mendapatkan data sensor dalam format dictionary
def baca_sensor():
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sensor_data = {
        "timestamp": timestamp,
        "mq135": None,
        "mq2": None,
        "mq4": None,
        "mq7": None
    }
    for sensor_name in active_sensors:
        ppm = hitung_ppm(SENSORS[sensor_name])
        sensor_data[sensor_name] = format(ppm, ".4f")  # Format ke 4 desimal
    return sensor_data

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

if __name__ == "__main__":
    try:
        while True:
            data = baca_sensor()
            print(f"[{data['timestamp']}] MQ135: {data['mq135']} ppm | MQ2: {data['mq2']} ppm | MQ4: {data['mq4']} ppm | MQ7: {data['mq7']} ppm")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️ Pembacaan dihentikan oleh pengguna.")