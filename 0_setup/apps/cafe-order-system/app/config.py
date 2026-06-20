import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/cafe_orders.db")
APP_NAME = "Cafe Order System"
APP_VERSION = "1.3.0"
MAX_ITEMS_PER_ORDER = 20
ORDER_TIMEOUT_MINUTES = 30
