import requests

url = 'http://ip-api.com/json/'

try:
    response = requests.get(url).json()
    print(response['city']) 
except Exception as e:
    print('An error occurred:', e)
except:
    print('There was an error')
else:
    print('Else always runs if TRY works')
finally:
    print('Finally always runs')