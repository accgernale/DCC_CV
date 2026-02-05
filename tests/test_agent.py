"""Tests for the DCC Agent module."""

import pytest
from datetime import date
from pathlib import Path

from dcc_cv.agent import DCCAgent, create_lab_info
from dcc_cv.models import (
    CalibrationCertificate,
    Organization,
    EquipmentInfo,
    MeasurementResult,
    MeasuredValue,
    MeasurementUnit,
)


class TestDCCAgent:
    """Tests for DCCAgent class."""
    
    @pytest.fixture
    def agent(self):
        """Create an agent instance."""
        return DCCAgent()
    
    def test_agent_initialization(self, agent):
        """Test agent initializes with default values."""
        assert agent.default_lab_name == "Calibration Laboratory"
        assert agent.extractor is not None
        assert agent.xml_generator is not None
        
    def test_agent_custom_initialization(self):
        """Test agent with custom parameters."""
        agent = DCCAgent(
            ocr_language="eng",
            schema_version="3.0.0",
            default_lab_name="My Lab"
        )
        assert agent.default_lab_name == "My Lab"


class TestCertificateValidation:
    """Tests for certificate validation."""
    
    @pytest.fixture
    def agent(self):
        """Create an agent instance."""
        return DCCAgent()
    
    def test_validate_complete_certificate(self, agent):
        """Test validation of a complete certificate."""
        lab = Organization(name="Test Lab")
        equipment = EquipmentInfo(
            name="Test Device",
            serial_number="SN123"
        )
        
        unit = MeasurementUnit(symbol="kN")
        results = [
            MeasurementResult(
                name="Point 1",
                measured_value=MeasuredValue(value=100.0, unit=unit)
            ),
            MeasurementResult(
                name="Point 2",
                measured_value=MeasuredValue(value=200.0, unit=unit)
            ),
        ]
        
        cert = CalibrationCertificate(
            certificate_number="CAL-001",
            calibration_date=date(2024, 1, 15),
            calibration_laboratory=lab,
            equipment=equipment,
            measurement_results=results
        )
        
        issues = agent.validate_certificate(cert)
        # Should have issue about environmental conditions
        assert any("Environmental" in issue for issue in issues)
        
    def test_validate_incomplete_certificate(self, agent):
        """Test validation catches missing data."""
        lab = Organization(name="Test Lab")
        equipment = EquipmentInfo(name="Test Device")
        
        cert = CalibrationCertificate(
            certificate_number="UNKNOWN-test",  # Starts with UNKNOWN
            calibration_laboratory=lab,
            equipment=equipment
        )
        
        issues = agent.validate_certificate(cert)
        assert len(issues) > 0
        # Should catch multiple issues
        assert any("Certificate number" in issue for issue in issues)
        assert any("serial number" in issue for issue in issues)


class TestCreateLabInfo:
    """Tests for the create_lab_info helper function."""
    
    def test_create_minimal_lab_info(self):
        """Test creating lab info with just name."""
        lab = create_lab_info(name="Test Laboratory")
        assert lab.name == "Test Laboratory"
        assert lab.address is None
        assert lab.contact is None
        
    def test_create_full_lab_info(self):
        """Test creating lab info with all fields."""
        lab = create_lab_info(
            name="Test Laboratory",
            street="Test Street 123",
            city="Berlin",
            postal_code="10115",
            country="Germany",
            country_code="DE",
            accreditation_number="DAkkS-12345",
            email="test@lab.com",
            phone="+49 123 456789"
        )
        
        assert lab.name == "Test Laboratory"
        assert lab.address.street == "Test Street 123"
        assert lab.address.city == "Berlin"
        assert lab.address.country_code == "DE"
        assert lab.contact.email == "test@lab.com"
        assert lab.accreditation_number == "DAkkS-12345"


class TestAgentProcess:
    """Tests for the agent process method."""
    
    @pytest.fixture
    def agent(self):
        """Create an agent instance."""
        return DCCAgent()
    
    def test_process_nonexistent_file(self, agent):
        """Test processing nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            agent.process("/nonexistent/file.pdf")
            
    def test_lab_info_creation_for_processing(self):
        """Test that lab info can be created and used."""
        lab_info = create_lab_info(name="Custom Lab")
        
        # The lab info should be properly created
        assert lab_info.name == "Custom Lab"
        
        # Can be used with an agent
        agent = DCCAgent(default_lab_name="Default Lab")
        assert agent.default_lab_name == "Default Lab"
