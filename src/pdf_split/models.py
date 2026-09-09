from dataclasses import dataclass


@dataclass(frozen=True)
class SplitInterval:
    start_page: int
    end_page_exclusive: int

    def __post_init__(self) -> None:
        if self.start_page < 0:
            raise ValueError("start_page must be >= 0")
        if self.end_page_exclusive <= self.start_page:
            raise ValueError("end_page_exclusive must be greater than start_page")

    def to_user_range(self) -> str:
        return f"pages {self.start_page + 1}-{self.end_page_exclusive}"
