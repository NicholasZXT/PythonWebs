import requests
from requests import Session

def get_stream(url: str):
    session: Session = requests.Session()
    with session.get(url, headers=None, stream=True) as response:
        for line in response.iter_lines(decode_unicode=True):
            if line:
                # print(line.decode('utf-8'))
                print(line)


if __name__ == '__main__':
    # host = 'localhost'
    host = '10.8.6.203'
    port = 8100
    url = f'http://{host}:{port}/streaming/contents'
    get_stream(url)
