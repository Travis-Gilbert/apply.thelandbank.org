---
name: django-models
description: Django model design patterns emphasizing fat models/thin views, QuerySet optimization, and domain logic encapsulation. Use when designing models, optimizing queries, implementing business logic, or working with the ORM.
---

# Django Model Patterns

## Core Philosophy: Fat Models, Thin Views

**Business logic belongs in models and managers, not views.** Views orchestrate workflows; models implement domain behavior. This principle creates testable, reusable code that stays maintainable as complexity grows.

**Good**: Model methods handle business rules, state transitions, validation
**Bad**: Views contain if/else logic for domain rules, calculate derived values

## Model Design

### Structure Your Models Around Domain Concepts
- Use `TextChoices`/`IntegerChoices` for status fields and enums
- Add `get_absolute_url()` for canonical object URLs
- Include `__str__()` for readable representations
- Set proper `ordering` in Meta for consistent default sorting
- Add database indexes for frequently filtered/sorted fields
- Use abstract base models for shared fields (timestamps, soft deletes, etc.)

### Field Selection Guidelines
- Use `blank=True, default=""` for optional text fields (avoid null)
- Use `null=True, blank=True` for optional foreign keys
- For unique optional fields, use `null=True` to avoid collision issues
- Leverage `JSONField` for flexible metadata (avoid creating many optional fields)
- Set appropriate `max_length` based on actual data needs

### Encapsulate Business Logic in Model Methods
- State transitions: `application.submit()`, `application.approve()`
- Permission checks: `application.is_editable_by(user)`
- Complex calculations: `application.days_since_submission()`
- Use properties for computed read-only values
- Specify `update_fields` when saving partial changes

## QuerySet Patterns: The Power of Composition

**Custom QuerySet classes are your secret weapon.** They make queries reusable, chainable, and testable.

### Pattern: QuerySet as Manager

Define a QuerySet subclass with domain-specific filter methods.
Attach it to your model: `objects = YourQuerySet.as_manager()`
Chain methods for composable queries.

### Common QuerySet Methods
- Filtering by status/state: `.submitted()`, `.under_review()`
- Date range queries: `.recent()`, `.this_month()`
- User-scoped queries: `.assigned_to(user)`
- Combined lookups: `.pending_review()`

## Query Optimization: Avoid N+1 Queries

### The Golden Rules
1. **select_related()**: Use for ForeignKey and OneToOneField (creates SQL JOIN)
2. **prefetch_related()**: Use for ManyToManyField and reverse ForeignKeys (separate query + Python join)
3. **only()**: Load specific fields when you don't need the whole object
4. **defer()**: Exclude heavy fields (TextField, JSONField) you won't use

### Efficient Counting and Existence Checks
- Use `.exists()` instead of `if queryset:` or `if len(queryset):`
- Use `.count()` instead of `len(queryset.all())`
- Both perform database-level operations without loading objects

### Aggregation and Annotation
- `annotate()`: Add computed fields to each object (Count, Sum, Avg, etc.)
- `aggregate()`: Compute values across entire queryset
- Use `F()` expressions for database-level updates
- Combine annotate with filter for "objects with at least N related items"

## Signals: Use Sparingly

Signals create implicit coupling and make code harder to follow. **Prefer explicit method calls.**

### When Signals Make Sense
- Audit logging (track all changes to a model)
- Cache invalidation
- Decoupling apps (third-party app needs to react to your models)

### When to Avoid Signals
- Business logic that should be in model methods
- Logic tightly coupled to the calling code
- Complex workflows (use explicit service layer instead)

## Anti-Patterns to Avoid

- Iterating over objects and accessing relations without `select_related()`/`prefetch_related()`
- Using `if queryset:` instead of `.exists()`
- Business logic in views instead of models
- Overusing signals for synchronous operations
- Forgetting to add indexes for filtered/sorted fields
