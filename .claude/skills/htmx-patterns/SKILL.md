---
name: htmx-patterns
description: HTMX patterns for Django including partial templates, form handling, response headers, and progressive enhancement. Use when building interactive views, handling HTMX requests, or creating dynamic page updates.
---

# HTMX Patterns for Django

## Core Philosophy

- Server renders HTML fragments, not JSON
- Partial templates (`_partial.html`) for HTMX responses
- Progressive enhancement — pages work without JS, HTMX enhances UX
- Minimal client-side complexity — let the server do the heavy lifting

## HTMX Detection in Views

With `django-htmx` middleware installed, use `request.htmx`:

```python
def my_view(request):
    context = {...}
    if request.htmx:
        return render(request, "app/_partial.html", context)
    return render(request, "app/full_page.html", context)
```

## Form Handling Pattern

```python
def create_view(request):
    if request.method == "POST":
        form = MyForm(request.POST)
        if form.is_valid():
            obj = form.save()
            if request.htmx:
                return render(request, "app/_item.html", {"item": obj})
            return redirect("app:list")
        # Return form WITH errors for HTMX
        if request.htmx:
            return render(request, "app/_form.html", {"form": form})
    else:
        form = MyForm()
    return render(request, "app/create.html", {"form": form})
```

## Template Organization

- **Partials**: `_partial.html` (underscore prefix) — HTML fragments only
- **Full pages**: `page.html` — extends `base.html`, includes partials
- Each partial = one logical UI component

## CSRF Configuration

Add to `<body>` tag in base template — all HTMX requests include it automatically:
```html
<body hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
```

## Response Headers

| Header | Purpose | Example |
|--------|---------|---------|
| `HX-Trigger` | Trigger client-side events | `response["HX-Trigger"] = "applicationCreated"` |
| `HX-Redirect` | Client-side redirect | `response["HX-Redirect"] = reverse("app:detail", args=[obj.pk])` |
| `HX-Retarget` | Override target from server | `response["HX-Retarget"] = "#main"` |
| `HX-Refresh` | Force full page refresh | `response["HX-Refresh"] = "true"` |

## UX Requirements

- **Always use `hx-indicator`** for loading states
- **Always use `hx-disabled-elt="this"`** to prevent double submissions
- **Always return form errors** in partial templates on validation failure
- **Always provide feedback** via Django messages or response content

## Common Pitfalls

- Missing loading indicators — users click multiple times
- Returning full pages instead of partials for HTMX requests
- Not handling form errors — only handling the success case
- N+1 queries — HTMX views need `select_related()` / `prefetch_related()` too
