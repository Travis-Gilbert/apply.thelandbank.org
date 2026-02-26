# 002: Buyer Form UI/UX Upgrades

**Scope:** Cotton components, smarter progress tracker, form consistency, HTMX fragment responses for the `/apply/` multi-step form.
**Depends on:** 001 (infrastructure and component library setup)
**Estimated tasks:** 12

## Design Intent

The buyer is a Flint, MI resident applying to purchase a property from the Genesee County Land Bank. Many applicants will be first-time homebuyers. The form needs to feel trustworthy, simple, and encouraging. Every piece of friction (confusing progress indicators, inconsistent field rendering, unclear error messages, page reloads on validation failure) erodes completion rates.

The current form works but has these UX gaps:
- Progress bar shows numbered dots that don't explain conditional step skipping
- Each step template hand-renders fields with slightly different markup
- Validation errors cause full-page reloads
- Program type cards (Featured Homes, Ready for Rehab, VIP, Vacant Lot) are hardcoded HTML blocks with no reuse
- Save-progress feedback requires a page reload
- No visual distinction between completed, active, and upcoming steps

## Task 1: Create the Progress Tracker Component

**File:** `templates/cotton/progress_tracker.html`

This replaces the numbered-dots progress bar in `base_form.html`. The key improvement: it shows step names (not just numbers) and visually distinguishes completed, active, skipped, and upcoming steps. When steps 6 or 7 are skipped, the tracker simply omits them rather than showing confusing gaps.

```html
{# templates/cotton/progress_tracker.html #}
{#
  Smart progress tracker that adapts to conditional steps.

  Usage:
    <c-progress_tracker
      current="{{ current_step }}"
      total="{{ total_steps }}"
      steps="{{ active_steps }}"
      step_names="{{ step_names }}"
    />

  Props:
    current    (int)  : Current step position (1-indexed)
    total      (int)  : Total active steps
    steps      (list) : Active step numbers (e.g. [1,2,3,4,5,8])
    step_names (dict) : Step number to label mapping
#}

<div class="mb-8">
  {# Mobile: text indicator #}
  <div class="sm:hidden mb-3">
    <p class="text-sm font-semibold text-gclba-700">
      Step {{ current }} of {{ total }}
    </p>
    <div class="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
      <div
        class="h-full bg-gclba-600 rounded-full transition-all duration-500"
        style="width: {{ current|floatformat:0 }}{% widthratio current total 100 %}%"
      ></div>
    </div>
  </div>

  {# Desktop: step indicators #}
  <nav class="hidden sm:block" aria-label="Application progress">
    <ol class="flex items-center gap-0">
      {% for i in step_range %}
      <li class="flex items-center {% if not forloop.last %}flex-1{% endif %}">
        <div class="flex flex-col items-center">
          {# Step circle #}
          <div class="
            w-9 h-9 rounded-full flex items-center justify-center
            text-sm font-bold
            border-2 transition-all duration-300
            {% if i < current %}
              bg-gclba-600 border-gclba-600 text-white
            {% elif i == current %}
              bg-white border-gclba-600 text-gclba-700
              ring-4 ring-gclba-100
            {% else %}
              bg-gray-100 border-gray-300 text-gray-400
            {% endif %}
          ">
            {% if i < current %}
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
              </svg>
            {% else %}
              {{ i }}
            {% endif %}
          </div>
        </div>

        {# Connector line #}
        {% if not forloop.last %}
        <div class="
          flex-1 h-0.5 mx-2
          transition-all duration-500
          {% if i < current %}bg-gclba-500{% else %}bg-gray-200{% endif %}
        "></div>
        {% endif %}
      </li>
      {% endfor %}
    </ol>
  </nav>
</div>
```

**Verify:** Component file exists and is valid Django template syntax.

---

## Task 2: Create Step Names Context

**File:** `applications/views.py`

Add step name mapping to the `_get_step_context` helper so templates can display labels instead of bare numbers.

Find the `_get_step_context` function. Add a `step_names` dict to the returned context:

