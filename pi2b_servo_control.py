from flask import Flask
import time
import threading
import pigpio

app = Flask(__name__)

# Shared state
class TiltServo:
    def __init__(self, pin, angle=90):
        self.angle = angle
        self.direction = "stop"   # "up", "down", or "stop"
        self.pin = pin
        self.lock = threading.Lock()


# BCM pin number (physical pin 11 = GPIO17)
TILT_PIN = 17  

# Initialise pigpio
pi = pigpio.pi()
if not pi.connected:
    exit("Could not connect to pigpio daemon. Did you run 'sudo pigpiod'?")
    
tiltServo = TiltServo(TILT_PIN, 90)


def angle_to_pw(angle):
    # returns the pulse width associated with the given angle (0° → 500 µs, 180° → 2500 µs)
    return 500 + 2000 * (angle / 180.0)

def set_servo_angle(angle, pin):
    pw = angle_to_pw(angle)
    pi.set_servo_pulsewidth(pin, pw)

# Background worker to gradually tilt
def tilt_worker():
    while True:
        time.sleep(0.01)  # adjust speed (10 ms step)
        with tiltServo.lock:
            if tiltServo.direction == "up":
                if tiltServo.angle < 180:
                    tiltServo.angle += 1
                    set_servo_angle(tiltServo.angle, tiltServo.pin)
            elif tiltServo.direction == "down":
                if tiltServo.angle > 0:
                    tiltServo.angle -= 1
                    set_servo_angle(tiltServo.angle, tiltServo.pin)
            # else: "stop" do nothing

# Start the worker thread
threading.Thread(target=tilt_worker, daemon=True).start()

@app.route("/tiltUp")
def tilt_up():
    with tiltServo.lock:
        tiltServo.direction = "up"
    return "servo tilting up"

@app.route("/tiltDown")
def tilt_down():
    with tiltServo.lock:
        tiltServo.direction = "down"
    return "servo tilting down"

@app.route("/tiltStop")
def tilt_stop():
    with tiltServo.lock:
        tiltServo.direction = "stop"
    return "servo stopped"

try:
    # Initialise at center
    print(tiltServo.pin)
    set_servo_angle(tiltServo.angle, tiltServo.pin)
    app.run(host="0.0.0.0", port=5000)
finally:
    pi.set_servo_pulsewidth(tiltServo.pin, 0)
    pi.stop()
