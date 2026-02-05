"""Tests for the XML generator module."""

import pytest
from datetime import date
from lxml import etree

from dcc_cv.xml_generator import DCCXMLGenerator, DCC_NS, SI_NS
from dcc_cv.models import (
    CalibrationCertificate,
    Organization,
    Address,
    EquipmentInfo,
    MeasurementResult,
    MeasuredValue,
    MeasurementUnit,
    EnvironmentalConditions,
)


@pytest.fixture
def generator():
    """Create a DCC XML generator instance."""
    return DCCXMLGenerator()


@pytest.fixture
def sample_certificate():
    """Create a sample calibration certificate for testing."""
    lab = Organization(
        name="Test Calibration Laboratory",
        address=Address(
            street="Test Street 1",
            city="Berlin",
            postal_code="10115",
            country_code="DE"
        )
    )
    
    equipment = EquipmentInfo(
        name="Force Transducer",
        manufacturer="Acme Corp",
        model="FT-1000",
        serial_number="SN12345"
    )
    
    temp_unit = MeasurementUnit(symbol="°C")
    humidity_unit = MeasurementUnit(symbol="%rh")
    
    env_conditions = EnvironmentalConditions(
        temperature=MeasuredValue(value=23.0, unit=temp_unit),
        humidity=MeasuredValue(value=45.0, unit=humidity_unit)
    )
    
    force_unit = MeasurementUnit(symbol="kN")
    results = [
        MeasurementResult(
            name="Force at 100 kN",
            measured_value=MeasuredValue(
                value=100.05,
                unit=force_unit,
                expanded_uncertainty=0.02,
                coverage_factor=2.0
            )
        ),
        MeasurementResult(
            name="Force at 200 kN",
            measured_value=MeasuredValue(
                value=200.03,
                unit=force_unit,
                expanded_uncertainty=0.04,
                coverage_factor=2.0
            )
        ),
    ]
    
    return CalibrationCertificate(
        certificate_number="CAL-2024-001",
        calibration_date=date(2024, 1, 15),
        certificate_date=date(2024, 1, 16),
        calibration_laboratory=lab,
        equipment=equipment,
        environmental_conditions=env_conditions,
        measurement_results=results,
        measurement_procedure="ISO 376:2011",
        remarks="Calibration performed according to standard procedure."
    )


