import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from random import random
import re
from random import shuffle
from vuzCities import CityGetter
from os import remove
import json

def load(mx = 10000):
    for _ in range(mx):
        try:
            page.wait_for_selector(".morediv", timeout=5000)
            page.click(".morediv")
            time.sleep(3 + (random() - 0.5) * 2)
        except:
            break

with open("database.json", "w") as f:
    f.write("[\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://tabiturient.ru/globalrating/")

    html_content = page.content()
    soup = BeautifulSoup(html_content, "html.parser")

    products = soup.find_all("table", class_="listtop100")
    vuzIds = []
    for prod in products[:-1]:
        id = prod.find("div", class_="vuzlogotop100").find("img")["src"]
        id = id[id.rfind('/') + 1:].split('.')[0]
        shortName = prod.find("b").text
        longName = prod.select_one("[valign=\"center\"]").find_all("span", class_="font2")[1].find("b").text
        longName = longName.strip()
        vuzIds.append((id, longName))
        with open("NewFile.txt", "a") as file:
            file.write(longName + ' ' + id + ' \n')


    #shuffle(vuzIds)

    shortages = {
        "РЯ": "Русский язык",
        "М": "Математика (профиль)",
        "Ф": "Физика",
        "Х": "Химия",
        "ИКТ": "Информатика",
        "Б": "Биология",
        "И": "История",
        "О": "Обществознание",
        "ИЯ": "Английский язык",
        "Л": "Литература",
        "Г": "География"
    }

    cityGetter = CityGetter()
    specId = dict()
    for vuzId, (vuzShort, vuzLong) in enumerate(vuzIds):
        page.goto(f"https://tabiturient.ru/vuzu/{vuzShort}/proxodnoi/")
        load()
        html_content = page.content()
        soup = BeautifulSoup(html_content, "html.parser")
        print(vuzLong)

        vuzId += 1

        city = cityGetter.getCity(vuzShort)
        site_abbreviations = {
            "РЯ": "ru",
            "M": "math",
            "Ф": "phys",
            "Х": "chem",
            "ИКТ": "inf",
            "Б": "bio",
            "И": "hist",
            "О": "soc",
            "ИЯ": "eng",
            "Л": "lit",
            "Г": "geo",
            "ДЭ" : "dvi"
        }
        for block in soup.find_all("div", class_="mobpaddcard"):
            try:
                lst = []
                font2 = block.find_all("span", class_="font2")
                progName1 = font2[0].text
                if progName1 == "Дизайн":
                    pass
                progName2 = font2[2].text
                progName2 = progName2[progName2.find(': ') + 2:]
                progName = None
                if progName1 != progName2:
                    progName = progName1 + ' (' + progName2 + ')'
                else:
                    progName = progName1
                subjTables = block.find_all("table", class_="cirfloat")
                subj1 = []
                for el in subjTables:
                    subj1.append('|'.join(x.text for x in el.find("td").find_all("b")))
                for i, el in enumerate(subj1):
                    if el[0].isdigit() or el in ["new", "БВИ", "Нет"]:
                        break
                if not el[0].isdigit():
                    continue
                subj = []
                for el in subj1[:i]:
                    if '|' in el:
                        subj.append('|'.join(site_abbreviations[x] for x in el.split('|')))
                    else:
                        subj.append(site_abbreviations[el])
                ball = int(subj1[i])
                del subj1

                vuzSite = soup.find("div", class_="obram").find("a")["href"]

                dict = {
                    "name" : vuzLong,
                    "program" : progName,
                    "city" : city,
                    "exams" : subj,
                    "min_score" : ball,
                    "url" : vuzSite
                }

                with open("database.json", "a", encoding="utf-8") as f:
                    curJson = json.dumps(dict, ensure_ascii=False, indent=4)
                    f.write(curJson + ",\n")
            except:
                continue

    finalText = None
    with open("database.json", "r", encoding="utf-8") as f:
        finalText = f.read()

    with open("database.json", "w", encoding="utf-8") as f:
        f.write(finalText[:-2] + '\n]')