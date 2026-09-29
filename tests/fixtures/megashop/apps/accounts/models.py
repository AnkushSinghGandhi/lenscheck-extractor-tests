"""accounts models — Account carries PII."""
from django.db import models


class Account(models.Model):
    email = models.EmailField()          # PII
    phone = models.CharField(max_length=20)   # PII
    name = models.CharField(max_length=120)

    class Meta:
        db_table = "accounts"


class Profile(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    bio = models.TextField()

    class Meta:
        db_table = "profiles"


class Article(models.Model):
    title = models.CharField(max_length=200)

    class Meta:
        db_table = "articles"
