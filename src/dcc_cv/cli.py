"""Command Line Interface for DCC CV Agent.

This module provides a command-line interface for processing
calibration certificates and generating DCC XML files.
"""

import argparse
import logging
import sys
from pathlib import Path

from .agent import DCCAgent, create_lab_info


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the CLI."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main() -> int:
    """Main entry point for the CLI.
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = argparse.ArgumentParser(
        description="Convert calibration certificates to PTB DCC XML format",
        prog="dcc-cv"
    )
    
    # Input/output arguments
    parser.add_argument(
        "input",
        type=str,
        help="Input file (PDF or image) or directory containing files"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output XML file or directory (default: same as input with .xml extension)"
    )
    
    # Processing options
    parser.add_argument(
        "--lang",
        type=str,
        default="eng+deu",
        help="OCR language(s) for Tesseract (default: eng+deu)"
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="Include raw OCR text in the XML output"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate extracted data and report issues"
    )
    
    # Laboratory information
    parser.add_argument(
        "--lab-name",
        type=str,
        default="Calibration Laboratory",
        help="Laboratory name"
    )
    parser.add_argument(
        "--lab-street",
        type=str,
        help="Laboratory street address"
    )
    parser.add_argument(
        "--lab-city",
        type=str,
        help="Laboratory city"
    )
    parser.add_argument(
        "--lab-postal",
        type=str,
        help="Laboratory postal code"
    )
    parser.add_argument(
        "--lab-country",
        type=str,
        help="Laboratory country code (ISO 3166-1)"
    )
    parser.add_argument(
        "--lab-accreditation",
        type=str,
        help="Laboratory accreditation number"
    )
    
    # Misc options
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # Create laboratory info if provided
        lab_info = create_lab_info(
            name=args.lab_name,
            street=args.lab_street,
            city=args.lab_city,
            postal_code=args.lab_postal,
            country_code=args.lab_country,
            accreditation_number=args.lab_accreditation
        )
        
        # Initialize agent
        agent = DCCAgent(
            ocr_language=args.lang,
            default_lab_name=args.lab_name
        )
        
        input_path = Path(args.input)
        
        if not input_path.exists():
            logger.error(f"Input not found: {input_path}")
            return 1
            
        # Handle directory input (batch processing)
        if input_path.is_dir():
            output_dir = Path(args.output) if args.output else input_path / "dcc_output"
            
            # Find all supported files
            supported_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}
            input_files = [
                f for f in input_path.iterdir()
                if f.suffix.lower() in supported_extensions
            ]
            
            if not input_files:
                logger.error(f"No supported files found in {input_path}")
                return 1
                
            logger.info(f"Processing {len(input_files)} files...")
            
            results = agent.batch_process(
                input_files,
                output_dir,
                lab_info=lab_info,
                include_raw_text=args.include_raw
            )
            
            # Report results
            success_count = sum(1 for r in results.values() if not r.startswith("ERROR"))
            print(f"\nProcessed {success_count}/{len(input_files)} files successfully")
            
            for input_file, result in results.items():
                if result.startswith("ERROR"):
                    print(f"  FAILED: {input_file} - {result}")
                else:
                    print(f"  OK: {input_file} -> {result}")
                    
            return 0 if success_count == len(input_files) else 1
            
        else:
            # Single file processing
            output_path = args.output
            if not output_path:
                output_path = input_path.with_suffix('.xml')
                
            # Process the file
            xml_content = agent.process(
                input_path,
                output_path=output_path,
                lab_info=lab_info,
                include_raw_text=args.include_raw
            )
            
            # Validate if requested
            if args.validate:
                certificate = agent.extract_only(input_path)
                issues = agent.validate_certificate(certificate)
                
                if issues:
                    print("\nValidation issues:")
                    for issue in issues:
                        print(f"  - {issue}")
                else:
                    print("\nValidation passed: No issues found")
                    
            print(f"\nDCC XML written to: {output_path}")
            return 0
            
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return 1
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.error("Please install required packages: pip install -r requirements.txt")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
