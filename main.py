# coding: utf-8
import csv
import datetime
from typing import Tuple, Dict, List

from crawler import Crawler


def scrap_page(crawler: Crawler, url: str) -> Tuple[str, List[Dict]]:
    crawler.open_page(url)
    place_name = crawler.get_page_title().replace(" ", "_")
    reviews = []
    debug_limit = 2
    while crawler.go_to_next_page() and debug_limit > 0:
        crawler.wait_reviews_to_load()
        reviews += crawler.scrap_page()
        debug_limit-=1

    return place_name, reviews


def main():
    urls = []
    with open("urls.txt", 'r') as urls_file:
        urls = urls_file.readlines()

    print("Páginas a serem analisadas:\n{}".format("\n".join(urls)))

    crawler = Crawler()
    for url in urls:
        crawler.select_language('pt')
        page_title, page_data = scrap_page(crawler, url)
        with open("{}.csv".format(page_title), "w") as file:
            dict_to_csv_writer = csv.DictWriter(file, page_data[0].keys())
            dict_to_csv_writer.writeheader()
            dict_to_csv_writer.writerows(page_data)

        print("{} terminada em {}".format(page_title, datetime.datetime.now().strftime("%d/%m/%Y %H:%i:%s")))


if __name__ == "__main__":
    main()