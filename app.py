import os
import sys
import contextlib
import hashlib

@contextlib.contextmanager
def suppress_stderr():
    try:
        with open(os.devnull, "w") as devnull:
            old_stderr = sys.stderr.fileno()
            saved_stderr = os.dup(old_stderr)
            try:
                os.dup2(devnull.fileno(), old_stderr)
                yield
            finally:
                os.dup2(saved_stderr, old_stderr)
                os.close(saved_stderr)
    except: yield

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
with suppress_stderr():
    import tkinter as tk
    from tkinter import simpledialog, messagebox
    import cv2
    import PIL.Image, PIL.ImageTk
    import numpy as np
    from lpad_core import FaceProcessor

import time
from colorama import init, Fore, Style
from config import *
from face_id import FaceIDSystem

init(autoreset=True)

class LPadApp:
    def __init__(self, window, window_title):
        self.window = window
        self.window.title(window_title)
        
        self.check_first_run()
        
        with suppress_stderr():
            self.proc = FaceProcessor()
            dummy = np.zeros((720, 1280, 3), dtype=np.uint8)
            self.proc.process(dummy)
        
        self.id_sys = FaceIDSystem()
        
        self.cap = None
        self.start_camera()

        self.video_label = tk.Label(window)
        self.video_label.pack(side=tk.TOP, padx=10, pady=10)

        self.btn_frame = tk.Frame(window)
        self.btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=20)

        self.btn_reg = tk.Button(self.btn_frame, text="1. РЕГИСТРАЦИЯ", width=15, height=2, command=self.start_registration)
        self.btn_reg.pack(side=tk.LEFT, padx=5)

        self.btn_sec = tk.Button(self.btn_frame, text="2. ОХРАНА", width=15, height=2, bg="#ccffcc", command=self.start_security)
        self.btn_sec.pack(side=tk.LEFT, padx=5)

        self.btn_del = tk.Button(self.btn_frame, text="3. УДАЛИТЬ", width=15, height=2, command=self.delete_user)
        self.btn_del.pack(side=tk.LEFT, padx=5)
        
        self.btn_pass = tk.Button(self.btn_frame, text="ПАРОЛЬ", width=10, height=2, bg="#ffffcc", command=self.change_password)
        self.btn_pass.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = tk.Button(self.btn_frame, text="СТОП", width=10, height=2, bg="#ffcccc", command=self.stop_mode)
        self.btn_stop.pack(side=tk.LEFT, padx=20)

        self.mode = "IDLE" 
        self.reg_name = ""
        self.reg_count = 0
        
        self.sec_state = "scan"
        self.user = ""
        self.flash_state = 0
        self.flash_timer = 0
        self.min_dark_val = 0
        self.max_light_val = 0
        self.max_center_bright = 0
        self.max_edge_bright = 0
        self.current_thresholds = THRESHOLDS.copy()
        self.last_check_time = 0
        self.flash_attempts = 0
        
        self.update_video()
        self.window.mainloop()

    def get_hash(self, text):
        return hashlib.sha256(text.encode()).hexdigest()

    def check_first_run(self):
        if not os.path.exists(PASSWORD_FILE):
            messagebox.showinfo("Setup", "Первый запуск! Установите пароль администратора.")
            while True:
                p1 = simpledialog.askstring("Setup", "Придумайте пароль:", show='*')
                if not p1: sys.exit()
                p2 = simpledialog.askstring("Setup", "Подтвердите пароль:", show='*')
                if p1 == p2:
                    with open(PASSWORD_FILE, "w") as f:
                        f.write(self.get_hash(p1))
                    messagebox.showinfo("Success", "Пароль установлен!")
                    break
                else:
                    messagebox.showerror("Error", "Пароли не совпадают!")

    def verify_admin(self):
        pwd = simpledialog.askstring("Auth", "Введите пароль администратора:", show='*')
        if not pwd: return False
        
        if not os.path.exists(PASSWORD_FILE):
            return False
            
        with open(PASSWORD_FILE, "r") as f:
            stored_hash = f.read().strip()
            
        if self.get_hash(pwd) == stored_hash:
            return True
        else:
            messagebox.showerror("Error", "Неверный пароль!")
            return False

    def change_password(self):
        if not self.verify_admin(): return
        
        while True:
            p1 = simpledialog.askstring("Change", "Новый пароль:", show='*')
            if not p1: return
            p2 = simpledialog.askstring("Change", "Подтвердите новый пароль:", show='*')
            
            if p1 == p2:
                with open(PASSWORD_FILE, "w") as f:
                    f.write(self.get_hash(p1))
                messagebox.showinfo("Success", "Пароль успешно изменен!")
                break
            else:
                messagebox.showerror("Error", "Пароли не совпадают!")

    def start_camera(self):
        if self.cap: self.cap.release()
        with suppress_stderr():
            self.cap = cv2.VideoCapture(CAMERA_ID, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(0)
            self.cap.set(3, FRAME_WIDTH)
            self.cap.set(4, FRAME_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FPS, 60)

    def stop_mode(self):
        self.mode = "IDLE"
        self.flash_state = 0

    def delete_user(self):
        if not self.verify_admin(): return
        name = simpledialog.askstring("Delete", "Кого удалить (Имя):")
        if name: self.id_sys.delete_user(name)

    def start_registration(self):
        if not self.verify_admin(): return
        name = simpledialog.askstring("Reg", "Имя нового пользователя:")
        if not name: return
        self.reg_name = name
        self.reg_count = 0
        self.mode = "REG"

    def start_security(self):
        if not self.id_sys.trained:
            messagebox.showerror("Error", "База пуста! Сначала добавьте пользователя.")
            return
        self.sec_state = "scan"
        self.flash_state = 0
        self.flash_attempts = 0
        self.current_thresholds = THRESHOLDS.copy()
        self.mode = "SECURITY"

    def update_video(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                res = self.proc.process(frame)
                
                if self.mode == "REG":
                    self.process_registration(frame, res)
                elif self.mode == "SECURITY":
                    frame = self.process_security(frame, res)
                else:
                    cv2.putText(frame, "IDLE MODE", (30,50), 1, 2, (200,200,200), 2)

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = PIL.Image.fromarray(rgb)
                imgtk = PIL.ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)

        self.window.after(10, self.update_video)

    def process_registration(self, frame, res):
        cv2.putText(frame, f"REC: {self.reg_count}/25", (30, 50), 1, 2, (0, 255, 0), 2)
        if res["detected"]:
            bbox = res["bbox"]
            cv2.rectangle(frame, (bbox[0],bbox[1]), (bbox[2],bbox[3]), (0,255,0), 2)
            if self.reg_count < 25:
                if self.id_sys.save_sample(frame, bbox, self.reg_name, self.reg_count):
                    self.reg_count += 1
            else:
                cv2.rectangle(frame, (0, 0), (FRAME_WIDTH, FRAME_HEIGHT), (0, 0, 0), -1)
                cv2.putText(frame, "TRAINING MODEL...", (300, 360), 1, 3, (0, 255, 0), 3)
                self.window.update_idletasks()
                self.id_sys.train()
                self.stop_mode()
                messagebox.showinfo("Success", f"Пользователь {self.reg_name} добавлен!")

    def process_security(self, frame, res):
        overlay = frame.copy()
        if self.flash_state == 1: 
            cv2.rectangle(overlay, (0,0), (FRAME_WIDTH, FRAME_HEIGHT), (0,0,0), -1)
            frame = cv2.addWeighted(overlay, 0.98, frame, 0.02, 0)
        elif self.flash_state == 2: 
            cv2.rectangle(overlay, (0,0), (FRAME_WIDTH, FRAME_HEIGHT), (255,255,255), -1)
            frame = cv2.addWeighted(overlay, 0.85, frame, 0.15, 0)

        msg, sub, col = "SYSTEM ACTIVE", "Scanning...", (255,255,255)

        if res["detected"]:
            bbox = res["bbox"]
            brightness = res["brightness"]
            lc = res["light_center"]
            le = res["light_edge"]
            
            if self.flash_state == 0:
                cv2.rectangle(frame, (bbox[0],bbox[1]), (bbox[2],bbox[3]), (255,255,0), 2)

            if self.sec_state == "scan":
                name, conf = self.id_sys.recognize(frame, bbox)
                if name != "Unknown" and conf > 50:
                    self.user = name
                    base_lux = brightness
                    self.current_thresholds["max_dark_val"] = base_lux + 30.0
                    if base_lux > 150: self.current_thresholds["min_flash_diff"] = 10.0
                    else: self.current_thresholds["min_flash_diff"] = 15.0
                    
                    self.sec_state = "flash_check"
                    self.flash_state = 1
                    self.flash_timer = time.time()
                    self.min_dark_val = 255.0
                    self.max_light_val = 0.0
                    self.flash_attempts = 0
                else:
                    col = (0,0,255)
                    sub = "Unknown User"

            elif self.sec_state == "flash_check":
                msg = f"VERIFYING: {self.user}"
                col = (0,255,255)
                
                if self.flash_state == 1:
                    sub = "ANALYZING LIGHT..."
                    if brightness < self.min_dark_val: self.min_dark_val = brightness
                    if time.time() - self.flash_timer > 0.6:
                        self.flash_state = 2
                        self.flash_timer = time.time()
                        self.max_center_bright = 0.0
                        self.max_edge_bright = 0.0
                
                elif self.flash_state == 2:
                    sub = "FLASHING..."
                    if time.time() - self.flash_timer > 0.3:
                        if brightness > self.max_light_val: self.max_light_val = brightness
                        if lc > self.max_center_bright: self.max_center_bright = lc
                        if le > self.max_edge_bright: self.max_edge_bright = le
                    
                    if time.time() - self.flash_timer > 0.8:
                        diff = self.max_light_val - self.min_dark_val
                        ratio_3d = self.max_center_bright / (self.max_edge_bright + 0.1)
                        has_glare = res["glare"]
                        
                        passed = True
                        fail_reason = ""
                        
                        is_paper_reflective = diff > THRESHOLDS["max_flash_diff"]
                        is_super_3d = ratio_3d > 1.50
                        
                        if self.min_dark_val > self.current_thresholds["max_dark_val"]:
                            passed, fail_reason = False, "Too Bright Env"
                        elif has_glare:
                            passed, fail_reason = False, "Glare Detected"
                        elif diff < self.current_thresholds["min_flash_diff"]:
                            passed, fail_reason = False, "No Reflection"
                        elif is_paper_reflective and not is_super_3d:
                            passed, fail_reason = False, "Too Reflective"
                        elif ratio_3d < THRESHOLDS["min_3d_ratio"]:
                            passed, fail_reason = False, "Flat Face"

                        if passed:
                            self.sec_state = "ok"
                            self.last_check_time = time.time()
                            self.flash_state = 0
                            print(f"{Fore.GREEN}[OK] {self.user} | Diff={diff:.1f} | 3D={ratio_3d:.2f} | {self.flash_attempts+1}/3{Style.RESET_ALL}")
                        else:
                            self.flash_attempts += 1
                            if self.flash_attempts >= THRESHOLDS["max_flash_attempts"]:
                                print(f"{Fore.RED}[SPOOF DETECTED] {self.user} | {fail_reason} | Diff={diff:.1f} | 3D={ratio_3d:.2f} | Attempt={self.flash_attempts}/3{Style.RESET_ALL}")
                                self.sec_state = "fail"
                                self.flash_state = 0
                            else:
                                self.flash_state = 1
                                self.flash_timer = time.time()
                                self.min_dark_val = 255.0
                                self.max_light_val = 0.0

            elif self.sec_state == "ok":
                msg = "ACCESS GRANTED"
                sub = f"Welcome, {self.user}!"
                col = (0,255,0)
                cv2.rectangle(frame, (bbox[0],bbox[1]), (bbox[2],bbox[3]), (0,255,0), 4)
                if time.time() - self.last_check_time > THRESHOLDS["reauth_interval"]:
                    self.sec_state = "scan"

            elif self.sec_state == "fail":
                msg = "ACCESS DENIED"
                sub = "SPOOFING DETECTED"
                col = (0,0,255)
                cv2.rectangle(frame, (bbox[0],bbox[1]), (bbox[2],bbox[3]), (0,0,255), 4)
                if time.time() - self.flash_timer > 5.0:
                    self.sec_state = "scan"

        cv2.rectangle(frame, (0,0), (FRAME_WIDTH, 110), (0,0,0), -1)
        cv2.putText(frame, msg, (30, 50), 1, 2.0, col, 2)
        cv2.putText(frame, sub, (30, 90), 1, 1.2, (200,200,200), 1)
        return frame

    def __del__(self):
        if self.cap: self.cap.release()

if __name__ == "__main__":
    root = tk.Tk()
    app = LPadApp(root, "L-PAD Security System")