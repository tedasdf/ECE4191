from flask import Flask, request
import RPi.GPIO as GPIO
import time

app = Flask(__name__)

SERVO_PIN_PAN = 13  # BCM pin
SERVO_PIN_TILT = 17 
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN_PAN, GPIO.OUT)
GPIO.setup(SERVO_PIN_TILT, GPIO.OUT)

pwm_pan = GPIO.PWM(SERVO_PIN_PAN, 50)  # 50 Hz
pwm_tilt = GPIO.PWM(SERVO_PIN_TILT, 50)  # 50 Hz

pwm_pan.start(0)
pwm_tilt.start(0)

def set_angle(angle, SERVO_PIN, pwm):
    duty = 2 + (angle / 18)
    GPIO.output(SERVO_PIN, True)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.3)
    GPIO.output(SERVO_PIN, False)
    pwm.ChangeDutyCycle(0)

@app.route("/servo")
def servo():
    pan_angle = request.args.get("pan_angle", default=90, type=int)
    tilt_angle = request.args.get("tilt_angle", default=90, type=int)
    set_angle(pan_angle, SERVO_PIN_PAN, pwm_pan)
    set_angle(tilt_angle, SERVO_PIN_TILT, pwm_tilt)
    return f"Servo moved to {pan_angle}° pan and {tilt_angle}° tilt"

app.run(host="0.0.0.0", port=5000)