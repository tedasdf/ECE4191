import serial
import time

# Replace 'COM3' with your Arduino port (e.g., '/dev/ttyACM0' on Linux)
arduino = serial.Serial('COM3', 9600)
time.sleep(2)  # wait for Arduino to reset

# Move continuous servo forward
arduino.write(b'S1:180\n')  # speed forward
# Move standard servo to angle 90
arduino.write(b'S2:90\n')

time.sleep(2)

# Stop continuous servo
arduino.write(b'S1:90\n')

# Move standard servo back
arduino.write(b'S2:0\n')
