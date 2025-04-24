import tkinter as tk
from PIL import Image, ImageTk
import time

class Renderer:
    def __init__(self, on_key, on_mouse):
        self.window = tk.Tk()
        self.window.title("Tkinter VNC Client")
        self.canvas = tk.Canvas(self.window)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.img = None
        self.img_tk = None
        self.canvas_image = None

        self.frame_times = []
        self.start_time = time.time()
        self.last_fps_update = time.time()

        self.window.bind("<KeyPress>", on_key)
        self.window.bind("<KeyRelease>", on_key)
        self.canvas.bind("<ButtonPress>", on_mouse)
        self.canvas.bind("<ButtonRelease>", on_mouse)
        self.canvas.bind("<Motion>", on_mouse)

    def update_image(self, img):
        self.img = img
        self.img_tk = ImageTk.PhotoImage(img)

        if self.canvas_image is None:
            self.canvas_image = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.img_tk)
        else:
            self.canvas.itemconfig(self.canvas_image, image=self.img_tk)

        now = time.time()
        self.frame_times.append(now)

        if now - self.last_fps_update >= 1.0:
            total_time = now - self.start_time
            avg_fps = len(self.frame_times) / total_time if total_time > 0 else 0

            # Update window title 
            # self.window.title(f"Tkinter VNC Client - Avg FPS: {avg_fps:.2f}")

            # Print to terminal
            # print(f"[Client] Average FPS: {avg_fps:.2f}")

            self.last_fps_update = now

        self.window.update_idletasks()
        self.window.update()

    def start_loop(self):
        self.window.mainloop()
