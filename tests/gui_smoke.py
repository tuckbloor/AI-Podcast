"""Open/close the real Tk installer without installing anything (Windows CI smoke)."""
from pathlib import Path
import sys
import tkinter as tk
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import podcast_install

Original=tk.Tk

def autoclose(*args,**kwargs):
    root=Original(*args,**kwargs)
    root.after(900,root.destroy)
    return root

tk.Tk=autoclose
podcast_install.gui()
print('Installer GUI opened and stayed responsive until closed.')
