import requests
import json

url = 'http://ip-api.com/json/'

response = requests.get(url).json()

print(response)
print(f'You live in {response["city"]}')

for key, value in response.items():
    print(f'{key} -- {value}') 

print(json.dumps(response, indent=4))
print(f'          {response["city"]}')