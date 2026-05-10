class Config:
    """Data processing and transformation configuration settings."""
    def __init__(self, debug: bool = False, verbose: bool = True):
        self.debug = debug
        self.verbose = verbose


class Customer:
    def profile(self, name):
        return f"Customer:{name}"
