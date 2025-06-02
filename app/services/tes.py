import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# Inisialisasi bus I2C
i2c = busio.I2C(board.SCL, board.SDA)

try:
    # Inisialisasi objek ADS1115 dengan alamat default 0x48
    ads = ADS.ADS1115(i2c, address=0x48)

    # Baca tegangan dari keempat channel
    channel_0 = AnalogIn(ads, ADS.P0)  # A0
    channel_1 = AnalogIn(ads, ADS.P1)  # A1
    channel_2 = AnalogIn(ads, ADS.P2)  # A2
    channel_3 = AnalogIn(ads, ADS.P3)  # A3

    print("✅ ADS1115 Terdeteksi!")
    print("📈 Tegangan A0: {:.3f} V".format(channel_0.voltage))
    print("📈 Tegangan A1: {:.3f} V".format(channel_1.voltage))
    print("📈 Tegangan A2: {:.3f} V".format(channel_2.voltage))
    print("📈 Tegangan A3: {:.3f} V".format(channel_3.voltage))

except Exception as e:
    print("❌ Gagal menghubungi ADS1115.")
    print("Error:", e)
