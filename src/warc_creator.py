import requests

def create_warc(url):
    """
    (str) -> None
    Connects to the front end and set up a link for a warc archieve of a
    particular item.
    """
    requests.get('http://localhost:8080/record/' + url)