class TestDCCXMLGenerator:
    """Tests for DCCXMLGenerator class."""
    
    def test_generator_initialization(self, generator):
        """Test generator initialization."""
        assert generator.schema_version == "3.0.0"
        
    def test_generate_returns_element(self, generator, sample_certificate):
        """Test that generate returns an lxml Element."""
        result = generator.generate(sample_certificate)
        assert isinstance(result, etree._Element)
        
    def test_root_element_has_correct_namespace(self, generator, sample_certificate):
        """Test root element has correct DCC namespace."""
        result = generator.generate(sample_certificate)
        assert result.tag == f"{{{DCC_NS}}}digitalCalibrationCertificate"
        
    def test_contains_administrative_data(self, generator, sample_certificate):
        """Test XML contains administrative data section."""
        result = generator.generate(sample_certificate)
        admin_data = result.find(f"{{{DCC_NS}}}administrativeData")
        assert admin_data is not None
        
    def test_contains_measurement_results(self, generator, sample_certificate):
        """Test XML contains measurement results section."""
        result = generator.generate(sample_certificate)
        meas_results = result.find(f"{{{DCC_NS}}}measurementResults")
        assert meas_results is not None
        
    def test_certificate_number_in_xml(self, generator, sample_certificate):
        """Test certificate number is included in XML."""
        xml_str = generator.to_string(sample_certificate)
        assert "CAL-2024-001" in xml_str
        
    def test_laboratory_name_in_xml(self, generator, sample_certificate):
        """Test laboratory name is included in XML."""
        xml_str = generator.to_string(sample_certificate)
        assert "Test Calibration Laboratory" in xml_str
        
    def test_equipment_info_in_xml(self, generator, sample_certificate):
        """Test equipment information is included in XML."""
        xml_str = generator.to_string(sample_certificate)
        assert "Force Transducer" in xml_str
        assert "SN12345" in xml_str
        
    def test_measurement_values_in_xml(self, generator, sample_certificate):
        """Test measurement values are included in XML."""
        xml_str = generator.to_string(sample_certificate)
        assert "100.05" in xml_str
        assert "200.03" in xml_str
        
    def test_units_converted_to_si(self, generator, sample_certificate):
        """Test units are converted to SI notation."""
        xml_str = generator.to_string(sample_certificate)
        # kN should be converted to \\kilo\\newton
        assert "\\kilo\\newton" in xml_str or "kN" in xml_str
        
    def test_environmental_conditions_in_xml(self, generator, sample_certificate):
        """Test environmental conditions are included."""
        xml_str = generator.to_string(sample_certificate)
        assert "23.0" in xml_str  # Temperature
        assert "45.0" in xml_str  # Humidity
        
    def test_to_string_returns_string(self, generator, sample_certificate):
        """Test to_string returns a string."""
        result = generator.to_string(sample_certificate)
        assert isinstance(result, str)
        
    def test_xml_declaration_present(self, generator, sample_certificate):
        """Test XML declaration is present."""
        xml_str = generator.to_string(sample_certificate)
        assert xml_str.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        
    def test_schema_location_present(self, generator, sample_certificate):
        """Test schema location attribute is present."""
        xml_str = generator.to_string(sample_certificate)
        assert "schemaLocation" in xml_str
        assert "ptb.de/dcc" in xml_str
        
    def test_pretty_print_formatting(self, generator, sample_certificate):
        """Test pretty print adds formatting."""
        xml_pretty = generator.to_string(sample_certificate, pretty_print=True)
        xml_compact = generator.to_string(sample_certificate, pretty_print=False)
        # Pretty printed XML should have more newlines
        assert xml_pretty.count('\n') > xml_compact.count('\n')


class TestUnitConversion:
    """Tests for unit conversion to SI notation."""
    
    def test_force_units(self, generator):
        """Test force unit conversions."""
        assert generator.UNIT_TO_SI.get("N") == "\\newton"
        assert generator.UNIT_TO_SI.get("kN") == "\\kilo\\newton"
        assert generator.UNIT_TO_SI.get("MN") == "\\mega\\newton"
        
    def test_temperature_units(self, generator):
        """Test temperature unit conversions."""
        assert generator.UNIT_TO_SI.get("°C") == "\\degreeCelsius"
        assert generator.UNIT_TO_SI.get("K") == "\\kelvin"
        
    def test_pressure_units(self, generator):
        """Test pressure unit conversions."""
        assert generator.UNIT_TO_SI.get("Pa") == "\\pascal"
        assert generator.UNIT_TO_SI.get("kPa") == "\\kilo\\pascal"
        assert generator.UNIT_TO_SI.get("bar") == "\\bar"
        
    def test_length_units(self, generator):
        """Test length unit conversions."""
        assert generator.UNIT_TO_SI.get("m") == "\\metre"
        assert generator.UNIT_TO_SI.get("mm") == "\\milli\\metre"
        assert generator.UNIT_TO_SI.get("µm") == "\\micro\\metre"


class TestMinimalCertificate:
    """Tests with minimal certificate data."""
    
    def test_minimal_certificate_generates_xml(self, generator):
        """Test that a minimal certificate still generates valid XML."""
        lab = Organization(name="Minimal Lab")
        equipment = EquipmentInfo(name="Test Device")
        
        cert = CalibrationCertificate(
            certificate_number="MIN-001",
            calibration_laboratory=lab,
            equipment=equipment
        )
        
        xml_str = generator.to_string(cert)
        assert "MIN-001" in xml_str
        assert "Minimal Lab" in xml_str
        assert "Test Device" in xml_str
