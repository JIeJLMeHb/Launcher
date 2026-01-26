import tkinter as tk
import ttkbootstrap as ttkb
from launcher import MinecraftLauncher

if __name__ == "__main__":
    try:
        root = ttkb.Window(themename="darkly")
        launcher = MinecraftLauncher(root)
        root.mainloop()
    except(KeyboardInterrupt):
        print("Keyboard interrupt called, closing app...")