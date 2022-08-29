# coding: utf-8
import time

BEEP_CODES = {
    "exception": 3,
    "done": 1,
}

def beep(times: str):
    for i in range(BEEP_CODES[times]):
        print("\a")
        time.sleep(0.4)
    time.sleep(0.7)