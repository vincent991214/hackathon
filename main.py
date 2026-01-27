import tkinter as tk
from gui.app import DocGeneratorApp

if __name__ == "__main__":
    root = tk.Tk()
    # We set the theme in the app, so just launch it
    app = DocGeneratorApp(root)
    root.mainloop()