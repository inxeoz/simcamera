#!/usr/bin/env python3
import os
import shutil
import subprocess
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

from PIL import Image, ImageOps, ImageTk

APP_NAME = "Simple Camera"
FRAME_RATE = 30
FRAME_DELAY_MS = max(1, int(1000 / FRAME_RATE))
CAPTURE_WIDTH = 1280
CAPTURE_HEIGHT = 720
FRAME_SIZE = CAPTURE_WIDTH * CAPTURE_HEIGHT * 3
CAMERA_DEVICE = "/dev/video0"


class CameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1000x750")
        self.root.configure(bg="#000000")

        self.capture_process = None
        self.record_process = None
        self.capture_thread = None
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.is_running = False
        self.is_recording = False
        self.mode = "photo"
        self.mirror_enabled = True
        self.show_settings = False
        self.start_time = None

        self.save_dir = Path.home() / "Pictures" / "Camera"
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self.start_camera)

    def setup_ui(self):
        self.view_container = tk.Frame(self.root, bg="black")
        self.view_container.pack(fill=tk.BOTH, expand=True)

        self.camera_label = tk.Label(self.view_container, bg="black", borderwidth=0)
        self.camera_label.place(relx=0.5, rely=0.5, anchor="center")

        self.timer_label = tk.Label(
            self.view_container,
            text="00:00",
            bg="#ff4d4d",
            fg="white",
            font=("Arial", 14, "bold"),
            padx=10,
        )

        self.settings_panel = tk.Frame(self.view_container, bg="#111111", width=260)
        self.setup_settings_content()

        self.controls = tk.Frame(self.root, bg="#0d0d0d", pady=15)
        self.controls.pack(fill=tk.X, side=tk.BOTTOM)

        self.action_btn = tk.Button(
            self.controls,
            text="CAPTURE",
            command=self.handle_action,
            bg="#89b4fa",
            fg="black",
            font=("Arial", 12, "bold"),
            relief="flat",
            width=18,
            pady=10,
        )
        self.action_btn.pack(side=tk.LEFT, expand=True)

        self.settings_btn = tk.Button(
            self.controls,
            text="SETTINGS",
            command=self.toggle_settings,
            bg="#313244",
            fg="white",
            font=("Arial", 12, "bold"),
            relief="flat",
            width=18,
            pady=10,
        )
        self.settings_btn.pack(side=tk.LEFT, expand=True)

    def setup_settings_content(self):
        tk.Label(
            self.settings_panel,
            text="CAMERA CONFIG",
            bg="#111111",
            fg="#bac2de",
            font=("Arial", 10, "bold"),
        ).pack(pady=20)

        mode_f = tk.Frame(self.settings_panel, bg="#111111")
        mode_f.pack(pady=10)
        self.btn_photo = tk.Button(
            mode_f,
            text="PHOTO",
            command=lambda: self.set_mode("photo"),
            bg="#89b4fa",
            width=9,
        )
        self.btn_photo.pack(side=tk.LEFT, padx=5)
        self.btn_video = tk.Button(
            mode_f,
            text="VIDEO",
            command=lambda: self.set_mode("video"),
            bg="#313244",
            width=9,
        )
        self.btn_video.pack(side=tk.LEFT, padx=5)

        self.mirror_btn = tk.Button(
            self.settings_panel,
            text="MIRROR: ON",
            command=self.toggle_mirror,
            bg="#45475a",
            fg="white",
        )
        self.mirror_btn.pack(pady=10, fill=tk.X, padx=30)

        tk.Label(
            self.settings_panel,
            text="SAVE FOLDER",
            bg="#111111",
            fg="#585b70",
            font=("Arial", 8, "bold"),
        ).pack(pady=(20, 0))
        self.dir_label = tk.Label(
            self.settings_panel,
            text=str(self.save_dir),
            bg="#111111",
            fg="#666666",
            font=("Arial", 8),
            wraplength=220,
        )
        self.dir_label.pack(pady=5)

        tk.Button(
            self.settings_panel,
            text="CHANGE FOLDER",
            command=self.change_dir,
            bg="#45475a",
            fg="white",
        ).pack(pady=5, padx=30, fill=tk.X)

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
        self.action_btn.config(text="CAPTURE" if mode == "photo" else "START")

    def toggle_mirror(self):
        self.mirror_enabled = not self.mirror_enabled
        self.mirror_btn.config(text=f"MIRROR: {'ON' if self.mirror_enabled else 'OFF'}")

    def update_timer(self):
        if self.is_recording:
            elapsed = datetime.now() - self.start_time
            minutes, seconds = divmod(int(elapsed.total_seconds()), 60)
            self.timer_label.config(text=f"{minutes:02d}:{seconds:02d}")
            self.root.after(1000, self.update_timer)

    def handle_action(self):
        if self.mode == "photo":
            with self.frame_lock:
                frame = self.current_frame.copy() if self.current_frame else None
            if frame is not None:
                path = self.save_dir / f"IMG_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                frame.save(path, format="JPEG", quality=95)
                self.notify("Photo Saved")
            return

        if not self.is_recording:
            self.start_recording()
            return

        self.stop_recording()

    def start_recording(self):
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path is None:
            self.notify("ffmpeg not found")
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_path = self.save_dir / f"VID_{ts}.mp4"
        cmd = [
            ffmpeg_path,
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{CAPTURE_WIDTH}x{CAPTURE_HEIGHT}",
            "-r",
            str(FRAME_RATE),
            "-i",
            "-",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(final_path),
        ]

        try:
            self.record_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            self.record_process = None
            self.notify("Could not start recording")
            return

        self.is_recording = True
        self.start_time = datetime.now()
        self.timer_label.place(relx=0.5, rely=0.05, anchor="n")
        self.update_timer()
        self.action_btn.config(text="STOP", bg="#f38ba8")

    def stop_recording(self):
        self.is_recording = False
        self.timer_label.place_forget()
        self.action_btn.config(text="START", bg="#a6e3a1")

        process = self.record_process
        self.record_process = None
        if process is None:
            return

        try:
            if process.stdin:
                process.stdin.close()
        except OSError:
            pass
        threading.Thread(target=self.finalize_recording, args=(process,), daemon=True).start()

    def finalize_recording(self, process):
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        self.notify("Video Saved")

    def start_camera(self):
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path is None:
            self.notify("ffmpeg not found")
            return

        cmd = [
            ffmpeg_path,
            "-f",
            "video4linux2",
            "-framerate",
            str(FRAME_RATE),
            "-video_size",
            f"{CAPTURE_WIDTH}x{CAPTURE_HEIGHT}",
            "-i",
            CAMERA_DEVICE,
            "-pix_fmt",
            "rgb24",
            "-f",
            "rawvideo",
            "-",
        ]

        try:
            self.capture_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                bufsize=FRAME_SIZE,
            )
        except OSError:
            self.capture_process = None
            self.notify("Could not open camera!")
            return

        self.is_running = True
        self.capture_thread = threading.Thread(target=self.capture_loop, daemon=True)
        self.capture_thread.start()
        self.update_frame()

    def capture_loop(self):
        if self.capture_process is None or self.capture_process.stdout is None:
            return

        while self.is_running:
            frame_bytes = self.capture_process.stdout.read(FRAME_SIZE)
            if len(frame_bytes) != FRAME_SIZE:
                break

            frame = Image.frombytes("RGB", (CAPTURE_WIDTH, CAPTURE_HEIGHT), frame_bytes)
            if self.mirror_enabled:
                frame = ImageOps.mirror(frame)

            with self.frame_lock:
                self.current_frame = frame

            if self.is_recording and self.record_process and self.record_process.stdin:
                try:
                    self.record_process.stdin.write(frame.tobytes())
                except OSError:
                    self.is_recording = False

        self.is_running = False

    def update_frame(self):
        with self.frame_lock:
            frame = self.current_frame.copy() if self.current_frame else None

        if frame is not None:
            win_w = self.view_container.winfo_width()
            win_h = self.view_container.winfo_height()
            if win_w > 10 and win_h > 10:
                preview = frame.copy()
                preview.thumbnail((win_w, win_h), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(preview)
                self.camera_label.config(image=photo)
                self.camera_label.image = photo

        if self.is_running:
            self.root.after(FRAME_DELAY_MS, self.update_frame)

    def change_dir(self):
        directory = filedialog.askdirectory(initialdir=str(self.save_dir))
        if directory:
            self.save_dir = Path(directory)
            self.save_dir.mkdir(parents=True, exist_ok=True)
            self.dir_label.config(text=str(self.save_dir))

    def notify(self, msg):
        try:
            subprocess.run(["notify-send", APP_NAME, msg], check=False)
        except Exception:
            print(msg)

    def on_close(self):
        self.is_running = False
        self.stop_recording()

        process = self.capture_process
        self.capture_process = None
        if process is not None:
            try:
                process.terminate()
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()
