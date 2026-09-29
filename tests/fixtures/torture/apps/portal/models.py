"""portal models — User carries PII; a CartEntry has NO db_table (Django convention test)."""
from django.db import models


class User(models.Model):
    email = models.EmailField()          # PII
    phone = models.CharField(max_length=20)   # PII
    display_name = models.CharField(max_length=120)

    class Meta:
        db_table = "users"


class Profile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bio = models.TextField()

    class Meta:
        db_table = "user_profiles"


class Article(models.Model):
    title = models.CharField(max_length=200)
    domain = models.ForeignKey("Domain", on_delete=models.CASCADE)

    class Meta:
        db_table = "articles"


class Domain(models.Model):
    host = models.CharField(max_length=120)

    class Meta:
        db_table = "domains"


class CartEntry(models.Model):        # NO Meta.db_table → convention: portal_cartentry
    product_id = models.IntegerField()
    qty = models.IntegerField()
