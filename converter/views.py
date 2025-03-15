from django.shortcuts import render, redirect, HttpResponse
from django.core.files.base import ContentFile
from django.core.files import File
from PIL import Image
from rembg import remove
import subprocess
import io
import os
import logging
from .models import ProcessedImage
from django.contrib import messages

logger = logging.getLogger(__name__)

def home(request):
    processed_images = ProcessedImage.objects.all().order_by('-created_at')
    return render(request, 'converter/home.html', {'processed_images': processed_images})


# def process_image(request, process_type):
#     if request.method == 'POST' and request.FILES.get('image'):
#         uploaded_file = request.FILES['image']
#         img = Image.open(uploaded_file).convert('RGBA')  # Ensure the image is in RGBA to maintain colors

#         # Save original image
#         processed_img = ProcessedImage(original_file=uploaded_file, process_type=process_type)
#         processed_img.save()

#         if process_type == 'svg':
#             # Remove background
#             img_no_bg = remove(img)

#             # Save intermediate PNG to a BytesIO object (in memory)
#             output_io = io.BytesIO()
#             img_no_bg.save(output_io, format='PNG')
#             png_data = output_io.getvalue()  # Get binary data of the PNG

#             # Write PNG to a temporary file for Autotrace conversion
#             temp_png = 'temp.png'
#             with open(temp_png, 'wb') as temp_file:
#                 temp_file.write(png_data)

#             # Use autotrace to convert PNG to SVG
#             temp_svg = 'temp.svg'
#             try:
#                 subprocess.run(['autotrace', '-output-format', 'svg', '-output-file', temp_svg, temp_png], check=True)
#             except subprocess.CalledProcessError as e:
#                 messages.error(request, f'Error converting image to SVG: {e}')
#                 return redirect('home')

#             # Check if the SVG file exists before trying to use it
#             if os.path.exists(temp_svg):
#                 with open(temp_svg, 'rb') as svg_file:
#                     processed_img.processed_file.save(f"{uploaded_file.name}.svg", ContentFile(svg_file.read()))
#                 processed_img.save()

#                 # Clean up temporary files
#                 os.remove(temp_png)
#                 os.remove(temp_svg)
#             else:
#                 messages.error(request, 'Error: SVG file was not generated.')
#                 logger.error('Error: SVG file was not generated.')


#         elif process_type == 'bg_remove':
#             # Remove background
#             img_no_bg = remove(img)
#             output_io = io.BytesIO()
#             img_no_bg.save(output_io, format='PNG')
#             processed_img.processed_file.save(f"{uploaded_file.name}_no_bg.png", ContentFile(output_io.getvalue()))
#             processed_img.save()

#         return render(request, 'converter/preview.html', {'processed_img': processed_img})

#     return render(request, 'converter/home.html')



def download_file(request, pk):
    processed_img = ProcessedImage.objects.get(pk=pk)
    file_path = processed_img.processed_file.path
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        return response
    
    

def process_image(request, process_type):
    if request.method == 'POST' and request.FILES.get('image'):
        uploaded_file = request.FILES['image']
        
        # Open the image and convert to RGBA for color preservation
        img = Image.open(uploaded_file).convert('RGBA')

        # Save the original image to the ProcessedImage model
        processed_img = ProcessedImage(original_file=uploaded_file, process_type=process_type)
        processed_img.save()

        if process_type == 'svg':
            # Remove background (assuming 'remove' is from rembg or similar)
            try:
                from rembg import remove  # Import here or at the top if needed
                img_no_bg = remove(img)
            except Exception as e:
                messages.error(request, f'Error removing background: {e}')
                return redirect('home')

            # Save intermediate PNG to a file
            temp_png = 'temp.png'
            try:
                img_no_bg.save(temp_png, format='PNG')
            except Exception as e:
                messages.error(request, f'Error saving intermediate PNG: {e}')
                return redirect('home')

            # Use Inkscape to convert PNG to SVG with color preservation
            temp_svg = 'temp.svg'
            try:
                subprocess.run([
                    'inkscape',
                    temp_png,                          # Input PNG file
                    '--export-type=svg',               # Export as SVG
                    '--export-filename', temp_svg,     # Output SVG file
                    '--actions', 'EditSelectAll;TraceBitmap:colors=8'  # Trace with 8 colors (adjust as needed)
                ], check=True)
            except subprocess.CalledProcessError as e:
                messages.error(request, f'Error converting image to SVG with Inkscape: {e}')
                if os.path.exists(temp_png):
                    os.remove(temp_png)
                return redirect('home')

            # Check if the SVG file was generated and save it
            if os.path.exists(temp_svg):
                try:
                    with open(temp_svg, 'rb') as svg_file:
                        processed_img.processed_file.save(
                            f"{uploaded_file.name}.svg", 
                            ContentFile(svg_file.read())
                        )
                    processed_img.save()
                except Exception as e:
                    messages.error(request, f'Error saving SVG to model: {e}')
            else:
                messages.error(request, 'Error: SVG file was not generated.')
                logger.error('Error: SVG file was not generated.')

            # Clean up temporary files
            if os.path.exists(temp_png):
                os.remove(temp_png)
            if os.path.exists(temp_svg):
                os.remove(temp_svg)

        elif process_type == 'bg_remove':
            # Remove background
            try:
                from rembg import remove  # Import here or at the top if needed
                img_no_bg = remove(img)
            except Exception as e:
                messages.error(request, f'Error removing background: {e}')
                return redirect('home')

            # Save the processed image as PNG
            output_io = io.BytesIO()
            img_no_bg.save(output_io, format='PNG')
            try:
                processed_img.processed_file.save(
                    f"{uploaded_file.name}_no_bg.png", 
                    ContentFile(output_io.getvalue())
                )
                processed_img.save()
            except Exception as e:
                messages.error(request, f'Error saving background-removed image: {e}')
                return redirect('home')

        # Render the preview page with the processed image
        return render(request, 'converter/preview.html', {'processed_img': processed_img})

    # If not POST or no image, render the home page
    return render(request, 'converter/home.html')