---
name: systematic-debugging
description: Four-phase debugging methodology with root cause analysis for Django. Use when investigating bugs, fixing test failures, or troubleshooting unexpected behavior.
---

# Systematic Debugging

## Core Principle: NO FIXES WITHOUT ROOT CAUSE FIRST

Never apply patches that mask underlying problems.

## Four-Phase Framework

### Phase 1: Reproduce
- Write a failing test that captures the bug
- Read error messages thoroughly
- Check recent changes with `git diff`, `git log`

### Phase 2: Isolate
- Add strategic logging
- Narrow down which component fails
- Check inputs and outputs at each step

### Phase 3: Identify Root Cause
- Read the full stack trace
- Use `breakpoint()` to inspect state
- Check what assumptions are violated

### Phase 4: Fix and Verify
1. Fix at the root cause
2. Run reproduction test (should pass)
3. Run full test suite
4. Verify manually if needed

## Django Debug Tools

### Django Debug Toolbar
```python
# settings (dev only)
INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
INTERNAL_IPS = ["127.0.0.1"]
```

### Python Debugger
```python
breakpoint()  # Stops execution here
# n(ext), s(tep), c(ontinue), p variable, q(uit)
```

### Query Debugging
```python
from django.test.utils import CaptureQueriesContext
from django.db import connection

def test_no_n_plus_one():
    with CaptureQueriesContext(connection) as ctx:
        list(Post.objects.select_related("author"))
    assert len(ctx) <= 2
```

## Common Django Issues
- **N+1 Queries**: Use `select_related()` / `prefetch_related()`
- **Form Not Saving**: Check `is_valid()`, `form.errors`, `commit=False`
- **CSRF 403**: Missing `{% csrf_token %}` in form template
- **Migration Issues**: `showmigrations`, fake migrations

## Red Flags - Stop and Reassess
- "Quick fix now, investigate later"
- Third consecutive workaround
- "This should work" without understanding why
