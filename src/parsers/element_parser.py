"""Parser for element_metadata/*.json files."""
import json
import logging
from pathlib import Path
from typing import Union, Dict, List, Optional

from src.models import PageMetadata, UIElement, ElementSelector, SelectorType

logger = logging.getLogger(__name__)


class ElementParser:
    """
    Parse element_metadata/*.json files into PageMetadata models.
    
    Element metadata files define:
    - UI elements on a page
    - Available selectors for each element
    - Selector stability and confidence
    """
    
    @staticmethod
    def parse(file_path: Union[str, Path]) -> PageMetadata:
        """
        Parse a single element metadata JSON file.
        
        Args:
            file_path: Path to element JSON file
            
        Returns:
            Validated PageMetadata model
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Element metadata not found: {path}")
        
        logger.info(f"Parsing element metadata: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Parse elements
        elements = []
        for elem_data in data.get('elements', []):
            element = ElementParser._parse_element(elem_data)
            elements.append(element)
        
        # Create PageMetadata
        page = PageMetadata(
            page_name=data.get('page_name', path.stem),
            page_url=data.get('page_url'),
            description=data.get('description'),
            elements=elements,
            extracted_from=data.get('extracted_from')
        )
        
        logger.info(
            f"Loaded page: {page.page_name} "
            f"({len(elements)} elements)"
        )
        
        return page
    
    @staticmethod
    def _parse_element(data: dict) -> UIElement:
        """Parse a single element from JSON."""
        selectors = []
        
        # Parse selectors
        for sel_data in data.get('selectors', []):
            try:
                # Support both 'selector_type' and 'type' keys for flexibility
                raw_type = sel_data.get('selector_type') or sel_data.get('type', 'css')
                selector_type = SelectorType(raw_type)
            except ValueError:
                # Handle unknown selector types
                selector_type = SelectorType.CSS
                logger.warning(f"Unknown selector type: {raw_type}")
            
            selector = ElementSelector(
                selector_type=selector_type,
                value=sel_data.get('value', ''),
                confidence=sel_data.get('confidence', 1.0),
                is_stable=sel_data.get('is_stable', True)
            )
            selectors.append(selector)
        
        # Also check for shorthand selectors (id, name, css, xpath as direct keys)
        for key in ['id', 'name', 'css', 'xpath', 'data-testid', 'aria-label']:
            if key in data and data[key]:
                try:
                    selector_type = SelectorType(key)
                except ValueError:
                    continue
                
                # Check if we already have this selector
                existing = [s for s in selectors if s.selector_type == selector_type]
                if not existing:
                    selector = ElementSelector(
                        selector_type=selector_type,
                        value=data[key],
                        confidence=1.0 if key in ['id', 'data-testid'] else 0.8,
                        is_stable=key not in ['xpath']
                    )
                    selectors.append(selector)
        
        return UIElement(
            name=data.get('name', 'unnamed_element'),
            description=data.get('description'),
            element_type=data.get('element_type', 'element'),
            selectors=selectors,
            is_required=data.get('is_required', False),
            wait_strategy=data.get('wait_strategy')
        )
    
    @staticmethod
    def parse_directory(
        directory: Union[str, Path],
        file_pattern: str = "*.json"
    ) -> Dict[str, PageMetadata]:
        """
        Parse all element metadata files in a directory.
        
        Args:
            directory: Path to element_metadata directory
            file_pattern: Glob pattern for files (default: *.json)
            
        Returns:
            Dict mapping page_name -> PageMetadata
        """
        dir_path = Path(directory)
        
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {dir_path}")
        
        if not dir_path.is_dir():
            raise ValueError(f"Not a directory: {dir_path}")
        
        pages = {}
        files = list(dir_path.glob(file_pattern))
        
        logger.info(f"Found {len(files)} element metadata files in {dir_path}")
        
        for file_path in files:
            try:
                page = ElementParser.parse(file_path)
                pages[page.page_name] = page
            except Exception as e:
                logger.error(f"Failed to parse {file_path}: {e}")
        
        return pages
    
    @staticmethod
    def find_unstable_selectors(page: PageMetadata) -> List[dict]:
        """
        Find selectors that may be unstable (CSS hashes, long XPaths, etc).
        
        Args:
            page: PageMetadata to analyze
            
        Returns:
            List of dicts with element_name, selector, and risk_reason
        """
        risks = []
        
        for element in page.elements:
            for selector in element.selectors:
                risk_reason = None
                
                # Check for CSS module hash
                if selector.is_css_module_hash():
                    risk_reason = "CSS module hash may change on rebuild"
                
                # Check for long XPath
                elif selector.selector_type == SelectorType.XPATH:
                    if len(selector.value) > 100 or selector.value.count('/') > 5:
                        risk_reason = "Long/deep XPath is fragile"
                
                # Check for index-based selectors
                elif '[' in selector.value and any(
                    c.isdigit() for c in selector.value.split('[')[-1]
                ):
                    if ':nth-child' in selector.value or ':eq(' in selector.value:
                        risk_reason = "Index-based selector may break if order changes"
                
                # Low confidence
                elif selector.confidence < 0.7:
                    risk_reason = f"Low confidence selector ({selector.confidence})"
                
                if risk_reason:
                    risks.append({
                        'element_name': element.name,
                        'selector_type': selector.selector_type.value,
                        'selector_value': selector.value,
                        'risk_reason': risk_reason
                    })
        
        return risks
    
    @staticmethod
    def get_summary(directory: Union[str, Path]) -> dict:
        """
        Get summary of all element metadata in a directory.
        
        Args:
            directory: Path to element_metadata directory
            
        Returns:
            Dict with summary stats
        """
        pages = ElementParser.parse_directory(directory)
        
        total_elements = 0
        total_selectors = 0
        selector_types = {}
        
        for page in pages.values():
            total_elements += len(page.elements)
            for elem in page.elements:
                total_selectors += len(elem.selectors)
                for sel in elem.selectors:
                    sel_type = sel.selector_type.value
                    selector_types[sel_type] = selector_types.get(sel_type, 0) + 1
        
        return {
            'total_pages': len(pages),
            'total_elements': total_elements,
            'total_selectors': total_selectors,
            'selector_types': selector_types,
            'page_names': list(pages.keys())
        }
