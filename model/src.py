import requests
import json

url = 'http://localhost:11434/api/chat'

data = {
    'model': 'llama3.2',
    'messages': [
        {'role': 'user', 'content': 'Hello, how are you?'}
    ],
    'stream': False
}

response = requests.post(url, json=data)
print(response.json()['message']['content'])