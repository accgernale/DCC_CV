"""Tests for the extractor module."""

import pytest
from datetime import date
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from dcc_cv.extractor import DocumentExtractor
from dcc_cv.models import MeasurementUnit, get_unit


class TestDocumentExtractor:
    """Tests for DocumentExtractor class."""
    
    @pytest.fixture
    def extractor(self):
        """Create an extractor instance."""
        return DocumentExtractor()
    
    def test_extractor_initialization(self, extractor):
        """Test extractor initializes with default language."""
        assert extractor.ocr_language == "eng+deu"
        
    def test_custom_language(self):
        """Test extractor with custom OCR language."""
        extractor = DocumentExtractor(ocr_language="eng")
        assert extractor.ocr_language == "eng"


class TestPatternExtraction:
    """Tests for pattern-based text extraction."""
    
    @pytest.fixture
    def extractor(self):
        """Create an extractor instance."""
        return DocumentExtractor()
    
    def test_extract_certificate_number(self, extractor):
        """Test certificate number extraction."""
        text = "Certificate No.: CAL-2024-001\nOther text"
        result = extractor.extract_pattern(text, "certificate_number")
        assert result == "CAL-2024-001"
        
    def test_extract_certificate_number_german(self, extractor):
        """Test German certificate number extraction."""
        text = "Kalibrierzertifikat Nr. DE-K-12345\nWeiterer Text"
        result = extractor.extract_pattern(text, "certificate_number")
        assert result == "DE-K-12345"
        
    def test_extract_calibration_date(self, extractor):
        """Test calibration date extraction."""
        text = "Calibration Date: 15.01.2024\nMore text"
        result = extractor.extract_pattern(text, "calibration_date")
        assert result == "15.01.2024"
        
    def test_extract_serial_number(self, extractor):
        """Test serial number extraction."""
        text = "Serial Number: SN-12345-XYZ\nDetails"
        result = extractor.extract_pattern(text, "serial_number")
        assert result == "SN-12345-XYZ"
        
    def test_extract_manufacturer(self, extractor):
        """Test manufacturer extraction."""
        text = "Manufacturer: Acme Corp\nModel: ABC"
        result = extractor.extract_pattern(text, "manufacturer")
        assert "Acme" in result
        
    def test_extract_temperature(self, extractor):
        """Test temperature extraction."""
        text = "Temperature: 23.5 °C\nHumidity: 45%"
        result = extractor.extract_pattern(text, "temperature")
        assert result == "23.5"
        
    def test_extract_humidity(self, extractor):
        """Test humidity extraction."""
        text = "Relative Humidity: 45.2 %\nPressure: 1013 hPa"
        result = extractor.extract_pattern(text, "humidity")
        assert result == "45.2"
        
    def test_pattern_not_found(self, extractor):
        """Test behavior when pattern not found."""
        text = "Some random text without patterns"
        result = extractor.extract_pattern(text, "certificate_number")
        assert result is None


class TestDateParsing:
    """Tests for date parsing functionality."""
    
    @pytest.fixture
    def extractor(self):
        """Create an extractor instance."""
        return DocumentExtractor()
    
    def test_parse_date_dot_format(self, extractor):
        """Test parsing date with dot separator."""
        result = extractor.parse_date("15.01.2024")
        assert result == date(2024, 1, 15)
        
    def test_parse_date_slash_format(self, extractor):
        """Test parsing date with slash separator."""
        result = extractor.parse_date("15/01/2024")
        assert result == date(2024, 1, 15)
        
    def test_parse_date_iso_format(self, extractor):
        """Test parsing ISO date format."""
        result = extractor.parse_date("2024-01-15")
        assert result == date(2024, 1, 15)
        
    def test_parse_invalid_date(self, extractor):
        """Test parsing invalid date returns None."""
        result = extractor.parse_date("not a date")
        assert result is None


class TestEnvironmentalConditionsExtraction:
    """Tests for environmental conditions extraction."""
    
    @pytest.fixture
    def extractor(self):
        """Create an extractor instance."""
        return DocumentExtractor()
    
    def test_extract_full_conditions(self, extractor):
        """Test extraction of all environmental conditions."""
        text = """
        Environmental Conditions:
        Temperature: 23.0 °C
        Humidity: 45 %
        Atmospheric Pressure: 1013 hPa
        """
        conditions = extractor.extract_environmental_conditions(text)
        assert conditions is not None
        assert conditions.temperature.value == 23.0
        assert conditions.humidity.value == 45.0
        
    def test_extract_partial_conditions(self, extractor):
        """Test extraction with only temperature."""
        text = "Temperature: 20.5 °C"
        conditions = extractor.extract_environmental_conditions(text)
        assert conditions is not None
        assert conditions.temperature.value == 20.5
        assert conditions.humidity is None
        
    def test_no_conditions_found(self, extractor):
        """Test when no conditions are found."""
        text = "Some text without environmental data"
        conditions = extractor.extract_environmental_conditions(text)
        assert conditions is None


class TestMeasurementExtraction:
    """Tests for measurement data extraction."""
    
    @pytest.fixture
    def extractor(self):
        """Create an extractor instance."""
        return DocumentExtractor()
    
    def test_extract_force_measurements(self, extractor):
        """Test extraction of force measurements."""
        text = """
        Force Reference: 100.00 kN
        Indication: 100.05 kN
        """
        results = extractor.extract_measurement_tables(text)
        # Should find at least one measurement with kN unit
        kn_results = [r for r in results if r.measured_value.unit.symbol == "kN"]
        assert len(kn_results) > 0
        
    def test_extract_temperature_measurements(self, extractor):
        """Test extraction of temperature measurements."""
        text = """
        Calibration point 1: 20.05 °C
        Calibration point 2: 50.02 °C
        """
        results = extractor.extract_measurement_tables(text)
        celsius_results = [r for r in results if r.measured_value.unit.symbol == "°C"]
        assert len(celsius_results) > 0


class TestFileValidation:
    """Tests for file validation."""
    
    @pytest.fixture
    def extractor(self):
        """Create an extractor instance."""
        return DocumentExtractor()
    
    def test_nonexistent_file_raises_error(self, extractor):
        """Test that nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            extractor.extract_from_file("/nonexistent/file.pdf")
            
    def test_unsupported_format_raises_error(self, extractor, tmp_path):
        """Test that unsupported file format raises ValueError."""
        # Create a file with unsupported extension
        test_file = tmp_path / "test.xyz"
        test_file.write_text("test content")
        
        with pytest.raises(ValueError, match="Unsupported file format"):
            extractor.extract_from_file(test_file)
