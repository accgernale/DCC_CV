"""Tests for the data models module."""

import pytest
from datetime import date, datetime

from dcc_cv.models import (
    CalibrationCertificate,
    Organization,
    Address,
    Contact,
    EquipmentInfo,
    MeasurementResult,
    MeasuredValue,
    MeasurementUnit,
    EnvironmentalConditions,
    COMMON_UNITS,
    get_unit,
)


class TestMeasurementUnit:
    """Tests for MeasurementUnit model."""
    
    def test_create_unit(self):
        """Test creating a measurement unit."""
        unit = MeasurementUnit(symbol="kN", name="kilonewton")
        assert unit.symbol == "kN"
        assert unit.name == "kilonewton"
        
    def test_unit_with_si_base(self):
        """Test unit with SI base representation."""
        unit = MeasurementUnit(
            symbol="kN",
            name="kilonewton",
            si_base="10³·kg·m/s²"
        )
        assert unit.si_base == "10³·kg·m/s²"


class TestMeasuredValue:
    """Tests for MeasuredValue model."""
    
    def test_create_value(self):
        """Test creating a measured value."""
        unit = MeasurementUnit(symbol="kN")
        value = MeasuredValue(value=100.5, unit=unit)
        assert value.value == 100.5
        assert value.unit.symbol == "kN"
        
    def test_value_with_uncertainty(self):
        """Test value with expanded uncertainty."""
        unit = MeasurementUnit(symbol="°C")
        value = MeasuredValue(
            value=23.0,
            unit=unit,
            expanded_uncertainty=0.5,
            coverage_factor=2.0,
            coverage_probability=0.95
        )
        assert value.expanded_uncertainty == 0.5
        assert value.coverage_factor == 2.0
        assert value.coverage_probability == 0.95


class TestMeasurementResult:
    """Tests for MeasurementResult model."""
    
    def test_create_result(self):
        """Test creating a measurement result."""
        unit = MeasurementUnit(symbol="kN")
        measured = MeasuredValue(value=100.0, unit=unit)
        result = MeasurementResult(
            name="Force at 100 kN",
            measured_value=measured
        )
        assert result.name == "Force at 100 kN"
        assert result.measured_value.value == 100.0
        
    def test_result_with_deviation(self):
        """Test result with reference and deviation."""
        unit = MeasurementUnit(symbol="kN")
        reference = MeasuredValue(value=100.0, unit=unit)
        measured = MeasuredValue(value=100.05, unit=unit)
        deviation = MeasuredValue(value=0.05, unit=unit)
        
        result = MeasurementResult(
            name="Force calibration point",
            reference_value=reference,
            measured_value=measured,
            deviation=deviation
        )
        assert result.reference_value.value == 100.0
        assert result.deviation.value == 0.05


class TestEquipmentInfo:
    """Tests for EquipmentInfo model."""
    
    def test_create_equipment(self):
        """Test creating equipment info."""
        equipment = EquipmentInfo(
            name="Force Transducer",
            manufacturer="Acme Corp",
            model="FT-1000",
            serial_number="SN12345"
        )
        assert equipment.name == "Force Transducer"
        assert equipment.manufacturer == "Acme Corp"
        assert equipment.serial_number == "SN12345"


class TestOrganization:
    """Tests for Organization model."""
    
    def test_create_organization(self):
        """Test creating an organization."""
        org = Organization(name="Test Laboratory")
        assert org.name == "Test Laboratory"
        
    def test_organization_with_address(self):
        """Test organization with full address."""
        address = Address(
            street="Test Street 123",
            city="Berlin",
            postal_code="10115",
            country="Germany",
            country_code="DE"
        )
        org = Organization(name="Test Laboratory", address=address)
        assert org.address.city == "Berlin"
        assert org.address.country_code == "DE"


class TestEnvironmentalConditions:
    """Tests for EnvironmentalConditions model."""
    
    def test_create_conditions(self):
        """Test creating environmental conditions."""
        temp_unit = MeasurementUnit(symbol="°C")
        humidity_unit = MeasurementUnit(symbol="%rh")
        
        conditions = EnvironmentalConditions(
            temperature=MeasuredValue(value=23.0, unit=temp_unit),
            humidity=MeasuredValue(value=45.0, unit=humidity_unit)
        )
        assert conditions.temperature.value == 23.0
        assert conditions.humidity.value == 45.0


class TestCalibrationCertificate:
    """Tests for CalibrationCertificate model."""
    
    def test_create_certificate(self):
        """Test creating a full calibration certificate."""
        lab = Organization(name="PTB")
        equipment = EquipmentInfo(name="Force Transducer")
        
        cert = CalibrationCertificate(
            certificate_number="CAL-2024-001",
            calibration_laboratory=lab,
            equipment=equipment,
            calibration_date=date(2024, 1, 15)
        )
        assert cert.certificate_number == "CAL-2024-001"
        assert cert.calibration_laboratory.name == "PTB"
        assert cert.calibration_date == date(2024, 1, 15)
        
    def test_certificate_with_measurements(self):
        """Test certificate with measurement results."""
        lab = Organization(name="Test Lab")
        equipment = EquipmentInfo(name="Thermometer")
        
        unit = MeasurementUnit(symbol="°C")
        result = MeasurementResult(
            name="Temperature at 20°C",
            measured_value=MeasuredValue(value=20.05, unit=unit)
        )
        
        cert = CalibrationCertificate(
            certificate_number="TEMP-001",
            calibration_laboratory=lab,
            equipment=equipment,
            measurement_results=[result]
        )
        assert len(cert.measurement_results) == 1
        assert cert.measurement_results[0].measured_value.value == 20.05


class TestCommonUnits:
    """Tests for common units dictionary."""
    
    def test_common_units_exist(self):
        """Test that common units are defined."""
        assert "kN" in COMMON_UNITS
        assert "°C" in COMMON_UNITS
        assert "Pa" in COMMON_UNITS
        assert "mm" in COMMON_UNITS
        
    def test_get_known_unit(self):
        """Test getting a known unit."""
        unit = get_unit("kN")
        assert unit.symbol == "kN"
        assert unit.name == "kilonewton"
        
    def test_get_unknown_unit(self):
        """Test getting an unknown unit creates a generic one."""
        unit = get_unit("custom_unit")
        assert unit.symbol == "custom_unit"
        assert unit.name is None
