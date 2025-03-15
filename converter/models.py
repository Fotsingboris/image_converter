from django.db import models

class ProcessedImage(models.Model):
    original_file = models.ImageField(upload_to='originals/')
    processed_file = models.FileField(upload_to='processed/', null=True, blank=True)
    process_type = models.CharField(max_length=20, choices=[('svg', 'SVG'), ('bg_remove', 'Background Removed')])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.process_type} - {self.created_at}"