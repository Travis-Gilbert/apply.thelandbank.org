# 001: Infrastructure and Component Library Setup

**Scope:** Replace Tailwind CDN with compiled build, install component libraries, establish shared patterns.
**Depends on:** Nothing (run first)
**Estimated tasks:** 8

## Context

The GCLBA Application Portal currently uses `<script src="https://cdn.tailwindcss.com">` in `base.html`. This ships the entire Tailwind runtime to every buyer visiting `/apply/`. Switching to a compiled build cuts CSS payload by ~95%, enables custom utilities, and unblocks the component library work in docs 002 and 003.

The portal has two surfaces with different audiences:
- **Buyer form** (`/apply/`): Public-facing, needs to feel trustworthy and simple
- **Staff admin** (`/admin/`): Django Unfold, needs workflow speed and clarity

Both share the same `config/settings.py`, `base.html`, and static pipeline.

## Tech Stack After This Doc

```
Existing (keep):  Django 6.0, HTMX, Django Unfold, django-htmx
Adding:           django-cotton, django-template-partials, django-crispy-forms
Replacing:        Tailwind CDN -> django-tailwind (compiled build)
```

## Task 1: Install Python Dependencies

**File:** `requirements/base.txt` (or `requirements.txt` if flat)

Add these lines:

```
django-cotton>=1.0.0
django-template-partials>=24.4
django-tailwind>=3.8.0
django-crispy-forms>=2.3
```

Run:
```bash
pip install django-cotton django-template-partials django-tailwind django-crispy-forms
```

**Verify:** `pip list | grep -E "(cotton|partials|tailwind|crispy)"` shows all four.

---

## Task 2: Initialize Tailwind App

Run:
```bash
cd county-landing-app
python manage.py tailwind init
```

When prompted for the app name, enter `theme`.

This creates `theme/` directory with `static_src/` containing `tailwind.config.js`.

**Verify:** `ls theme/static_src/tailwind.config.js` exists.

---

## Task 3: Configure Tailwind with GCLBA Tokens

**File:** `theme/static_src/tailwind.config.js`

Replace the entire file contents with:

```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    // Django templates
    "../templates/**/*.html",
    "../../templates/**/*.html",
    "../../**/templates/**/*.html",
    // Cotton components
    "../../templates/cotton/**/*.html",
    // Crispy template pack
    "../../crispy_gclba/templates/**/*.html",
  ],
  theme: {
    extend: {
      colors: {
        gclba: {
          50: "#f0fdf4",
          100: "#dcfce7",
          200: "#bbf7d0",
          300: "#86efac",
          400: "#4ade80",
          500: "#22c55e",
          600: "#16a34a",
          700: "#15803d",
          800: "#166534",
          900: "#14532d",
        },

        // Semantic status (matches Application.Status choices)
        status: {
          submitted: "#2563eb",
          "under-review": "#d97706",
          "docs-requested": "#9333ea",
          approved: "#16a34a",
          denied: "#dc2626",
          withdrawn: "#6b7280",
        },

        // Program type accent colors
        program: {
          "featured-homes": "#16a34a",
          "ready-for-rehab": "#d97706",
          vip: "#7c3aed",
          "vacant-lot": "#6b7280",
        },

        // Surface and text
        surface: {
          DEFAULT: "#ffffff",
          alt: "#f9fafb",
          muted: "#f3f4f6",
        },
        muted: "#6b7280",
      },

      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
        heading: ["Inter", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "monospace"],
      },

      borderRadius: {
        card: "8px",
        pill: "9999px",
      },

      boxShadow: {
        card: "0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)",
        "card-hover": "0 4px 12px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04)",
        focus: "0 0 0 3px rgba(22, 163, 74, 0.2)",
      },

      animation: {
        "fade-in": "fadeIn 0.2s ease-out",
        "slide-up": "slideUp 0.3s ease-out",
      },

      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
```

**Verify:** `node -e "require('./theme/static_src/tailwind.config.js')"` exits without error.

---

## Task 4: Update Django Settings

**File:** `config/settings.py`

Add to `INSTALLED_APPS` (order matters; cotton must come before template engine apps):

