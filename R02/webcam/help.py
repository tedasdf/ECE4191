import subprocess

def list_devices():
    cmd = ['ffmpeg', '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy']
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(proc)
    out, err = proc.communicate()  # wait for process to finish
    print(err)
    for line in err.splitlines():  # FFmpeg lists devices in stderr
        print(line)
        if "DirectShow video devices" in line or "DirectShow audio devices" in line:
            print("\n" + line.strip())
        elif '  "' in line:
            print(line.strip())

if __name__ == "__main__":
    list_devices()
