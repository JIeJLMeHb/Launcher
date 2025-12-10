import tkinter as tk
import ttkbootstrap as ttkb
from launcher import MinecraftLauncher

if __name__ == "__main__":
    root = ttkb.Window(themename="darkly")
    launcher = MinecraftLauncher(root)
    root.mainloop()