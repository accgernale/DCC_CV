# DCC_CV - Digital Calibration Certificate Computer Vision Agent

An intelligent agent for converting calibration certificates (PDF or image format) to XML following the [PTB Germany Digital Calibration Certificate (DCC) schema](https://ptb.de/dcc/).

## Features

- **Multi-format Input Support**: Process calibration certificates in PDF or image formats (PNG, JPG, TIFF, BMP)
- **Intelligent Text Extraction**: Uses OCR (Tesseract) for scanned documents and direct text extraction for text-based PDFs
- **PTB DCC Schema Compliance**: Generates XML following the official PTB Germany DCC schema (v3.0.0)
- **Measurement Unit Recognition**: Handles various measurement units (kN, °C, Pa, mm, etc.) with proper SI conversion
- **Table Data Extraction**: Extracts measurement results from tabular data
- **Environmental Conditions**: Captures temperature, humidity, and pressure data
- **Batch Processing**: Process multiple certificates at once
- **Validation**: Validates extracted data for completeness

## Installation

### Prerequisites

- Python 3.9 or higher
- Tesseract OCR (for image/scanned PDF processing)
- Poppler (for PDF to image conversion)

### Install Tesseract OCR

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-deu poppler-utils
```

**macOS:**
```bash
brew install tesseract poppler
```

**Windows:**
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

### Install the Package

```bash
# Clone the repository
git clone https://github.com/accgernale/DCC_CV.git
cd DCC_CV

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Quick Start

### Python API

```python
from dcc_cv import DCCAgent

# Create the agent
agent = DCCAgent()

# Process a calibration certificate
xml_content = agent.process(
    "certificate.pdf",
    output_path="certificate_dcc.xml"
)

# With laboratory information
from dcc_cv.agent import create_lab_info

lab = create_lab_info(
    name="Acme Calibration Laboratory",
    street="Industrial Park 123",
    city="Berlin",
    postal_code="10115",
    country_code="DE",
    accreditation_number="DAkkS-12345"
)

xml_content = agent.process(
    "certificate.pdf",
    output_path="certificate_dcc.xml",
    lab_info=lab
)
```

### Command Line Interface

```bash
# Basic usage
dcc-cv certificate.pdf -o certificate_dcc.xml

# With laboratory information
dcc-cv certificate.pdf \
    --lab-name "Acme Laboratory" \
    --lab-city "Berlin" \
    --lab-country "DE" \
    -o certificate_dcc.xml

# Process a directory of certificates
dcc-cv ./certificates/ -o ./output/

# Include validation
dcc-cv certificate.pdf --validate

# Enable verbose output
dcc-cv certificate.pdf -v
```

## Supported Measurement Units

The agent recognizes and properly converts the following units to SI notation:

| Category | Units |
|----------|-------|
| Force | N, kN, MN |
| Temperature | °C, K, °F |
| Pressure | Pa, kPa, MPa, bar, mbar, hPa |
| Length | m, mm, µm, nm |
| Mass | kg, g, mg |
| Electrical | V, mV, A, mA, Ω |
| Time | s, ms, min, h |
| Frequency | Hz, kHz, MHz |
| Other | %, ppm, %rh |

## Output Format

The generated XML follows the PTB DCC schema structure:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<dcc:digitalCalibrationCertificate 
    xmlns:dcc="https://ptb.de/dcc"
    xmlns:si="https://ptb.de/si"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="https://ptb.de/dcc https://ptb.de/dcc/v3.0.0/dcc.xsd">
    
    <dcc:administrativeData>
        <!-- Certificate identification, lab info, equipment details -->
    </dcc:administrativeData>
    
    <dcc:measurementResults>
        <!-- Calibration measurement data -->
    </dcc:measurementResults>
    
</dcc:digitalCalibrationCertificate>
```

## Project Structure

```
DCC_CV/
├── src/
│   └── dcc_cv/
│       ├── __init__.py      # Package initialization
│       ├── agent.py         # Main agent class
│       ├── extractor.py     # PDF/image text extraction
│       ├── xml_generator.py # DCC XML generation
│       ├── models.py        # Data models
│       └── cli.py           # Command line interface
├── tests/
│   ├── test_models.py
│   ├── test_extractor.py
│   ├── test_xml_generator.py
│   └── test_agent.py
├── requirements.txt
├── setup.py
└── README.md
```

## API Reference

### DCCAgent

The main class for processing calibration certificates.

```python
class DCCAgent:
    def __init__(
        self,
        ocr_language: str = "eng+deu",
        schema_version: str = "3.0.0",
        default_lab_name: str = "Calibration Laboratory"
    ):
        """Initialize the DCC Agent."""
    
    def process(
        self,
        input_file: str | Path,
        output_path: str | Path | None = None,
        lab_info: Organization | None = None,
        customer_info: Organization | None = None,
        include_raw_text: bool = False,
        pretty_print: bool = True
    ) -> str:
        """Process a calibration certificate and generate DCC XML."""
    
    def extract_only(
        self,
        input_file: str | Path,
        lab_name: str | None = None
    ) -> CalibrationCertificate:
        """Extract certificate data without generating XML."""
    
    def validate_certificate(
        self,
        certificate: CalibrationCertificate
    ) -> list[str]:
        """Validate extracted certificate data."""
    
    def batch_process(
        self,
        input_files: list[str | Path],
        output_dir: str | Path,
        lab_info: Organization | None = None,
        include_raw_text: bool = False
    ) -> dict[str, str]:
        """Process multiple certificate files."""
```

### CalibrationCertificate

Data model representing an extracted calibration certificate.

```python
class CalibrationCertificate:
    certificate_number: str
    certificate_date: date | None
    calibration_date: date | None
    language: str = "en"
    calibration_laboratory: Organization
    customer: Organization | None
    equipment: EquipmentInfo
    environmental_conditions: EnvironmentalConditions | None
    measurement_results: list[MeasurementResult]
    measurement_procedure: str | None
    traceability: str | None
    remarks: str | None
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dcc_cv

# Run specific test file
pytest tests/test_xml_generator.py
```

## References

- [PTB DCC Schema Documentation](https://www.ptb.de/dcc/v3.0.0/autogenerated-docs/dcc_xsd.htm)
- [PTB DCC GitLab Repository](https://gitlab.com/ptb/dcc/xsd-dcc)
- [PTB DCC Wiki](https://wiki.dcc.ptb.de/)
- [ISO 17025 - General requirements for calibration laboratories](https://www.iso.org/standard/66912.html)

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.