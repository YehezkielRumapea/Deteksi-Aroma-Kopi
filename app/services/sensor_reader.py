import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from datetime import datetime
import logging

# Setup logging dengan format yang lebih jelas
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Inisialisasi I2C dan ADS1115
i2c = None
ads = None
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c, address=0x48)
    logger.info("✅ I2C dan ADS1115 berhasil diinisialisasi")
except Exception as e:
    logger.error(f"❌ Gagal menghubungkan ke I2C: {e}")
    raise

# Sensor Channels
channel_mq135 = AnalogIn(ads, ADS.P0)
channel_mq2 = AnalogIn(ads, ADS.P1)
channel_mq4 = AnalogIn(ads, ADS.P2)
channel_mq7 = AnalogIn(ads, ADS.P3)

# Definisi sensor dengan channel
SENSORS = {
    "mq135": {"channel": channel_mq135},
    "mq2": {"channel": channel_mq2},
    "mq4": {"channel": channel_mq4},
    "mq7": {"channel": channel_mq7}
}

# Sensor aktif
active_sensors = set()

# Fungsi untuk membaca voltage dengan retry
def read_voltage_with_retry(channel, retries=5, delay=0.5):
    for attempt in range(retries):
        try:
            voltage = channel.voltage
            logger.info(f"📏 Percobaan {attempt+1}/{retries}: Voltage = {voltage:.3f}V")
            if voltage <= 0:
                logger.warning(f"⚠️ Voltage <= 0 ({voltage:.3f}V), mencoba lagi")
                continue
            return voltage
        except (OSError, ValueError) as e:
            logger.error(f"❌ Gagal membaca voltage (percobaan {attempt+1}/{retries}): {e}")
            time.sleep(delay)
    logger.error(f"❌ Gagal membaca voltage setelah {retries} percobaan")
    return None

# Fungsi membaca sensor dengan nilai tegangan langsung
def baca_sensor(sensor_name=None):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sensor_data = {
        "timestamp": timestamp,
        "mq135": None,
        "mq2": None,
        "mq4": None,
        "mq7": None
    }
    try:
        if not active_sensors:
            logger.warning("⚠️ Tidak ada sensor aktif!")
        if sensor_name is None:
            for s_name in active_sensors:
                voltage = read_voltage_with_retry(SENSORS[s_name]["channel"])
                if voltage is not None:
                    sensor_data[s_name] = format(voltage, ".3f")
                    logger.info(f"Sensor {s_name}: Tegangan disimpan = {sensor_data[s_name]}V")
                else:
                    sensor_data[s_name] = "0.000"
                    logger.warning(f"Sensor {s_name}: Gagal membaca tegangan, diset ke 0.000V")
        elif sensor_name in SENSORS:
            if sensor_name in active_sensors:
                voltage = read_voltage_with_retry(SENSORS[sensor_name]["channel"])
                if voltage is not None:
                    sensor_data[sensor_name] = format(voltage, ".3f")
                    logger.info(f"Sensor {sensor_name}: Tegangan disimpan = {sensor_data[sensor_name]}V")
                else:
                    sensor_data[sensor_name] = "0.000"
                    logger.warning(f"Sensor {sensor_name}: Gagal membaca tegangan, diset ke 0.000V")
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
            logger.info(f"Sensor {sensor_name} diaktifkan. Active sensors: {active_sensors}")
    except Exception as e:
        logger.error(f"Error starting sensor {sensor_name}: {str(e)}")

# Fungsi menghentikan sensor
def stop_sensor(sensor_name: str):
    try:
        if sensor_name in active_sensors:
            active_sensors.remove(sensor_name)
            logger.info(f"Sensor {sensor_name} dihentikan. Active sensors: {active_sensors}")
    except Exception as e:
        logger.error(f"Error stopping sensor {sensor_name}: {str(e)}")

def stop_all_sensors():
    try:
        active_sensors.clear()
        logger.info("Semua sensor dihentikan. Active sensors: {active_sensors}")
    except Exception as e:
        logger.error(f"Error stopping all sensors: {str(e)}")

# Jalankan jika file ini dieksekusi langsung
if __name__ == "__main__":
    try:
        start_sensor("all")  # Aktifkan semua sensor tanpa kalibrasi
        while True:
            data = baca_sensor()
            print(f"[{data['timestamp']}] MQ135: {data['mq135']}V | MQ2: {data['mq2']}V | MQ4: {data['mq4']}V | MQ7: {data['mq7']}V")
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n⏹️ Pembacaan dihentikan oleh pengguna.")