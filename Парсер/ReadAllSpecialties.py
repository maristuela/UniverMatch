import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from random import random
import re

def clean_text(text):
    cyrillic_only = re.sub(r'[^а-яёА-ЯЁ]', '', text)
    return cyrillic_only.lower()

def clean(x):
    return x.replace("\xa0", " ")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    for i in range(1, 22):
        page.goto(f"https://www.ucheba.ru/for-abiturients/speciality/search?examSubjectIds[]=2&examSubjectIds[]=1&page={i}")
        html_content = page.content()
        soup = BeautifulSoup(html_content, "html.parser")

        print(i)
        specialities = soup.select("[class^=\"SpecialitiesList\"]")
        for spec in specialities:
            name = spec.find("a")
            description = spec.select(".hGCpdV")
            if description != []:
                name = clean_text(name.text)
                description = clean(description[0].text)
                with open("SpecialtiesDescriptions.txt", "a") as f:
                    f.write(name + "\n")
                    f.write(description + "\n")

        time.sleep(2 + (random() - 0.5) * 2)