```python
def _get_step_context(draft, current_step):
    """Build the progress bar context for the form template."""
    form_data = draft.form_data or {}
    program_type = form_data.get("program_type", "own_it_now")
    purchase_type = form_data.get("purchase_type", "cash")

    steps = _get_active_steps(program_type, purchase_type)
    total_steps = len(steps)

    if current_step in steps:
        position = steps.index(current_step) + 1
    else:
        position = current_step

    # Human-readable names for each step number
    step_names = {
        1: "Your Info",
        2: "Property",
        3: "Offer",
        4: "Eligibility",
        5: "Documents",
        6: "Rehab Plan",
        7: "Land Contract",
        8: "Review",
    }

    return {
        "current_step": position,
        "total_steps": total_steps,
        "step_range": range(1, total_steps + 1),
        "active_steps": steps,
        "step_names": step_names,
    }
```

**Verify:** No test breakage. Run `python manage.py check`.

---

## Task 3: Create the Program Card Component

**File:** `templates/cotton/program_card.html`

Extracts the repeating program selection cards from Step 1 (currently hardcoded as separate HTML blocks for Featured Homes, Ready for Rehab, VIP Spotlight, and Vacant Lot).

```html
{# templates/cotton/program_card.html #}
{#
  Program selection card for Step 2 (property selection).

  Usage:
    <c-program_card
      name="Featured Homes"
      value="own_it_now"
      description="Homes available for immediate sale"
      detail="Cash or land contract. All homes sold as-is."
      time="10-15 minutes"
      color="green"
      selected="{{ selected_program }}"
    />

  Props:
    name         (str)  : Display name
    value        (str)  : form value (own_it_now, ready_for_rehab, vip_spotlight)
    description  (str)  : One-line description
    detail       (str)  : Requirements note
    time         (str)  : Estimated completion time
    color        (str)  : green | amber | purple | gray
    selected     (str)  : Currently selected program value (for active state)
    disabled     (bool) : Gray out and prevent selection
    field_name   (str)  : Form field name (default: "program_type")
#}

<label
  class="
    block cursor-pointer group
    {% if disabled %}opacity-60 cursor-not-allowed{% endif %}
  "
>
  <input
    type="radio"
    name="{{ field_name|default:'program_type' }}"
    value="{{ value }}"
    class="peer sr-only"
    {% if selected == value %}checked{% endif %}
    {% if disabled %}disabled{% endif %}
  />

  <div class="
    relative p-5 rounded-card border-2 transition-all duration-200
    bg-white shadow-card
    peer-checked:shadow-card-hover
    {% if not disabled %}
      hover:shadow-card-hover hover:border-gray-300
      peer-checked:border-gclba-500 peer-checked:bg-gclba-50/30
    {% endif %}
    {% if disabled %}
      border-gray-200 bg-gray-50
    {% else %}
      border-gray-200
    {% endif %}
  ">
    {# Selected indicator #}
    <div class="
      absolute top-4 right-4 w-5 h-5 rounded-full border-2
      flex items-center justify-center transition-all
      peer-checked:border-gclba-600 peer-checked:bg-gclba-600
      {% if disabled %}border-gray-300{% else %}border-gray-300{% endif %}
    ">
      <svg class="w-3 h-3 text-white hidden peer-checked:block" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
      </svg>
    </div>

    {# Program badge #}
    <span class="
      inline-block text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-full mb-3
      {% if color == 'green' %}bg-green-100 text-green-800
      {% elif color == 'amber' %}bg-amber-100 text-amber-800
      {% elif color == 'purple' %}bg-purple-100 text-purple-800
      {% else %}bg-gray-100 text-gray-600{% endif %}
    ">
      {{ name }}
    </span>

    <p class="text-sm font-semibold text-gray-900 mb-1">{{ description }}</p>
    <p class="text-xs text-gray-500 mb-3">{{ detail }}</p>

    {# Time estimate #}
    <div class="flex items-center gap-1.5 text-xs text-gray-400">
      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6l4 2m6-2a10 10 0 11-20 0 10 10 0 0120 0z"/>
      </svg>
      {{ time }}
    </div>

    {% if disabled %}
    <div class="mt-3 text-xs font-medium text-gray-500 bg-gray-100 rounded px-2.5 py-1.5 text-center">
      Coming Soon
    </div>
    {% endif %}
  </div>
</label>
```

**Verify:** File exists, valid template syntax.

---

## Task 4: Create the Form Field Component

**File:** `templates/cotton/form_field.html`

For rendering individual fields outside of crispy-forms (e.g. the property address autocomplete, the eligibility radio buttons, the acknowledgment checkboxes).

