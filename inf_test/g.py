from gonka_openai import GonkaOpenAI
from gonka_openai.utils import Endpoint

# Create endpoints directly
endpoints = [
        Endpoint(url="https://node4.gonka.ai/v1", address="gonka1kx9mca3xm8u8ypzfuhmxey66u0ufxhs7nm6wc5"),
    ]

#endpoints = [
#    Endpoint(url="https://api.gonka.testnet.example.com", address="gonka1transferaddress"),
#    Endpoint(url="https://api2.gonka.testnet.example.com", address="gonka2transferaddress")
#]

def first_endpoint_strategy(endpoints):
    """Always select the first endpoint."""
    return endpoints[0]

client = GonkaOpenAI(
    api_key="mock-api-key",
    gonka_private_key="c081b2dad6d8def9855cfd034e4fcfd11ab364f41e43a7c6d6d9697832f1e704",
    endpoints=endpoints,
    endpoint_selection_strategy=first_endpoint_strategy
)

# Use normally
response = client.chat.completions.create(
    #model="Qwen/Qwen3-235B-A22B-Instruct-2507-FP8",
    model="moonshotai/Kimi-K2.6",
    messages=[{"role": "user", "content": "Ответ на мой прошлый запрос оборвался незаконченым. Я обращаюсь по api. Можно ли как то получать продолжение ответов? Почему ответ образается?"}],
)

print(response.choices[0].message.content)