import os

host = ['google.com', 'yahoo.com', 'bing.com', 'duckduckgo.com', 'ask.com']

command = 'ping -c 1'

while True:
    page = '''
            <meta http-equiv="refresh" content="5">
            <h1>Ping Page</h1>
            '''
    
    for site in host:
        response = os.popen(f'{command} {site}').read()
        page += f'<pre>{response}</pre>'
    
    with open('pingPage.html', 'w') as file:
        file.write(page)