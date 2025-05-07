from sensor import sensor

sensor = sensor(1, "Czujnik temperatury", "C", -20, 50, 1)

sensor.start()

print(sensor.get_last_value())

sensor.stop()