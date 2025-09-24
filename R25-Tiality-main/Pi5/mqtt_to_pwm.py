from typing import List
import paho.mqtt.client as mqtt
import threading
import time
import math
from gpiozero import PWMOutputDevice, DigitalOutputDevice


# BCM pin numbers
ENABLE_PINS: List[int] = [22, 27, 19, 26]
INPUT_PINS: List[int] = [2, 3, 4, 17, 6, 13, 5, 11]  # 8 pins -> 4 pairs


class Motor:
    def __init__(self, en_pin: int, in_a: int, in_b: int, freq_hz: int):
        self.en = PWMOutputDevice(en_pin, frequency=freq_hz, initial_value=0)
        self.in_a = DigitalOutputDevice(in_a)
        self.in_b = DigitalOutputDevice(in_b)
        self._duty = 0.0
        self._dir = "stop"
        self._lock = threading.Lock()

    def set_direction(self, direction: str):
        with self._lock:
            self._dir = direction
            if direction == "forward":
                self.in_a.on()
                self.in_b.off()
            elif direction == "reverse":
                self.in_a.off()
                self.in_b.on()
            else:  # stop
                self.in_a.off()
                self.in_b.off()

    def set_duty(self, duty: float):
        duty = max(0.0, min(100.0, float(duty)))
        with self._lock:
            self._duty = duty
            self.en.value = duty / 100.0   # gpiozero expects 0..1

    def get_duty(self) -> float:
        with self._lock:
            return self._duty

    def stop(self):
        self.set_duty(0)
        self.set_direction("stop")


class MotorController:
    def __init__(self, enable_pins: List[int], input_pins: List[int], pwm_freq: int = 1000):
        self.motors = []
        for i, en_pin in enumerate(enable_pins):
            motor = Motor(en_pin, input_pins[2 * i], input_pins[2 * i + 1], pwm_freq)
            self.motors.append(motor)

    def set_all(self, speed: float, direction: str):
        for motor in self.motors:
            motor.set_duty(speed)
            motor.set_direction(direction)

    def set_vector(self, x: float, y: float):
        """Set motor powers based on vector (x, y)."""
        speeds = [
            y + x,  # motor 1
            y - x,  # motor 2
            y + x,  # motor 3
            y - x   # motor 4
        ]
        max_speed = max(abs(s) for s in speeds)
        if max_speed > 1:
            speeds = [s / max_speed for s in speeds]

        for motor, s in zip(self.motors, speeds):
            if s >= 0:
                motor.set_direction("forward")
                motor.set_duty(abs(s) * 100)
            else:
                motor.set_direction("reverse")
                motor.set_duty(abs(s) * 100)

    def stop_all(self):
        for motor in self.motors:
            motor.stop()


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("robot/move")


def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"Received: {payload}")

    if payload == "STOP":
        userdata.stop_all()
    elif payload.startswith("MOVE"):
        try:
            _, x_str, y_str = payload.split()
            x, y = float(x_str), float(y_str)
            userdata.set_vector(x, y)
        except Exception as e:
            print("Error parsing MOVE command:", e)


def main():
    motor_controller = MotorController(ENABLE_PINS, INPUT_PINS)

    client = mqtt.Client(userdata=motor_controller)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("localhost", 1883, 60)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Stopping motors...")
        motor_controller.stop_all()


if __name__ == "__main__":
    main()
