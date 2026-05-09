class Customer:
    def stable(self) -> str:
        return "stable"

    def label(self) -> str:
        return "label"

    def normalize(self, value: str) -> str:
        return value.strip().lower()
