import requests


class Client:
    def fetch(self, url):
        return requests.get(url)
