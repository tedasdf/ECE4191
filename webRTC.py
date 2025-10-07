import asyncio, cv2
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamError, MediaStreamTrack
import aiohttp
import queue
import threading

class WebRTCStream:
    def __init__(self, link="192.168.77.1"):
        self.link: str = link
        # WebRTC objects
        self.peer_connection: RTCPeerConnection = None
        self.whep_answer: str = None
        self.buffer = queue.Queue(maxsize=3)  # buffer for video frames
        
        self.thread_loop: asyncio.AbstractEventLoop = None
        self.start_event: asyncio.Event = None
        self.stop_event: asyncio.Event = None
        self.stream_connected: asyncio.Event = None

    def set_stream_link(self, link):
        self.link = link
    
    def get_frame(self, timeout=None):
        try:
            frame = self.buffer.get(timeout=timeout)
            return frame
        except queue.Empty:
            return None

    def get_peer_connection(self):
        return self.peer_connection
    
    def start_thread(self):
        if self.thread_loop is None or not self.thread_loop.is_running():
            self.thread_loop = asyncio.new_event_loop()
            threading.Thread(target=lambda: self.thread_loop.run_forever(), daemon=True).start()
            asyncio.run_coroutine_threadsafe(self._connection_loop(), self.thread_loop)

    def close_thread(self):
        if self.thread_loop is not None and self.thread_loop.is_running():
            if self.stop_event is not None:
                self.stop_event.set()
            self.thread_loop.call_soon_threadsafe(self.thread_loop.stop)
            self.thread_loop = None
            print("Video thread: Thread closed")
    
    async def _set_start_event(self):
        if self.start_event is not None:
            self.start_event.set()

    async def _set_stop_event(self):
        if self.stop_event is not None:
            self.stop_event.set()

    def start_connection(self):
        if self.start_event is not None:
            job = asyncio.run_coroutine_threadsafe(self._set_start_event(), self.thread_loop)
            job.result()  # wait for it to complete
            print("Video thread: Start event set")

    def stop_connection(self):
        if self.stop_event is not None:
            job = asyncio.run_coroutine_threadsafe(self._set_stop_event(), self.thread_loop)
            job.result()  # wait for it to complete
            print("Video thread: Stop event set")

    def is_connected(self):
        return self.stream_connected.is_set() if self.stream_connected else False

    async def _connection_loop(self):
        try:
            self.stop_event = asyncio.Event()
            self.start_event = asyncio.Event()
            self.stream_connected = asyncio.Event()

            while True:
                pc = RTCPeerConnection()
                print("Video thread: Waiting for start event...")

                await self.start_event.wait()
                print("Video thread: Start event detected, starting connection...")

                pc.addTransceiver("video", direction="recvonly")
                # pc.addTransceiver("audio", direction="recvonly")

                # Handle incoming tracks (audio/video)
                @pc.on("track")
                async def on_track(track: MediaStreamTrack):
                    print(f"Video thread: Track {track.kind} received!")
                    if track.kind == "audio":
                        print("Video thread: Audio track received, but not handled in this implementation.")
                        return
                    # You can process the track here, e.g., save video frames or play audio
                    try:
                        while True:
                            try:
                                frame = await track.recv()
                            except asyncio.TimeoutError:
                                print("Video thread: Timeout waiting for video frame")
                                continue
                            
                            # print("Video thread: Video frame received")

                            frame = frame.to_ndarray(format="bgr24")
                            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                            try:
                                self.buffer.put_nowait(frame)
                            except queue.Full:
                                self.buffer.get_nowait()  # discard oldest frame
                                self.buffer.put_nowait(frame)

                    except MediaStreamError:
                        print("Video thread: Track ended")

                # Create an SDP offer
                offer = await pc.createOffer()
                await pc.setLocalDescription(offer)

                print("Video thread: Sending offer to MediaMTX...")

                headers = {"Content-Type": "application/sdp"}
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                            f"{self.link}/whep", 
                            data=pc.localDescription.sdp, 
                            headers=headers
                        ) as resp:
                        if resp.status not in (200, 201):
                            raise RuntimeError(f"Video thread: MediaMTX error: {resp.status} {await resp.text()}")
                        self.whep_answer = await resp.text()
                
                answer = RTCSessionDescription(sdp=self.whep_answer, type="answer")

                print("Video thread: Received answer")
                # print(self.whep_answer)

                await pc.setRemoteDescription(answer)

                self.stream_connected.set()

                print("Video thread: ✅ Connected to MediaMTX WebRTC stream")
                print("Video thread: Press 'q' in the video window to exit.")

                # self.peer_connection = pc

                # Keep the connection alive
                # try:
                #     while not self.stop_event.is_set():
                #         await asyncio.sleep(1)
                #         print("Connection alive...")
                # except KeyboardInterrupt:
                #     pass

                await self.stop_event.wait()
                print("Video thread: Stop event set, closing connection...")
                try:
                    await asyncio.wait_for(pc.close(), timeout=5)
                except asyncio.TimeoutError:
                    print("Video thread: Timeout waiting for peer connection to close")
                print("Video thread: Peer connection closed")
                
                self.peer_connection = None
                self.whep_answer = None
                self.start_event.clear()
                self.stop_event.clear()
                self.stream_connected.clear()
                while not self.buffer.empty():
                    self.buffer.get_nowait()  # clear buffer

                print("Video thread: Exiting connection loop")
        except KeyboardInterrupt:
            print(f"Video thread: Keyboard interrupt, exiting...")

