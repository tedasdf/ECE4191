import RPi.GPIO as GPIO
import time

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


while True:
    set_pan_speed(-50, SERVO_PIN_PAN, pwm_pan)
    time.sleep(1)
    set_pan_speed(20, SERVO_PIN_PAN, pwm_pan)
    time.sleep(1)


    # for angle in range(0, 90, 5):
    #     set_tilt_angle(angle, SERVO_PIN_TILT, pwm_tilt)
    #     print(f'set tilt to {angle}')
    # time.sleep(2)
    # set_tilt_angle(0, SERVO_PIN_TILT, pwm_tilt)
    # print(f'set tilt to {0}')
    # time.sleep(2)