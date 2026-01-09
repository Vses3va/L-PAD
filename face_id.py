import cv2
import os
import numpy as np
import shutil
from config import USERS_DIR, MODEL_FILE

class FaceIDSystem:
    def __init__(self):
        self.rec = cv2.face.LBPHFaceRecognizer_create()
        self.trained = False
        self.names = {}
        self.load()

    def load(self):
        if os.path.exists(MODEL_FILE):
            try:
                self.rec.read(MODEL_FILE)
                self.update_names()
                self.trained = True
            except: pass

    def update_names(self):
        self.names = {}
        if not os.path.exists(USERS_DIR): return
        for i, name in enumerate(sorted(os.listdir(USERS_DIR))):
            self.names[i] = name

    def save_sample(self, frame, bbox, name, count):
        if bbox is None: return False
        x1, y1, x2, y2 = bbox
        w, h = x2 - x1, y2 - y1
        
        try:
            face = frame[y1:y2, x1:x2]
            if face.size == 0: return False
            gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (200, 200))
            
            path = os.path.join(USERS_DIR, name)
            os.makedirs(path, exist_ok=True)
            cv2.imwrite(f"{path}/{count}.jpg", gray)
            return True
        except: return False

    def train(self):
        print("\n[INFO] Обучение модели...")
        faces, ids = [], []
        
        if not os.path.exists(USERS_DIR): return
        
        for i, name in enumerate(sorted(os.listdir(USERS_DIR))):
            path = os.path.join(USERS_DIR, name)
            for file in os.listdir(path):
                try:
                    img = cv2.imread(os.path.join(path, file), cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        faces.append(img)
                        ids.append(i)
                except: pass
        
        if faces:
            self.rec.train(faces, np.array(ids))
            self.rec.write(MODEL_FILE)
            self.update_names()
            self.trained = True
            print(f"[OK] Модель обучена. Пользователей: {len(self.names)}")
        else:
            print("[ERR] Нет данных для обучения!")

    def delete_user(self, name):
        path = os.path.join(USERS_DIR, name)
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
                print(f"[OK] Папка {name} удалена.")
                self.train()
                return True
            except Exception as e:
                print(f"[ERR] Ошибка удаления: {e}")
        return False

    def recognize(self, frame, bbox):
        if bbox is None: return "Unknown", 0
        if not self.trained: return "Unknown", 0
        
        x1, y1, x2, y2 = bbox
        w, h = x2 - x1, y2 - y1
        
        try:
            face = frame[y1:y2, x1:x2]
            gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (200, 200))
            
            id_, conf = self.rec.predict(gray)
            score = max(0, 100 - conf)
            
            name = self.names.get(id_, "Unknown")
            return name, score

        except: return "Error", 0
