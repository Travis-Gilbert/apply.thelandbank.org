---
name: pytest-django-patterns
description: pytest-django testing patterns, Factory Boy, fixtures, and TDD workflow. Use when writing tests, creating test factories, or following TDD red-green-refactor cycle.
---

# pytest-django Testing Patterns

## TDD Workflow (RED-GREEN-REFACTOR)

1. **RED**: Write a failing test first that describes desired behavior
2. **GREEN**: Write minimal code to make the test pass
3. **REFACTOR**: Clean up code while keeping tests green
4. **REPEAT**: Never write production code without a failing test

## Essential Patterns

### Database Access
- Use `@pytest.mark.django_db` on any test touching the database
- Apply to entire module: `pytestmark = pytest.mark.django_db`

### Factory Boy for Test Data
- `factory.Sequence()` for unique fields
- `factory.Faker()` for realistic fake data
- `factory.SubFactory()` for foreign keys
- `@factory.post_generation` for M2M relationships

### Test Organization
```
tests/
├── apps/
│   └── applications/
│       ├── test_models.py
│       ├── test_views.py
│       └── test_forms.py
├── factories.py
└── conftest.py
```

## What to Test

### Views
- Status codes (200, 404, 302)
- Authentication/authorization
- Context data
- Side effects (DB changes, emails)

### Forms
- Valid data passes, invalid fails with correct errors
- Edge cases (empty fields, max lengths)
- Custom `clean()` methods

### Models
- `__str__`, custom methods
- Custom managers/QuerySets
- Database constraints

## Running Tests

```bash
pytest                          # All tests
pytest -x                       # Stop on first failure
pytest --lf                     # Run last failed
pytest -k "test_name"           # Run matching pattern
pytest --cov=applications       # With coverage
```

## Common Pitfalls
- Forgetting `@pytest.mark.django_db`
- Creating instances manually instead of using factories
- Testing implementation details instead of behavior
- Writing tests after code (defeats TDD purpose)
