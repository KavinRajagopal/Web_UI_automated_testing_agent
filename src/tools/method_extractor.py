"""AST-based method extraction and signature parsing utilities."""

import ast
import logging
from typing import Dict, List, Any, Optional, Set, Tuple

logger = logging.getLogger(__name__)


def extract_method_signatures(code: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract full method signatures from Python code using AST.
    
    Args:
        code: Python code string
        
    Returns:
        Dict mapping class_name -> {method_name: {params, returns, docstring, line}}
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        logger.warning(f"Syntax error parsing code: {e}")
        return {}
    
    signatures_by_class = {}
    
    # Iterate through top-level nodes to preserve class structure
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            signatures_by_class[class_name] = {}
            
            # Extract methods from this class
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    params = []
                    for arg in item.args.args:
                        if arg.arg != 'self':  # Skip self parameter
                            param_info = {
                                "name": arg.arg,
                                "type": None,
                                "default": None
                            }
                            # Extract type hints if available
                            if arg.annotation:
                                try:
                                    if hasattr(ast, 'unparse'):
                                        param_info["type"] = ast.unparse(arg.annotation)
                                    else:
                                        # Python < 3.9 fallback
                                        param_info["type"] = str(arg.annotation)
                                except Exception:
                                    param_info["type"] = str(arg.annotation)
                            params.append(param_info)
                    
                    return_type = None
                    if item.returns:
                        try:
                            if hasattr(ast, 'unparse'):
                                return_type = ast.unparse(item.returns)
                            else:
                                return_type = str(item.returns)
                        except Exception:
                            return_type = str(item.returns)
                    
                    signatures_by_class[class_name][item.name] = {
                        "params": params,
                        "returns": return_type,
                        "docstring": ast.get_docstring(item),
                        "line": item.lineno
                    }
    
    return signatures_by_class


def extract_method_names(code: str) -> Dict[str, List[str]]:
    """
    Extract method names from Python code (simpler version).
    
    Args:
        code: Python code string
        
    Returns:
        Dict mapping class_name -> [method_names]
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {}
    
    methods_by_class = {}
    
    # Iterate through top-level nodes to preserve class structure
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            methods_by_class[class_name] = []
            
            # Extract methods from this class
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    if item.name != '__init__':  # Skip constructors
                        methods_by_class[class_name].append(item.name)
    
    return methods_by_class


def extract_method_calls(code: str) -> List[Dict[str, Any]]:
    """
    Extract method calls from Python code.
    
    Args:
        code: Python code string
        
    Returns:
        List of {class_name, method_name, line, context}
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    
    method_calls = []
    
    def visit_node(node, context=""):
        """Recursively visit AST nodes to find method calls."""
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                method_name = node.func.attr
                
                # Try to identify the object/class
                obj_name = None
                if isinstance(node.func.value, ast.Name):
                    obj_name = node.func.value.id
                elif isinstance(node.func.value, ast.Attribute):
                    # Handle chained calls like self.page.method()
                    if isinstance(node.func.value.value, ast.Name):
                        obj_name = node.func.value.value.id
                    obj_name = node.func.value.attr
                elif isinstance(node.func.value, ast.Call):
                    # Handle cases like LoginPage(driver).method()
                    if isinstance(node.func.value.func, ast.Name):
                        obj_name = node.func.value.func.id
                
                method_calls.append({
                    "class_name": obj_name,
                    "method_name": method_name,
                    "line": node.lineno,
                    "context": context
                })
        
        # Recursively visit child nodes
        for child in ast.iter_child_nodes(node):
            visit_node(child, context)
    
    visit_node(tree)
    return method_calls


def extract_page_object_structure(code: str) -> Dict[str, Any]:
    """
    Extract page object structure information.
    
    Args:
        code: Python code string
        
    Returns:
        Dict with structure info: {inherits_base, has_locators, required_methods, ...}
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"valid": False, "error": "Syntax error"}
    
    structure = {
        "valid": True,
        "class_name": None,
        "inherits_base": False,
        "has_locators": False,
        "methods": [],
        "required_methods": {
            "is_page_loaded": False,
            "is_on_page": False
        }
    }
    
    # Iterate through top-level nodes (not using walk to preserve structure)
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            structure["class_name"] = node.name
            
            # Check inheritance
            for base in node.bases:
                if isinstance(base, ast.Name):
                    if "BasePage" in base.id:
                        structure["inherits_base"] = True
                elif isinstance(base, ast.Attribute):
                    # Try to get the attribute name
                    try:
                        if hasattr(ast, 'unparse'):
                            base_str = ast.unparse(base)
                        else:
                            # Fallback for Python < 3.9
                            base_str = base.attr if hasattr(base, 'attr') else str(base)
                        if "BasePage" in base_str:
                            structure["inherits_base"] = True
                    except:
                        if hasattr(base, 'attr') and "BasePage" in base.attr:
                            structure["inherits_base"] = True
            
            # Check for locators (class attributes)
            for item in node.body:
                if isinstance(item, ast.Assign):
                    # Check if it's a locator (tuple assignment or By.X pattern)
                    structure["has_locators"] = True
                
                if isinstance(item, ast.FunctionDef):
                    structure["methods"].append(item.name)
                    if item.name in structure["required_methods"]:
                        structure["required_methods"][item.name] = True
    
    return structure


def extract_methods_from_files(generated_files: Dict[str, str]) -> Dict[str, Dict[str, List[str]]]:
    """
    Extract methods from all page object files.
    
    Args:
        generated_files: Dict of filepath -> code
        
    Returns:
        Dict mapping filepath -> {class_name: [method_names]}
    """
    all_methods = {}
    
    for filepath, code in generated_files.items():
        if filepath.startswith("pages/") and filepath.endswith(".py") and "base_page" not in filepath:
            methods = extract_method_names(code)
            if methods:
                all_methods[filepath] = methods
    
    return all_methods


def find_missing_methods(
    test_code: str,
    page_methods: Dict[str, List[str]],
    page_imports: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Find method calls in test code that don't exist in page objects.
    
    Args:
        test_code: Test file code
        page_methods: Dict mapping page_file -> {class_name: [methods]}
        page_imports: Dict mapping import_name -> page_file
        
    Returns:
        List of {class_name, method_name, line, available_methods}
    """
    missing = []
    calls = extract_method_calls(test_code)
    
    for call in calls:
        class_name = call["class_name"]
        method_name = call["method_name"]
        
        # Find which page file this class belongs to
        page_file = None
        for import_name, file_path in page_imports.items():
            if class_name and class_name.lower() in import_name.lower():
                page_file = file_path
                break
        
        if page_file and page_file in page_methods:
            class_methods = page_methods[page_file]
            # Check all classes in this page file
            found = False
            available_methods = []
            
            for cls_name, methods in class_methods.items():
                if class_name and class_name.lower() == cls_name.lower():
                    if method_name in methods:
                        found = True
                    else:
                        available_methods = methods
                    break
            
            if not found and class_name:
                missing.append({
                    "class_name": class_name,
                    "method_name": method_name,
                    "line": call["line"],
                    "page_file": page_file,
                    "available_methods": available_methods
                })
    
    return missing
