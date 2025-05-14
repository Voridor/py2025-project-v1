import datetime
import random
import time
from typing import override, Callable
# Assuming Logger is defined elsewhere and importable
# import Logger


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
        self._callbacks = []
        self.sensor_id = sensor_id
        self.name = name
        self.unit = unit
        self.min_value = min_value
        self.max_value = max_value
        self.frequency = frequency
        self.active = True
        self.last_value = None
        self._last_read_time = None

    def read_value(self):
        """
        Symuluje pobranie odczytu z czujnika.
        Jeśli od ostatniego odczytu minęło mniej niż self.frequency, zwraca ostatnią wartość.
        W przeciwnym razie generuje nową losową wartość.
        """
        if not self.active:
            raise Exception(f"Czujnik {self.name} jest wyłączony.")

        now = datetime.datetime.now()
        if self._last_read_time is not None and (now - self._last_read_time).total_seconds() < self.frequency:
            return self.last_value
        else:
            value = random.uniform(self.min_value, self.max_value)
            self.last_value = value
            self._last_read_time = now
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

    def register_callback(self, callback: Callable[[str, datetime.datetime, float, str], None]) -> None:
        """
        Rejestruje funkcję (callback), która zostanie wywołana po każdym NOWYM odczycie.
        Callback powinien akceptować: sensor_id, timestamp, value, unit.
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)


class TemperatureSensor(sensor):
    @override
    def read_value(self):
        now = datetime.datetime.now()
        if self._last_read_time is not None and (now - self._last_read_time).total_seconds() < self.frequency:
            return self.last_value
        else:
            currMonth = now.month
            currHour = now.hour
            monthAvgDayTemp = [-1, 2, 6, 12, 18, 20, 22, 22, 18, 13, 5, 1]
            monthAvgNightTemp = [-9, -7, -4, 1, 5, 8, 10, 9, 6, 2, -2, -8]
            if currHour < 8 or currHour > 20:
                value = monthAvgNightTemp[currMonth - 1] + random.uniform(-2, 2)
            else:
                value = monthAvgDayTemp[currMonth - 1] + random.uniform(-2, 2)
            self.last_value = round(value, 2)
            self._last_read_time = now
            return self.last_value


class HumiditySensor(sensor):
    @override
    def read_value(self):
        now = datetime.datetime.now()
        if self._last_read_time is not None and (now - self._last_read_time).total_seconds() < self.frequency:
            return self.last_value
        else:
            currMonth = now.month
            currHour = now.hour
            hourDiff = random.uniform(0, 5)
            if currHour < 20 or currHour > 6:
                hourDiff = -hourDiff
            if currMonth in [3, 4, 5]:
                value = 50 + random.uniform(-5, 5) + hourDiff
            elif currMonth in [6, 7, 8]:
                value = 60 + random.uniform(-5, 5) + hourDiff
            elif currMonth in [9, 10, 11]:
                value = 50 + random.uniform(-5, 5) + hourDiff
            elif currMonth in [12, 1, 2]:
                value = 40 + random.uniform(-5, 5) + hourDiff
            else:
                value = 0  # Should not happen
            self.last_value = round(value, 2)
            self._last_read_time = now
            return self.last_value


class PressureSensor(sensor):
    @override
    def read_value(self):
        now = datetime.datetime.now()
        if self._last_read_time is not None and (now - self._last_read_time).total_seconds() < self.frequency:
            return self.last_value
        else:
            if random.uniform(0, 1) > 0.5:
                value = 950 + random.uniform(0, 50)
            else:
                value = 1000 + random.uniform(0, 50)
            self.last_value = round(value, 2)
            self._last_read_time = now
            return self.last_value


class LightSensor(sensor):
    @override
    def read_value(self):
        now = datetime.datetime.now()
        if self._last_read_time is not None and (now - self._last_read_time).total_seconds() < self.frequency:
            return self.last_value
        else:
            currHour = now.hour
            if currHour <= 12:
                value = currHour * 83 + random.uniform(-10, 4)
            else:
                value = (currHour - (currHour - 12)) * 83 + random.uniform(-10, 4)
            self.last_value = round(value, 2)
            self._last_read_time = now
            return self.last_value