```python
INSTALLED_APPS = [
    # Unfold must be before django.contrib.admin
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "django_htmx",
    "django_cotton",
    "template_partials",
    "crispy_forms",
    "rest_framework",

    # Tailwind theme app
    "theme",

    # Custom crispy template pack
    "crispy_gclba",

    # Project apps
    "applications",
]

# Crispy Forms config
CRISPY_TEMPLATE_PACK = "gclba"

# Tailwind config
TAILWIND_APP_NAME = "theme"
```

Also ensure `INTERNAL_IPS` includes `"127.0.0.1"` (required by django-tailwind for dev mode):

```python
INTERNAL_IPS = ["127.0.0.1"]
```

**Verify:** `python manage.py check` reports 0 issues.

---

## Task 5: Create the Crispy GCLBA Template Pack

**Directory:** `crispy_gclba/`

Create this as a Django app in the project root (alongside `applications/`, `config/`).

**File:** `crispy_gclba/__init__.py`
```python
# Custom crispy-forms template pack for GCLBA Application Portal.
# Renders form fields with civic green focus rings, clear error states,
# and consistent label/help text treatment across all 8 application steps.
```

**File:** `crispy_gclba/templates/gclba/field.html`
```html
{% load template_partials %}

<div class="mb-5">
  {% if field.label %}
  <label
    for="{{ field.id_for_label }}"
    class="block mb-1.5 text-sm font-semibold text-gray-900"
  >
    {{ field.label }}
    {% if field.field.required %}
    <span class="text-red-500 ml-0.5" aria-hidden="true">*</span>
    {% endif %}
  </label>
  {% endif %}

  {{ field }}

  {% if field.help_text %}
  <p class="mt-1.5 text-xs text-gray-500 leading-relaxed">
    {{ field.help_text }}
  </p>
  {% endif %}

  {% if field.errors %}
  <ul class="mt-1.5 list-none p-0 m-0" role="alert">
    {% for error in field.errors %}
    <li class="text-xs text-red-600 font-medium flex items-center gap-1">
      <svg class="w-3.5 h-3.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
      </svg>
      {{ error }}
    </li>
    {% endfor %}
  </ul>
  {% endif %}
</div>
```

**File:** `crispy_gclba/templates/gclba/layout/fieldset.html`
```html
<fieldset class="mb-6 p-5 bg-white border border-gray-200 rounded-card shadow-card">
  {% if fieldset.legend %}
  <legend class="sr-only">{{ fieldset.legend }}</legend>
  <div class="flex items-center gap-2 mb-4 pb-3 border-b border-gray-100">
    <div class="w-1 h-5 rounded-full bg-gclba-600"></div>
    <h3 class="text-sm font-bold text-gray-900 uppercase tracking-wide">
      {{ fieldset.legend }}
    </h3>
  </div>
  {% endif %}
  {{ fields }}
</fieldset>
```

**File:** `crispy_gclba/templates/gclba/widget/input.html`
```html
<input
  type="{{ widget.type|default:'text' }}"
  name="{{ widget.name }}"
  {% if widget.value != None %}value="{{ widget.value }}"{% endif %}
  {% for attr_name, attr_val in widget.attrs.items %}
    {{ attr_name }}="{{ attr_val }}"
  {% endfor %}
  class="
    w-full px-3.5 py-2.5
    text-sm text-gray-900 placeholder:text-gray-400
    bg-white border border-gray-300 rounded-md
    shadow-sm
    transition-all duration-150
    focus:border-gclba-500 focus:ring-2 focus:ring-gclba-500/20 focus:outline-none
    {% if widget.attrs.has_error %}
      border-red-400 bg-red-50/30
    {% endif %}
    disabled:opacity-50 disabled:cursor-not-allowed
  "
/>
```

**File:** `crispy_gclba/templates/gclba/widget/textarea.html`
```html
<textarea
  name="{{ widget.name }}"
  {% for attr_name, attr_val in widget.attrs.items %}
    {{ attr_name }}="{{ attr_val }}"
  {% endfor %}
  class="
    w-full px-3.5 py-2.5
    text-sm text-gray-900 placeholder:text-gray-400
    bg-white border border-gray-300 rounded-md
    shadow-sm resize-y min-h-[120px]
    transition-all duration-150
    focus:border-gclba-500 focus:ring-2 focus:ring-gclba-500/20 focus:outline-none
    {% if widget.attrs.has_error %}
      border-red-400 bg-red-50/30
    {% endif %}
    disabled:opacity-50 disabled:cursor-not-allowed
  "
>{% if widget.value != None %}{{ widget.value }}{% endif %}</textarea>
```

