"""
Unit tests for the ImageCaptioner class.
Run with: python -m pytest tests/test_captioner.py
"""

import os
import sys
import pytest
from PIL import Image
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.captioner import ImageCaptioner


@pytest.fixture
def captioner():
    """Fixture to create an ImageCaptioner instance."""
    return ImageCaptioner()


@pytest.fixture
def sample_image():
    """Fixture to create a sample test image."""
    # Create a temporary RGB image
    img = Image.new('RGB', (224, 224), color='red')
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    img.save(temp_file.name)
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    os.unlink(temp_file.name)


def test_captioner_initialization(captioner):
    """Test that the captioner initializes correctly."""
    assert captioner is not None
    assert captioner.model is not None
    assert captioner.feature_extractor is not None
    assert captioner.tokenizer is not None


def test_device_selection(captioner):
    """Test that device is selected appropriately."""
    assert captioner.device in ['cuda', 'cpu']


def test_generate_caption(captioner, sample_image):
    """Test caption generation on a sample image."""
    caption = captioner.generate_caption(sample_image)
    
    assert caption is not None
    assert isinstance(caption, str)
    assert len(caption) > 0


def test_generate_caption_with_params(captioner, sample_image):
    """Test caption generation with custom parameters."""
    caption = captioner.generate_caption(
        sample_image,
        max_length=20,
        num_beams=3
    )
    
    assert caption is not None
    assert isinstance(caption, str)


def test_invalid_image_path(captioner):
    """Test handling of invalid image path."""
    caption = captioner.generate_caption("nonexistent_image.jpg")
    assert caption is None


def test_batch_generate_captions(captioner, sample_image):
    """Test batch caption generation."""
    image_paths = [sample_image, sample_image]
    captions = captioner.batch_generate_captions(image_paths)
    
    assert len(captions) == 2
    assert all(isinstance(cap, str) for cap in captions)


def test_grayscale_image_conversion(captioner):
    """Test that grayscale images are converted to RGB."""
    # Create a grayscale image
    img = Image.new('L', (224, 224), color=128)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    img.save(temp_file.name)
    temp_file.close()
    
    try:
        caption = captioner.generate_caption(temp_file.name)
        assert caption is not None
        assert isinstance(caption, str)
    finally:
        os.unlink(temp_file.name)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
