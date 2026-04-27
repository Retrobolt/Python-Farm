import requests
import time

url = 'https://official-joke-api.appspot.com/random_joke'

while True:
    page = '''
            <meta http-equiv="refresh" content="5">
            <h1>Joke Web App</h1>
            '''
    response = requests.get(url).json()

    print(response['setup'])
    print(response['punchline'])

    with open('joke.html', 'w') as file:
        file.write('<meta http-equiv="refresh" content="5">')
        file.write('<h1>Joke Web App</h1>')
        file.write(f'<p>{response["setup"]}</p>')
        file.write(f'<hr>')
        file.write(f'<p>{response["punchline"]}</p>')

    time.sleep(5)