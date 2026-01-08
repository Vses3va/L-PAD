import cv2
import numpy as np
from config import THRESHOLDS

class LivenessDetector:
    @staticmethod
    def check_specular_highlights(image, bbox):
        try:
            x1, y1, x2, y2 = bbox
            h, w, _ = image.shape
            face = image[max(0,y1):min(h,y2), max(0,x1):min(w,x2)]
            if face.size == 0: return False
            gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
            count = np.count_nonzero(gray > THRESHOLDS["specular_threshold"])
            return (count / gray.size) > THRESHOLDS["specular_ratio"]
        except: return False

    @staticmethod
    def get_face_brightness(frame, bbox):
        try:
            x1, y1, x2, y2 = bbox
            h, w, _ = frame.shape
            cx, cy = (x1+x2)//2, (y1+y2)//2
            w_f, h_f = (x2-x1)//4, (y2-y1)//4
            face = frame[max(0, cy-h_f):min(h, cy+h_f), max(0, cx-w_f):min(w, cx+w_f)]
            if face.size == 0: return 0.0
            lab = cv2.cvtColor(face, cv2.COLOR_BGR2LAB)
            return np.mean(lab[:,:,0])
        except: return 0.0
        
    @staticmethod
    def get_face_light_distribution(frame, landmarks):
        try:
            h, w, _ = frame.shape
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            nx, ny = int(landmarks[1][0]), int(landmarks[1][1])
            nose_roi = gray[max(0, ny-10):min(h, ny+10), max(0, nx-10):min(w, nx+10)]
            c = np.mean(nose_roi) if nose_roi.size > 0 else 0
            edge_vals = []
            for idx in [234, 454]:
                ex, ey = int(landmarks[idx][0]), int(landmarks[idx][1])
                roi = gray[max(0, ey-10):min(h, ey+10), max(0, ex-10):min(w, ex+10)]
                if roi.size > 0: edge_vals.append(np.mean(roi))
            e = np.mean(edge_vals) if edge_vals else 0
            return c, e
        except: return 0.0, 0.0