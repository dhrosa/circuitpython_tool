import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://circuitpython.org"


@dataclass
class Version:
    version: str
    url: str

    @staticmethod
    def from_url(url: str) -> "Version":
        return Version(re.search("en_US-(.+)\.uf2", url).group(1), url)


@dataclass
class Board:
    id: str
    name: str
    url: str

    @staticmethod
    def all() -> dict[str, "Board"]:
        downloads = BeautifulSoup(
            requests.get(f"{BASE_URL}/downloads").text, features="html.parser"
        ).find_all(class_="download")
        return {
            d.get("data-id"): Board(
                d.get("data-id"), d.get("data-name"), BASE_URL + d.find("a").get("href")
            )
            for d in downloads
        }

    def versions(self) -> list[Version]:
        page = BeautifulSoup(requests.get(self.url).text, features="html.parser")
        return [
            Version.from_url(option.get("value"))
            for option in page.find_all("option", attrs={"data-locale": "en-US"})
        ]
