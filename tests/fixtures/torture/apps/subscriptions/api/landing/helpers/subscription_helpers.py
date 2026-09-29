"""Landing helpers (helpers nested under api/<feature>/helpers/) — class fronting the repo."""
from apps.subscriptions.repository import ProductRepository


class SubscriptionHelper:
    @staticmethod
    def landing_data():
        return {"catalog": ProductRepository.catalog()}      # -> products:read + cache
