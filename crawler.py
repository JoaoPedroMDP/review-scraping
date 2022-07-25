# coding: utf-8
from typing import Dict, List
from json import dumps
import datetime
import re

from selenium import webdriver
from selenium.common import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions

XPATHS = {
    "accept_cookies": '//*[@id="onetrust-accept-btn-handler"]',
    "language_selector": '//*[@id="tab-data-qa-reviews-0"]/div/div[1]/span/div/div[2]/div/div/span[2]/span/div/div/button',
    "portuguese_option": '//span[@id="menu-item-pt"]',
    "next_page_button": '//*[@id="tab-data-qa-reviews-0"]/div/div[5]/div[11]/div[1]/div/div[1]/div[2]/div/a',
    "review_cards": '//*[@id="tab-data-qa-reviews-0"]/div/div[5]/div',
    "review_title": './/span/div/div[3]/a/span',
    "review_comment": './/span/div/div[5]/div[1]/div/span',
    "review_date_no_image": './/span/div/div[8]/div[1]',  # Alguns reviews possuem imagem. Isso altera o índice da <div> que contém a data
    "review_date_image": './/span/div/div[7]/div[1]',
    "review_rating": ".//span/div/div[2]/*[name()='svg']"
}

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.get("https://www.tripadvisor.com/Attraction_Review-g303441-d1493739-Reviews-Jardim_Botanico_de_Curitiba-Curitiba_State_of_Parana.html")


# Aceita Cookies
WebDriverWait(driver, 10).until(
    expected_conditions.element_to_be_clickable((By.XPATH, XPATHS["accept_cookies"]))
).click()


WebDriverWait(driver, 3).until(expected_conditions.element_to_be_clickable((By.XPATH, XPATHS["language_selector"])))
WebDriverWait(driver, 3).until(expected_conditions.element_to_be_clickable((By.XPATH, XPATHS["language_selector"])))
language_selector = driver.find_element(By.XPATH, XPATHS["language_selector"])
cannot_click = True
while cannot_click:
    try:
        language_selector.click()
        cannot_click = False
    except ElementClickInterceptedException as e:
        print("Erro ao clicar")
        cannot_click = True

portuguese_option = driver.find_element(By.XPATH, XPATHS["portuguese_option"])
portuguese_option.click()

def parse_date(date: str):
    parsed = datetime.datetime.strptime(date, "Written %B %d, %Y").strftime("%d/%m/%Y")
    return parsed

def get_review_date(review: WebElement):
    try:
        return review.find_element(By.XPATH, XPATHS["review_date_no_image"]).text
    except Exception as e:
        #  Pode ser que tenha imagem, e por isso não foi possível encontrar a data
        return review.find_element(By.XPATH, XPATHS["review_date_image"]).text


def parse_rating(rating: str):
    pattern = re.compile("^(\d.\d) of \d bubbles$")
    return float(re.match(pattern, rating).group(1))


def handle_review(review: WebElement) -> Dict:
    title = review.find_element(By.XPATH, XPATHS["review_title"]).text
    comment = review.find_element(By.XPATH, XPATHS["review_comment"]).text
    date = get_review_date(review)
    rating = review.find_element(By.XPATH, XPATHS["review_rating"]).get_attribute("aria-label")

    return {
        "title": title,
        "comment": comment,
        "date": parse_date(date),
        "rating": parse_rating(rating)
    }

def scrap_page(driver: WebDriver) -> List[Dict]:
    raw_reviews = driver.find_elements(By.XPATH, XPATHS["review_cards"])
    page_reviews = []

    raw_reviews.pop()  # O último elemento é um botão nada a ver
    for review in raw_reviews:
        page_reviews.append(handle_review(review))

    return page_reviews

try:
    reviews = []
    has_next_page = True
    limit = 1
    while has_next_page and limit > 0:
        WebDriverWait(driver, 5).until(expected_conditions.presence_of_element_located((By.XPATH, XPATHS["next_page_button"])))
        reviews.append(scrap_page(driver))
        limit-=1

        try:
            driver.find_element(By.XPATH, XPATHS["next_page_button"]).click()
        except NoSuchElementException as e:
            print("Acabaram as páginas")
            has_next_page = False

    with open("data.json", "a") as file:
        file.write(dumps(reviews, indent=4, ensure_ascii=False))

except Exception as e:
    print(e)
finally:
    driver.close()