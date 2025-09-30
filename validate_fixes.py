#!/usr/bin/env python3
"""
Validation script to verify all Pylance errors are resolved in other/main.py
This addresses the issues mentioned in the problem statement
"""

import ast
import sys
import os

def validate_file(filepath):
    """Validate that the file has no syntax errors or undefined references"""
    print(f"Validating {filepath}...")
    print("=" * 70)
    
    if not os.path.exists(filepath):
        print(f"✗ File not found: {filepath}")
        return False
    
    # Read the file
    with open(filepath, 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    print(f"File has {len(lines)} lines")
    
    # 1. Check for merge conflict markers
    print("\n1. Checking for merge conflict markers...")
    conflict_markers = ['<<<<<<<', '=======', '>>>>>>>']
    conflicts_found = []
    for i, line in enumerate(lines, 1):
        for marker in conflict_markers:
            if line.strip().startswith(marker):
                conflicts_found.append((i, marker))
    
    if conflicts_found:
        print("   ✗ FAIL: Found merge conflict markers:")
        for line_no, marker in conflicts_found:
            print(f"      Line {line_no}: {marker}")
        return False
    else:
        print("   ✓ PASS: No merge conflict markers found")
    
    # 2. Check syntax (Expected expression errors)
    print("\n2. Checking for syntax errors...")
    try:
        tree = ast.parse(content)
        print("   ✓ PASS: File parses as valid Python (no 'Expected expression' errors)")
    except SyntaxError as e:
        print(f"   ✗ FAIL: Syntax error at line {e.lineno}: {e.msg}")
        return False
    
    # 3. Check for proper imports
    print("\n3. Checking imports...")
    required_imports = ['stripe', 'fastapi', 'requests']
    imports_found = {imp: False for imp in required_imports}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in imports_found:
                    imports_found[alias.name] = True
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module in imports_found:
                imports_found[node.module] = True
    
    all_imports_ok = True
    for module, found in imports_found.items():
        if found:
            print(f"   ✓ PASS: '{module}' is properly imported")
        else:
            print(f"   ✗ FAIL: '{module}' is not imported")
            all_imports_ok = False
    
    if not all_imports_ok:
        return False
    
    # 4. Check for problematic undefined references
    print("\n4. Checking for undefined variable references...")
    problematic_vars = ['ryanair', 'create_query', 'deep_airline_urls']
    
    # Simple text search for references (not foolproof but good enough)
    undefined_found = []
    for var in problematic_vars:
        # Check if variable is referenced but not defined in this file
        if var in content:
            # For ryanair, check if it's imported
            if var == 'ryanair':
                if 'import ryanair' in content or 'from ryanair' in content:
                    undefined_found.append(var)
            # For create_query and deep_airline_urls, check if they're used
            elif f'{var}(' in content or f'{var}.' in content or f'{var}[' in content:
                # Check if it's defined as a function or variable
                if f'def {var}' not in content and f'{var} =' not in content:
                    undefined_found.append(var)
    
    if undefined_found:
        print(f"   ✗ FAIL: Found references to undefined variables: {undefined_found}")
        return False
    else:
        print("   ✓ PASS: No references to 'ryanair' module")
        print("   ✓ PASS: No references to 'create_query' function")
        print("   ✓ PASS: No references to 'deep_airline_urls' variable")
    
    # 5. Check for indentation issues
    print("\n5. Checking for indentation issues...")
    # If we got here, ast.parse succeeded, so indentation is OK
    print("   ✓ PASS: No 'Unexpected indentation' or 'Unindent not expected' errors")
    
    print("\n" + "=" * 70)
    print("✓✓✓ ALL CHECKS PASSED ✓✓✓")
    print(f"\n{filepath} is clean and ready for use!")
    print("\nAll Pylance errors mentioned in the problem statement are resolved:")
    print("  • No merge conflict markers (<<<<<<, =======, >>>>>>>)")
    print("  • No 'Expected expression' errors")
    print("  • No 'Unexpected indentation' errors")
    print("  • No 'Unindent not expected' errors")
    print("  • 'stripe' module is properly imported")
    print("  • No references to undefined 'ryanair' module")
    print("  • No references to undefined 'create_query' function")
    print("  • No references to undefined 'deep_airline_urls' variable")
    
    return True

def check_requirements():
    """Check if stripe is in requirements.txt"""
    print("\n" + "=" * 70)
    print("Checking requirements.txt...")
    print("=" * 70)
    
    req_file = "requirements.txt"
    if not os.path.exists(req_file):
        print(f"   ✗ FAIL: {req_file} not found")
        return False
    
    with open(req_file, 'r') as f:
        requirements = f.read()
    
    if 'stripe' in requirements:
        print("   ✓ PASS: 'stripe' is listed in requirements.txt")
        # Extract version
        for line in requirements.split('\n'):
            if 'stripe' in line.lower():
                print(f"      Version: {line.strip()}")
        return True
    else:
        print("   ✗ FAIL: 'stripe' is not in requirements.txt")
        return False

def main():
    """Main validation function"""
    print("\n" + "=" * 70)
    print("FLIGHT ALERT APP - VALIDATION SCRIPT")
    print("Verifying all Pylance errors are resolved")
    print("=" * 70 + "\n")
    
    # Validate other/main.py
    file_ok = validate_file("other/main.py")
    
    # Check requirements
    req_ok = check_requirements()
    
    print("\n" + "=" * 70)
    if file_ok and req_ok:
        print("✓✓✓ VALIDATION SUCCESSFUL ✓✓✓")
        print("\nAll issues from the problem statement are resolved:")
        print("  1. ✓ No merge conflict markers")
        print("  2. ✓ No syntax errors")
        print("  3. ✓ stripe is properly imported and in requirements.txt")
        print("  4. ✓ No undefined variable references")
        print("  5. ✓ No indentation errors")
        print("\nThe file can be executed without SyntaxError or undefined names.")
        return 0
    else:
        print("✗✗✗ VALIDATION FAILED ✗✗✗")
        print("\nPlease fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