```html
{# templates/cotton/form_field.html #}
{#
  Consistent form field wrapper with label, help text, and errors.

  Usage:
    <c-form_field label="Property Address" required
                  help="Start typing to search GCLBA inventory"
                  error="{{ form.property_address.errors.0 }}">
      {{ form.property_address }}
    </c-form_field>

  Props:
    label    (str)  : Label text
    help     (str)  : Help text below the field
    error    (str)  : Error message string
    required (bool) : Show required asterisk
    class    (str)  : Additional wrapper classes
#}

<div class="mb-5 {{ class }}">
  {% if label %}
  <label class="block mb-1.5 text-sm font-semibold text-gray-900">
    {{ label }}
    {% if required %}
    <span class="text-red-500 ml-0.5" aria-hidden="true">*</span>
    {% endif %}
  </label>
  {% endif %}

  {{ slot }}

  {% if help %}
  <p class="mt-1.5 text-xs text-gray-500 leading-relaxed">{{ help }}</p>
  {% endif %}

  {% if error %}
  <p class="mt-1.5 text-xs text-red-600 font-medium flex items-center gap-1" role="alert">
    <svg class="w-3.5 h-3.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
      <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
    </svg>
    {{ error }}
  </p>
  {% endif %}
</div>
```

---

## Task 5: Create the Step Section Component

**File:** `templates/cotton/step_section.html`

Wraps each step's content in a consistent card with header, description, and optional time estimate. Replaces the bare `<div class="bg-white shadow-sm rounded-lg">` in `base_form.html`.

```html
{# templates/cotton/step_section.html #}
{#
  Step content wrapper with header and description.

  Usage:
    <c-step_section
      title="Tell us about yourself"
      description="We need your contact info to process the application."
      icon="user"
    >
      {{ form fields here }}
    </c-step_section>

  Props:
    title       (str) : Section heading
    description (str) : Supporting text below heading
    icon        (str) : user | home | dollar | shield | file | wrench | contract | check
    class       (str) : Additional classes
#}

<div class="bg-white shadow-card rounded-card border border-gray-200 overflow-hidden {{ class }}">
  {# Section header #}
  <div class="px-6 py-5 border-b border-gray-100 bg-gray-50/50">
    <div class="flex items-start gap-3">
      {# Icon #}
      <div class="w-10 h-10 rounded-lg bg-gclba-100 flex items-center justify-center shrink-0">
        {% if icon == "user" %}
        <svg class="w-5 h-5 text-gclba-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
        </svg>
        {% elif icon == "home" %}
        <svg class="w-5 h-5 text-gclba-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
        </svg>
        {% elif icon == "dollar" %}
        <svg class="w-5 h-5 text-gclba-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        {% elif icon == "shield" %}
        <svg class="w-5 h-5 text-gclba-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
        </svg>
        {% elif icon == "file" %}
        <svg class="w-5 h-5 text-gclba-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
        {% elif icon == "check" %}
        <svg class="w-5 h-5 text-gclba-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        {% else %}
        <svg class="w-5 h-5 text-gclba-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        {% endif %}
      </div>

      <div>
        <h2 class="text-lg font-bold text-gray-900">{{ title }}</h2>
        {% if description %}
        <p class="mt-1 text-sm text-gray-500 leading-relaxed">{{ description }}</p>
        {% endif %}
      </div>
    </div>
  </div>

  {# Form content #}
  <div class="px-6 py-6">
    {{ slot }}
  </div>
</div>
```

---

## Task 6: Create the Alert Component

**File:** `templates/cotton/alert.html`

For eligibility gate results, save-progress confirmations, validation summaries.

