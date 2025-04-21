from django.db import models
from django.contrib.auth.models import User

class Order(models.Model):
    username = models.CharField(max_length=150)
    email = models.EmailField()
    patient_id = models.CharField(max_length=150)
    
    def __str__(self):
        return f"{self.username}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    patient_id = models.CharField(max_length=100)

    def __str__(self):
        return self.user.username
# Create your models here.
class Chat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username}: {self.message}'
class PatientChat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)