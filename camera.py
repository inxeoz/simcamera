#!/usr/bin/env python3
import cv2
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import subprocess
from datetime import datetime
from pathlib import Path
import threading
import numpy as np
import os

APP_NAME = "Simple Camera"
FRAME_RATE = 30
FRAME_DELAY_MS = max(1, int(1000 / FRAME_RATE))
VIDEO_CODEC = cv2.VideoWriter_fourcc(*"mp4v")

# Try to import audio libs; fallback gracefully if missing
try:
    import sounddevice as sd
    from scipy.io.wavfile import write
    AUDIO_SUPPORT = True
except ImportError:
    AUDIO_SUPPORT = False

class CameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1000x750")
        self.root.configure(bg="#000000")
        
        # State Management
        self.cap = None
        self.video_writer = None
        self.audio_stream = None
        self.is_recording = False
        self.mode = "photo"
        self.mirror_enabled = True
        self.show_settings = False
        
        # Audio & Recording 
        self.audio_data = []
        self.sample_rate = 44100
        self.start_time = None
        self.temp_audio = "temp_audio.wav"
        self.temp_video = "temp_video.mp4"
        
        # Unified Save Directory
        self.save_dir = Path.home() / "Pictures" / "Camera"
        self.save_dir.mkdir(parents=True, exist_ok=True)
        
        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        # Delay camera start slightly to let Tkinter calculate window sizes
        self.root.after(100, self.start_camera)

    def setup_ui(self):
        self.view_container = tk.Frame(self.root, bg="black")
        self.view_container.pack(fill=tk.BOTH, expand=True)
        
        self.camera_label = tk.Label(self.view_container, bg="black", borderwidth=0)
        self.camera_label.place(relx=0.5, rely=0.5, anchor="center")

        self.timer_label = tk.Label(self.view_container, text="00:00", bg="#ff4d4d", fg="white", 
                                   font=("Arial", 14, "bold"), padx=10)

        self.settings_panel = tk.Frame(self.view_container, bg="#111111", width=260)
        self.setup_settings_content()

        self.controls = tk.Frame(self.root, bg="#0d0d0d", pady=15)
        self.controls.pack(fill=tk.X, side=tk.BOTTOM)

        self.action_btn = tk.Button(self.controls, text="⏺ CAPTURE", command=self.handle_action,
                                   bg="#89b4fa", fg="black", font=("Arial", 12, "bold"),
                                   relief="flat", width=18, pady=10)
        self.action_btn.pack(side=tk.LEFT, expand=True)

        self.settings_btn = tk.Button(self.controls, text="⚙ SETTINGS", command=self.toggle_settings,
                                     bg="#313244", fg="white", font=("Arial", 12, "bold"),
                                     relief="flat", width=18, pady=10)
        self.settings_btn.pack(side=tk.LEFT, expand=True)

    def setup_settings_content(self):
        tk.Label(self.settings_panel, text="CAMERA CONFIG", bg="#111111", fg="#bac2de", font=("Arial", 10, "bold")).pack(pady=20)
        
        mode_f = tk.Frame(self.settings_panel, bg="#111111")
        mode_f.pack(pady=10)
        self.btn_photo = tk.Button(mode_f, text="PHOTO", command=lambda: self.set_mode("photo"), bg="#89b4fa", width=9)
        self.btn_photo.pack(side=tk.LEFT, padx=5)
        self.btn_video = tk.Button(mode_f, text="VIDEO", command=lambda: self.set_mode("video"), bg="#313244", width=9)
        self.btn_video.pack(side=tk.LEFT, padx=5)

        self.mirror_btn = tk.Button(self.settings_panel, text="MIRROR: ON", command=self.toggle_mirror, bg="#45475a", fg="white")
        self.mirror_btn.pack(pady=10, fill=tk.X, padx=30)

        tk.Label(self.settings_panel, text="SAVE FOLDER", bg="#111111", fg="#585b70", font=("Arial", 8, "bold")).pack(pady=(20,0))
        self.dir_label = tk.Label(self.settings_panel, text=str(self.save_dir), bg="#111111", fg="#666666", font=("Arial", 8), wraplength=220)
        self.dir_label.pack(pady=5)
        
        tk.Button(self.settings_panel, text="CHANGE FOLDER", command=self.change_dir, bg="#45475a", fg="white").pack(pady=5, padx=30, fill=tk.X)

    def toggle_settings(self):
        if self.show_settings:
            self.settings_panel.place_forget()
        else:
            self.settings_panel.place(relx=1.0, rely=0, anchor="ne", relheight=1.0)
        self.show_settings = not self.show_settings

    def set_mode(self, mode):
        self.mode = mode
        self.btn_photo.config(bg="#89b4fa" if mode == "photo" else "#313244")
        self.btn_video.config(bg="#89b4fa" if mode == "video" else "#313244")
        self.action_btn.config(text="⏺ CAPTURE" if mode == "photo" else "⬤ START")

    def toggle_mirror(self):
        self.mirror_enabled = not self.mirror_enabled
        self.mirror_btn.config(text=f"MIRROR: {'ON' if self.mirror_enabled else 'OFF'}")

    def audio_callback(self, indata, frames, time, status):
        if self.is_recording:
            self.audio_data.append(indata.copy())

    def update_timer(self):
        if self.is_recording:
            elapsed = datetime.now() - self.start_time
            m, s = divmod(int(elapsed.total_seconds()), 60)
            self.timer_label.config(text=f"{m:02d}:{s:02d}")
            self.root.after(1000, self.update_timer)

    def handle_action(self):
        if self.mode == "photo":
            ret, frame = self.cap.read()
            if ret:
                if self.mirror_enabled: frame = cv2.flip(frame, 1)
                path = self.save_dir / f"IMG_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                cv2.imwrite(str(path), frame)
                self.notify("Photo Saved")
        else:
            if not self.is_recording:
                # START RECORDING
                ret, frame = self.cap.read()
                if not ret: return
                h, w = frame.shape[:2]
                self.video_writer = cv2.VideoWriter(self.temp_video, VIDEO_CODEC, float(FRAME_RATE), (w, h))
                self.audio_data = []
                self.is_recording = True
                self.start_time = datetime.now()
                
                if AUDIO_SUPPORT:
                    try:
                        self.audio_stream = sd.InputStream(samplerate=self.sample_rate, channels=2, callback=self.audio_callback)
                        self.audio_stream.start()
                    except Exception:
                        self.audio_stream = None
                        self.notify("Audio device error - recording video only")
                
                self.timer_label.place(relx=0.5, rely=0.05, anchor="n")
                self.update_timer()
                self.action_btn.config(text="⬛ STOP", bg="#f38ba8")
            else:
                self.is_recording = False
                if AUDIO_SUPPORT and self.audio_stream is not None:
                    self.audio_stream.stop()
                    self.audio_stream.close()
                    self.audio_stream = None
                if self.video_writer:
                    self.video_writer.release()
                    self.video_writer = None
                self.timer_label.place_forget()
                self.action_btn.config(text="⬤ START", bg="#a6e3a1")
                threading.Thread(target=self.finalize_video, daemon=True).start()

    def finalize_video(self):
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        final_path = self.save_dir / f"VID_{ts}.mp4"
        
        if AUDIO_SUPPORT and self.audio_data:
            audio_array = np.concatenate(self.audio_data, axis=0)
            write(self.temp_audio, self.sample_rate, audio_array)
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    self.temp_video,
                    "-i",
                    self.temp_audio,
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    str(final_path),
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            if os.path.exists(self.temp_video):
                os.rename(self.temp_video, str(final_path))

        for temp_path in (self.temp_audio, self.temp_video):
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except OSError:
                pass
            
        self.notify("Video Saved")

    def update_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                if self.mirror_enabled: frame = cv2.flip(frame, 1)
                if self.is_recording and self.video_writer:
                    self.video_writer.write(frame)

                # Get dimensions, ensuring they aren't zero to avoid cv2 error
                win_w = self.view_container.winfo_width()
                win_h = self.view_container.winfo_height()
                img_h, img_w = frame.shape[:2]

                if win_w > 10 and win_h > 10:
                    # Scale to fit (Letterbox)
                    scale = min(win_w / img_w, win_h / img_h)
                    new_w, new_h = int(img_w * scale), int(img_h * scale)

                    # Only resize if scale results in valid dimensions
                    if new_w > 0 and new_h > 0:
                        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                        img = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                        photo = ImageTk.PhotoImage(Image.fromarray(img))
                        self.camera_label.config(image=photo)
                        self.camera_label.image = photo
                
        self.root.after(FRAME_DELAY_MS, self.update_frame)

    def start_camera(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FPS, FRAME_RATE)
        if not self.cap.isOpened():
            self.notify("Could not open camera!")
            return
        self.update_frame()

    def change_dir(self):
        d = filedialog.askdirectory(initialdir=str(self.save_dir))
        if d:
            self.save_dir = Path(d)
            self.dir_label.config(text=str(self.save_dir))

    def notify(self, msg):
        try: subprocess.run(["notify-send", APP_NAME, msg], check=False)
        except: print(msg)

    def on_close(self):
        self.is_recording = False
        if AUDIO_SUPPORT and self.audio_stream is not None:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.audio_stream = None
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()
