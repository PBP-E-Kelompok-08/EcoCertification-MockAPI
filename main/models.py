from django.db import models
import uuid

# Create your models here.
class Certification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_name = models.CharField(max_length=255)
    certification = models.BooleanField()
    eco_rating = models.FloatField()
    expire_at = models.DateTimeField()

