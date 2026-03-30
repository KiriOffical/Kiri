"""
Tests for File Bot - Extension-based classification rules.
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.servants.file_bot import FileBot, Category, ClassificationResult


class TestFileBotInitialization:
    """Test File Bot initialization."""
    
    def test_init_default(self):
        """Test default initialization."""
        bot = FileBot()
        assert bot.extension_rules is not None
        assert bot.content_signatures is not None
        assert bot.keyword_patterns is not None
    
    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = {
            'custom_extensions': {
                'DOCUMENTS': ['.custom', '.myext']
            }
        }
        bot = FileBot(config=config)
        assert '.custom' in bot.extension_to_category
        assert '.myext' in bot.extension_to_category


class TestExtensionClassification:
    """Test extension-based file classification."""
    
    @pytest.fixture
    def bot(self):
        return FileBot()
    
    @pytest.mark.parametrize("extension,expected_category", [
        ('.pdf', Category.DOCUMENTS),
        ('.docx', Category.DOCUMENTS),
        ('.txt', Category.DOCUMENTS),
        ('.jpg', Category.IMAGES),
        ('.png', Category.IMAGES),
        ('.mp3', Category.AUDIO),
        ('.wav', Category.AUDIO),
        ('.mp4', Category.VIDEO),
        ('.avi', Category.VIDEO),
        ('.py', Category.CODE),
        ('.js', Category.CODE),
        ('.zip', Category.ARCHIVES),
        ('.gz', Category.ARCHIVES),  # .tar.gz becomes .gz
        ('.exe', Category.EXECUTABLES),
        ('.dll', Category.EXECUTABLES),
        ('.ttf', Category.FONTS),
        ('.otf', Category.FONTS),
        ('.html', Category.CODE),  # HTML is in CODE category
        ('.css', Category.CODE),  # CSS is in CODE category
        ('.dwg', Category.CAD),
        ('.stl', Category.CAD),
        ('.iso', Category.DISK),
        ('.db', Category.DATA),
        ('.sqlite', Category.DATA),
    ])
    def test_classify_by_extension(self, bot, extension, expected_category):
        """Test classification by file extension."""
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as f:
            temp_path = f.name
        
        try:
            result = bot.classify_file(temp_path)
            assert result.category == expected_category
            assert result.confidence == 0.9
            assert result.rule_matched.startswith("extension:")
            assert result.extension == extension
        finally:
            os.unlink(temp_path)
    
    def test_classify_unknown_extension(self, bot):
        """Test classification of unknown extension."""
        with tempfile.NamedTemporaryFile(suffix='.xyz123', delete=False) as f:
            f.write(b'Test content')
            temp_path = f.name
        
        try:
            result = bot.classify_file(temp_path)
            # Should fall back to content analysis or UNKNOWN
            assert result.confidence < 0.9  # Not high confidence
        finally:
            os.unlink(temp_path)
    
    def test_classify_nonexistent_file(self, bot):
        """Test classification of non-existent file."""
        result = bot.classify_file('/nonexistent/path/file.txt')
        assert result.category == Category.UNKNOWN
        assert result.confidence == 0.0
        assert result.rule_matched == "file_not_found"


class TestContentSignatureClassification:
    """Test content signature-based classification."""
    
    @pytest.fixture
    def bot(self):
        return FileBot()
    
    def test_classify_pdf_by_signature(self, bot):
        """Test PDF classification by magic bytes."""
        with tempfile.NamedTemporaryFile(suffix='', delete=False) as f:
            f.write(b'%PDF-1.4\nTest PDF content')
            temp_path = f.name
        
        try:
            result = bot.classify_file(temp_path)
            assert result.category == Category.DOCUMENTS
            assert result.confidence >= 0.5
        finally:
            os.unlink(temp_path)
    
    def test_classify_png_by_signature(self, bot):
        """Test PNG classification by magic bytes."""
        with tempfile.NamedTemporaryFile(suffix='', delete=False) as f:
            # PNG magic bytes
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR')
            temp_path = f.name
        
        try:
            result = bot.classify_file(temp_path)
            assert result.category == Category.IMAGES
            assert result.confidence >= 0.5
        finally:
            os.unlink(temp_path)
    
    def test_classify_zip_by_signature(self, bot):
        """Test ZIP classification by magic bytes."""
        with tempfile.NamedTemporaryFile(suffix='', delete=False) as f:
            # ZIP magic bytes (PK)
            f.write(b'PK\x03\x04\x14\x00\x00\x00')
            temp_path = f.name
        
        try:
            result = bot.classify_file(temp_path)
            assert result.category == Category.ARCHIVES
            assert result.confidence >= 0.5
        finally:
            os.unlink(temp_path)
    
    def test_classify_elf_by_signature(self, bot):
        """Test ELF executable classification by magic bytes."""
        with tempfile.NamedTemporaryFile(suffix='', delete=False) as f:
            # ELF magic bytes
            f.write(b'\x7fELF\x02\x01\x01\x00')
            temp_path = f.name
        
        try:
            result = bot.classify_file(temp_path)
            assert result.category == Category.EXECUTABLES
            assert result.confidence >= 0.5
        finally:
            os.unlink(temp_path)


class TestKeywordPatternClassification:
    """Test keyword pattern-based classification."""
    
    @pytest.fixture
    def bot(self):
        return FileBot()
    
    def test_classify_python_by_keywords(self, bot):
        """Test Python file classification by keywords."""
        # Use unknown extension so keyword matching is triggered
        with tempfile.NamedTemporaryFile(suffix='.unknown_ext', mode='w', delete=False) as f:
            f.write('def hello():\n    print("Hello")\n\nclass MyClass:\n    pass')
            temp_path = f.name
        
        try:
            result = bot.classify_file(temp_path)
            assert result.category == Category.CODE
            assert result.confidence >= 0.5
        finally:
            os.unlink(temp_path)
    
    def test_classify_html_by_keywords(self, bot):
        """Test HTML file classification by keywords."""
        # Use unknown extension so keyword matching is triggered
        with tempfile.NamedTemporaryFile(suffix='.unknown_ext', mode='w', delete=False) as f:
            f.write('<html>\n<head>\n<title>Test</title>\n</head>\n<body>\n</body>\n</html>')
            temp_path = f.name
        
        try:
            result = bot.classify_file(temp_path)
            assert result.category == Category.WEB
            assert result.confidence >= 0.5
        finally:
            os.unlink(temp_path)


class TestCategoryHelpers:
    """Test category helper methods."""
    
    @pytest.fixture
    def bot(self):
        return FileBot()
    
    def test_get_category_folder(self, bot):
        """Test getting folder name for category."""
        assert bot.get_category_folder(Category.DOCUMENTS) == "Documents"
        assert bot.get_category_folder(Category.IMAGES) == "Images"
        assert bot.get_category_folder(Category.CODE) == "Code"
    
    def test_get_all_categories(self, bot):
        """Test getting all categories."""
        categories = bot.get_all_categories()
        assert len(categories) > 0
        assert Category.DOCUMENTS in categories
        assert Category.IMAGES in categories
        assert Category.CODE in categories
    
    def test_get_extensions_for_category(self, bot):
        """Test getting extensions for a category."""
        doc_extensions = bot.get_extensions_for_category(Category.DOCUMENTS)
        assert '.pdf' in doc_extensions
        assert '.docx' in doc_extensions
        assert '.txt' in doc_extensions
        
        image_extensions = bot.get_extensions_for_category(Category.IMAGES)
        assert '.jpg' in image_extensions
        assert '.png' in image_extensions


class TestClassificationResult:
    """Test ClassificationResult dataclass."""
    
    def test_result_str(self):
        """Test string representation of result."""
        result = ClassificationResult(
            category=Category.DOCUMENTS,
            confidence=0.9,
            rule_matched="extension:.pdf",
            extension=".pdf"
        )
        str_repr = str(result)
        assert "Documents" in str_repr
        assert "0.90" in str_repr
        assert "extension:.pdf" in str_repr


class TestConfidenceScoring:
    """Test confidence scoring logic."""
    
    @pytest.fixture
    def bot(self):
        return FileBot()
    
    def test_extension_high_confidence(self, bot):
        """Test that extension matches have high confidence."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            temp_path = f.name
        
        try:
            result = bot.classify_file(temp_path)
            assert result.confidence == 0.9
        finally:
            os.unlink(temp_path)
    
    def test_signature_medium_confidence(self, bot):
        """Test that signature matches have medium confidence."""
        with tempfile.NamedTemporaryFile(suffix='', delete=False) as f:
            f.write(b'%PDF-1.4 content')
            temp_path = f.name
        
        try:
            result = bot.classify_file(temp_path)
            # Signature match should be less than extension but > 0
            assert 0.0 < result.confidence < 0.9
        finally:
            os.unlink(temp_path)
    
    def test_keyword_lower_confidence(self, bot):
        """Test that keyword matches have lower confidence."""
        with tempfile.NamedTemporaryFile(suffix='.unknown', mode='w', delete=False) as f:
            f.write('def test_function():\n    pass')
            temp_path = f.name
        
        try:
            result = bot.classify_file(temp_path)
            # Keyword match should have moderate confidence
            if result.category == Category.CODE:
                assert result.confidence <= 0.7
        finally:
            os.unlink(temp_path)


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def bot(self):
        return FileBot()
    
    def test_empty_file(self, bot):
        """Test classification of empty file."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            result = bot.classify_file(temp_path)
            # Empty file with known extension should still classify
            assert result.category == Category.DOCUMENTS
        finally:
            os.unlink(temp_path)
    
    def test_file_with_spaces_in_name(self, bot):
        """Test classification of file with spaces in name."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False, prefix='test file ') as f:
            temp_path = f.name
        
        try:
            result = bot.classify_file(temp_path)
            assert result.category == Category.DOCUMENTS
        finally:
            os.unlink(temp_path)
    
    def test_unicode_filename(self, bot):
        """Test classification of file with unicode in name."""
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, 'тест.pdf')
        
        try:
            with open(temp_path, 'w') as f:
                f.write('test')
            result = bot.classify_file(temp_path)
            assert result.category == Category.DOCUMENTS
        finally:
            os.unlink(temp_path)
            os.rmdir(temp_dir)
    
    def test_case_insensitive_extension(self, bot):
        """Test that extension matching is case insensitive."""
        with tempfile.NamedTemporaryFile(suffix='.PDF', delete=False) as f:
            temp_path = f.name
        
        try:
            result = bot.classify_file(temp_path)
            assert result.category == Category.DOCUMENTS
            assert result.extension == '.pdf'  # Normalized to lowercase
        finally:
            os.unlink(temp_path)
