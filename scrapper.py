# coding: utf-8
import datetime
import os
import re
from logger import debug, error, info
from typing import Dict, List, Union, Tuple

from selenium import webdriver
from selenium.common import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from config import HEADLESS

CSS_CLASSES = {
    "review": {
        "title": "BMQDV _F Gv wSSLS SwZTJ FGwzt ukgoS",
        "date": "biGQs _P pZUbB ncFvv osNWb",
        "category": "RpeCd",
        "comment": {
            "div": "biGQs _P pZUbB KxBGd",
            "span": "JguWG"
        },
        "local": {
            "div": "JINyA"
        },
        "rating": "UctUV d H0"
    },
    "obstacles": {
        "bottom_ads": "ZHIlj E s f e"
    }
}


XPATHS = {
    "bottom_ads_closer": ".//button[contains(@type, 'button') and contains (@aria-label, 'Close')]",
    "bottom_ads": ".//div[contains(@class, '{}')]".format(CSS_CLASSES["obstacles"]["bottom_ads"]),
    "accept_cookies": '//*[@id="onetrust-accept-btn-handler"]',
    "language_selector": '//span[text()="English"]',
    "lang_option": './/span[@id="menu-item-{}"]',
    "next_page_button": '//a[contains(@data-smoke-attr, "pagination-next-arrow")]',
    "pagination_info": '//div[contains(text(),"Mostrando")]',
    "place_name": './/h1[@data-automation="mainH1"]',
    "review_cards": '//*[@data-automation="reviewCard"]',
    "review_title": './/a[contains(@class, "'+ CSS_CLASSES["review"]["title"] +'")]/span',
    "review_comment": './/div[contains(@class, "'+ CSS_CLASSES["review"]["comment"]["div"] +'")]/span[contains(@class, "'+ CSS_CLASSES["review"]["comment"]["span"] +'")]',
    "review_date": './/div[contains(@class, "'+ CSS_CLASSES["review"]["date"] +'")]',
    "review_rating": './/*[local-name()="svg" and @class="' + CSS_CLASSES["review"]["rating"] + '"]',
    "local": './/div[contains(@class, "'+ CSS_CLASSES["review"]["local"]["div"] +'")]',
    "category": './/div[contains(@class, "'+ CSS_CLASSES["review"]["category"] +'")]',
}
REGEXES = {
    "starts_with_number": '^\d.+$',
    "rating": "^(\d.\d) de \d círculos$",
    "get_local": "^([a-zA-Z, ]+)\d.+$",
    "get_review_amount": "^Mostrando.* de (.*) resultados$",
    "get_category": "^.*• (.*)$",
}


