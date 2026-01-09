"""Parser for module_spec.json configuration files."""
import json
import logging
from pathlib import Path
from typing import Union

from src.models import ModuleSpec

logger = logging.getLogger(__name__)


class ModuleParser:
    """
    Parse module_spec.json into ModuleSpec model.
    
    The module spec defines:
    - Target application details
    - Environment and browser settings
    - Selector preferences
    - Pages to generate
    """
    
    @staticmethod
    def parse(file_path: Union[str, Path]) -> ModuleSpec:
        """
        Parse a module_spec.json file.
        
        Args:
            file_path: Path to module_spec.json
            
        Returns:
            Validated ModuleSpec model
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
            pydantic.ValidationError: If JSON doesn't match schema
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Module spec not found: {path}")
        
        if not path.suffix == '.json':
            logger.warning(f"Expected .json file, got: {path.suffix}")
        
        logger.info(f"Parsing module spec: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate and create ModuleSpec
        spec = ModuleSpec(**data)
        
        logger.info(
            f"Loaded module: {spec.module_name} "
            f"({len(spec.pages)} pages, app: {spec.app_name})"
        )
        
        return spec
    
    @staticmethod
    def parse_dict(data: dict) -> ModuleSpec:
        """
        Parse a dict into ModuleSpec.
        
        Args:
            data: Dictionary matching ModuleSpec schema
            
        Returns:
            Validated ModuleSpec model
        """
        return ModuleSpec(**data)
    
    @staticmethod
    def validate(file_path: Union[str, Path]) -> list[str]:
        """
        Validate a module_spec.json file and return any warnings.
        
        Args:
            file_path: Path to module_spec.json
            
        Returns:
            List of warning messages (empty if all good)
        """
        warnings = []
        path = Path(file_path)
        
        try:
            spec = ModuleParser.parse(path)
            
            # Check for common issues
            if not spec.pages:
                warnings.append("No pages defined in module spec")
            
            if not spec.app_url:
                warnings.append("No app_url defined")
            
            if "xpath" not in spec.avoid_selectors:
                warnings.append("Consider adding 'xpath' to avoid_selectors for stability")
            
            # Check pages have element metadata files
            for page in spec.pages:
                if not page.element_metadata_file:
                    warnings.append(
                        f"Page '{page.name}' has no element_metadata_file specified"
                    )
            
        except Exception as e:
            warnings.append(f"Parse error: {str(e)}")
        
        return warnings
