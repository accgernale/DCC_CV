"""DCC Agent module - Main agent for calibration certificate processing.

This module provides the main agent class that orchestrates the
extraction of calibration certificates and conversion to DCC XML.
"""

import logging
from pathlib import Path
from typing import Optional, Union
from datetime import datetime

from .models import (
    CalibrationCertificate,
    Organization,
    Address,
    Contact,
)
from .extractor import DocumentExtractor
from .xml_generator import DCCXMLGenerator

logger = logging.getLogger(__name__)


class DCCAgent:
    """Agent for processing calibration certificates to DCC XML format.
    
    This agent reads calibration certificates from PDF or image files,
    extracts relevant information using OCR and text analysis, and
    generates XML documents following the PTB Germany DCC schema.
    
    Example:
        >>> agent = DCCAgent()
        >>> xml_content = agent.process("certificate.pdf")
        >>> print(xml_content)
        
        >>> # Or save directly to file
        >>> agent.process("certificate.pdf", output_path="certificate.xml")
    """
    
    def __init__(
        self,
        ocr_language: str = "eng+deu",
        schema_version: str = "3.0.0",
        default_lab_name: str = "Calibration Laboratory"
    ):
        """Initialize the DCC Agent.
        
        Args:
            ocr_language: Tesseract language code(s) for OCR (e.g., "eng+deu")
            schema_version: DCC schema version to use
            default_lab_name: Default laboratory name if not extracted
        """
        self.extractor = DocumentExtractor(ocr_language=ocr_language)
        self.xml_generator = DCCXMLGenerator(schema_version=schema_version)
        self.default_lab_name = default_lab_name
        
    def process(
        self,
        input_file: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        lab_info: Optional[Organization] = None,
        customer_info: Optional[Organization] = None,
        include_raw_text: bool = False,
        pretty_print: bool = True
    ) -> str:
        """Process a calibration certificate file and generate DCC XML.
        
        Args:
            input_file: Path to the PDF or image file
            output_path: Optional path to save the XML output
            lab_info: Optional laboratory information to use
            customer_info: Optional customer information to add
            include_raw_text: Whether to include raw OCR text in output
            pretty_print: Whether to format the XML output
            
        Returns:
            XML content as string
            
        Raises:
            FileNotFoundError: If input file doesn't exist
            ValueError: If file format is not supported
        """
        input_path = Path(input_file)
        
        logger.info(f"Processing calibration certificate: {input_path}")
        
        # Extract certificate data
        lab_name = lab_info.name if lab_info else self.default_lab_name
        certificate = self.extractor.parse_certificate(input_path, lab_name)
        
        # Update with provided organization info
        if lab_info:
            certificate.calibration_laboratory = lab_info
            
        if customer_info:
            certificate.customer = customer_info
            
        # Generate XML
        xml_content = self.xml_generator.to_string(
            certificate,
            pretty_print=pretty_print,
            include_raw_text=include_raw_text
        )
        
        # Save to file if output path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            logger.info(f"DCC XML saved to: {output_path}")
            
        return xml_content
        
    def extract_only(
        self,
        input_file: Union[str, Path],
        lab_name: Optional[str] = None
    ) -> CalibrationCertificate:
        """Extract certificate data without generating XML.
        
        Useful for inspection or further processing of extracted data.
        
        Args:
            input_file: Path to the PDF or image file
            lab_name: Laboratory name to use
            
        Returns:
            CalibrationCertificate object
        """
        input_path = Path(input_file)
        return self.extractor.parse_certificate(
            input_path,
            lab_name or self.default_lab_name
        )
        
    def validate_certificate(
        self,
        certificate: CalibrationCertificate
    ) -> list[str]:
        """Validate a certificate object for completeness.
        
        Args:
            certificate: CalibrationCertificate to validate
            
        Returns:
            List of validation warnings/errors
        """
        issues = []
        
        # Check required fields
        if certificate.certificate_number.startswith("UNKNOWN"):
            issues.append("Certificate number could not be extracted")
            
        if not certificate.calibration_date:
            issues.append("Calibration date is missing")
            
        if not certificate.equipment.serial_number:
            issues.append("Equipment serial number is missing")
            
        if not certificate.measurement_results:
            issues.append("No measurement results were extracted")
        elif len(certificate.measurement_results) < 2:
            issues.append("Very few measurement results extracted - manual review recommended")
            
        if not certificate.environmental_conditions:
            issues.append("Environmental conditions are missing")
            
        return issues
        
    def batch_process(
        self,
        input_files: list[Union[str, Path]],
        output_dir: Union[str, Path],
        lab_info: Optional[Organization] = None,
        include_raw_text: bool = False
    ) -> dict[str, str]:
        """Process multiple certificate files.
        
        Args:
            input_files: List of input file paths
            output_dir: Directory for output XML files
            lab_info: Optional laboratory information
            include_raw_text: Whether to include raw text
            
        Returns:
            Dict mapping input files to output files or error messages
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {}
        
        for input_file in input_files:
            input_path = Path(input_file)
            output_path = output_dir / f"{input_path.stem}_dcc.xml"
            
            try:
                self.process(
                    input_file,
                    output_path=output_path,
                    lab_info=lab_info,
                    include_raw_text=include_raw_text
                )
                results[str(input_path)] = str(output_path)
                logger.info(f"Successfully processed: {input_path}")
            except Exception as e:
                results[str(input_path)] = f"ERROR: {str(e)}"
                logger.error(f"Failed to process {input_path}: {e}")
                
        return results


def create_lab_info(
    name: str,
    street: Optional[str] = None,
    city: Optional[str] = None,
    postal_code: Optional[str] = None,
    country: Optional[str] = None,
    country_code: Optional[str] = None,
    accreditation_number: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None
) -> Organization:
    """Helper function to create laboratory organization info.
    
    Args:
        name: Laboratory name
        street: Street address
        city: City name
        postal_code: Postal/ZIP code
        country: Country name
        country_code: ISO country code
        accreditation_number: Lab accreditation number
        email: Contact email
        phone: Contact phone
        
    Returns:
        Organization object
    """
    address = None
    if any([street, city, postal_code, country]):
        address = Address(
            street=street,
            city=city,
            postal_code=postal_code,
            country=country,
            country_code=country_code
        )
        
    contact = None
    if email or phone:
        contact = Contact(email=email, phone=phone)
        
    return Organization(
        name=name,
        address=address,
        contact=contact,
        accreditation_number=accreditation_number
    )
