import json
import os
import sys
import tkinter as tk
from tkinter import filedialog
from tkinter import font as tkfont


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_PATH = os.path.join(app_dir(), "config.json")

DEFAULT_CONFIG = {
    "width": 600,
    "height": 110,
    "buttons_height": 20,
    "margin": 8,
    "font_family": "Segoe UI",
    "font_weight": "normal",
    "background": "#1e1e1e",
    "foreground": "#ffffff",
    "button_foreground": "#ffffff",
    "marquee_step": 1,
    "marquee_interval_ms": 40,
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as config_file:
            json.dump(DEFAULT_CONFIG, config_file, ensure_ascii=False, indent=2)
        return dict(DEFAULT_CONFIG)

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_CONFIG)

    if not isinstance(data, dict):
        return dict(DEFAULT_CONFIG)

    config = dict(DEFAULT_CONFIG)
    config.update({key: value for key, value in data.items() if key in DEFAULT_CONFIG})
    return config


def read_lines(path):
    for encoding in ("utf-8-sig", "cp1251", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as text_file:
                return text_file.read().splitlines()
        except UnicodeDecodeError:
            continue
        except OSError:
            return []
    return []


class LineViewer:
    def __init__(self, root, config, lines):
        self.root = root
        self.config = config
        self.lines = lines
        self.index = 0
        self.after_id = None
        self.direction = -1
        self.x = 0.0
        self.y = 0.0
        self.left_limit = 0.0
        self.right_limit = 0.0

        self.width = self._number("width", 600, 80)
        self.height = self._number("height", 110, 40)
        self.buttons_height = self._number("buttons_height", 20, 16)
        self.height = max(self.height, self.buttons_height + 30)
        self.margin = self._number("margin", 8, 0)
        self.step = self._number("marquee_step", 1, 1)
        self.interval = self._number("marquee_interval_ms", 40, 10)
        self.font_family = self._string("font_family", "Segoe UI")
        self.font_weight = self._string("font_weight", "normal")
        self.background = self._string("background", "#1e1e1e")
        self.foreground = self._string("foreground", "#ffffff")
        self.button_foreground = self._string("button_foreground", "#ffffff")

        self._build_window()
        self._build_controls()
        self._bind_keys()

        self.root.deiconify()
        self.root.update_idletasks()
        self.root.attributes("-topmost", True)
        self.root.focus_force()
        self.render()

    def _number(self, key, default, minimum):
        try:
            value = int(self.config.get(key, default))
        except (TypeError, ValueError):
            value = default
        return max(minimum, value)

    def _string(self, key, default):
        value = self.config.get(key, default)
        return value if isinstance(value, str) and value else default

    def _build_window(self):
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=self.background)
        screen_width = self.root.winfo_screenwidth()
        x = max(0, screen_width - self.width)
        self.root.geometry(f"{self.width}x{self.height}+{x}+0")

    def _build_controls(self):
        button_style = {
            "bg": self.background,
            "fg": self.button_foreground,
            "activebackground": self.background,
            "activeforeground": self.button_foreground,
            "relief": "flat",
            "bd": 0,
            "highlightthickness": 0,
            "font": (self.font_family, 10, "bold"),
            "width": 2,
            "pady": 0,
            "cursor": "hand2",
            "takefocus": False,
        }

        self.buttons_frame = tk.Frame(self.root, bg=self.background)
        self.buttons_frame.place(
            relx=1.0, rely=1.0, anchor="se", x=-self.margin, y=-2
        )

        self.previous_button = tk.Button(
            self.buttons_frame, text="<", command=self.show_previous, **button_style
        )
        self.previous_button.pack(side="left", padx=(0, 4))

        self.next_button = tk.Button(
            self.buttons_frame, text=">", command=self.show_next, **button_style
        )
        self.next_button.pack(side="left")

        self.canvas = tk.Canvas(
            self.root, bg=self.background, highlightthickness=0, bd=0
        )
        self.canvas.place(
            x=0,
            y=0,
            relwidth=1,
            relheight=1,
            height=-self.buttons_height,
        )
        self.text_id = self.canvas.create_text(
            0,
            0,
            text="",
            fill=self.foreground,
            anchor="ne",
            font=(self.font_family, 10),
        )

    def _bind_keys(self):
        self.root.bind("<Escape>", lambda event: self.close())
        self.root.bind("<Left>", lambda event: self.show_previous())
        self.root.bind("<Right>", lambda event: self.show_next())

    def _fit_font(self):
        self.canvas.update_idletasks()
        field_height = max(1, self.canvas.winfo_height() - 2 * self.margin)
        measuring_font = tkfont.Font(
            root=self.root,
            family=self.font_family,
            size=-1,
            weight=self.font_weight,
        )

        def linespace(size):
            measuring_font.configure(size=-size)
            return measuring_font.metrics("linespace")

        low, high = 1, max(1, field_height)
        best = 1
        while low <= high:
            middle = (low + high) // 2
            if linespace(middle) <= field_height:
                best = middle
                low = middle + 1
            else:
                high = middle - 1

        self.font = tkfont.Font(
            root=self.root,
            family=self.font_family,
            size=-best,
            weight=self.font_weight,
        )
        self.canvas.itemconfigure(self.text_id, font=self.font)

    def render(self):
        self._stop_animation()
        current_text = self.lines[self.index]
        self.canvas.itemconfigure(self.text_id, text=current_text)
        self._fit_font()
        self.canvas.update_idletasks()

        canvas_width = self.canvas.winfo_width()
        text_width = self.font.measure(current_text) if current_text else 0
        available_width = canvas_width - 2 * self.margin
        self.y = float(self.margin)

        if available_width > 0 and text_width > available_width:
            self.right_limit = float(canvas_width - self.margin)
            self.left_limit = float(self.margin + text_width)
            self.x = self.left_limit
            self.direction = -1
            self.canvas.coords(self.text_id, self.x, self.y)
            self.after_id = self.root.after(self.interval, self._tick)
        else:
            self.canvas.coords(self.text_id, float(canvas_width - self.margin), self.y)

    def _tick(self):
        self.after_id = None
        self.x += self.direction * self.step

        if self.direction < 0 and self.x <= self.right_limit:
            self.x = self.right_limit
            self.direction = 1
        elif self.direction > 0 and self.x >= self.left_limit:
            self.x = self.left_limit
            self.direction = -1

        self.canvas.coords(self.text_id, self.x, self.y)
        self.after_id = self.root.after(self.interval, self._tick)

    def _stop_animation(self):
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def show_previous(self):
        if self.index == 0:
            return
        self.index -= 1
        self.render()

    def show_next(self):
        if self.index >= len(self.lines) - 1:
            self.close()
            return
        self.index += 1
        self.render()

    def close(self):
        self._stop_animation()
        self.root.destroy()


def main():
    config = load_config()
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    path = filedialog.askopenfilename(
        parent=root,
        title="Выберите текстовый файл",
        filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")],
    )
    if not path:
        root.destroy()
        return

    lines = read_lines(path)
    if not lines:
        root.destroy()
        return

    LineViewer(root, config, lines)
    root.mainloop()


if __name__ == "__main__":
    main()
