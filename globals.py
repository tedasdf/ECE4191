video_url = "https://www3.cde.ca.gov/download/rod/big_buck_bunny.mp4"
audio_url = "https://samplelib.com/lib/preview/mp3/sample-9s.mp3"
# pi_url = "http://192.168.77.1:7123/stream.mjpg"
# video_url = "udp://10.173.94.23:5000"
# video_url = "tcp://192.168.21.90:5000"
# video_url = "tcp://192.168.77.1:5000"
# audio_url = "http://10.94.102.23:8080"
audio_url = "http://192.168.137.2:8080/audio.mp3"
# PI_IP = "192.168.0.145"
PI_IP = "10.94.102.23"  # Riley's Raspberry Pi IP
controller_IP = "10.1.1.79:2883" # R25's MQTT server address

upKeyState = False
downKeyState = False
leftKeyState = False
rightKeyState = False

streaming = False
capture = None
audio_stream_process = None
audio_stream = None