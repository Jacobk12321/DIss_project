import tkinter as tk
from PIL import Image, ImageTk

class Renderer:
    def __init__(self, on_key, on_mouse):
        self.window = tk.Tk()
        self.window.title("Tkinter VNC Client")
        self.canvas = tk.Canvas(self.window)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.img = None
        self.img_tk = None

        # Bind input callbacks
        self.window.bind("<KeyPress>", on_key)
        self.window.bind("<KeyRelease>", on_key)
        self.canvas.bind("<ButtonPress>", on_mouse)
        self.canvas.bind("<ButtonRelease>", on_mouse)
        self.canvas.bind("<Motion>", on_mouse)

    def update_image(self, img):
        self.img_tk = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.img_tk)
        self.window.update_idletasks()
        self.window.update()

    def start_loop(self):
        self.window.mainloop()
