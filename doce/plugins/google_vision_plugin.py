import os
from typing import List, Optional
import io
from google.cloud import vision
from semantic_kernel.plugin_definition import kernel_function, KernelPlugin

class GoogleVisionPlugin(KernelPlugin):
    """
    Plugin for Google Cloud Vision API to perform OCR on images and PDFs.
    """
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize the Google Vision plugin.
        
        Args:
            credentials_path: Path to the Google Cloud credentials JSON file.
                             If None, it will use the GOOGLE_APPLICATION_CREDENTIALS environment variable.
        """
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        
        self.client = vision.ImageAnnotatorClient()
    
    @kernel_function(
        description="Performs OCR on an image file and returns the extracted text",
        name="extract_text_from_image"
    )
    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from an image file using Google Cloud Vision OCR.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            Extracted text from the image.
        """
        # Read the image file
        with io.open(image_path, "rb") as image_file:
            content = image_file.read()
        
        # Create an image object
        image = vision.Image(content=content)
        
        # Perform text detection
        response = self.client.text_detection(image=image)
        
        # Extract the text
        if response.error.message:
            raise Exception(f"Error: {response.error.message}")
        
        if not response.text_annotations:
            return ""
        
        # The first annotation contains the entire text
        return response.text_annotations[0].description
    
    @kernel_function(
        description="Performs OCR on a PDF file and returns the extracted text",
        name="extract_text_from_pdf"
    )
    def extract_text_from_pdf(self, pdf_path: str, pages: Optional[List[int]] = None) -> str:
        """
        Extract text from a PDF file using Google Cloud Vision OCR.
        
        Args:
            pdf_path: Path to the PDF file.
            pages: List of page numbers to process (0-based). If None, process all pages.
            
        Returns:
            Extracted text from the PDF.
        """
        from pdf2image import convert_from_path
        
        # Convert PDF to images
        images = convert_from_path(pdf_path)
        
        # Process specified pages or all pages
        if pages:
            images = [images[i] for i in pages if i < len(images)]
        
        all_text = []
        
        # Process each page
        for i, image in enumerate(images):
            # Save the image temporarily
            temp_image_path = f"{pdf_path}_page_{i}.jpg"
            image.save(temp_image_path, "JPEG")
            
            try:
                # Extract text from the image
                page_text = self.extract_text_from_image(temp_image_path)
                all_text.append(f"--- Page {i+1} ---\n{page_text}")
            finally:
                # Clean up temporary file
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
        
        return "\n\n".join(all_text)
    
    @kernel_function(
        description="Detects the file type and performs OCR accordingly",
        name="extract_text"
    )
    def extract_text(self, file_path: str) -> str:
        """
        Extract text from a file, automatically detecting if it's an image or PDF.
        
        Args:
            file_path: Path to the file.
            
        Returns:
            Extracted text from the file.
        """
        # Check file extension
        _, ext = os.path.splitext(file_path.lower())
        
        if ext in [".pdf"]:
            return self.extract_text_from_pdf(file_path)
        elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif"]:
            return self.extract_text_from_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")