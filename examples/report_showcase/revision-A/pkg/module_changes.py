class Config:
    """Configuration holder for data processing."""
    def __init__(self, debug: bool = True):
        self.debug = debug


def calc_total(values):
    return sum(values)


def bridge(data):
    normalized = data.strip()
    return normalized.lower()


DEBUG = True
TIMEOUT = 30
LEGACY_FLAG = "remove-me"
RETRY_DELAY = 5
