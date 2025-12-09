import ssl
import warnings
import os
import urllib3
import requests
import minecraft_launcher_lib as mclib
from tkinter import ttk
import subprocess

ssl._create_default_https_context = ssl._create_unverified_context
warnings.filterwarnings("ignore")
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['PYTHONHTTPSVERIFY'] = '0'

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class InsecureSession(requests.Session):
    def __init__(self):
        super().__init__()
        self.verify = False
        self.timeout = 30
        self.max_retries = 3

requests.Session = InsecureSession

original_get_requests = mclib._helper.get_requests_response_cache

def insecure_get_requests(url: str):
    session = InsecureSession()
    response = session.get(url)
    response.raise_for_status()
    return response

mclib._helper.get_requests_response_cache = insecure_get_requests

def setup_dark_theme():
    style = ttk.Style()
    
    bg_color = '#2b2b2b'
    fg_color = '#ffffff'
    entry_bg = '#3c3c3c'
    button_bg = '#4a4a4a'
    accent_color = '#4a76b8'
    
    style.theme_use('default')
    
    style.configure('TFrame', background=bg_color)
    style.configure('TLabel', background=bg_color, foreground=fg_color, font=('Segoe UI', 10))
    style.configure('TButton', 
                   background=button_bg, 
                   foreground=fg_color,
                   borderwidth=1,
                   relief='raised',
                   font=('Segoe UI', 10))
    style.map('TButton',
             background=[('active', '#5a5a5a'), ('pressed', '#3a3a3a')],
             foreground=[('active', 'white')])
    
    style.configure('TEntry', 
                   fieldbackground=entry_bg,
                   foreground=fg_color,
                   insertcolor=fg_color,
                   borderwidth=1,
                   relief='sunken')
    
    style.configure('TCombobox', 
                   fieldbackground=entry_bg,
                   background=entry_bg,
                   foreground=fg_color,
                   arrowcolor=fg_color)
    
    style.configure('Vertical.TScrollbar', 
                   background=button_bg,
                   troughcolor=bg_color,
                   borderwidth=0)
    
    style.configure('Horizontal.TScrollbar', 
                   background=button_bg,
                   troughcolor=bg_color,
                   borderwidth=0)
    
    style.configure('Treeview',
                   background=entry_bg,
                   foreground=fg_color,
                   fieldbackground=entry_bg,
                   rowheight=25)
    style.configure('Treeview.Heading',
                   background=button_bg,
                   foreground=fg_color,
                   relief='flat',
                   font=('Segoe UI', 10, 'bold'))
    style.map('Treeview',
             background=[('selected', accent_color)],
             foreground=[('selected', 'white')])

def check_java_installed():
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False