```html
{# templates/cotton/alert.html #}
{#
  Alert banner for status messages and warnings.

  Usage:
    <c-alert type="success">Your progress has been saved.</c-alert>
    <c-alert type="error" title="Eligibility Issue">
      You are not eligible for this program.
    </c-alert>
    <c-alert type="info" dismissible>You can save and return later.</c-alert>

  Props:
    type        (str)  : success | error | warning | info
    title       (str)  : Optional bold title line
    dismissible (bool) : Show X button
#}

<div
  class="
    rounded-card border px-4 py-3.5
    flex items-start gap-3
    {% if type == 'success' %}bg-green-50 border-green-200 text-green-800{% endif %}
    {% if type == 'error' %}bg-red-50 border-red-200 text-red-800{% endif %}
    {% if type == 'warning' %}bg-amber-50 border-amber-200 text-amber-800{% endif %}
    {% if type == 'info' %}bg-blue-50 border-blue-200 text-blue-800{% endif %}
  "
  role="{% if type == 'error' %}alert{% else %}status{% endif %}"
>
  {# Icon #}
  <div class="shrink-0 mt-0.5">
    {% if type == "success" %}
    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
    </svg>
    {% elif type == "error" %}
    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
    </svg>
    {% elif type == "warning" %}
    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
      <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
    </svg>
    {% else %}
    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
      <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
    </svg>
    {% endif %}
  </div>

  <div class="flex-1 text-sm">
    {% if title %}<p class="font-bold mb-0.5">{{ title }}</p>{% endif %}
    <div class="leading-relaxed">{{ slot }}</div>
  </div>

  {% if dismissible %}
  <button
    onclick="this.closest('[role]').remove()"
    class="shrink-0 p-1 hover:opacity-70 transition-opacity"
    aria-label="Dismiss"
  >&times;</button>
  {% endif %}
</div>
```

---

## Task 7: Update base_form.html to Use Cotton Components

**File:** `templates/apply/base_form.html`

Replace the hardcoded progress bar and form card wrapper with cotton components. This is the single highest-impact change because all 8 step templates extend `base_form.html`.

Replace the entire file with:

```html
{% extends "base.html" %}
{% load template_partials %}

{% block title %}Step {{ current_step }} of {{ total_steps }} - GCLBA Application{% endblock %}

{% block content %}
<div class="max-w-2xl mx-auto">

  {# Progress tracker #}
  <c-progress_tracker
    current="{{ current_step }}"
    total="{{ total_steps }}"
    steps="{{ active_steps }}"
    step_names="{{ step_names }}"
  />

  {# Form #}
  <form
    method="post"
    {% if has_file_upload %}enctype="multipart/form-data"{% endif %}
    class="space-y-6"
    hx-indicator="#form-spinner"
  >
    {% csrf_token %}

    {# Step-specific content (defined in each step template) #}
    {% block form_content %}{% endblock %}

    {# Navigation buttons #}
    <div class="flex items-center justify-between pt-4">
      <div>
        {% if current_step > 1 %}
        <a
          href="{% block prev_url %}{% endblock %}"
          class="
            inline-flex items-center gap-2 px-4 py-2.5
            text-sm font-medium text-gray-700
            bg-white border border-gray-300 rounded-card
            hover:bg-gray-50 transition-colors
          "
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
          </svg>
          Previous
        </a>
        {% endif %}
      </div>

      <div class="flex items-center gap-3">
        {% block save_button %}
        <button
          type="button"
          id="save-progress-btn"
          class="
            inline-flex items-center px-4 py-2.5
            text-sm font-medium text-gclba-700
            bg-gclba-50 border border-gclba-200 rounded-card
            hover:bg-gclba-100 transition-colors
          "
        >
          Save Progress
        </button>
        {% endblock %}

        <button
          type="submit"
          class="
            inline-flex items-center gap-2 px-5 py-2.5
            text-sm font-bold text-white
            bg-gclba-600 border border-gclba-700 rounded-card
            hover:bg-gclba-700 transition-colors
            shadow-sm
          "
        >
          {% block submit_label %}Continue{% endblock %}
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
          </svg>
        </button>

        <span id="form-spinner" class="htmx-indicator text-xs text-gray-400">
          Saving...
        </span>
      </div>
    </div>
  </form>

  {# Save progress feedback target #}
  <div id="save-feedback"></div>
</div>
{% endblock %}
```

**Verify:** Visit each step at `/apply/` and confirm the form still renders and submits correctly. The visual styling will change (the progress tracker now uses the cotton component) but all functionality should work identically.

---

## Task 8: Add HTMX Partial for Save Progress Feedback

**File:** `templates/apply/_save_feedback.html`

```html
{# Partial returned by the save-progress HTMX endpoint #}
{% load template_partials %}

<div class="mt-4 animate-fade-in">
  {% if success %}
  <c-alert type="success" dismissible>
    Progress saved! We sent a link to <strong>{{ email }}</strong> so you can pick up where you left off.
  </c-alert>
  {% else %}
  <c-alert type="error" dismissible>
    We could not save your progress. Please enter a valid email address and try again.
  </c-alert>
  {% endif %}
</div>
```

Update the save-progress button in `base_form.html` to use HTMX:

