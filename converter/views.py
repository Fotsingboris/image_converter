from django.shortcuts import render, HttpResponse
from django.core.files.base import ContentFile
from django.core.files import File
from PIL import Image
from rembg import remove
import subprocess
import io
import os
from .models import ProcessedImage

def home(request):
    processed_images = ProcessedImage.objects.all().order_by('-created_at')
    return render(request, 'converter/home.html', {'processed_images': processed_images})

def process_image(request, process_type):
    if request.method == 'POST' and request.FILES.get('image'):
        uploaded_file = request.FILES['image']
        img = Image.open(uploaded_file).convert('RGBA')

        # Save original image
        processed_img = ProcessedImage(original_file=uploaded_file, process_type=process_type)
        processed_img.save()

        if process_type == 'svg':
            # Remove background
            img_no_bg = remove(img)

            # Convert PNG to PPM (Potrace only supports PBM, PGM, PPM, BMP)
            temp_png = 'temp.png'
            temp_ppm = 'temp.ppm'
            temp_svg = 'temp.svg'

            img_no_bg.save(temp_png, format='PNG')  # Save intermediate PNG
            img_no_bg.convert('L').save(temp_ppm, format='PPM')  # Convert PNG to PPM

            # Use potrace to convert PPM to SVG
            subprocess.run(['potrace', temp_ppm, '-s', '-o', temp_svg], check=True)

            # Save SVG to model
            with open(temp_svg, 'rb') as svg_file:
                processed_img.processed_file.save(f"{uploaded_file.name}.svg", File(svg_file))
            processed_img.save()

            # Clean up temporary files
            os.remove(temp_png)
            os.remove(temp_ppm)
            os.remove(temp_svg)

        elif process_type == 'bg_remove':
            # Remove background
            img_no_bg = remove(img)
            output_io = io.BytesIO()
            img_no_bg.save(output_io, format='PNG')
            processed_img.processed_file.save(f"{uploaded_file.name}_no_bg.png", ContentFile(output_io.getvalue()))
            processed_img.save()

        return render(request, 'converter/preview.html', {'processed_img': processed_img})

    return render(request, 'converter/home.html')


def download_file(request, pk):
    processed_img = ProcessedImage.objects.get(pk=pk)
    file_path = processed_img.processed_file.path
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        return response