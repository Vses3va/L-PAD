import os
import cv2
import mediapipe as mp
from config import THRESHOLDS
from anti_spoofing import LivenessDetector

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

class FaceProcessor:
    def __init__(self):
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def process(self, frame):
        if frame is None: return {"detected": False}
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)
        analysis = {
            "detected": False, 
            "bbox": None,
            "glare": False,
            "brightness": 0.0,
            "light_center": 0.0,
            "light_edge": 0.0
        }
        if results.multi_face_landmarks:
            mesh = results.multi_face_landmarks[0]
            h, w, _ = frame.shape
            pts = []
            for lm in mesh.landmark:
                pts.append((int(lm.x * w), int(lm.y * h)))
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            pad = 20
            bbox = (max(0, min(xs)-pad), max(0, min(ys)-pad), min(w, max(xs)+pad), min(h, max(ys)+pad))
            analysis["bbox"] = bbox
            analysis["glare"] = LivenessDetector.check_specular_highlights(frame, bbox)
            analysis["brightness"] = LivenessDetector.get_face_brightness(frame, bbox)
            lc, le = LivenessDetector.get_face_light_distribution(frame, pts)
            analysis["light_center"] = lc
            analysis["light_edge"] = le
            analysis["detected"] = True
        return analysis