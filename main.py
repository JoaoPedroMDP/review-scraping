# coding: utf-8
import csv
import datetime
import os
from concurrent import futures
import traceback
from typing import Dict, List, TextIO
from logging import getLogger
import locale

from beeper import beep
from config import THREADS
from crawler import Crawler
from logger import init_logging, debug
from timer import Timer

timer = Timer()
logger = getLogger("scrapper")
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')

def write_data_chunk(csv_writer: csv.DictWriter, data: List[Dict], amount: int):
    try:
        debug("Salvando {} reviews em {}".format(
            amount, datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
        csv_writer.writerows(data)
        debug("Salvamento terminado em {}".format(
            datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
    except Exception as e:
        debug("Erro ao salvar os reviews: {}".format(e), "error")
        beep("exception")


def scrap_url(crawler: Crawler, csv_writer: csv.DictWriter, file: TextIO, page_title: str):
    language = 'pt'
    review_amount = crawler.get_review_amount()
    debug(
        "{} -> {} reviews encontrados".format(page_title, review_amount))
    reviews = []
    counter = 0
    has_next_page = True
    saving_threshold = 100

    try:
        while has_next_page:
            crawler.wait_reviews_to_load()
            reviews, processed = crawler.scrap_page()
            counter += processed

            debug("{} -> {:.2f}% ({}/{})".format(page_title,
                         (counter/review_amount)*100, counter, review_amount))
            has_next_page = crawler.has_next_page()

            if counter % saving_threshold == 0:
                write_data_chunk(csv_writer, reviews, saving_threshold)
                reviews = []

            if has_next_page:
                crawler.go_to_next_page(page_title)
    except Exception as exc:
        debug("{} gerou uma exceção => {}".format(page_title, exc))
        beep("exception")

    debug(
        "{} -> Salvando os restantes {} reviews".format(page_title, len(reviews)))
    if reviews:
        write_data_chunk(csv_writer, reviews, len(reviews))


def start_csv_writer(file: TextIO) -> csv.DictWriter:
    example = {
        "title": "",
        "comment": "",
        "date": "",
        "rating": "",
        "local": "",
        "category": ""
    }
    dict_to_csv_writer = csv.DictWriter(file, example.keys())
    return dict_to_csv_writer


def url_task(url: str, directory: str):
    debug("Iniciando {}".format(url))
    crawler = Crawler()
    url_timer = Timer()
    url_timer.start()

    crawler.open_page(url)
    page_title = crawler.get_page_title().replace(" ", "_")
    debug("{} -> Página 1 aberta".format(page_title))

    debug("{} -> Abrindo o arquivo".format(page_title))
    file = open("reviews/{}/{}.csv".format(directory, page_title), "w")
    dict_to_csv_writer = start_csv_writer(file)

    debug("{} -> Iniciando o scraping".format(page_title))
    scrap_url(
        crawler=crawler,
        csv_writer=dict_to_csv_writer,
        file=file,
        page_title=page_title
    )

    debug("{} -> Fechando o arquivo".format(page_title))
    file.close()
    beep("done")
    debug("DONE -----> {} terminada em {} segundos".format(page_title, url_timer.stop()))


def main():
    urls = []

    with open("urls.txt", 'r') as urls_file:
        urls = urls_file.readlines()

    begin_time = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    directory = "reviews/{}".format(begin_time)
    os.mkdir("reviews/{}".format(begin_time))
    tasks = set()
    with futures.ThreadPoolExecutor(THREADS) as executor:
        future_results = {url: executor.submit(
            url_task, url, begin_time) for url in urls}
        for url, future in future_results.items():
            try:
                future.result()
            except Exception as exc:
                debug("Thread de {} gerou uma exceção:" .format(url))
                traceback.print_exception(type(exc), exc, exc.__traceback__)


if __name__ == "__main__":
    init_logging()
    main()
