import asyncio
import cv2
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamError, MediaStreamTrack
import aiohttp
import multiprocessing
import time
import traceback

# -----------------------------
# Top-level worker function
# -----------------------------
def webrtc_worker(link, frame_queue, start_event, stop_event, connected_event, max_frames=3):
    async def run_connection():
        try:
            while True:
                # wait for start_event
                while not start_event.is_set():
                    if stop_event.is_set():
                        return
                    await asyncio.sleep(0.1)

                pc = RTCPeerConnection()
                pc.addTransceiver("video", direction="recvonly")

                @pc.on("track")
                async def on_track(track: MediaStreamTrack):
                    if track.kind != "video":
                        return
                    try:
                        while True:
                            frame = await track.recv()
                            arr = frame.to_ndarray(format="bgr24")
                            # maintain queue size
                            if frame_queue.qsize() >= max_frames:
                                try:
                                    frame_queue.get_nowait()
                                except:
                                    pass
                            frame_queue.put_nowait(arr)
                    except MediaStreamError:
                        pass

                # SDP offer/answer
                offer = await pc.createOffer()
                await pc.setLocalDescription(offer)

                headers = {"Content-Type": "application/sdp"}
                async with aiohttp.ClientSession() as session:
                    async with session.post(f"{link}/whep", data=pc.localDescription.sdp, headers=headers) as resp:
                        if resp.status not in (200, 201):
                            text = await resp.text()
                            raise RuntimeError(f"[worker] MediaMTX error: {resp.status} {text}")
                        answer_sdp = await resp.text()

                await pc.setRemoteDescription(RTCSessionDescription(sdp=answer_sdp, type="answer"))
                connected_event.set()
                print("[worker] ✅ Connected")

                # keep alive until stop_event or start_event cleared
                while not stop_event.is_set() and start_event.is_set():
                    await asyncio.sleep(0.1)

                # close connection
                try:
                    await pc.close()
                except Exception as e:
                    print("[worker] pc.close() error:", e)
                connected_event.clear()
                await asyncio.sleep(0.05)

        except Exception as e:
            print("[worker] Exception:", e)
            traceback.print_exc()

    asyncio.run(run_connection())

# -----------------------------
# WebRTCStream class (multiprocessing)
# -----------------------------
class WebRTCStream:
    def __init__(self, link="http://192.168.77.1"):
        self.link = link
        ctx = multiprocessing.get_context()
        self.frame_queue = ctx.Queue(maxsize=3)
        self.start_event = ctx.Event()
        self.stop_event = ctx.Event()
        self.connected_event = ctx.Event()
        self.proc: multiprocessing.Process = None

    def set_stream_link(self, link):
        self.link = link

    def get_frame(self, timeout=None):
        try:
            return self.frame_queue.get(timeout=timeout)
        except:
            return None

    def start_connection(self):
        if self.proc is None or not self.proc.is_alive():
            self.start_event.clear()
            self.stop_event.clear()
            self.connected_event.clear()
            self.proc = multiprocessing.Process(
                target=webrtc_worker,
                args=(self.link, self.frame_queue, self.start_event, self.stop_event, self.connected_event),
                daemon=True
            )
            self.proc.start()
            print("[main] Worker process started (pid=%s)" % self.proc.pid)
        self.start_event.set()
        print("[main] Start event set")

    def stop_connection(self):
        self.start_event.clear()
        t0 = time.time()
        while self.connected_event.is_set() and time.time() - t0 < 5:
            time.sleep(0.05)
        print("[main] Stop event set")

    def is_connected(self, timeout=10):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.connected_event.is_set():
                return True
            time.sleep(0.05)
        return False

    def close_thread(self):
        if self.proc is None:
            return
        self.stop_event.set()
        self.start_event.clear()
        self.proc.join(timeout=2)
        if self.proc.is_alive():
            print("[main] Terminating worker process")
            self.proc.terminate()
            self.proc.join()
        print("[main] Worker process stopped")
        self.proc = None


if __name__ == "__main__":
    stream = WebRTCStream("http://192.168.212.90:8889/cam")
    stream.start_connection()

    if stream.is_connected():
        print("Connected!")

    try:
        while True:
            frame = stream.get_frame(timeout=1)
            if frame is not None:
                cv2.imshow("frame", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        stream.close_thread()
        cv2.destroyAllWindows()
