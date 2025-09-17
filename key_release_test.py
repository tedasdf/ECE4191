import tkinter as tk
from tkinter import ttk
import time


upKeyState = False
downKeyState = False

def keyup(e):
    global upKeyState
    global downKeyState
    stateChange = False
    if e.keysym == "Up" and upKeyState:
        upKeyState = False
        stateChange = True

    elif e.keysym == "Down" and downKeyState:
        downKeyState = False
        stateChange = True
    
    if stateChange:
        print(e.keysym, 'released')

def keydown(e):
    global upKeyState
    global downKeyState
    stateChange = False
    if e.keysym == "Up" and not upKeyState:
        upKeyState = True
        stateChange = True

    elif e.keysym == "Down" and not downKeyState:
        downKeyState = True
        stateChange = True
    
    if stateChange:
        print(e.keysym, 'pressed')

root = tk.Tk()
frame = tk.Frame(root, width=100, height=100)
frame.bind("<KeyPress>", keydown)
frame.bind("<KeyRelease>", keyup)
frame.pack()
frame.focus_set()
root.mainloop()