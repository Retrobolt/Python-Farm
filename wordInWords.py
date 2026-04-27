password = 'password'

while True:
    phrase = input('Enter your password: ')

    if password in phrase:
        print('Welcome back!')
        break
    else:
        print('Incorrect password, try again.')