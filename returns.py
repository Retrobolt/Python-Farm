def hello (name):
    welcome = f'hello {name}'
    leave = f'goodbye {name}'
    future = f'come again {name}'

    return welcome, leave, future

person = 'bob'

response = hello(person)

print(response[1])
print()

print(response) # this will print the entire tuple that is returned from the function
print(response[0]) # this will print the first value in the tuple that is returned from the function
print(response[1]) # this will print the second value in the tuple that is returned from the function
print(response[2]) # this will print the third value in the tuple that is returned from the function

