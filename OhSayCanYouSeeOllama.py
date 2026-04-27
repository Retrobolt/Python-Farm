from ollama import chat, ChatResponse

def ai(query):
    injection = 'Answer in under 20 words.'
    query = f'{injection} -- {query}'
    response: ChatResponse = chat(model='granite4:1b', messages=[
        {
            'role': 'user',
            'content': query
    }
    ])
    return response.message.content

while True:
    query = input('Query: ')
    response = ai(query)
    print(response)
