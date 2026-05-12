import requests

API_URL = "https://api-inference.huggingface.co/models/11Raghav/SciFive"
headers = {}
payload = {"inputs": "test"}

res = requests.post(API_URL, json=payload)
print("api-inference:", res.status_code)

API_URL2 = "https://router.huggingface.co/hf-inference/models/11Raghav/SciFive"
res2 = requests.post(API_URL2, json=payload)
print("router:", res2.status_code)

