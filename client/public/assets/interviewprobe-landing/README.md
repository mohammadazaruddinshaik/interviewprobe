# InterviewProbe Landing — Locked Asset Pack

This pack is built specifically from the user's locked 1536×1024 landing-page reference.

IMPORTANT:
- The `reference/landing-reference-locked.png` file is the visual source of truth.
- Do NOT use that screenshot as the website background.
- Rebuild the page from real HTML/React + Tailwind + SVG + GSAP.
- Every decorative/visual element is provided as an individual file where practical.
- The logo is intentionally a PLACEHOLDER. Do not treat it as the final InterviewProbe brand mark.
- Do not import assets from the old `frontend/` project.
- Do not mix these assets with previous frontend asset packs.

Recommended destination:
client/public/assets/interviewprobe-landing/

Suggested structure:
assets/
  interviewprobe-landing/
    brand/
    hero/
    people/
    backgrounds/
    decorations/
    annotations/
    icons/
    cards/
    typography/
    spec/
    reference/

Hero:
- `hero/interviewer-portrait.png` is a clean portrait crop derived from the locked reference.
- `hero/interviewer-avatar.png` is the small interviewer avatar crop.
- `hero/interviewer-hero-source-crop.png` preserves the contextual hero crop when matching the reference composition.

Use the standalone SVG cards only if useful; the page should still recreate their text as HTML when responsive behavior is needed.
