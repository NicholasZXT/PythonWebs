import httpx
from httpx import Request, Response

r: Response = httpx.get('https://httpbin.org/get')
r: Response = httpx.post('https://httpbin.org/post', data={'key': 'value'})

params = {'key1': 'value1', 'key2': 'value2'}
r = httpx.get('https://httpbin.org/get', params=params)

print(r.request)
print(r.headers)
print(r.status_code)
print(r.is_success)
print(r.url)
print(r.content)
print(r.text)

r = httpx.get('https://api.github.com/events')
print(r.json())


# ----------------- 异步请求 -----------------

async with httpx.AsyncClient() as client:
    r: Response = await client.get('https://httpbin.org/get')


print(r.text)