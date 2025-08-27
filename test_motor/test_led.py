import lgpio_python as lgpio
import time

CHIP = 0          # /dev/gpiochip0
LED = 18          # GPIO18 (Pin 12)

# Open GPIO chip
h = lgpio.gpiochip_open(CHIP)

# Set GPIO18 as output
lgpio.gpio_claim_output(h, LED)

try:
    for i in range(5):
        print("LED ON")
        lgpio.gpio_write(h, LED, 1)
        time.sleep(1)
        print("LED OFF")
        lgpio.gpio_write(h, LED, 0)
        time.sleep(1)
finally:
    lgpio.gpiochip_close(h)
