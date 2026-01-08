from PyInstaller.utils.hooks import collect_data_files

# Собираем все данные из mediapipe (модели, конфиги)
datas = collect_data_files('mediapipe')