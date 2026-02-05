"""DCC XML Generator module.

This module generates XML documents following the PTB Germany
Digital Calibration Certificate (DCC) schema.

Reference: https://ptb.de/dcc/v3.0.0/dcc.xsd
"""

import logging
from datetime import datetime
from typing import Optional
from lxml import etree

from .models import (
    CalibrationCertificate,
    MeasurementResult,
    MeasuredValue,
    Organization,
    EnvironmentalConditions,
)

logger = logging.getLogger(__name__)

# DCC Namespaces
DCC_NS = "https://ptb.de/dcc"
SI_NS = "https://ptb.de/si"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

NSMAP = {
    "dcc": DCC_NS,
    "si": SI_NS,
    "xsi": XSI_NS,
}


class DCCXMLGenerator:
    """Generate DCC XML documents from calibration certificate data."""
    
    # Schema location
    SCHEMA_LOCATION = "https://ptb.de/dcc https://ptb.de/dcc/v3.0.0/dcc.xsd"
    
    # SI unit mapping to proper DCC notation
    UNIT_TO_SI = {
        # Force
        "N": "\\newton",
        "kN": "\\kilo\\newton", 
        "MN": "\\mega\\newton",
        # Temperature
        "°C": "\\degreeCelsius",
        "K": "\\kelvin",
        # Pressure
        "Pa": "\\pascal",
        "kPa": "\\kilo\\pascal",
        "MPa": "\\mega\\pascal",
        "bar": "\\bar",
        "mbar": "\\milli\\bar",
        "hPa": "\\hecto\\pascal",
        # Length
        "m": "\\metre",
        "mm": "\\milli\\metre",
        "µm": "\\micro\\metre",
        "nm": "\\nano\\metre",
        # Mass
        "kg": "\\kilogram",
        "g": "\\gram",
        "mg": "\\milli\\gram",
        # Electrical
        "V": "\\volt",
        "mV": "\\milli\\volt",
        "A": "\\ampere",
        "mA": "\\milli\\ampere",
        "Ω": "\\ohm",
        # Time
        "s": "\\second",
        "ms": "\\milli\\second",
        "min": "\\minute",
        "h": "\\hour",
        # Frequency
        "Hz": "\\hertz",
        "kHz": "\\kilo\\hertz",
        "MHz": "\\mega\\hertz",
        # Other
        "%": "\\percent",
        "%rh": "\\percent",
    }
    
    def __init__(self, schema_version: str = "3.0.0"):
        """Initialize the DCC XML generator.
        
        Args:
            schema_version: DCC schema version to use
        """
        self.schema_version = schema_version
        
    def _dcc(self, tag: str) -> str:
        """Create a fully qualified DCC namespace tag."""
        return f"{{{DCC_NS}}}{tag}"
        
    def _si(self, tag: str) -> str:
        """Create a fully qualified SI namespace tag."""
        return f"{{{SI_NS}}}{tag}"
        
    def _create_text_element(
        self, 
        parent: etree.Element, 
        tag: str, 
        text: str,
        lang: str = "en"
    ) -> etree.Element:
        """Create a DCC text element with language attribute.
        
        Args:
            parent: Parent element
            tag: Element tag name
            text: Text content
            lang: Language code
            
        Returns:
            Created element
        """
        elem = etree.SubElement(parent, self._dcc(tag))
        content = etree.SubElement(elem, self._dcc("content"))
        content.set("lang", lang)
        content.text = text
        return elem
        
    def _create_value_element(
        self,
        parent: etree.Element,
        value: MeasuredValue,
        tag: str = "real"
    ) -> etree.Element:
        """Create a SI value element.
        
        Args:
            parent: Parent element  
            value: MeasuredValue object
            tag: Element tag name
            
        Returns:
            Created element
        """
        real_elem = etree.SubElement(parent, self._si(tag))
        
        # Add value
        value_elem = etree.SubElement(real_elem, self._si("value"))
        value_elem.text = str(value.value)
        
        # Add unit
        unit_elem = etree.SubElement(real_elem, self._si("unit"))
        si_unit = self.UNIT_TO_SI.get(value.unit.symbol, value.unit.symbol)
        unit_elem.text = si_unit
        
        # Add uncertainty if present
        if value.expanded_uncertainty is not None:
            uncertainty_elem = etree.SubElement(real_elem, self._si("expandedUnc"))
            unc_value = etree.SubElement(uncertainty_elem, self._si("uncertainty"))
            unc_value.text = str(value.expanded_uncertainty)
            
            if value.coverage_factor is not None:
                cov_factor = etree.SubElement(uncertainty_elem, self._si("coverageFactor"))
                cov_factor.text = str(value.coverage_factor)
                
            if value.coverage_probability is not None:
                cov_prob = etree.SubElement(uncertainty_elem, self._si("coverageProbability"))
                cov_prob.text = str(value.coverage_probability)
                
        return real_elem
        
    def _create_administrative_data(
        self,
        parent: etree.Element,
        certificate: CalibrationCertificate
    ) -> etree.Element:
        """Create the administrativeData section.
        
        Args:
            parent: Parent element
            certificate: Certificate data
            
        Returns:
            Created element
        """
        admin = etree.SubElement(parent, self._dcc("administrativeData"))
        
        # DCC software info
        software = etree.SubElement(admin, self._dcc("dccSoftware"))
        sw_name = etree.SubElement(software, self._dcc("software"))
        self._create_text_element(sw_name, "name", "DCC CV Agent")
        release = etree.SubElement(sw_name, self._dcc("release"))
        release.text = "0.1.0"
        
        # Core data
        core = etree.SubElement(admin, self._dcc("coreData"))
        
        # Country code (default to DE for PTB)
        country = etree.SubElement(core, self._dcc("countryCodeISO3166_1"))
        country.text = "DE"
        
        # Used languages
        used_lang = etree.SubElement(core, self._dcc("usedLangCodeISO639_1"))
        used_lang.text = certificate.language
        
        # Mandatory languages
        mand_lang = etree.SubElement(core, self._dcc("mandatoryLangCodeISO639_1"))
        mand_lang.text = certificate.language
        
        # Unique identifier
        uid = etree.SubElement(core, self._dcc("uniqueIdentifier"))
        uid.text = certificate.certificate_number
        
        # Begin and end validity period
        begin_perf = etree.SubElement(core, self._dcc("beginPerformanceDate"))
        if certificate.calibration_date:
            begin_perf.text = certificate.calibration_date.isoformat()
        else:
            begin_perf.text = datetime.now().date().isoformat()
            
        end_perf = etree.SubElement(core, self._dcc("endPerformanceDate"))
        if certificate.calibration_date:
            end_perf.text = certificate.calibration_date.isoformat()
        else:
            end_perf.text = datetime.now().date().isoformat()
        
        # Performance location (default)
        perf_loc = etree.SubElement(core, self._dcc("performanceLocation"))
        perf_loc.text = "laboratory"
        
        # Items section
        items = etree.SubElement(admin, self._dcc("items"))
        item = etree.SubElement(items, self._dcc("item"))
        
        # Item name
        self._create_text_element(item, "name", certificate.equipment.name)
        
        # Manufacturer
        if certificate.equipment.manufacturer:
            manufacturer = etree.SubElement(item, self._dcc("manufacturer"))
            self._create_text_element(manufacturer, "name", certificate.equipment.manufacturer)
            
        # Model
        if certificate.equipment.model:
            model = etree.SubElement(item, self._dcc("model"))
            model.text = certificate.equipment.model
            
        # Serial number
        if certificate.equipment.serial_number:
            identifications = etree.SubElement(item, self._dcc("identifications"))
            ident = etree.SubElement(identifications, self._dcc("identification"))
            self._create_text_element(ident, "issuer", "manufacturer")
            self._create_text_element(ident, "value", certificate.equipment.serial_number)
            ident_type = etree.SubElement(ident, self._dcc("type"))
            ident_type.text = "serialNumber"
            
        # Calibration laboratory
        cal_lab = etree.SubElement(admin, self._dcc("calibrationLaboratory"))
        contact = etree.SubElement(cal_lab, self._dcc("contact"))
        self._create_text_element(contact, "name", certificate.calibration_laboratory.name)
        
        if certificate.calibration_laboratory.address:
            addr = certificate.calibration_laboratory.address
            location = etree.SubElement(contact, self._dcc("location"))
            
            if addr.street:
                street = etree.SubElement(location, self._dcc("street"))
                street.text = addr.street
                
            if addr.city:
                city = etree.SubElement(location, self._dcc("city"))
                city.text = addr.city
                
            if addr.postal_code:
                post_code = etree.SubElement(location, self._dcc("postCode"))
                post_code.text = addr.postal_code
                
            if addr.country_code:
                country = etree.SubElement(location, self._dcc("countryCode"))
                country.text = addr.country_code
                
        # Customer information
        if certificate.customer:
            customer = etree.SubElement(admin, self._dcc("respPersons"))
            resp_person = etree.SubElement(customer, self._dcc("respPerson"))
            person = etree.SubElement(resp_person, self._dcc("person"))
            self._create_text_element(person, "name", certificate.customer.name)
            
            # Role
            role = etree.SubElement(resp_person, self._dcc("role"))
            role.text = "customer"
            
        return admin
        
    def _create_measurement_results(
        self,
        parent: etree.Element,
        certificate: CalibrationCertificate
    ) -> etree.Element:
        """Create the measurementResults section.
        
        Args:
            parent: Parent element
            certificate: Certificate data
            
        Returns:
            Created element
        """
        results_section = etree.SubElement(parent, self._dcc("measurementResults"))
        
        # Add measurement results
        result = etree.SubElement(results_section, self._dcc("measurementResult"))
        
        # Result name
        self._create_text_element(result, "name", "Calibration Results")
        
        # Used methods/procedures
        if certificate.measurement_procedure:
            methods = etree.SubElement(result, self._dcc("usedMethods"))
            method = etree.SubElement(methods, self._dcc("usedMethod"))
            self._create_text_element(method, "name", certificate.measurement_procedure)
            
        # Environmental conditions if present
        if certificate.environmental_conditions:
            self._add_influence_conditions(result, certificate.environmental_conditions)
            
        # Data section with results
        data = etree.SubElement(result, self._dcc("data"))
        data_list = etree.SubElement(data, self._dcc("list"))
        
        for i, meas_result in enumerate(certificate.measurement_results, 1):
            self._add_measurement_quantity(data_list, meas_result, i)
            
        return results_section
        
    def _add_influence_conditions(
        self,
        parent: etree.Element,
        conditions: EnvironmentalConditions
    ) -> etree.Element:
        """Add influence conditions (environmental conditions) to the result.
        
        Args:
            parent: Parent element
            conditions: Environmental conditions
            
        Returns:
            Created element
        """
        influence = etree.SubElement(parent, self._dcc("influenceConditions"))
        
        if conditions.temperature:
            temp_elem = etree.SubElement(influence, self._dcc("influenceCondition"))
            temp_elem.set("refId", "temperature")
            self._create_text_element(temp_elem, "name", "Ambient Temperature")
            
            data = etree.SubElement(temp_elem, self._dcc("data"))
            quantity = etree.SubElement(data, self._dcc("quantity"))
            self._create_value_element(quantity, conditions.temperature)
            
        if conditions.humidity:
            humid_elem = etree.SubElement(influence, self._dcc("influenceCondition"))
            humid_elem.set("refId", "humidity")
            self._create_text_element(humid_elem, "name", "Relative Humidity")
            
            data = etree.SubElement(humid_elem, self._dcc("data"))
            quantity = etree.SubElement(data, self._dcc("quantity"))
            self._create_value_element(quantity, conditions.humidity)
            
        if conditions.pressure:
            pressure_elem = etree.SubElement(influence, self._dcc("influenceCondition"))
            pressure_elem.set("refId", "pressure")
            self._create_text_element(pressure_elem, "name", "Atmospheric Pressure")
            
            data = etree.SubElement(pressure_elem, self._dcc("data"))
            quantity = etree.SubElement(data, self._dcc("quantity"))
            self._create_value_element(quantity, conditions.pressure)
            
        return influence
        
    def _add_measurement_quantity(
        self,
        parent: etree.Element,
        result: MeasurementResult,
        index: int
    ) -> etree.Element:
        """Add a measurement quantity to the data list.
        
        Args:
            parent: Parent element (list)
            result: MeasurementResult object
            index: Result index for refId
            
        Returns:
            Created element
        """
        quantity = etree.SubElement(parent, self._dcc("quantity"))
        quantity.set("refId", f"measurement_{index}")
        
        # Name of the measured quantity
        self._create_text_element(quantity, "name", result.name)
        
        # Create SI real element for the measured value
        self._create_value_element(quantity, result.measured_value)
        
        # Add reference value if present
        if result.reference_value:
            ref_quantity = etree.SubElement(parent, self._dcc("quantity"))
            ref_quantity.set("refId", f"reference_{index}")
            self._create_text_element(ref_quantity, "name", f"{result.name} (Reference)")
            self._create_value_element(ref_quantity, result.reference_value)
            
        # Add deviation if present
        if result.deviation:
            dev_quantity = etree.SubElement(parent, self._dcc("quantity"))
            dev_quantity.set("refId", f"deviation_{index}")
            self._create_text_element(dev_quantity, "name", f"{result.name} (Deviation)")
            self._create_value_element(dev_quantity, result.deviation)
            
        return quantity
        
    def generate(
        self,
        certificate: CalibrationCertificate,
        include_raw_text: bool = False
    ) -> etree.Element:
        """Generate a DCC XML document from a calibration certificate.
        
        Args:
            certificate: CalibrationCertificate object
            include_raw_text: Whether to include the raw OCR text in comments
            
        Returns:
            lxml Element representing the DCC document
        """
        # Create root element
        root = etree.Element(
            self._dcc("digitalCalibrationCertificate"),
            nsmap=NSMAP
        )
        
        # Set schema location
        root.set(
            f"{{{XSI_NS}}}schemaLocation",
            self.SCHEMA_LOCATION
        )
        
        # Add administrative data
        self._create_administrative_data(root, certificate)
        
        # Add measurement results
        self._create_measurement_results(root, certificate)
        
        # Add comments section if needed
        if certificate.remarks or (include_raw_text and certificate.raw_text):
            comments = etree.SubElement(root, self._dcc("comment"))
            
            if certificate.remarks:
                self._create_text_element(comments, "content", certificate.remarks)
                
            if include_raw_text and certificate.raw_text:
                raw_comment = etree.SubElement(comments, self._dcc("content"))
                raw_comment.set("lang", certificate.language)
                raw_comment.text = f"Raw extracted text:\n{certificate.raw_text[:2000]}"
                
        return root
        
    def to_string(
        self,
        certificate: CalibrationCertificate,
        pretty_print: bool = True,
        include_raw_text: bool = False
    ) -> str:
        """Generate DCC XML as a string.
        
        Args:
            certificate: CalibrationCertificate object
            pretty_print: Whether to format the XML
            include_raw_text: Whether to include raw OCR text
            
        Returns:
            XML document as string
        """
        root = self.generate(certificate, include_raw_text)
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_body = etree.tostring(
            root,
            pretty_print=pretty_print,
            encoding="unicode"
        )
        return xml_declaration + xml_body
        
    def to_file(
        self,
        certificate: CalibrationCertificate,
        output_path: str,
        pretty_print: bool = True,
        include_raw_text: bool = False
    ) -> None:
        """Write DCC XML to a file.
        
        Args:
            certificate: CalibrationCertificate object
            output_path: Path to output file
            pretty_print: Whether to format the XML
            include_raw_text: Whether to include raw OCR text
        """
        xml_content = self.to_string(certificate, pretty_print, include_raw_text)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        logger.info(f"DCC XML written to {output_path}")
