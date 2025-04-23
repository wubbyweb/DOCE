import pytest
import os
from unittest.mock import patch, MagicMock
import tempfile

from doce.plugins.google_vision_plugin import GoogleVisionPlugin


@pytest.fixture
def sample_pdf_file():
    # Create a temporary PDF file for testing
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(b'%PDF-1.5\nSample PDF content for testing')
        temp_path = f.name
    
    yield temp_path
    
    # Clean up the temporary file
    os.unlink(temp_path)


@pytest.fixture
def sample_image_file():
    # Create a temporary image file for testing
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        f.write(b'Sample image content for testing')
        temp_path = f.name
    
    yield temp_path
    
    # Clean up the temporary file
    os.unlink(temp_path)


@pytest.fixture
def mock_vision_client():
    with patch('google.cloud.vision.ImageAnnotatorClient') as mock:
        # Create a mock client
        mock_client = MagicMock()
        mock.return_value = mock_client
        
        # Create a mock response
        mock_response = MagicMock()
        mock_text_annotation = MagicMock()
        mock_text_annotation.description = "Sample OCR text from Google Vision API"
        mock_response.text_annotations = [mock_text_annotation]
        
        # Set up the mock client to return the mock response
        mock_client.text_detection.return_value = mock_response
        
        yield mock_client


def test_init_with_credentials_path():
    # Test initialization with credentials path
    plugin = GoogleVisionPlugin(credentials_path="/path/to/credentials.json")
    assert plugin.credentials_path == "/path/to/credentials.json"


def test_init_without_credentials_path():
    # Test initialization without credentials path
    with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": "/env/path/credentials.json"}):
        plugin = GoogleVisionPlugin()
        assert plugin.credentials_path is None


@patch('google.cloud.vision.ImageAnnotatorClient')
def test_extract_text_from_pdf(mock_client_class, sample_pdf_file, mock_vision_client):
    # Set up the mock client
    mock_client_class.return_value = mock_vision_client
    
    # Create the plugin
    plugin = GoogleVisionPlugin()
    
    # Extract text from the PDF
    text = plugin.extract_text(sample_pdf_file)
    
    # Verify the result
    assert text == "Sample OCR text from Google Vision API"
    
    # Verify that the client was called correctly
    mock_vision_client.text_detection.assert_called()


@patch('google.cloud.vision.ImageAnnotatorClient')
def test_extract_text_from_image(mock_client_class, sample_image_file, mock_vision_client):
    # Set up the mock client
    mock_client_class.return_value = mock_vision_client
    
    # Create the plugin
    plugin = GoogleVisionPlugin()
    
    # Extract text from the image
    text = plugin.extract_text(sample_image_file)
    
    # Verify the result
    assert text == "Sample OCR text from Google Vision API"
    
    # Verify that the client was called correctly
    mock_vision_client.text_detection.assert_called()


@patch('google.cloud.vision.ImageAnnotatorClient')
def test_extract_text_with_empty_response(mock_client_class, sample_image_file):
    # Create a mock client with an empty response
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text_annotations = []
    mock_client.text_detection.return_value = mock_response
    mock_client_class.return_value = mock_client
    
    # Create the plugin
    plugin = GoogleVisionPlugin()
    
    # Extract text from the image
    text = plugin.extract_text(sample_image_file)
    
    # Verify the result
    assert text == ""


@patch('google.cloud.vision.ImageAnnotatorClient')
def test_extract_text_with_exception(mock_client_class, sample_image_file):
    # Create a mock client that raises an exception
    mock_client = MagicMock()
    mock_client.text_detection.side_effect = Exception("Test exception")
    mock_client_class.return_value = mock_client
    
    # Create the plugin
    plugin = GoogleVisionPlugin()
    
    # Extract text from the image
    text = plugin.extract_text(sample_image_file)
    
    # Verify the result
    assert "Error extracting text" in text
    assert "Test exception" in text


def test_extract_text_file_not_found():
    # Create the plugin
    plugin = GoogleVisionPlugin()
    
    # Extract text from a non-existent file
    text = plugin.extract_text("/path/to/nonexistent/file.pdf")
    
    # Verify the result
    assert "File not found" in text


@patch('google.cloud.vision.ImageAnnotatorClient')
@patch('pdf2image.convert_from_path')
def test_extract_text_from_multipage_pdf(mock_convert, mock_client_class, sample_pdf_file, mock_vision_client):
    # Set up the mock client
    mock_client_class.return_value = mock_vision_client
    
    # Set up the mock pdf2image converter
    mock_page1 = MagicMock()
    mock_page2 = MagicMock()
    mock_convert.return_value = [mock_page1, mock_page2]
    
    # Create the plugin
    plugin = GoogleVisionPlugin()
    
    # Extract text from the PDF
    text = plugin.extract_text(sample_pdf_file)
    
    # Verify the result
    assert text == "Sample OCR text from Google Vision API\nSample OCR text from Google Vision API"
    
    # Verify that the client was called twice (once for each page)
    assert mock_vision_client.text_detection.call_count == 2


@patch('google.cloud.vision.ImageAnnotatorClient')
def test_extract_text_with_credentials(mock_client_class, sample_image_file, mock_vision_client):
    # Set up the mock client
    mock_client_class.return_value = mock_vision_client
    
    # Create the plugin with credentials path
    plugin = GoogleVisionPlugin(credentials_path="/path/to/credentials.json")
    
    # Extract text from the image
    text = plugin.extract_text(sample_image_file)
    
    # Verify the result
    assert text == "Sample OCR text from Google Vision API"
    
    # Verify that the client was created with the credentials
    mock_client_class.assert_called_once()