"""Parser for testcases.csv files."""
import csv
import logging
from pathlib import Path
from typing import Union, List, Optional

from src.models import TestCaseRow

logger = logging.getLogger(__name__)


class CSVParser:
    """
    Parse testcases.csv into TestCaseRow models.
    
    Expected CSV format:
    - Headers in first row
    - Pipe-delimited fields for steps and test_data
    - Required columns: test_id, test_name, module, steps, expected_result
    """
    
    # Required columns
    REQUIRED_COLUMNS = {'test_id', 'test_name', 'module', 'steps', 'expected_result'}
    
    # Optional columns with defaults
    OPTIONAL_COLUMNS = {
        'priority': 'P1',
        'preconditions': '',
        'test_data': '',
        'tags': '',
        'page_name': ''
    }
    
    @staticmethod
    def parse(
        file_path: Union[str, Path],
        module_filter: Optional[str] = None
    ) -> List[TestCaseRow]:
        """
        Parse a testcases.csv file.
        
        Args:
            file_path: Path to testcases.csv
            module_filter: Optional module name to filter by
            
        Returns:
            List of validated TestCaseRow models
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If required columns are missing
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Test cases file not found: {path}")
        
        logger.info(f"Parsing test cases: {path}")
        
        test_cases = []
        errors = []
        
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Validate headers
            if reader.fieldnames is None:
                raise ValueError("CSV file is empty or has no headers")
            
            headers = set(reader.fieldnames)
            missing = CSVParser.REQUIRED_COLUMNS - headers
            
            if missing:
                raise ValueError(f"Missing required columns: {missing}")
            
            # Parse rows
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                try:
                    # Build test case with defaults for missing optional fields
                    test_data = {}
                    
                    for col in CSVParser.REQUIRED_COLUMNS:
                        value = row.get(col, '').strip()
                        if not value:
                            raise ValueError(f"Required field '{col}' is empty")
                        test_data[col] = value
                    
                    for col, default in CSVParser.OPTIONAL_COLUMNS.items():
                        test_data[col] = row.get(col, default).strip() or default
                    
                    # Create and validate model
                    test_case = TestCaseRow(**test_data)
                    
                    # Apply module filter if specified
                    if module_filter and test_case.module != module_filter:
                        continue
                    
                    test_cases.append(test_case)
                    
                except Exception as e:
                    error_msg = f"Row {row_num}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
        
        if errors:
            logger.warning(f"Parsed with {len(errors)} errors")
        
        logger.info(
            f"Loaded {len(test_cases)} test cases"
            f"{f' (filtered by module: {module_filter})' if module_filter else ''}"
        )
        
        return test_cases
    
    @staticmethod
    def parse_string(csv_content: str) -> List[TestCaseRow]:
        """
        Parse CSV content from a string.
        
        Args:
            csv_content: CSV content as string
            
        Returns:
            List of validated TestCaseRow models
        """
        import io
        
        test_cases = []
        reader = csv.DictReader(io.StringIO(csv_content))
        
        for row in reader:
            test_data = {}
            
            for col in CSVParser.REQUIRED_COLUMNS:
                test_data[col] = row.get(col, '').strip()
            
            for col, default in CSVParser.OPTIONAL_COLUMNS.items():
                test_data[col] = row.get(col, default).strip() or default
            
            test_cases.append(TestCaseRow(**test_data))
        
        return test_cases
    
    @staticmethod
    def get_modules(file_path: Union[str, Path]) -> List[str]:
        """
        Get list of unique modules in the CSV.
        
        Args:
            file_path: Path to testcases.csv
            
        Returns:
            List of unique module names
        """
        path = Path(file_path)
        modules = set()
        
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                module = row.get('module', '').strip()
                if module:
                    modules.add(module)
        
        return sorted(modules)
    
    @staticmethod
    def get_summary(file_path: Union[str, Path]) -> dict:
        """
        Get summary statistics for the CSV.
        
        Args:
            file_path: Path to testcases.csv
            
        Returns:
            Dict with summary stats
        """
        test_cases = CSVParser.parse(file_path)
        
        modules = {}
        priorities = {}
        
        for tc in test_cases:
            modules[tc.module] = modules.get(tc.module, 0) + 1
            priorities[tc.priority] = priorities.get(tc.priority, 0) + 1
        
        return {
            'total_test_cases': len(test_cases),
            'modules': modules,
            'priorities': priorities,
            'unique_modules': len(modules)
        }
