import os
command = 'ping -c 4'

def ping(host):
    response = os.popen(f'{command} {host}').read()
    return response

while True:
    host = input('Host to ping: ')
    response = ping(host)
    print(response)