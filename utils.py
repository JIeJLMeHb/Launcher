import ssl
import warnings
import os
import urllib3
import requests
import minecraft_launcher_lib as mclib
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

def check_java_installed():
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False