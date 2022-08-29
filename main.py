# coding: utf-8
import csv
import datetime
import os
from concurrent import futures
from typing import Dict, List, TextIO

from beeper import beep
from crawler import Crawler
from logger import custom_print
from timer import Timer

timer = Timer()

def write_data_chunk(csv_writer: csv.DictWriter, data: List[Dict], amount: int):
    try:
        custom_print("Salvando {} reviews em {}".format(amount, datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
        csv_writer.writerows(data)
        custom_print("Salvamento terminado em {}".format(datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
    except Exception as e:
        custom_print("Erro ao salvar os reviews: {}".format(e), "error")
        beep("exception")

def scrap_url(crawler: Crawler, csv_writer: csv.DictWriter, file: TextIO, page_title: str):
    language = 'pt'
    review_amount = int(crawler.language_routine(language))
    custom_print("{} -> {} reviews encontrados".format(page_title, review_amount))
    reviews = []
    counter = 0
    has_next_page = True
    saving_threshold = 100

    try:
        while has_next_page:
            crawler.wait_reviews_to_load()
            reviews, processed = crawler.scrap_page()
            counter += processed

            custom_print("{} -> {:.2f}% ({}/{})".format(page_title, (counter/review_amount)*100, counter, review_amount))
            has_next_page = crawler.has_next_page()

            if counter % saving_threshold == 0:
                write_data_chunk(csv_writer, reviews, saving_threshold)
                reviews = []

            if has_next_page:
                crawler.go_to_next_page()
    except Exception as exc:
        custom_print("{} gerou uma exceção => {}".format(page_title, exc))
        beep("exception")

    custom_print("{} -> Salvando os restantes {} reviews".format(page_title, len(reviews)))
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
    custom_print("Iniciando {}".format(url))
    crawler = Crawler()
    url_timer = Timer()
    url_timer.start()

    crawler.open_page(url)
    page_title = crawler.get_page_title().replace(" ", "_")
    custom_print("{} -> Página 1 aberta".format(page_title))

    custom_print("{} -> Abrindo o arquivo".format(page_title))
    file = open("reviews/{}/{}.csv".format(directory, page_title), "w")
    dict_to_csv_writer = start_csv_writer(file)

    custom_print("{} -> Iniciando o scraping".format(page_title))
    scrap_url(
        crawler=crawler,
        csv_writer=dict_to_csv_writer,
        file=file,
        page_title=page_title
    )

    custom_print("{} -> Fechando o arquivo".format(page_title))
    file.close()
    beep("done")
    custom_print("DONE -----> {} terminada em {} segundos".format(page_title, url_timer.stop()))

def main():
    urls = []

    with open("urls.txt", 'r') as urls_file:
        urls = urls_file.readlines()

    begin_time = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    directory = "reviews/{}".format(begin_time)
    os.mkdir("reviews/{}".format(begin_time))
    tasks = set()
    with futures.ThreadPoolExecutor(2) as executor:
        future_results = {url: executor.submit(url_task, url, begin_time) for url in urls}
        for url, future in future_results.items():
            try:
                future.result()
            except Exception as exc:
                custom_print("Thread de {} gerou uma exceção: {}".format(url, exc))

directory = ""
if __name__ == "__main__":
    main()