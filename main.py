import tkinter as tk
from launcher import MinecraftLauncher

if __name__ == "__main__":
    root = tk.Tk()
    launcher = MinecraftLauncher(root)
    root.mainloop()