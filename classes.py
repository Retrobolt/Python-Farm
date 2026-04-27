class Message():
    alert = 'hello world'
    def hello(name):
        print(f'Hello {name}')
    def bye (name):
        print('Bye')


person = 'bob'
Message.hello(person)
print(Message.alert)
print()
Message.bye(person)