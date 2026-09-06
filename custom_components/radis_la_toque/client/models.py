"""Immutable data models used by the client and Home Assistant."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

class MenuCategory(StrEnum):
    STARTER = "starter"
    MAIN_COURSE = "main_course"
    SIDE = "side"
    DAIRY = "dairy"
    DESSERT = "dessert"
    OTHER = "other"

@dataclass(frozen=True, slots=True)
class Restaurant:
    code: str | None
    name: str
    address: str | None
    city: str
    postal_code: str
    page_url: str

    @property
    def label(self) -> str:
        location = " ".join(p for p in (self.postal_code, self.city) if p)
        return f"{self.name} — {location}" if location else self.name

@dataclass(frozen=True, slots=True)
class MenuItem:
    name: str
    category: MenuCategory = MenuCategory.OTHER
    labels: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class DayMenu:
    menu_date: date
    label: str
    items: tuple[MenuItem, ...]

    def items_by_category(self, category: MenuCategory) -> tuple[str, ...]:
        return tuple(i.name for i in self.items if i.category == category)

@dataclass(frozen=True, slots=True)
class WeeklyMenu:
    restaurant_code: str
    restaurant_name: str
    source_url: str
    days: tuple[DayMenu, ...]
    document_etag: str | None = None
    document_last_modified: str | None = None
    parser_kind: str | None = None
    parser_score: int | None = None

    def menu_for_date(self, target: date) -> DayMenu | None:
        return next((day for day in self.days if day.menu_date == target), None)

    def next_menu_after(self, target: date) -> DayMenu | None:
        future = (d for d in self.days if d.menu_date > target)
        return min(future, key=lambda d: d.menu_date, default=None)
