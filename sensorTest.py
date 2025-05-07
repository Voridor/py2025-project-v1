import unittest
import random

# Zakładamy, że wszystkie klasy są zdefiniowane w jednym module
from sensor import sensor, TemperatureSensor, HumiditySensor, PressureSensor, LightSensor


class TestSensorBase(unittest.TestCase):

    def setUp(self):
        self.s = sensor(sensor_id=1, name="TestSensor", unit="unit", min_value=0, max_value=100, frequency=1)

    def test_initialization(self):
        self.assertEqual(self.s.sensor_id, 1)
        self.assertEqual(self.s.name, "TestSensor")
        self.assertEqual(self.s.unit, "unit")
        self.assertEqual(self.s.min_value, 0)
        self.assertEqual(self.s.max_value, 100)
        self.assertTrue(self.s.active)

    def test_read_value_within_range(self):
        val = self.s.read_value()
        self.assertGreaterEqual(val, 0)
        self.assertLessEqual(val, 100)

    def test_last_value_after_read(self):
        val = self.s.read_value()
        self.assertEqual(val, self.s.get_last_value())

    def test_calibrate(self):
        original = self.s.read_value()
        calibrated = self.s.calibrate(1.1)
        self.assertAlmostEqual(calibrated, original * 1.1)

    def test_get_last_value_without_read(self):
        val = self.s.get_last_value()
        self.assertEqual(val, self.s.last_value)

    def test_start_stop(self):
        self.s.stop()
        self.assertFalse(self.s.active)
        with self.assertRaises(Exception):
            self.s.read_value()
        self.s.start()
        self.assertTrue(self.s.active)

    def test_str_representation(self):
        self.assertEqual(str(self.s), "sensor(id=1, name=TestSensor, unit=unit)")


class TestTemperatureSensor(unittest.TestCase):

    def setUp(self):
        self.sensor = TemperatureSensor(sensor_id=101, name="Temp", unit="°C", min_value=-20, max_value=50)

    def test_temperature_range(self):
        val = self.sensor.read_value()
        self.assertGreaterEqual(val, -20)
        self.assertLessEqual(val, 50)


class TestHumiditySensor(unittest.TestCase):

    def setUp(self):
        self.sensor = HumiditySensor(sensor_id=102, name="Humidity", unit="%", min_value=0, max_value=100)

    def test_humidity_range(self):
        val = self.sensor.read_value()
        self.assertGreaterEqual(val, 0)
        self.assertLessEqual(val, 100)


class TestPressureSensor(unittest.TestCase):

    def setUp(self):
        self.sensor = PressureSensor(sensor_id=103, name="Pressure", unit="hPa", min_value=950, max_value=1050)

    def test_pressure_range(self):
        val = self.sensor.read_value()
        self.assertGreaterEqual(val, 950)
        self.assertLessEqual(val, 1050)


class TestLightSensor(unittest.TestCase):

    def setUp(self):
        self.sensor = LightSensor(sensor_id=104, name="Light", unit="lx", min_value=0, max_value=10000)

    def test_light_range(self):
        val = self.sensor.read_value()
        self.assertGreaterEqual(val, 0)
        self.assertLessEqual(val, 10000)


if __name__ == '__main__':
    unittest.main()
