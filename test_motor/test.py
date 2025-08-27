import lgpio
import time

CHIP = 0          # first GPIO chip (/dev/gpiochip0)
SERVO = 18        # GPIO18 (Pin 12), has hardware PWM

# Open the chip
h = lgpio.gpiochip_open(CHIP)

# Start PWM: 50 Hz (standard for servos), 7.5% duty = ~1500 µs pulse
lgpio.tx_pwm(h, SERVO, 50, 7.5)

try:
    print("Stop (neutral)")
    time.sleep(2)

    print("Rotate one way (pulse ~1300µs → ~6.5% duty)")
    lgpio.tx_pwm(h, SERVO, 50, 6.5)
    time.sleep(2)

    print("Rotate other way (pulse ~1700µs → ~8.5% duty)")
    lgpio.tx_pwm(h, SERVO, 50, 8.5)
    time.sleep(2)

    print("Stop")
    lgpio.tx_pwm(h, SERVO, 50, 7.5)
    time.sleep(2)

finally:
    lgpio.tx_pwm(h, SERVO, 0, 0)      # stop PWM
    lgpio.gpiochip_close(h)
