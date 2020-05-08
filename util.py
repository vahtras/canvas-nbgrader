import time


class Timer:
    def __init__(self, text="", timer=time.time):
        self.timer = timer
        self.text = text

    def __enter__(self):
        self.t0 = self.timer()

    def __exit__(self, exc_type, exc_value, traceback):
        self.t1 = self.timer()
        print(f'{self.text}: {round(self.t1 - self.t0, 2)}')
