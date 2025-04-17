def test_temp():
    import requests
    response = requests.get("http://localhost:8000/api/v1/challenges/achievements", headers={"Authorization": "Bearer FAKE_TOKEN"})
    print(response.text)
