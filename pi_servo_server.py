from flask import Flask, request
import RPi.GPIO as GPIO
import time

app = Flask(__name__)

SERVO_PIN = 18  # BCM pin
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

pwm = GPIO.PWM(SERVO_PIN, 50)  # 50 Hz
pwm.start(0)

def set_angle(angle):
    duty = 2 + (angle / 18)
    GPIO.output(SERVO_PIN, True)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.3)
    GPIO.output(SERVO_PIN, False)
    pwm.ChangeDutyCycle(0)

@app.route("/servo")
def servo():
    angle = request.args.get("angle", default=90, type=int)
    set_angle(angle)
    return f"Servo moved to {angle}°"

app.run(host="0.0.0.0", port=5000)