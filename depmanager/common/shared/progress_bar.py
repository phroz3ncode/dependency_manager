import sys


class ProgressBar:
    def __init__(self, total, description=None):
        self.description = description
        self.progress_count = 0
        self.progress_total = total
        self.progress_complete = False
        self.bar_len = 60
        if self.description is not None:
            total_len = 80
            description_len = len(description) + 2
            self.bar_len = total_len - description_len

    @property
    def filled_len(self):
        return int(round(self.bar_len * self.progress_count / float(self.progress_total)))

    @property
    def percents(self):
        return round(100.0 * self.progress_count / float(self.progress_total), 1)

    @property
    def bar_fill(self):
        return "=" * self.filled_len + "-" * (self.bar_len - self.filled_len)

    def reset(self):
        self.progress_count = 0
        self.progress_complete = False

    def inc(self):
        if not self.progress_complete:
            self.progress_count += 1
            description_string = f"{self.description}: " if self.description is not None else ""
            sys.stdout.write(f"{description_string}[{self.bar_fill}] {self.percents}%\r")
            sys.stdout.flush()
            if self.progress_count == self.progress_total:
                self.progress_complete = True
                print("")
