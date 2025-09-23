import asyncio
import json
import logging
import cv2
from fractions import Fraction
from aiohttp import web
from av import VideoFrame
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from ultralytics import YOLO

logging.basicConfig(level=logging.INFO)

# ---------- Camera + YOLO track ----------
class CameraVideoTrack(VideoStreamTrack):
    kind = "video"

    def __init__(self, cam_index=0, model_path="best.pt"):
        super().__init__()
        self.cap = cv2.VideoCapture(cam_index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera {cam_index}")
        self.model = YOLO(model_path)

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        ret, frame = self.cap.read()
        if not ret:
            return None

        # Skip frames for YOLO
        self.frame_count = getattr(self, "frame_count", 0) + 1
        if self.frame_count % 2 == 0:
            self.last_results = self.model(frame, verbose=False)

        # Use last annotated frame if available
        annotated = self.last_results[0].plot() if hasattr(self, "last_results") else frame

        frame_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        video_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame


camera_track = CameraVideoTrack()

pcs = set()

# ---------- Routes ----------
async def index(request):
    return web.FileResponse("index.html")

async def offer(request):
    try:
        params = await request.json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

        pc = RTCPeerConnection()
        pcs.add(pc)

        # Add outgoing video track BEFORE creating answer
        pc.addTrack(camera_track)

        # Handle connection state changes
        @pc.on("connectionstatechange")
        async def on_state_change():
            logging.info(f"Connection state: {pc.connectionState}")
            if pc.connectionState in ["failed", "closed"]:
                await pc.close()
                pcs.discard(pc)

        # Set remote description (browser offer)
        await pc.setRemoteDescription(offer)

        # Create and set local answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)

        return web.json_response({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return web.json_response({"error": str(e)}, status=500)

async def on_shutdown(app):
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

# ---------- App ----------
app = web.Application()
app.on_shutdown.append(on_shutdown)
app.router.add_get("/", index)
app.router.add_post("/offer", offer)

if __name__ == "__main__":
    web.run_app(app, host="127.0.0.1", port=8080)
