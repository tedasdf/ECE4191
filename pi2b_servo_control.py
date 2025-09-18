from flask import Flask, request
import RPi.GPIO as GPIO
import time
import threading

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

def set_pan_speed_old(speed_percent, SERVO_PIN, pwm):
    duty = 7.5 + (speed_percent / 200) * 5
    GPIO.output(SERVO_PIN, True)
    pwm.ChangeDutyCycle(duty)
    time.sleep(3)
    GPIO.output(SERVO_PIN, False)
    pwm.ChangeDutyCycle(7.5)

def set_pan_speed(speed_percent, pwm):
    duty = 7.5 + (speed_percent / 200) * 5
    pwm.ChangeDutyCycle(duty)


@app.route("/tiltUp")
def tiltUp():
    print("tiltUp Request received.")

    threading.Thread(
            target=tilt_servo,
            args=(pwm_tilt, 0, 90), 
            daemon=True
        ).start()

    return f"servo tilting up"

@app.route("/tiltDown")
def tiltDown():
    print("tiltDown Request received.")

    threading.Thread(
            target=tilt_servo,
            args=(pwm_tilt, 90, 0), 
            daemon=True
        ).start()

    return f"servo tilting down"

@app.route("/tiltStop")
def tiltStop():
    print("tiltStop Request received.")

    return f"servo tilting stopped"


@app.route("/panLeft")
def panLeft():
    print("panleft Request received.")

    set_pan_speed(-50, pwm_pan)

    return f"servo panning left"

@app.route("/panRight")
def panRight():
    print("tiltDown Request received.")

    # set pan speed to -ive
    set_pan_speed(50, pwm_pan)

    return f"servo panning right"

@app.route("/panStop")
def panStop():
    print("panStop Request received.")

    # set pan speed to zero
    set_pan_speed(0, pwm_pan)

    return f"servo pan stop"



def tilt_servo(pwm, start_angle, end_angle, step=1, delay=0.02):
    """
    Gradually move an SG90 servo from start_angle to end_angle.
    
    :param pin: GPIO pin number (BCM mode).
    :param start_angle: Starting angle in degrees (0 to 90).
    :param end_angle: Target angle in degrees (0 to 90).
    :param step: Step size in degrees (default 1).
    :param delay: Delay between steps in seconds (default 0.02s).
    """
    def angle_to_duty(angle):
        # Map 0–90 degrees → 2.5–12.5% duty cycle
        return 2.5 + (angle / 90.0) * 10

    # Determine direction of motion
    if start_angle < end_angle:
        angle_range = range(start_angle, end_angle + 1, step)
    else:
        angle_range = range(start_angle, end_angle - 1, -step)

    for angle in angle_range:
        duty = angle_to_duty(angle)
        pwm.ChangeDutyCycle(duty)
        time.sleep(delay)


# app.run(host="0.0.0.0", port=5000)
set_pan_speed_old(50, SERVO_PIN_PAN, pwm_pan)