class Scrapper:
    def __init__(self):
        chrome_options = webdriver.ChromeOptions()
        if HEADLESS:
            chrome_options.add_argument("--headless")

        self.driver = webdriver.Chrome(service=Service(
            ChromeDriverManager().install()), chrome_options=chrome_options)

    def open_page(self, url: str, cookies: bool = True):
        debug("Abrindo página {}".format(url))
        self.driver.get(url)
        if cookies:
            debug("Aceitando cookies")
            self.__handle_cookies()

        self.__handle_obstacles()

    def __handle_obstacles(self):
        bottom_ads = self.__have_ads_at_bottom()
        if bottom_ads is not None:
            self.__handle_ads(bottom_ads)

    def __have_ads_at_bottom(self) -> Union[WebElement, None]:
        debug("Verificando se há anúncios no final da página")
        try:
            return self.driver.find_element(By.XPATH, XPATHS["bottom_ads"])
        except NoSuchElementException:
            return None

    def __handle_ads(self, bottom_ads: WebElement):
        debug("Fechando anúncios")
        bottom_ads.find_element(By.XPATH, XPATHS["bottom_ads_closer"]).click()

    def close(self):
        debug("Fechando navegador")
        self.driver.close()

    def get_page_title(self):
        debug("Obtendo título da página")
        return self.driver.find_element(By.XPATH, XPATHS["place_name"]).text

    def has_next_page(self):
        debug("Verificando se há próxima página")
        try:
            if self.driver.find_element(By.XPATH, XPATHS["next_page_button"]) is not None:
                debug("Há próxima página")
                return True
        except NoSuchElementException:
            debug("Acabaram-se as páginas!")
            return False
        except Exception as e:
            debug(
                "Erro ao verificar se há próxima página: {}".format(e))
            return False

    def __handle_cookies(self):
        try:
            WebDriverWait(self.driver, 10).until(
                expected_conditions.element_to_be_clickable(
                    (By.XPATH, XPATHS["accept_cookies"]))
            ).click()
            debug("Cookies aceitos, oráculo!")
        except TimeoutException:
            debug("Supondo que não haverão mais cookies, prosseguindo.")

    def go_to_next_page(self, page_title: str):
        debug("Indo para próxima página")
        try:
            el = self.driver.find_element(
                By.XPATH, XPATHS["next_page_button"])
            info("{} -> Indo para próxima página".format(page_title))
            el.click()
        except NoSuchElementException:
            raise Exception("Não foi possível encontrar o botão de próxima página.")

    def wait_reviews_to_load(self):
        debug("Aguardando carregamento das reviews")
        try:
            WebDriverWait(self.driver, 10).until(
                expected_conditions.presence_of_element_located((By.XPATH, XPATHS["pagination_info"])))
        except TimeoutException:
            debug("Tempo esgotado ao aguardar o carregamento das reviews")
        except Exception as e:
            raise Exception(
                "Erro ao aguardar o carregamento das reviews: {}".format(e))

    def scrap_page(self) -> Tuple[List[Dict], int]:
        debug("Extraindo reviews da página")
        raw_reviews = self.driver.find_elements(
            By.XPATH, XPATHS["review_cards"])
        page_reviews = []

        raw_reviews.pop()  # O último elemento é um botão nada a ver
        counter = 0
        for review in raw_reviews:
            new_data = self.handle_review(review)
            info("Review extraído: {}".format(new_data))
            if new_data is not None:
                page_reviews.append(new_data)
                counter += 1
        
        info(f"Encontrados {counter} reviews")
        return page_reviews, counter

    def parse_date(self, date: str):
        debug("Parseando data")
        parsed = datetime.datetime.strptime(date, "Feita em %d de %B de %Y").strftime("%d/%m/%Y")
        return parsed

    def get_review_date(self, review: WebElement):
        debug("Obtendo data do review")
        return review.find_element(By.XPATH, XPATHS["review_date"]).text

    def get_review_amount(self):
        debug("Obtendo quantidade de reviews no ponto turístico")
        pagination_info = self.driver.find_element(
            By.XPATH, XPATHS["pagination_info"]).text
        pattern = re.compile(REGEXES["get_review_amount"])
        amount = 0
        try:
            review_amount_str = re.match(pattern, pagination_info).group(1)
            amount = int(review_amount_str.replace(".", ""))
            debug(f"{amount} reviews no total")
        except Exception as e:
            error("Erro ao obter a quantidade de reviews: {}".format(e))

        return amount

    def parse_rating(self, rating_str: str):
        debug("Parseando avaliação do turista")
        pattern = re.compile(REGEXES["rating"])
        rating = "?"
        try:
            rating = float(
                re.
                match(pattern, rating_str).
                group(1).
                replace(",", ".")
            )
        except Exception as e:
            error("Erro ao parsear o rating ({}): {}".format(rating_str, e))

        return rating

    def get_local(self, review: WebElement) -> Union[str, None]:
        debug("Obtendo local no turista")
        local_and_contributions = review.find_element(
            By.XPATH, XPATHS["local"]).text

        # Se não começa com número, significa que, antes, vem a cidade de onde a pessoa escreve
        match = re.match(REGEXES["get_local"], local_and_contributions)
        local = ""
        if match:
            try:
                local = match.group(1)
            except Exception as e:
                error("Erro ao obter o local: {}".format(e))

        return local

    def get_category(self, review: WebElement) -> Union[str, None]:
        debug("Obtendo categoria do review")
        raw_category = review.find_element(By.XPATH, XPATHS["category"]).text
        match = re.match(REGEXES["get_category"], raw_category)
        try:
            if match:
                category = match.group(1)
            else:
                category = ""
        except NoSuchElementException:
            return ""

        return category

    def handle_review(self, review: WebElement) -> Dict:
        debug("Extraindo dados do review")
        debug("Pegando título")
        title = review.find_element(By.XPATH, XPATHS["review_title"]).text
        debug("Pegando comentário")
        comment = review.find_element(By.XPATH, XPATHS["review_comment"]).text
        debug("Pegando data")
        date = self.get_review_date(review)
        debug("Pegando rating")
        rating = review.find_element(
            By.XPATH, XPATHS["review_rating"]).get_attribute("aria-label")
        debug("Pegando local")
        local = self.get_local(review)
        debug("Pegando categoria")
        category = self.get_category(review)

        return {
            "title": title,
            "comment": comment,
            "date": self.parse_date(date),
            "rating": self.parse_rating(rating),
            "local": local,
            "category": category
        }

    def print_element(self, element: WebElement):
        # now = datetime.datetime.now()
        # debug(element.screenshot(f"{os.getcwd()}/element{now}.png"))
        debug(element.screenshot(f"{os.getcwd()}/element.png"))