**File:** `crispy_gclba/templates/gclba/widget/select.html`
```html
<div class="relative">
  <select
    name="{{ widget.name }}"
    {% for attr_name, attr_val in widget.attrs.items %}
      {{ attr_name }}="{{ attr_val }}"
    {% endfor %}
    class="
      w-full px-3.5 py-2.5 pr-10
      text-sm text-gray-900
      bg-white border border-gray-300 rounded-md
      shadow-sm appearance-none cursor-pointer
      transition-all duration-150
      focus:border-gclba-500 focus:ring-2 focus:ring-gclba-500/20 focus:outline-none
      {% if widget.attrs.has_error %}
        border-red-400 bg-red-50/30
      {% endif %}
      disabled:opacity-50 disabled:cursor-not-allowed
    "
  >
    {% for group_name, group_choices, group_index in widget.optgroups %}
      {% for option in group_choices %}
      <option
        value="{{ option.value }}"
        {% if option.selected %}selected{% endif %}
      >{{ option.label }}</option>
      {% endfor %}
    {% endfor %}
  </select>
  <div class="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400">
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M3 4.5L6 7.5L9 4.5"/>
    </svg>
  </div>
</div>
```

**Verify:** `python manage.py check` still reports 0 issues. Directories exist:
```
crispy_gclba/
  __init__.py
  templates/gclba/
    field.html
    layout/fieldset.html
    widget/input.html
    widget/textarea.html
    widget/select.html
```

---

## Task 6: Replace Tailwind CDN in base.html

**File:** `templates/base.html`

Remove the CDN script tag and inline config. Replace with compiled CSS.

Find and delete these lines:
```html
<script src="https://cdn.tailwindcss.com"></script>
<script>
    tailwind.config = {
        theme: {
            extend: {
                colors: {
                    gclba: { ... }
                }
            }
        }
    }
</script>
```

Replace with:
```html
{% load static %}
<link rel="stylesheet" href="{% static 'css/dist/styles.css' %}">
```

**Verify:** Run `python manage.py tailwind build` then `python manage.py collectstatic --noinput`. The compiled CSS file should exist at `theme/static/css/dist/styles.css`.

---

## Task 7: Create Cotton Component Directory

**Directory:** `templates/cotton/`

Create the directory. Cotton auto-discovers components here by default.

```bash
mkdir -p templates/cotton
```

Create a placeholder to verify cotton is working:

**File:** `templates/cotton/test_card.html`
```html
{# Temporary test component. Delete after verifying cotton works. #}
<div class="p-4 bg-gclba-50 border border-gclba-200 rounded-card">
  {{ slot }}
</div>
```

**Verify:** Add `<c-test_card>Hello cotton</c-test_card>` temporarily to any existing template. If it renders the green-bordered card, cotton is wired up. Remove the test after confirming.

---

## Task 8: Dev Server Setup

Update the dev workflow. Two terminals needed:

```bash
# Terminal 1: Tailwind watcher (recompiles on template changes)
python manage.py tailwind start

# Terminal 2: Django dev server
python manage.py runserver
```

Add a note to the project README or CLAUDE.md:

**File:** Top of CLAUDE.md, in the Development Commands section, add:

```
python manage.py tailwind start         # Terminal 1: CSS watcher (required for dev)
python manage.py tailwind build         # One-time CSS build (for CI/deploy)
```

**Verify:** Visit http://127.0.0.1:8000/apply/ and confirm styles render correctly. The page should look identical to before (same green header, same form styling) since the Tailwind config preserves the `gclba` color scale.

---

## Completion Checklist

- [ ] All four Python packages installed
- [ ] `theme/` app created with custom `tailwind.config.js`
- [ ] `config/settings.py` updated with all new apps
- [ ] `crispy_gclba/` template pack created (5 template files)
- [ ] CDN script tag removed from `base.html`, replaced with compiled CSS link
- [ ] `templates/cotton/` directory created
- [ ] Dev server starts without errors
- [ ] `/apply/` page renders with correct styles
- [ ] `/admin/` page still works (Unfold unaffected)
