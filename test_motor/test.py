# sudo apt install pigpio
# sudo systemctl start pigpiod
import pigpio, time
pi = pigpio.pi()
SERVO = 18   # GPIO18 (Pin 12)

def pulse(us):  # set pulse width in microseconds
    pi.set_servo_pulsewidth(SERVO, us)

try:
    pulse(1500)           # stop
    time.sleep(1)
    pulse(1300)           # slow one direction
    time.sleep(2)
    pulse(1700)           # slow other direction
    time.sleep(2)
    pulse(0)              # turn off pulses
finally:
    pi.set_servo_pulsewidth(SERVO, 0)
    pi.stop()
