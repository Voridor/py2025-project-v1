import datetime
import random
import time
from typing import override


class sensor:
    def __init__(self, sensor_id, name, unit, min_value, max_value, frequency=1):
        """
        Inicjalizacja czujnika.

        :param sensor_id: Unikalny identyfikator czujnika
        :param name: Nazwa lub opis czujnika
        :param unit: Jednostka miary (np. '°C', '%', 'hPa', 'lux')
        :param min_value: Minimalna wartość odczytu
        :param max_value: Maksymalna wartość odczytu
        :param frequency: Częstotliwość odczytów (sekundy)
        """
        self.sensor_id = sensor_id
        self.name = name
        self.unit = unit
        self.min_value = min_value
        self.max_value = max_value
        self.frequency = frequency
        self.active = True
        self.last_value = None

    def read_value(self):
        """
        Symuluje pobranie odczytu z czujnika.
        W klasie bazowej zwraca losową wartość z przedziału [min_value, max_value].
        """
        if not self.active:
            raise Exception(f"Czujnik {self.name} jest wyłączony.")

        value = random.uniform(self.min_value, self.max_value)
        self.last_value = value
        return value

    def calibrate(self, calibration_factor):
        """
        Kalibruje ostatni odczyt przez przemnożenie go przez calibration_factor.
        Jeśli nie wykonano jeszcze odczytu, wykonuje go najpierw.
        """
        if self.last_value is None:
            self.read_value()

        self.last_value *= calibration_factor
        return self.last_value

    def get_last_value(self):
        """
        Zwraca ostatnią wygenerowaną wartość, jeśli była wygenerowana.
        """
        if self.last_value is None:
            return self.read_value()
        return self.last_value

    def start(self):
        """
        Włącza czujnik.
        """
        self.active = True

    def stop(self):
        """
        Wyłącza czujnik.
        """
        self.active = False

    def __str__(self):
        return f"sensor(id={self.sensor_id}, name={self.name}, unit={self.unit})"

class TemperatureSensor(sensor):
    def __init__(self, sensor_id, name, unit, min_value, max_value, frequency=1):
        sensor.__init__(self, sensor_id, name, unit, min_value, max_value, frequency)
        self.sensor_id = sensor_id
        self.name = name
        self.unit = unit
        self.min_value = min_value
        self.max_value = max_value
        self.frequency = frequency

    @override
    def read_value(self):
        currMonth = datetime.datetime.now().month
        currHour = datetime.datetime.now().hour
        monthAvgDayTemp = [-1, 2, 6, 12, 18, 20, 22, 22, 18, 13, 5, 1]
        monthAvgNightTemp = [-9, -7, -4, 1, 5, 8, 10, 9, 6, 2, -2, -8]
        if currHour < 8 or currHour > 20:
            value = monthAvgNightTemp[currMonth - 1] + random.uniform(-2, 2)
        else:
            value = monthAvgDayTemp[currMonth - 1] + random.uniform(-2, 2)
        self.last_value = value
        return value

class HumiditySensor(sensor):

    @override
    def read_value(self):
        currMonth = datetime.datetime.now().month
        currHour = datetime.datetime.now().hour
        hourDiff = random.uniform(0, 5)
        if currHour < 20 or currHour > 6:
            hourDiff = -hourDiff
        if currMonth in [3, 4, 5]:
            return 50 + random.uniform(-5, 5) + hourDiff
        if currMonth in [6, 7, 8]:
            return 60 + random.uniform(-5, 5)+ hourDiff
        if currMonth in [9, 10, 11]:
            return 50 + random.uniform(-5, 5)+ hourDiff
        if currMonth in [12, 1, 2]:
            return 40 + random.uniform(-5, 5)+ hourDiff

class PressureSensor(sensor):
    @override
    def read_value(self):
        if random.uniform(0, 1) > 0.5:
            return 950 + random.uniform(0,50)
        else:
            return 1000 + random.uniform(0,50)

class LightSensor(sensor):
    @override
    def read_value(self):
        currHour = datetime.datetime.now().hour
        if currHour <=12:
            return currHour * 83 + random.uniform(-10,4)
        if currHour >12:
            return (currHour - (currHour-12)) * 83 + random.uniform(-10,4)

