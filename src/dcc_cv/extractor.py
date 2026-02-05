"""Document extraction module for reading PDF and image files.

This module handles the extraction of text and data from calibration
certificates in PDF or image format using OCR and PDF parsing.
"""

import logging
import re
from pathlib import Path
from typing import Optional, Union
from datetime import date, datetime

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from pdf2image import convert_from_path
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

import numpy as np

from .models import (
    CalibrationCertificate,
    Organization,
    Address,
    Contact,
    EquipmentInfo,
    MeasurementResult,
    MeasuredValue,
    MeasurementUnit,
    EnvironmentalConditions,
    get_unit,
)

logger = logging.getLogger(__name__)


class DocumentExtractor:
    """Extract text and data from PDF and image files."""
    
    # Common patterns for calibration certificate data
    PATTERNS = {
        "certificate_number": [
            r"[Cc]ertificate\s*(?:[Nn]o\.?|[Nn]umber)\s*[:.]?\s*([A-Z0-9\-/]+)",
            r"[Kk]alibrierzertifikat\s*(?:[Nn]r\.?)\s*[:.]?\s*([A-Z0-9\-/]+)",
            r"[Cc]ertificate\s*[Ii][Dd]\s*[:.]?\s*([A-Z0-9\-/]+)",
        ],
        "calibration_date": [
            r"[Cc]alibration\s*[Dd]ate\s*[:.]?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
            r"[Dd]ate\s+of\s+[Cc]alibration\s*[:.]?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
            r"[Kk]alibrierdatum\s*[:.]?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
        ],
        "certificate_date": [
            r"[Dd]ate\s+of\s+[Ii]ssue\s*[:.]?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
            r"[Ii]ssue\s*[Dd]ate\s*[:.]?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
            r"[Aa]usstellungsdatum\s*[:.]?\s*(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4})",
        ],
        "serial_number": [
            r"[Ss]erial\s*(?:[Nn]o\.?|[Nn]umber)\s*[:.]?\s*([A-Z0-9\-/]+)",
            r"[Ss]erien[Nn]ummer\s*[:.]?\s*([A-Z0-9\-/]+)",
            r"S/N\s*[:.]?\s*([A-Z0-9\-/]+)",
        ],
        "manufacturer": [
            r"[Mm]anufacturer\s*[:.]?\s*([A-Za-z0-9\s&]+?)(?:\n|$|,)",
            r"[Hh]ersteller\s*[:.]?\s*([A-Za-z0-9\s&]+?)(?:\n|$|,)",
            r"[Mm]ade\s+[Bb]y\s*[:.]?\s*([A-Za-z0-9\s&]+?)(?:\n|$|,)",
        ],
        "model": [
            r"[Mm]odel\s*[:.]?\s*([A-Za-z0-9\-/\s]+?)(?:\n|$|,)",
            r"[Tt]ype\s*[:.]?\s*([A-Za-z0-9\-/\s]+?)(?:\n|$|,)",
            r"[Mm]odell\s*[:.]?\s*([A-Za-z0-9\-/\s]+?)(?:\n|$|,)",
        ],
        "temperature": [
            r"[Tt]emperature\s*[:.]?\s*([\d.,]+)\s*°?C",
            r"[Tt]emp\.?\s*[:.]?\s*([\d.,]+)\s*°?C",
            r"([\d.,]+)\s*°C",
        ],
        "humidity": [
            r"[Hh]umidity\s*[:.]?\s*([\d.,]+)\s*%",
            r"[Rr]elative\s*[Hh]umidity\s*[:.]?\s*([\d.,]+)\s*%",
            r"[Ff]euchtigkeit\s*[:.]?\s*([\d.,]+)\s*%",
        ],
        "pressure": [
            r"[Pp]ressure\s*[:.]?\s*([\d.,]+)\s*(hPa|mbar|Pa|kPa)",
            r"[Aa]tmospheric\s*[Pp]ressure\s*[:.]?\s*([\d.,]+)\s*(hPa|mbar|Pa|kPa)",
            r"[Ll]uftdruck\s*[:.]?\s*([\d.,]+)\s*(hPa|mbar|Pa|kPa)",
        ],
    }
    
    # Common unit patterns for extraction
    UNIT_PATTERNS = [
        (r"([\d.,]+)\s*(kN)", "kN"),
        (r"([\d.,]+)\s*(MN)", "MN"),
        (r"([\d.,]+)\s*N(?![a-zA-Z])", "N"),
        (r"([\d.,]+)\s*°C", "°C"),
        (r"([\d.,]+)\s*K(?![a-zA-Z])", "K"),
        (r"([\d.,]+)\s*(MPa)", "MPa"),
        (r"([\d.,]+)\s*(kPa)", "kPa"),
        (r"([\d.,]+)\s*(Pa)(?![a-zA-Z])", "Pa"),
        (r"([\d.,]+)\s*(bar)", "bar"),
        (r"([\d.,]+)\s*(mbar)", "mbar"),
        (r"([\d.,]+)\s*(mm)", "mm"),
        (r"([\d.,]+)\s*(µm|um)", "µm"),
        (r"([\d.,]+)\s*m(?![a-zA-Z])", "m"),
        (r"([\d.,]+)\s*(kg)", "kg"),
        (r"([\d.,]+)\s*g(?![a-zA-Z])", "g"),
        (r"([\d.,]+)\s*(mg)", "mg"),
        (r"([\d.,]+)\s*(mV)", "mV"),
        (r"([\d.,]+)\s*V(?![a-zA-Z])", "V"),
        (r"([\d.,]+)\s*(mA)", "mA"),
        (r"([\d.,]+)\s*A(?![a-zA-Z])", "A"),
        (r"([\d.,]+)\s*%\s*(?:rh|RH)", "%rh"),
        (r"([\d.,]+)\s*%", "%"),
    ]
    
    def __init__(self, ocr_language: str = "eng+deu"):
        """Initialize the document extractor.
        
        Args:
            ocr_language: Tesseract language code(s) for OCR
        """
        self.ocr_language = ocr_language
        
    def extract_from_file(self, file_path: Union[str, Path]) -> str:
        """Extract text from a PDF or image file.
        
        Args:
            file_path: Path to the PDF or image file
            
        Returns:
            Extracted text content
            
        Raises:
            ValueError: If file format is not supported
            FileNotFoundError: If file does not exist
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        suffix = file_path.suffix.lower()
        
        if suffix == ".pdf":
            return self._extract_from_pdf(file_path)
        elif suffix in {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}:
            return self._extract_from_image(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
            
    def _extract_from_pdf(self, file_path: Path) -> str:
        """Extract text from a PDF file.
        
        Tries PyMuPDF first for text-based PDFs, falls back to OCR for scanned PDFs.
        """
        text = ""
        
        # Try PyMuPDF first for text extraction
        if HAS_PYMUPDF:
            try:
                doc = fitz.open(file_path)
                for page in doc:
                    text += page.get_text()
                doc.close()
                
                # If we got substantial text, return it
                if len(text.strip()) > 100:
                    logger.info("Extracted text using PyMuPDF")
                    return text
            except Exception as e:
                logger.warning(f"PyMuPDF extraction failed: {e}")
                
        # Fall back to OCR for scanned PDFs
        if HAS_OCR:
            logger.info("Falling back to OCR for PDF extraction")
            try:
                images = convert_from_path(file_path)
                text_parts = []
                for i, image in enumerate(images):
                    page_text = pytesseract.image_to_string(
                        image, 
                        lang=self.ocr_language
                    )
                    text_parts.append(page_text)
                text = "\n\n".join(text_parts)
                return text
            except Exception as e:
                logger.error(f"OCR extraction failed: {e}")
                raise
        else:
            raise ImportError(
                "Neither PyMuPDF nor pytesseract/pdf2image available for PDF extraction"
            )
            
    def _extract_from_image(self, file_path: Path) -> str:
        """Extract text from an image file using OCR."""
        if not HAS_OCR:
            raise ImportError("pytesseract not available for OCR")
            
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image, lang=self.ocr_language)
            return text
        except Exception as e:
            logger.error(f"Image OCR failed: {e}")
            raise
            
    def parse_date(self, date_str: str) -> Optional[date]:
        """Parse a date string in various formats.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            Parsed date or None if parsing fails
        """
        date_formats = [
            "%d.%m.%Y",
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%m/%d/%Y",
            "%d.%m.%y",
            "%d/%m/%y",
        ]
        
        for fmt in date_formats:
            try:
                parsed = datetime.strptime(date_str.strip(), fmt)
                return date(parsed.year, parsed.month, parsed.day)
            except ValueError:
                continue
        return None
        
    def extract_pattern(self, text: str, pattern_key: str) -> Optional[str]:
        """Extract a value using predefined patterns.
        
        Args:
            text: Text to search
            pattern_key: Key in PATTERNS dict
            
        Returns:
            First matched value or None
        """
        patterns = self.PATTERNS.get(pattern_key, [])
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        return None
        
    def extract_measurement_tables(self, text: str) -> list[MeasurementResult]:
        """Extract measurement results from tabular data in text.
        
        This method attempts to identify and parse measurement tables
        from the extracted text.
        
        Args:
            text: Raw text content
            
        Returns:
            List of MeasurementResult objects
        """
        results = []
        lines = text.split('\n')
        
        # Look for patterns that might indicate measurement data
        # Common patterns: reference value, measured value, deviation, uncertainty
        measurement_pattern = re.compile(
            r'^([^|:\t]+?)\s*[|:\t]\s*([\d.,]+)\s*([A-Za-z°%]+)?\s*[|:\t]?\s*([\d.,]*)\s*([A-Za-z°%]*)?\s*[|:\t]?\s*([\d.,]*)',
            re.MULTILINE
        )
        
        for match in measurement_pattern.finditer(text):
            try:
                name = match.group(1).strip()
                value_str = match.group(2).replace(',', '.')
                unit_str = match.group(3) or ""
                
                if not name or len(name) > 100:  # Skip invalid entries
                    continue
                    
                value = float(value_str)
                unit = get_unit(unit_str) if unit_str else MeasurementUnit(symbol="")
                
                measured_value = MeasuredValue(value=value, unit=unit)
                result = MeasurementResult(name=name, measured_value=measured_value)
                results.append(result)
            except (ValueError, IndexError):
                continue
                
        # Also try to find standalone value-unit pairs
        for pattern, unit_symbol in self.UNIT_PATTERNS:
            for match in re.finditer(pattern, text):
                try:
                    value_str = match.group(1).replace(',', '.')
                    value = float(value_str)
                    
                    # Check context to get a name
                    start = max(0, match.start() - 50)
                    context = text[start:match.start()].strip()
                    name = context.split('\n')[-1].strip() if context else f"Measurement ({unit_symbol})"
                    
                    if len(name) > 100:
                        name = f"Measurement ({unit_symbol})"
                        
                    unit = get_unit(unit_symbol)
                    measured_value = MeasuredValue(value=value, unit=unit)
                    result = MeasurementResult(name=name, measured_value=measured_value)
                    
                    # Avoid duplicates
                    if not any(r.name == name and r.measured_value.value == value for r in results):
                        results.append(result)
                except (ValueError, IndexError):
                    continue
                    
        return results
        
    def extract_environmental_conditions(self, text: str) -> Optional[EnvironmentalConditions]:
        """Extract environmental conditions from text.
        
        Args:
            text: Raw text content
            
        Returns:
            EnvironmentalConditions object or None
        """
        temp_str = self.extract_pattern(text, "temperature")
        humidity_str = self.extract_pattern(text, "humidity")
        
        conditions = EnvironmentalConditions()
        has_data = False
        
        if temp_str:
            try:
                temp_value = float(temp_str.replace(',', '.'))
                conditions.temperature = MeasuredValue(
                    value=temp_value,
                    unit=get_unit("°C")
                )
                has_data = True
            except ValueError:
                pass
                
        if humidity_str:
            try:
                humidity_value = float(humidity_str.replace(',', '.'))
                conditions.humidity = MeasuredValue(
                    value=humidity_value,
                    unit=get_unit("%rh")
                )
                has_data = True
            except ValueError:
                pass
                
        # Try to extract pressure
        pressure_match = None
        for pattern in self.PATTERNS["pressure"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                pressure_match = match
                break
                
        if pressure_match:
            try:
                pressure_value = float(pressure_match.group(1).replace(',', '.'))
                pressure_unit = pressure_match.group(2) if len(pressure_match.groups()) > 1 else "hPa"
                conditions.pressure = MeasuredValue(
                    value=pressure_value,
                    unit=get_unit(pressure_unit)
                )
                has_data = True
            except (ValueError, IndexError):
                pass
                
        return conditions if has_data else None
        
    def parse_certificate(
        self, 
        file_path: Union[str, Path],
        lab_name: str = "Unknown Laboratory"
    ) -> CalibrationCertificate:
        """Parse a calibration certificate file and extract structured data.
        
        Args:
            file_path: Path to the PDF or image file
            lab_name: Default laboratory name if not found in document
            
        Returns:
            CalibrationCertificate object with extracted data
        """
        file_path = Path(file_path)
        
        # Extract raw text
        raw_text = self.extract_from_file(file_path)
        
        # Extract certificate number
        cert_number = self.extract_pattern(raw_text, "certificate_number")
        if not cert_number:
            cert_number = f"UNKNOWN-{file_path.stem}"
            
        # Extract dates
        cal_date_str = self.extract_pattern(raw_text, "calibration_date")
        cert_date_str = self.extract_pattern(raw_text, "certificate_date")
        
        calibration_date = self.parse_date(cal_date_str) if cal_date_str else None
        certificate_date = self.parse_date(cert_date_str) if cert_date_str else None
        
        # Extract equipment info
        serial = self.extract_pattern(raw_text, "serial_number")
        manufacturer = self.extract_pattern(raw_text, "manufacturer")
        model = self.extract_pattern(raw_text, "model")
        
        equipment = EquipmentInfo(
            name=model or "Unknown Equipment",
            manufacturer=manufacturer,
            model=model,
            serial_number=serial
        )
        
        # Extract laboratory info
        lab = Organization(name=lab_name)
        
        # Extract environmental conditions
        env_conditions = self.extract_environmental_conditions(raw_text)
        
        # Extract measurement results
        measurements = self.extract_measurement_tables(raw_text)
        
        # Create the certificate object
        certificate = CalibrationCertificate(
            certificate_number=cert_number,
            certificate_date=certificate_date,
            calibration_date=calibration_date,
            calibration_laboratory=lab,
            equipment=equipment,
            environmental_conditions=env_conditions,
            measurement_results=measurements,
            raw_text=raw_text,
            source_file=str(file_path)
        )
        
        return certificate
