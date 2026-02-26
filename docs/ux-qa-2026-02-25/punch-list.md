# UX QA Punch List (Apply + Admin)

Date: 2026-02-25
Scope: `/apply/`, `/admin/`
Environment: local dev (`http://127.0.0.1:8200`), seeded QA data

## Screenshot Set
- `/Users/travisgilbert/Library/Mobile Documents/com~apple~CloudDocs/Tech Dev/Application Portal Git/docs/ux-qa-2026-02-25/screens/A1-apply-landing.png`
- `/Users/travisgilbert/Library/Mobile Documents/com~apple~CloudDocs/Tech Dev/Application Portal Git/docs/ux-qa-2026-02-25/screens/A2-apply-resume-step4.png`
- `/Users/travisgilbert/Library/Mobile Documents/com~apple~CloudDocs/Tech Dev/Application Portal Git/docs/ux-qa-2026-02-25/screens/B1-admin-dashboard.png`
- `/Users/travisgilbert/Library/Mobile Documents/com~apple~CloudDocs/Tech Dev/Application Portal Git/docs/ux-qa-2026-02-25/screens/B2-admin-app-list.png`
- `/Users/travisgilbert/Library/Mobile Documents/com~apple~CloudDocs/Tech Dev/Application Portal Git/docs/ux-qa-2026-02-25/screens/B3-admin-app-detail.png`

## Findings (Prioritized)

1. [P0] Admin application detail can hard-crash when `STORAGES.default` is undefined
- Evidence: `B3-admin-app-detail.png`
- Impact: Staff cannot open application detail records; core admin workflow blocked.
- Suggested fix: Define `STORAGES['default']` fallback to local filesystem in non-S3/dev environments.

2. [P1] Apply page hero copy is misleading for resumed/in-progress drafts
- Evidence: `A1-apply-landing.png`, `A2-apply-resume-step4.png`
- Observation: Header says "Let's get started on your application" while user is already on step 4/7.
- Impact: Confusing progression language during resume flow.
- Suggested fix: Dynamic heading/subcopy by step state, e.g. "Continue your application" for `current_step > 1`.

3. [P1] Apply top section consumes too much vertical space in later steps
- Evidence: `A1-apply-landing.png`, `A2-apply-resume-step4.png`
- Observation: Progress + hero + summary stack pushes active form controls lower, increasing scroll before action.
- Impact: Slower completion on laptop-height viewports.
- Suggested fix: Compact top intro block after first step (smaller spacing, optional hide subcopy, tighter section margins).

4. [P2] Admin list right-side content is visually cramped/truncated at moderate widths
- Evidence: `B2-admin-app-list.png`
- Observation: Quick docs column and right-most content are hard to scan with constrained width.
- Impact: Lower scannability and slower triage in list view.
- Suggested fix: Shorten quick-doc labels (chips/icons + tooltip), enforce min column widths, and/or horizontal sticky actions.

5. [P3] Status/date context in list could be stronger for prioritization
- Evidence: `B2-admin-app-list.png`
- Observation: Row status is visible, but list lacks an obvious "last update"/"age" cue at glance.
- Impact: Harder to identify stale or urgent items quickly.
- Suggested fix: Add "Updated"/"Submitted" relative-time column and default sort/filter for aging items.

## Notes
- Admin dashboard screenshot (`B1`) is partially obscured by local desktop overlays during capture, but admin list/detail captures are clear enough for issue identification.
- This pass focused on UX behavior and usability signals, not visual design re-theme.
