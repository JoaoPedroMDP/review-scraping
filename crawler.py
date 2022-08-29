# coding: utf-8
import datetime
import re
from typing import Dict, List, Union, Tuple
from logger import custom_print

from selenium import webdriver
from selenium.common import NoSuchElementException, ElementClickInterceptedException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

CSS_CLASSES = {
    "review":{
        "title": "biGQs _P fiohW qWPrE ncFvv fOtGX",
        "date": "TreSq",
        "category": "RpeCd",
        "comment": {
            "div": "biGQs _P pZUbB KxBGd",
            "span": "yCeTE"
        },
        "local": {
            "div": "JINyA"
        }
    }
}


XPATHS = {
    "accept_cookies": '//*[@id="onetrust-accept-btn-handler"]',
    "language_selector": '//*[@id="tab-data-qa-reviews-0"]/div/div[1]/span/div/div[2]/div/div/span[2]/span/div/div/button',
    "lang_option": './/span[@id="menu-item-{}"]',
    "next_page_button": '//a[contains(@data-smoke-attr, "pagination-next-arrow")]',
    "pagination_info": '//*[@id="tab-data-qa-reviews-0"]/div/div[5]/div[11]/div[2]/div/div',
    "place_name": './/h1[@data-automation="mainH1"]',
    "review_amount": './span',
    "review_cards": '//*[@id="tab-data-qa-reviews-0"]/div/div[5]/div',
    "review_title": './/span/div/div[contains(@class, "'+CSS_CLASSES["review"]["title"]+'")]/a/span',
    "review_comment": './/div[contains(@class, "'+CSS_CLASSES["review"]["comment"]["div"]+'")]/span[contains(@class, "'+CSS_CLASSES["review"]["comment"]["span"]+'")]',
    "review_date": './/span/div/div[contains(@class, "'+CSS_CLASSES["review"]["date"]+'")]/div[1]',
    "review_rating": './/span/div/div[2]/*[name()="svg"]',
    "local": './/div[contains(@class, "'+CSS_CLASSES["review"]["local"]["div"]+'")]',
    "category": './/div[contains(@class, "'+CSS_CLASSES["review"]["category"]+'")]',
}

REGEXES = {
    "starts_with_number": '^\d.+$',
    "rating": "^(\d.\d) of \d bubbles$",
    "get_local": "^([a-zA-Z, ]+)\d.+$",
    "get_review_amount": "^\((\d+)\)$"
}

class Crawler:
    def __init__(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        # self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), chrome_options=chrome_options)

    def open_page(self, url: str, cookies: bool = True):
        self.driver.get(url)
        if cookies:
            self.__handle_cookies()

    def close(self):
        self.driver.close()

    def select_language(self, lang: str):
        self.__open_language_selector()
        try:
            lang_option = self.driver.find_element(By.XPATH, XPATHS["lang_option"].format(lang))
            lang_option.click()
        except NoSuchElementException as e:
            custom_print("Não foi possível encontrar a língua {}".format(lang))
            raise e

    def get_page_title(self):
        return self.driver.find_element(By.XPATH, XPATHS["place_name"]).text

    def has_next_page(self):
        try:
            if self.driver.find_element(By.XPATH, XPATHS["next_page_button"]) is not None:
                return True
        except NoSuchElementException:
            custom_print("Acabaram-se as páginas!")
            return False
        except Exception as e:
            custom_print("Erro ao verificar se há próxima página: {}".format(e))
            return False

    def __handle_cookies(self):
        try:
            WebDriverWait(self.driver, 10).until(
                expected_conditions.element_to_be_clickable((By.XPATH, XPATHS["accept_cookies"]))
            ).click()
        except TimeoutException:
            custom_print("Supondo que não haverão mais cookies, prosseguindo.")

    def __open_language_selector(self):
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
                custom_print("Erro ao clicar no seletor de idioma. Tentando novamente...")
                cannot_click = True

    def go_to_next_page(self):
        try:
            self.driver.find_element(By.XPATH, XPATHS["next_page_button"]).click()
        except NoSuchElementException:
            raise Exception("Não foi possível encontrar o botão de próxima página.")

    def wait_reviews_to_load(self):
        try:
            WebDriverWait(self.driver, 10).until(expected_conditions.presence_of_element_located((By.XPATH, XPATHS["pagination_info"])))
        except TimeoutException:
            custom_print("Tempo esgotado ao aguardar o carregamento das reviews")
        except Exception as e:
            raise Exception("Erro ao aguardar o carregamento das reviews: {}".format(e))

    def scrap_page(self) -> Tuple[List[Dict], int]:
        raw_reviews = self.driver.find_elements(By.XPATH, XPATHS["review_cards"])
        page_reviews = []

        raw_reviews.pop()  # O último elemento é um botão nada a ver
        counter = 0
        for review in raw_reviews:
            page_reviews.append(self.handle_review(review))
            counter += 1

        return page_reviews, counter


    def parse_date(self, date: str):
        parsed = datetime.datetime.strptime(date, "Written %B %d, %Y").strftime("%d/%m/%Y")
        return parsed

    def get_review_date(self, review: WebElement):
        return review.find_element(By.XPATH, XPATHS["review_date"]).text

    def parse_rating(self, rating_str: str):
        pattern = re.compile(REGEXES["rating"])
        rating = "?"
        try:
            rating = float(re.match(pattern, rating_str).group(1))
        except Exception as e:
            custom_print("Erro ao parsear o rating ({}): {}".format(rating_str, e))

        return rating


    def get_local(self, review: WebElement) -> Union[str, None]:
        local_and_contributions = review.find_element(By.XPATH, XPATHS["local"]).text

        # Se não começa com número, significa que, antes, vem a cidade de onde a pessoa escreve
        match = re.match(REGEXES["get_local"], local_and_contributions)
        local = ""
        if match:
            try:
                local =  match.group(1)
            except Exception as e:
                custom_print("Erro ao obter o local: {}".format(e))

        return local

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

    def get_review_amount(self, language: str):
        self.__open_language_selector()
        lang_option = self.driver.find_element(By.XPATH, XPATHS["lang_option"].format(language))
        lang_string = lang_option.find_element(By.XPATH, XPATHS["review_amount"]).text
        return "".join(lang_string.split()[1:-2])

    def language_routine(self, lang: str):
        self.__open_language_selector()
        try:
            lang_option = self.driver.find_element(By.XPATH, XPATHS["lang_option"].format(lang))
            review_amount_str = lang_option.find_element(By.XPATH, XPATHS["review_amount"]).text
            lang_option.click()
        except NoSuchElementException as e:
            raise Exception("Não foi possível encontrar a língua {}".format(lang))

        review_amount = 0
        try:
            review_amount = re.match(REGEXES["get_review_amount"], review_amount_str).group(1)
        except Exception as e:
            raise Exception("Não foi possível encontrar a quantidade de reviews da língua {}: {}".format(lang, e))

        return review_amount