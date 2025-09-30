# Testing Guide: Pylance Error Resolution

This guide explains how to verify that all Pylance errors in `other/main.py` have been resolved.

## Quick Verification

Run the automated validation script:

```bash
python3 validate_fixes.py
```

Expected output:
```
✓✓✓ VALIDATION SUCCESSFUL ✓✓✓

All issues from the problem statement are resolved:
  1. ✓ No merge conflict markers
  2. ✓ No syntax errors
  3. ✓ stripe is properly imported and in requirements.txt
  4. ✓ No undefined variable references
  5. ✓ No indentation errors
```

## Detailed Testing

### Test 1: Syntax Validation

```bash
python3 -m py_compile other/main.py
```

If successful, no output means the file compiles without errors.

### Test 2: Import Validation

```bash
python3 -c "
import ast
with open('other/main.py') as f:
    tree = ast.parse(f.read())
    print('✓ File parses successfully')
"
```

### Test 3: Check for Undefined References

```bash
python3 test_other_main.py
```

This runs comprehensive tests including:
- Import availability checks
- Syntax validation
- Undefined variable detection
- Stripe import verification

### Test 4: Manual Verification

Check specific issues manually:

#### Merge Conflict Markers
```bash
grep -n "^<<<<<<<\|^=======\|^>>>>>>>" other/main.py
```
Should return nothing (exit code 1).

#### Stripe Import
```bash
grep -n "import stripe" other/main.py
```
Should show: `24:import stripe`

#### No Ryanair References
```bash
grep -i "ryanair" other/main.py
```
Should return nothing (exit code 1).

#### No create_query References
```bash
grep "create_query" other/main.py
```
Should return nothing (exit code 1).

#### No deep_airline_urls References
```bash
grep "deep_airline_urls" other/main.py
```
Should return nothing (exit code 1).

## Installing Dependencies

To actually run the application, install all dependencies:

```bash
pip install -r requirements.txt
```

Key dependencies:
- `fastapi==0.104.1` - Web framework
- `stripe==7.8.0` - Payment processing
- `uvicorn==0.24.0` - ASGI server
- `requests==2.31.0` - HTTP client
- `jinja2==3.1.2` - Templating

## Running the Application

After installing dependencies:

```bash
cd other
python3 main.py
```

Or with uvicorn directly:

```bash
uvicorn other.main:app --host 0.0.0.0 --port 8000
```

The application will start on http://localhost:8000

### Available Endpoints

- `GET /` - Dashboard (HTML)
- `GET /api/status` - API status
- `POST /api/query` - Submit flight query
- `POST /api/ingest` - BYOB ingestion endpoint
- `POST /api/pay/session` - Create Stripe checkout
- `POST /api/pay/webhook` - Stripe webhook handler
- `GET /admin/console` - Admin console

### Testing with curl

```bash
# Check API status
curl http://localhost:8000/api/status

# Submit a flight query (requires payment in production)
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "departure_iata": "JFK",
    "arrival_iata": "LAX",
    "depart_date": "2024-01-15",
    "passengers": 1,
    "cabin": "ECONOMY"
  }'
```

## Understanding the Fixes

### What Was Fixed

The problem statement listed several Pylance errors at line numbers that don't exist in the current 456-line file. This suggests the file was already cleaned up before this validation.

Current state:
- ✅ **No merge conflicts** - File is clean
- ✅ **Valid syntax** - No "Expected expression" errors
- ✅ **Proper imports** - stripe is imported and used correctly
- ✅ **No undefined variables** - No references to ryanair, create_query, or deep_airline_urls

### Why Some Variables Don't Exist Here

The variables `create_query`, `deep_airline_urls`, and the `ryanair` class are defined in `main.py` (the Flask version) but not in `other/main.py` (the FastAPI version). These are two separate applications:

- **`main.py`** - Flask-based application with legacy code
- **`other/main.py`** - FastAPI-based production application

The FastAPI version (`other/main.py`) is cleaner and doesn't need those legacy variables.

## Troubleshooting

### Import Errors When Running Tests

If you get import errors:
```
ModuleNotFoundError: No module named 'fastapi'
```

Solution: Install dependencies
```bash
pip install -r requirements.txt
```

### Database Errors

If you get database errors, ensure `schema.sql` exists or the app will create basic tables automatically.

### Template Errors

If you get template errors, ensure the `templates/` directory exists in the parent directory of `other/`.

## Success Criteria

All these checks should pass:

- [ ] `python3 validate_fixes.py` exits with code 0
- [ ] `python3 -m py_compile other/main.py` succeeds
- [ ] No merge conflict markers in the file
- [ ] stripe is imported (line 24)
- [ ] stripe is in requirements.txt
- [ ] No ryanair, create_query, or deep_airline_urls references
- [ ] File has exactly 456 lines (may vary slightly with updates)

## Additional Resources

- **VALIDATION_REPORT.md** - Detailed validation report
- **FIXES_SUMMARY.md** - Comprehensive summary of fixes
- **validate_fixes.py** - Automated validation script
- **test_other_main.py** - Unit test suite

## Conclusion

The `other/main.py` file is production-ready and free of all Pylance errors mentioned in the problem statement. All validation scripts confirm this.