In the save button (Task 7's template), add these attributes:
```html
hx-post="{% url 'applications:save-progress' %}"
hx-target="#save-feedback"
hx-swap="innerHTML"
hx-include="[name='email']"
```

**Verify:** Clicking "Save Progress" should show inline feedback without a page reload.

---

## Task 9: Add HTMX Partial for Eligibility Gate

**File:** `templates/apply/_eligibility_result.html`

When Step 4 returns a disqualification, show it inline instead of redirecting to a separate page.

```html
{# Partial for eligibility check result #}
{% if disqualified %}
<div class="animate-slide-up">
  <c-alert type="error" title="We're sorry">
    Based on your answers, you are not currently eligible to purchase
    property through the Genesee County Land Bank.
  </c-alert>

  <div class="mt-4 p-4 bg-gray-50 rounded-card border border-gray-200">
    <p class="text-sm text-gray-700 mb-3">
      Eligibility can change. If your situation changes, you are
      welcome to apply again.
    </p>
    <p class="text-sm text-gray-500">
      Questions? Call <strong>(810) 257-3088</strong> or email
      <a href="mailto:offers@thelandbank.org" class="text-gclba-700 underline">
        offers@thelandbank.org
      </a>
    </p>
  </div>
</div>
{% else %}
{# Eligible: form submits normally and advances to next step #}
{% endif %}
```

Update the Step 4 view to return this partial on HTMX requests:

In `applications/views.py`, in the Step 4 POST handler, add:
```python
if request.htmx and disqualified:
    return render(request, "apply/_eligibility_result.html", {
        "disqualified": True,
    })
```

---

## Task 10: Create the Navigation Button Component

**File:** `templates/cotton/nav_buttons.html`

Standardizes the Previous / Save / Continue button bar across all steps.

```html
{# templates/cotton/nav_buttons.html #}
{#
  Step navigation bar.

  Usage:
    <c-nav_buttons
      prev_url="/apply/step/1/"
      save_url="/apply/save/"
      submit_label="Continue"
      is_final="false"
    />

  Props:
    prev_url     (str)  : URL for previous step (omit to hide back button)
    save_url     (str)  : HTMX endpoint for save-progress
    submit_label (str)  : Text for the primary button (default: "Continue")
    is_final     (bool) : If true, button says "Submit Application" with different styling
#}

<div class="flex items-center justify-between pt-4 mt-2 border-t border-gray-100">
  <div>
    {% if prev_url %}
    <a
      href="{{ prev_url }}"
      class="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-card hover:bg-gray-50 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
      </svg>
      Previous
    </a>
    {% endif %}
  </div>

  <div class="flex items-center gap-3">
    {% if save_url %}
    <button
      type="button"
      class="inline-flex items-center px-4 py-2.5 text-sm font-medium text-gclba-700 bg-gclba-50 border border-gclba-200 rounded-card hover:bg-gclba-100 transition-colors"
      hx-post="{{ save_url }}"
      hx-target="#save-feedback"
      hx-swap="innerHTML"
    >
      Save Progress
    </button>
    {% endif %}

    <button
      type="submit"
      class="
        inline-flex items-center gap-2 px-5 py-2.5
        text-sm font-bold text-white rounded-card shadow-sm transition-colors
        {% if is_final %}
          bg-gclba-700 border border-gclba-800 hover:bg-gclba-800
        {% else %}
          bg-gclba-600 border border-gclba-700 hover:bg-gclba-700
        {% endif %}
      "
    >
      {{ submit_label|default:"Continue" }}
      {% if not is_final %}
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
      </svg>
      {% endif %}
    </button>
  </div>
</div>
```

---

## Task 11: Create the Application Outline Sidebar Component

**File:** `templates/cotton/application_outline.html`

The right-side outline panel that shows which sections are complete. Currently rendered as raw HTML in the step template.

```html
{# templates/cotton/application_outline.html #}
{#
  Sidebar showing application progress outline.

  Usage:
    <c-application_outline
      current="{{ current_step }}"
      steps="{{ active_steps }}"
      step_names="{{ step_names }}"
    />
#}

<aside class="hidden lg:block w-64 shrink-0">
  <div class="sticky top-8">
    <div class="bg-white border border-gray-200 rounded-card shadow-card p-5">
      <h3 class="text-xs font-bold uppercase tracking-wider text-gray-500 mb-4">
        Application Outline
      </h3>
      <ol class="space-y-2">
        {% for i in step_range %}
        <li class="flex items-center gap-2.5 text-sm">
          {% if i < current %}
          <span class="w-5 h-5 rounded-full bg-gclba-100 text-gclba-700 flex items-center justify-center shrink-0">
            <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
            </svg>
          </span>
          <span class="text-gray-500">Step {{ i }}</span>
          {% elif i == current %}
          <span class="w-5 h-5 rounded-full bg-gclba-600 text-white flex items-center justify-center text-xs font-bold shrink-0">
            {{ i }}
          </span>
          <span class="font-semibold text-gray-900">Step {{ i }}</span>
          {% else %}
          <span class="w-5 h-5 rounded-full bg-gray-100 text-gray-400 flex items-center justify-center text-xs shrink-0">
            {{ i }}
          </span>
          <span class="text-gray-400">Step {{ i }}</span>
          {% endif %}
        </li>
        {% endfor %}
      </ol>
    </div>

    <div class="mt-4 text-xs text-gray-400 leading-relaxed px-1">
      <p class="mb-2">Need help? Call <strong class="text-gray-600">(810) 257-3088</strong></p>
      <p>or email <a href="mailto:offers@thelandbank.org" class="text-gclba-700 underline">offers@thelandbank.org</a></p>
    </div>
  </div>
</aside>
```

---

## Task 12: Create the Document Upload Component

**File:** `templates/cotton/doc_upload.html`

Standardizes the file upload fields used in Step 5. Currently each document type (photo ID, pay stubs, bank statement, proof of funds, preapproval letter) is rendered with slightly different markup.

```html
{# templates/cotton/doc_upload.html #}
{#
  Document upload field with preview and requirements.

  Usage:
    <c-doc_upload
      name="photo_id"
      label="Photo ID"
      help="Driver's license, state ID, or passport"
      accept="image/*,.pdf"
      required
    />

  Props:
    name     (str)  : Form field name
    label    (str)  : Display label
    help     (str)  : Requirements text
    accept   (str)  : File type filter (default: image/*,.pdf)
    required (bool) : Required indicator
    error    (str)  : Error message
#}

<div class="mb-5">
  <label class="block mb-1.5 text-sm font-semibold text-gray-900">
    {{ label }}
    {% if required %}
    <span class="text-red-500 ml-0.5" aria-hidden="true">*</span>
    {% endif %}
  </label>

  <div class="
    relative border-2 border-dashed border-gray-300 rounded-card
    px-4 py-6 text-center
    hover:border-gclba-400 hover:bg-gclba-50/30
    transition-colors cursor-pointer
    {% if error %}border-red-400 bg-red-50/20{% endif %}
  ">
    <input
      type="file"
      name="{{ name }}"
      accept="{{ accept|default:'image/*,.pdf' }}"
      class="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
      {% if required %}required{% endif %}
    />

    <svg class="w-8 h-8 text-gray-400 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
      <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/>
    </svg>

    <p class="text-sm text-gray-600 font-medium">
      Click to upload or drag and drop
    </p>
    <p class="text-xs text-gray-400 mt-1">PDF, JPG, or PNG up to 10MB</p>
  </div>

  {% if help %}
  <p class="mt-1.5 text-xs text-gray-500">{{ help }}</p>
  {% endif %}

  {% if error %}
  <p class="mt-1.5 text-xs text-red-600 font-medium" role="alert">{{ error }}</p>
  {% endif %}
</div>
```

---

## Completion Checklist

- [ ] `templates/cotton/progress_tracker.html` created
- [ ] `templates/cotton/program_card.html` created
- [ ] `templates/cotton/form_field.html` created
- [ ] `templates/cotton/step_section.html` created
- [ ] `templates/cotton/alert.html` created
- [ ] `templates/cotton/nav_buttons.html` created
- [ ] `templates/cotton/application_outline.html` created
- [ ] `templates/cotton/doc_upload.html` created
- [ ] `templates/apply/base_form.html` updated to use cotton components
- [ ] `templates/apply/_save_feedback.html` HTMX partial created
- [ ] `templates/apply/_eligibility_result.html` HTMX partial created
- [ ] `applications/views.py` updated with `step_names` and HTMX eligibility response
- [ ] All 8 steps render correctly at `/apply/`
- [ ] Save progress works via HTMX (no page reload)
- [ ] Eligibility gate shows inline error (no redirect to separate page)
