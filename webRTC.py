import asyncio, cv2, requests, typing
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamError
import aiohttp

from PIL import Image, ImageTk
import tkinter as tk


class WebRTCStream:
    def __init__(self, link="192.168.77.1"):
        self.link: str = link
        # WebRTC objects
        self.peer_connection: RTCPeerConnection = None
        self.whep_answer: str = None
        self.buffer: list = None
        self.stop_event: asyncio.Event = asyncio.Event()

    def set_stream_link(self, link):
        self.link = link
    
    def set_buffer(self, buffer):
        self.buffer = buffer

    def get_peer_connection(self):
        return self.peer_connection
    
    # def start_stream(self):

    async def connect_to_server(self, vid_label: tk.Label=None, frame_buffer: list=None, stop_event=None):
        pc = RTCPeerConnection()
        self.stop_event = asyncio.Event()

        pc.addTransceiver("video", direction="recvonly")
        # pc.addTransceiver("audio", direction="recvonly")

        # Handle incoming tracks (audio/video)
        @pc.on("track")
        async def on_track(track):
            print(f"Track {track.kind} received!")
            # You can process the track here, e.g., save video frames or play audio
            try:
                while True:
                    frame = await track.recv()
                    if not vid_label:
                        img = frame.to_ndarray(format="bgr24")
                        self.buffer.append(img)
                    # await asyncio.sleep(0.03)
                    else:
                        frame_array = frame.to_ndarray(format="bgr24")
                        frame_array = cv2.cvtColor(frame_array, cv2.COLOR_BGR2RGB)
                        frame_array = cv2.resize(frame_array, (600, 400))  # fit the label size
                        img = Image.fromarray(frame_array)
                        imgtk = ImageTk.PhotoImage(image=img)
                        vid_label.imgtk = imgtk
                        vid_label.config(image=imgtk)
                        frame_buffer.append(frame_array.copy())
            except MediaStreamError:
                print("Track ended")

        # Create an SDP offer
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)

        print("Sending offer to MediaMTX...")

        headers = {"Content-Type": "application/sdp"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    f"{self.link}/whep", 
                    data=pc.localDescription.sdp, 
                    headers=headers
                ) as resp:
                if resp.status not in (200, 201):
                    raise RuntimeError(f"MediaMTX error: {resp.status} {await resp.text()}")
                self.whep_answer = await resp.text()
        
        answer = RTCSessionDescription(sdp=self.whep_answer, type="answer")

        # print("Received answer:")
        # print(self.whep_answer)

        await pc.setRemoteDescription(answer)

        print("✅ Connected to MediaMTX WebRTC stream")
        print("Press 'q' in the video window to exit.")

        self.peer_connection = pc

        # Keep the connection alive
        # try:
        #     while not self.stop_event.is_set():
        #         await asyncio.sleep(1)
        #         print("Connection alive...")
        # except KeyboardInterrupt:
        #     pass

        await self.stop_event.wait()
        await self.peer_connection.close()
        self.peer_connection = None
        self.whep_answer = None        

        print("Exiting connection loop")


    async def close_connection(self):
        self.stop_event.set() # Close the connection loop
        # Reset state
        # self.stop_event = asyncio.Event()
        print("Connection closed")

async def display_frames(buffer, stop_event: asyncio.Event):
    print("Display frame running")

    while not stop_event.is_set():
        print(len(buffer))
        if buffer:
            frame = buffer.pop(0)
            cv2.imshow("MediaMTX Stream", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
        await asyncio.sleep(0.005)  # yield to other tasks

    print("display_frames stopped")

async def main():
    rtc_stream = WebRTCStream("http://192.168.0.236:8889/blacklist")
    stream_buffer = []
    rtc_stream.set_buffer(stream_buffer)

    await rtc_stream.connect_to_server()  # run in async loop

    print("Connect returned")

    stop_event = asyncio.Event()
    display_task = asyncio.create_task(display_frames(stream_buffer, stop_event))

    await asyncio.sleep(60)
    
    stop_event.set()
    await display_task

    await rtc_stream.close_connection()

    print("Main exitted")

if __name__ == "__main__":
    asyncio.run(main())