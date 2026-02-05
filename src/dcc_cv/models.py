"""Data models for calibration certificate information.

This module contains Pydantic models representing the structure
of calibration certificates and their components.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class Contact(BaseModel):
    """Contact information model."""
    
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None


class Address(BaseModel):
    """Address information model."""
    
    street: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None


class Organization(BaseModel):
    """Organization information model."""
    
    name: str
    address: Optional[Address] = None
    contact: Optional[Contact] = None
    accreditation_number: Optional[str] = None


class MeasurementUnit(BaseModel):
    """Measurement unit model following SI conventions."""
    
    symbol: str = Field(..., description="Unit symbol (e.g., 'kN', '°C', 'Pa')")
    name: Optional[str] = Field(None, description="Full unit name (e.g., 'kilonewton')")
    si_base: Optional[str] = Field(None, description="SI base representation")
    

class MeasuredValue(BaseModel):
    """A single measured value with uncertainty."""
    
    value: float = Field(..., description="The measured value")
    unit: MeasurementUnit = Field(..., description="Unit of measurement")
    expanded_uncertainty: Optional[float] = Field(None, description="Expanded uncertainty (U)")
    coverage_factor: Optional[float] = Field(None, description="Coverage factor (k)")
    coverage_probability: Optional[float] = Field(None, description="Coverage probability")


class MeasurementResult(BaseModel):
    """A measurement result entry from calibration."""
    
    name: str = Field(..., description="Name/description of the measured quantity")
    reference_value: Optional[MeasuredValue] = Field(None, description="Reference/nominal value")
    measured_value: MeasuredValue = Field(..., description="The measured/calibration value")
    deviation: Optional[MeasuredValue] = Field(None, description="Deviation from reference")
    remarks: Optional[str] = None


class EquipmentInfo(BaseModel):
    """Information about the calibrated equipment."""
    
    name: str = Field(..., description="Name/type of the equipment")
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    equipment_class: Optional[str] = None
    identification_number: Optional[str] = None


class EnvironmentalConditions(BaseModel):
    """Environmental conditions during calibration."""
    
    temperature: Optional[MeasuredValue] = None
    humidity: Optional[MeasuredValue] = None
    pressure: Optional[MeasuredValue] = None


class CalibrationCertificate(BaseModel):
    """Main model representing a calibration certificate.
    
    This model captures all essential information from a calibration
    certificate that needs to be converted to DCC XML format.
    """
    
    # Certificate identification
    certificate_number: str = Field(..., description="Unique certificate number")
    certificate_date: Optional[date] = Field(None, description="Date of certificate issue")
    calibration_date: Optional[date] = Field(None, description="Date of calibration")
    valid_until: Optional[date] = Field(None, description="Validity end date if specified")
    
    # Language information
    language: str = Field(default="en", description="Primary language code (ISO 639-1)")
    
    # Organizations
    calibration_laboratory: Organization = Field(..., description="Lab performing calibration")
    customer: Optional[Organization] = Field(None, description="Customer receiving certificate")
    
    # Equipment under test
    equipment: EquipmentInfo = Field(..., description="Equipment being calibrated")
    
    # Environmental conditions
    environmental_conditions: Optional[EnvironmentalConditions] = None
    
    # Measurement results
    measurement_results: list[MeasurementResult] = Field(
        default_factory=list,
        description="List of measurement results"
    )
    
    # Additional information
    measurement_procedure: Optional[str] = Field(None, description="Calibration procedure reference")
    traceability: Optional[str] = Field(None, description="Traceability statement")
    remarks: Optional[str] = Field(None, description="Additional remarks/notes")
    
    # Raw extracted text (for reference)
    raw_text: Optional[str] = Field(None, description="Raw OCR extracted text")
    
    # Metadata
    extraction_timestamp: Optional[datetime] = Field(
        default_factory=datetime.now,
        description="When the data was extracted"
    )
    source_file: Optional[str] = Field(None, description="Source file path")


# Common measurement units lookup
COMMON_UNITS: dict[str, MeasurementUnit] = {
    # Force units
    "N": MeasurementUnit(symbol="N", name="newton", si_base="kg·m/s²"),
    "kN": MeasurementUnit(symbol="kN", name="kilonewton", si_base="10³·kg·m/s²"),
    "MN": MeasurementUnit(symbol="MN", name="meganewton", si_base="10⁶·kg·m/s²"),
    
    # Temperature units
    "°C": MeasurementUnit(symbol="°C", name="degree Celsius", si_base="K"),
    "K": MeasurementUnit(symbol="K", name="kelvin", si_base="K"),
    "°F": MeasurementUnit(symbol="°F", name="degree Fahrenheit"),
    
    # Pressure units
    "Pa": MeasurementUnit(symbol="Pa", name="pascal", si_base="kg/(m·s²)"),
    "kPa": MeasurementUnit(symbol="kPa", name="kilopascal", si_base="10³·kg/(m·s²)"),
    "MPa": MeasurementUnit(symbol="MPa", name="megapascal", si_base="10⁶·kg/(m·s²)"),
    "bar": MeasurementUnit(symbol="bar", name="bar", si_base="10⁵·kg/(m·s²)"),
    "mbar": MeasurementUnit(symbol="mbar", name="millibar", si_base="10²·kg/(m·s²)"),
    
    # Length units
    "m": MeasurementUnit(symbol="m", name="meter", si_base="m"),
    "mm": MeasurementUnit(symbol="mm", name="millimeter", si_base="10⁻³·m"),
    "µm": MeasurementUnit(symbol="µm", name="micrometer", si_base="10⁻⁶·m"),
    "nm": MeasurementUnit(symbol="nm", name="nanometer", si_base="10⁻⁹·m"),
    
    # Mass units
    "kg": MeasurementUnit(symbol="kg", name="kilogram", si_base="kg"),
    "g": MeasurementUnit(symbol="g", name="gram", si_base="10⁻³·kg"),
    "mg": MeasurementUnit(symbol="mg", name="milligram", si_base="10⁻⁶·kg"),
    
    # Electrical units
    "V": MeasurementUnit(symbol="V", name="volt", si_base="kg·m²/(A·s³)"),
    "mV": MeasurementUnit(symbol="mV", name="millivolt", si_base="10⁻³·kg·m²/(A·s³)"),
    "A": MeasurementUnit(symbol="A", name="ampere", si_base="A"),
    "mA": MeasurementUnit(symbol="mA", name="milliampere", si_base="10⁻³·A"),
    "Ω": MeasurementUnit(symbol="Ω", name="ohm", si_base="kg·m²/(A²·s³)"),
    
    # Time units
    "s": MeasurementUnit(symbol="s", name="second", si_base="s"),
    "ms": MeasurementUnit(symbol="ms", name="millisecond", si_base="10⁻³·s"),
    "min": MeasurementUnit(symbol="min", name="minute", si_base="60·s"),
    "h": MeasurementUnit(symbol="h", name="hour", si_base="3600·s"),
    
    # Frequency units
    "Hz": MeasurementUnit(symbol="Hz", name="hertz", si_base="s⁻¹"),
    "kHz": MeasurementUnit(symbol="kHz", name="kilohertz", si_base="10³·s⁻¹"),
    "MHz": MeasurementUnit(symbol="MHz", name="megahertz", si_base="10⁶·s⁻¹"),
    
    # Relative units
    "%": MeasurementUnit(symbol="%", name="percent"),
    "ppm": MeasurementUnit(symbol="ppm", name="parts per million"),
    "%rh": MeasurementUnit(symbol="%rh", name="percent relative humidity"),
}


def get_unit(symbol: str) -> MeasurementUnit:
    """Get a MeasurementUnit by its symbol, or create a generic one.
    
    Args:
        symbol: The unit symbol (e.g., 'kN', '°C')
        
    Returns:
        MeasurementUnit instance
    """
    if symbol in COMMON_UNITS:
        return COMMON_UNITS[symbol]
    return MeasurementUnit(symbol=symbol)
