---
name: django-forms
description: Django form patterns including ModelForm, validation, HTMX form handling, and formsets. Use when creating forms, implementing validation, or handling form submissions.
---

# Django Form Patterns

## Core Principle: ModelForm First

Use `ModelForm` for any form backed by a model. It handles field generation, validation, and saving automatically.

## Validation

### Field-Level Validation
Use `clean_<field>()` methods for individual field validation:
- Check field-specific constraints
- Raise `ValidationError` with clear messages

### Cross-Field Validation
Use `clean()` for relationships between multiple fields:
- Always call `super().clean()` first
- Access cleaned data via `self.cleaned_data`

## View Handling Pattern

```python
def my_view(request):
    if request.method == "POST":
        form = MyForm(request.POST, request.FILES)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.created_by = request.user  # Set extra fields
            instance.save()
            return redirect("success")
    else:
        form = MyForm()
    return render(request, "template.html", {"form": form})
```

### Key Points
- Explicitly check `request.method`
- Use `commit=False` when you need to set additional fields before saving
- Always handle the GET case (empty form)
- Always display form errors in templates

## HTMX Form Handling

For async form submission without full page reload:

```python
def form_view(request):
    form = MyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        if request.headers.get("HX-Request"):
            return render(request, "partials/_success.html")
        return redirect("list")

    template = "partials/_form.html" if request.headers.get("HX-Request") else "form.html"
    return render(request, template, {"form": form})
```

## Formsets

Use `inlineformset_factory` for managing multiple related objects:
- Set `extra=0` and add "Add another" button dynamically
- Handle formset validation alongside parent form

## Common Mistakes to Avoid

- Validating in views instead of forms
- Not displaying `form.errors` in templates
- Forgetting `commit=False` when setting related fields
- Not passing `request.FILES` for file upload forms
- Skipping CSRF token in templates
