import requests
res = requests.post('http://localhost:80/api/auth/register', json={"name": "test", "email": "test@test", "password": "pass"})
print(res.status_code)
print(res.text)
