def compute_total(values):
    return sum(values)


class Worker:
    def bridge(self, data):
        normalized = data.strip()
        return normalized.upper()


VERBOSE = True
TIMEOUT = 60
NEW_FLAG = "added"
