import os

# === L-PAD CONFIGURATION ===
PROJECT_NAME = "L-PAD"

DATA_DIR = "data"
USERS_DIR = os.path.join(DATA_DIR, "users")
MODELS_DIR = "models"
MODEL_FILE = os.path.join(MODELS_DIR, "face_trainer.yml")
PASSWORD_FILE = os.path.join(DATA_DIR, "admin.secret")

CAMERA_ID = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

TARGET_SCORE = 100 

THRESHOLDS = {
    # === FLASH SETTINGS ===
    
    # Минимальная разница яркости (Свет - Тьма).
    "min_flash_diff": 15.0,
    
    # Максимальная разница.
    "max_flash_diff": 160.0,
    
    # 3D CHECK.
    "min_3d_ratio": 1.35, 
    
    # Максимальная яркость в темноте (защита от экранов).
    "max_dark_val": 110.0,   
    
    # Параметры бликов (Гистограмма).
    "specular_threshold": 250,
    "specular_ratio": 0.01,
    
    "max_flash_attempts": 3,
    "reauth_interval": 30.0
}

os.makedirs(USERS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)