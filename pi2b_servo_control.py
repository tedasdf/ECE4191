from flask import Flask, request
import RPi.GPIO as GPIO
import time

app = Flask(__name__)

SERVO_PIN_PAN = 11  # BOARD pin
SERVO_PIN_TILT = 12 
GPIO.setmode(GPIO.BOARD)
GPIO.setup(SERVO_PIN_PAN, GPIO.OUT)
GPIO.setup(SERVO_PIN_TILT, GPIO.OUT)

pwm_pan = GPIO.PWM(SERVO_PIN_PAN, 50)  # 50 Hz
pwm_tilt = GPIO.PWM(SERVO_PIN_TILT, 50)  # 50 Hz

pwm_pan.start(0)
pwm_tilt.start(0)

def set_tilt_angle(angle, SERVO_PIN, pwm):
    duty = 2 + (angle / 12)
    GPIO.output(SERVO_PIN, True)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.3)
    GPIO.output(SERVO_PIN, False)
    pwm.ChangeDutyCycle(0)

def set_pan_speed(speed_percent, SERVO_PIN, pwm):
    duty = 7.5 + (speed_percent / 200) * 5
    GPIO.output(SERVO_PIN, True)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.2)
    GPIO.output(SERVO_PIN, False)
    pwm.ChangeDutyCycle(7.5)

@app.route("/tiltUp")
def tiltUp():
    print("tiltUp Request received.")

    # pan_speed_percent = request.args.get("pan_speed_percent", default=0, type=int)
    # tilt_angle = request.args.get("tilt_angle", default=90, type=int)
    # set_pan_speed(pan_speed_percent, SERVO_PIN_PAN, pwm_pan)
    # set_tilt_angle(tilt_angle, SERVO_PIN_TILT, pwm_tilt)
    return f"servo tilting up"

@app.route("/tiltDown")
def tiltDown():
    print("tiltDown Request received.")

    # pan_speed_percent = request.args.get("pan_speed_percent", default=0, type=int)
    # tilt_angle = request.args.get("tilt_angle", default=90, type=int)
    # set_pan_speed(pan_speed_percent, SERVO_PIN_PAN, pwm_pan)
    # set_tilt_angle(tilt_angle, SERVO_PIN_TILT, pwm_tilt)
    return f"servo tilting down"

@app.route("/tiltStop")
def tiltStop():
    print("tiltStop Request received.")

    # pan_speed_percent = request.args.get("pan_speed_percent", default=0, type=int)
    # tilt_angle = request.args.get("tilt_angle", default=90, type=int)
    # set_pan_speed(pan_speed_percent, SERVO_PIN_PAN, pwm_pan)
    # set_tilt_angle(tilt_angle, SERVO_PIN_TILT, pwm_tilt)
    return f"servo tilting stopped"

app.run(host="0.0.0.0", port=5000)