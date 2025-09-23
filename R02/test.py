from aiohttp import web
import json
import asyncio
import cv2
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
import time
from fractions import Fraction
from ultralytics import YOLO
import logging

logging.basicConfig(level=logging.INFO)
from aiortc import VideoStreamTrack
from av import VideoFrame
import cv2
from fractions import Fraction
from ultralytics import YOLO

class CameraVideoTrack(VideoStreamTrack):
    kind = "video"

    def __init__(self, cam_index=0, model_path="best.pt", skip_frames=2):
        super().__init__()
        self.cap = cv2.VideoCapture(cam_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {cam_index}")

        self.model = YOLO(model_path)      # YOLO model
        self.skip_frames = skip_frames     # Process YOLO every N frames
        self.frame_count = 0               # Counter
        self.last_results = None           # Last annotated frame

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        ret, frame = self.cap.read()
        if not ret:
            return None

        self.frame_count += 1

        # Run YOLO only every N frames
        if self.frame_count % self.skip_frames == 0:
            results = self.model(frame, verbose=False)
            self.last_results = results[0].plot()  # annotated frame

        annotated = self.last_results if self.last_results is not None else frame

        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)

        # Return WebRTC frame
        video_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

    def __del__(self):
        if hasattr(self, "cap"):
            self.cap.release()


# ----- WebRTC -----
pcs = set()
camera_track = CameraVideoTrack()
async def offer(request):
    try:
        params = await request.json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

        pc = RTCPeerConnection()
        
        pcs.add(pc)

        # Add camera track before creating answer
        pc.addTrack(camera_track)

        # Set remote (browser) offer
        await pc.setRemoteDescription(offer)

        # Create local answer
        answer = await pc.createAnswer()
        print('==============ANSWER================')
        print(answer)
        await pc.setLocalDescription(answer)

        return web.json_response({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return web.json_response({"error": str(e)}, status=500)


async def index(request):
    return web.FileResponse("index.html")

async def on_shutdown(app):
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

# ----- Start server -----
app = web.Application()
app.on_shutdown.append(on_shutdown)
app.router.add_get("/", index)
app.router.add_post("/offer", offer)

if __name__ == "__main__":
    web.run_app(app, host="127.0.0.1", port=8080)
