import os
import sys
import time
from datetime import datetime

import pandas as pd
from tqdm import tqdm

from .singleton import Singleton
from ..utilities.context_manager_tqdm import Nostdout
from ..utilities.configuration import Configuration


class Performance(metaclass=Singleton):
    def __init__(self, perf_path: str):
        self.start = time.time()
        self.last = self.start
        self.perf = pd.DataFrame(columns=["name", "start", "end", "duration"])
        self.path = perf_path
        self.count = 0
        self.pbar = tqdm(file=sys.stdout)
        self.total = None
        # start python trickery
        self.ctx = Nostdout()
        self.ctx.__enter__()

    def string_time(self, epoch_time):
        return datetime.utcfromtimestamp(epoch_time).strftime("%H:%M:%S")

    def finished_step(self, log_message: str = None):
        end = time.time()
        if log_message is None:
            self.perf = pd.concat([self.perf, pd.DataFrame.from_records([
                {
                    "name": log_message,
                    "start": self.string_time(self.last),
                    "end": self.string_time(end),
                    "duration": (end - self.last)
                }])])
        self.pbar.set_description(f"{log_message}: took {round(end - self.last, 2)} seconds")
        self.last = end
        self.count += 1
        self.pbar.update(1)

    def track(argument: str = None):
        def performance_tracker_wrapper(func):
            def wrapper(self, *args, **kwargs):
                result = func(self, *args, **kwargs)
                end = time.time()
                perf = Performance()
                if argument is None or argument not in kwargs:
                    log_message = func.__name__
                else:
                    log_message = f"{func.__name__} for {kwargs[argument]}"
                perf.perf = pd.concat([perf.perf, pd.DataFrame.from_records([
                    {
                        "name": log_message,
                        "start": perf.string_time(perf.last),
                        "end": perf.string_time(end),
                        "duration": (end - perf.last)
                    }])])
                perf.pbar.set_description(f"{log_message}: took {round(end - perf.last, 2)} seconds")
                perf.last = end
                perf.count += 1
                perf.pbar.update(1)
                return result

            return wrapper

        return performance_tracker_wrapper

    def finish(self):
        end = time.time()
        print(f"{self.count} steps")
        self.perf = pd.concat([self.perf, pd.DataFrame.from_records([
            {
                "name": "total",
                "start": self.string_time(self.start),
                "end": self.string_time(end),
                "duration": (end - self.start)
            }])])
        self.total = round(end - self.start, 2)
        print(f"Total: took {round(end - self.start, 2)} seconds")
        self.pbar.set_description(f"Completed")
        self.pbar.close()
        # close python trickery
        self.ctx.__exit__()

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.perf.to_csv(self.path, sep=";", decimal=",")

    @staticmethod
    def set_up_performance_with_path(path):
        return Performance(perf_path=path)

    @staticmethod
    def set_up_performance(config: Configuration):
        path = os.path.join("perf", f"{config.db_name}_{'sample_' * config.use_sample}Performance.csv")
        return Performance.set_up_performance_with_path(path=path)

    def finish_and_save(self):
        self.finish()
        self.save()
