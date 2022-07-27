# coding: utf-8
import datetime
import re
from typing import Dict, List, Union

from selenium import webdriver
from selenium.common import NoSuchElementException, ElementClickInterceptedException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

XPATHS = {
    "accept_cookies": '//*[@id="onetrust-accept-btn-handler"]',
    "language_selector": '//*[@id="tab-data-qa-reviews-0"]/div/div[1]/span/div/div[2]/div/div/span[2]/span/div/div/button',
    "lang_option": '//span[@id="menu-item-{}"]',
    "next_page_button": '//*[@id="tab-data-qa-reviews-0"]/div/div[5]/div[11]/div[1]/div/div[1]/div[2]/div/a',
    "pagination_info": '//*[@id="tab-data-qa-reviews-0"]/div/div[5]/div[11]/div[2]/div/div',
    "place_name": './/*[@data-automation="mainH1"]',
    "review_cards": '//*[@id="tab-data-qa-reviews-0"]/div/div[5]/div',
    "review_title": './/span/div/div[3]/a/span',
    "review_comment": './/span/div/div[5]/div[1]/div/span',
    "review_date_no_image": './/span/div/div[8]/div[1]',  # Alguns reviews possuem imagem. Isso altera o índice da <div> que contém a data
    "review_date_image": './/span/div/div[7]/div[1]',
    "review_rating": ".//span/div/div[2]/*[name()='svg']",
    "local": ".//span/div/div[1]/div[1]/div[2]/div/div",
    "category": ".//span/div/div[4]"
}

REGEXES = {
    "starts_with_number": '^\d.+$',
    "rating": "^(\d.\d) of \d bubbles$",
    "get_local": "^([a-zA-Z, ]+)\d.+$"
}

class Crawler:
    def __init__(self):
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    def open_page(self, url: str, cookies: bool = True):
        self.driver.get(url)
        if cookies:
            self.__handle_cookies()

    def close(self):
        self.driver.close()

    def select_language(self, lang: str):
        self.__go_to_language_selector()
        try:
            lang_option = self.driver.find_element(By.XPATH, XPATHS["lang_option"].format(lang))
            lang_option.click()
        except NoSuchElementException:
            print("Não foi possível encontrar a língua {}".format(lang))

    def get_page_title(self):
        return self.driver.find_element(By.XPATH, XPATHS["place_name"]).text

    def __handle_cookies(self):
        try:
            WebDriverWait(self.driver, 10).until(
                expected_conditions.element_to_be_clickable((By.XPATH, XPATHS["accept_cookies"]))
            ).click()
        except TimeoutException:
            print("Supondo que não haverão mais cookies, prosseguindo.")

    def __go_to_language_selector(self):
        WebDriverWait(self.driver, 10).until(
            expected_conditions.element_to_be_clickable(
                (By.XPATH, XPATHS["language_selector"])
            )
        )
        language_selector = self.driver.find_element(By.XPATH, XPATHS["language_selector"])
        cannot_click = True
        while cannot_click:
            try:
                language_selector.click()
                cannot_click = False
            except ElementClickInterceptedException:
                print("Erro ao clicar no seletor de idioma. Tentando novamente...")
                cannot_click = True

    def go_to_next_page(self):
        try:
            self.driver.find_element(By.XPATH, XPATHS["next_page_button"]).click()
            return True
        except NoSuchElementException:
            print("Acabaram-se as páginas")
            return False

    def wait_reviews_to_load(self):
        WebDriverWait(self.driver, 10).until(expected_conditions.presence_of_element_located((By.XPATH, XPATHS["pagination_info"])))

    def scrap_page(self) -> List[Dict]:
        raw_reviews = self.driver.find_elements(By.XPATH, XPATHS["review_cards"])
        page_reviews = []

        raw_reviews.pop()  # O último elemento é um botão nada a ver
        for review in raw_reviews:
            page_reviews.append(self.handle_review(review))

        return page_reviews


    def parse_date(self, date: str):
        parsed = datetime.datetime.strptime(date, "Written %B %d, %Y").strftime("%d/%m/%Y")
        return parsed


    def get_review_date(self, review: WebElement):
        try:
            return review.find_element(By.XPATH, XPATHS["review_date_no_image"]).text
        except Exception:
            #  Pode ser que tenha imagem, e por isso não foi possível encontrar a data
            return review.find_element(By.XPATH, XPATHS["review_date_image"]).text

    def parse_rating(self, rating: str):
        pattern = re.compile(REGEXES["rating"])
        return float(re.match(pattern, rating).group(1))


    def get_local(self, review: WebElement) -> Union[str, None]:
        local_and_contributions = review.find_element(By.XPATH, XPATHS["local"]).text

        # Se não começa com número, significa que, antes, vem a cidade de onde a pessoa escreve
        match = re.match(REGEXES["get_local"], local_and_contributions)
        if match:
            return match.group(1)

        return None

    def get_category(self, review: WebElement) -> Union[str, None]:
        try:
            return review.find_element(By.XPATH, XPATHS["category"]).text
        except NoSuchElementException:
            return None

    def handle_review(self, review: WebElement) -> Dict:
        title = review.find_element(By.XPATH, XPATHS["review_title"]).text
        comment = review.find_element(By.XPATH, XPATHS["review_comment"]).text
        date = self.get_review_date(review)
        rating = review.find_element(By.XPATH, XPATHS["review_rating"]).get_attribute("aria-label")
        local = self.get_local(review)
        category = self.get_category(review)

        return {
            "title": title,
            "comment": comment,
            "date": self.parse_date(date),
            "rating": self.parse_rating(rating),
            "local": local,
            "category": category
        }