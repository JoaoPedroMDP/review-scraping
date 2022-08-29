# coding: utf-8
import time

class Timer:
    def __init__(self):
        self.start_time = 0

    def start(self):
        self.start_time = time.time()

    def stop(self):
        start = self.start_time
        self.start_time = 0
        return time.time() - start