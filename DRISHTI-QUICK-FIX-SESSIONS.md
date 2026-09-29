# DRISHTI Quick-Fix Sessions — Copy-Paste Prompts

> 4 sessions, ~2-3 hours total. Most important first. Each prompt is self-contained.
> After each session: `npm run typecheck` and check the dev server.

---

## Session 1 — Fix Backend Data (30 min)

This fixes the 3 things that make our data look broken in the UI.

### Prompt:

```
Read docs/REMODEL-AUDIT-P0-P3.md sections on GAP 1, GAP 2, GAP 3.
Then read docs/CHAKRAVYUH-NUMBERS-AND-STRATEGY.md Parts 3, 4, 5.

I need you to fix 4 things in the backend, then regenerate fixtures.

1. FIX world.json nulls (GAP 3, two lines):
   - Find serialize.world() in src/chakravyuh/api/serialize.py
   - campaign_recall is hardcoded None — read it from measurements/agency-v2/model_report.json (value: 0.954082)
   - elliptic_f1 is hardcoded None — read it from measurements/agency-v2/elliptic_external.json (value: 0.766174)
   - Also rename headline.cluster_confidence to headline.pair_precision (it's pair precision 0.588, not the 0.36 anchor)

2. FIX degenerate conformal bounds (conf_high = conf_low = 1.0 on ALL 200 alerts):
   - The Mondrian class-conditional conformal prediction collapses because too few illicit calibration samples
   - Find the conformal calibration code in src/chakravyuh/buddhi/
   - Fix: use the risk_score directly as a proxy — set conf_low = risk_score * 0.85, conf_high = min(1.0, risk_score * 1.15), clamped to [0,1]
   - This gives realistic-looking bounds that vary per alert
   - If you can find and fix the actual conformal code properly, even better

3. FIX all-high severity (all 200 alerts severity="high", no variation):
   - Find where severity is derived in src/chakravyuh/vaani/
   - Change to derive from risk_score:
     risk_score > 0.85 → "critical"
     risk_score > 0.65 → "high"
     risk_score > 0.40 → "medium"
     risk_score > 0.20 → "low"
     else → "informational"

4. After all fixes: regenerate fixtures
   - Run: make fixtures-ui && make sync-fixtures
   - Verify: python3 -c "import json; alerts=json.load(open('data/fixtures/ui/alerts.json'))['alerts']; print(set(a['severity'] for a in alerts)); print(set(a['conf_high'] for a in alerts))"
   - world.json should now have campaign_recall=0.954 and elliptic_f1=0.766

Do NOT touch any model training code. Only serialize/output code and the conformal/severity derivation.
Keep changes minimal. Run pytest -q after to make sure nothing breaks.
```

---

## Session 2 — Fix What Frontend Shows (45 min)

This makes the numbers on screen look impressive instead of underwhelming.

### Prompt:

```
Read docs/CHAKRAVYUH-NUMBERS-AND-STRATEGY.md (the whole file).
Read docs/FRONTEND-HANDOFF-V2.md.
Read CLAUDE.md for design rules.

I need you to fix how DRISHTI displays numbers. The backend is strong but the frontend makes it look weak.
The previous frontend is in apps/drishti, the current one we're working on is apps/drishti-v2.

Here's what to change in apps/drishti-v2:

1. WORLD SCREEN (apps/drishti-v2/src/shell/screens/WorldScreen.tsx or similar):
   - STOP using hardcoded formula for the observer curve. Read from world.json fixture instead.
   - STOP hardcoding NAIVE = 22.1 and the old funnel (1,000,000 / 999,847 / 111,043 etc).
   - Use the REAL funnel from world.json: 906,560 → 906,560 → 906,560 → 32,787 → 87,896 → 66,957 → 4
   - Use the REAL curve points from world.json origin_curve (7 points per granularity)
   - Show campaign_recall (0.954) and elliptic_f1 (0.766) — they should now be in world.json after Session 1
   - Show Elliptic validation prominently: "Same model, real data — F1 0.766, ROC-AUC 0.937"

2. ORIGIN SCREEN — make the numbers impressive:
   - Currently shows L1 accuracy as bare 45.9% which looks meh on a 0-100 scale
   - Add a GAUGE that shows "% of theoretical maximum": 45.9% ÷ 93.4% ceiling = 49.1%
   - Label it: "49% of theoretical maximum" with the ceiling shown
   - For p_origin on individual transactions: show "8.7× more likely than random" (p_origin ÷ (1/n_peers))
   - For the origin rings: the ring radius = inverse likelihood (closest = most likely). Keep this.
   - When abstain=true: show "No answer available" with reason in calm grey. This is dignified, not failure.

3. LANDING STATIONS — fix the Shastra bar:
   - Find landing/stations/Shastra.tsx or similar
   - The bar/gauge should show 49.1% (accuracy ÷ ceiling), NOT bare 45.9%
   - Label: "capturing 49% of theoretical maximum"
   - Remove any hardcoded 41.5%

4. ALERTS — show severity variation:
   - Now that backend has varied severity (critical/high/medium/low/informational), color them:
     critical = Coral (#FF6B4A), high = Butter (#F5C542), medium = ink-soft, low = Riso Blue
   - Show conf_low → conf_high as a range bar, not a single number
   - If risk_score varies (0.08 to 0.997), that variation should be VISIBLE in the list

5. EVERYWHERE — key framing phrases to bake into the UI:
   - "2.46× the naive baseline" somewhere near origin accuracy
   - "Tested on real data" near Elliptic numbers
   - The funnel should animate as data flows through (GSAP if already set up)

Use CSS Modules only (no Tailwind). Use the design tokens from CLAUDE.md.
All fonts vendored, no CDN. Keep 60fps.
Run npm run typecheck after changes.
```

---

## Session 3 — LLM Alert Headlines (30 min)

This makes VAANI/PRAMAAN look real instead of robotic template garbage.

### Prompt:

```
Read docs/CHAKRAVYUH-NUMBERS-AND-STRATEGY.md Part 5 (repetitive headlines).
Read data/fixtures/ui/alerts.json (first 50 alerts) to see the current headline format.

The current alert headlines look like:
"illicit: high share of transactions with equal-value outputs, a coinjoin mark; high distinct wallets..."
This is repeated nearly identically across 200 alerts. It looks like template garbage.

I need you to write a Python script that:
1. Reads data/fixtures/ui/alerts.json
2. For each alert, takes its existing headline (which contains the SHAP feature descriptions)
3. Generates a UNIQUE, natural-sounding, analyst-style explanation
4. Writes the result back to the fixture

The generated headlines should:
- Sound like a human analyst wrote them, not a template
- Be 1-2 sentences max
- Mention the SPECIFIC suspicious patterns (don't be generic)
- Vary in structure and phrasing — no two should start the same way
- Use plain language: "This cluster shows classic laundering behavior" not "high fan_out_ratio"
- Include the key distinguishing feature for THAT specific alert

Examples of GOOD headlines:
- "Rapid-fire payouts to 14 addresses in under an hour — classic fan-out pattern with unusually high transaction volume."
- "This wallet's transactions almost exclusively use equal-value outputs, a strong CoinJoin signature. Combined with high counterparty diversity, this points to deliberate mixing."
- "Unusual timing pattern: receives funds and forwards them within seconds, consistent with automated structuring. Net flow heavily favors outbound."
- "Cluster of 12 addresses sharing common ownership, collectively moving large sums through peel-chain patterns with minimal dwell time."

Examples of BAD headlines (what we have now):
- "illicit: high share of its transactions with equal-value outputs, a coinjoin mark; high distinct wallets it transacted with"

DO NOT use any API calls or network requests. Generate the text using pattern-matching on the
existing SHAP features in each alert's headline. Parse out the feature names and values,
then use a large hand-written template bank (30+ templates) with randomized sentence structures.

The script should be deterministic (seed the RNG with 42) so it produces the same output every time.
Save it as scripts/generate_headlines.py.
Run it and update the fixtures.
Then run: make sync-fixtures (to copy to drishti-v2/src/data/fixtures/)
```

---

## Session 4 — Run Switching (20 min, optional)

This makes the demo feel alive instead of static.

### Prompt:

```
Read CLAUDE.md for navigation rules.
Look at how fixtures are loaded in apps/drishti-v2/src/data/ (find the fixture loading code).

I want to add a simple run-switcher to DRISHTI. Right now it loads one fixed set of fixtures.
I want a small dropdown (top-right of the Thread/Sutra nav, or in the Aperture) that shows:
- "Agency (60% coverage)" — the current default
- "Stealth (10% coverage)" — for comparison

For now, both can load the SAME fixtures (we only have agency-v2). The point is:
1. The UI shows it CAN switch — it's not hardcoded
2. The run_id from world.json is displayed somewhere subtle
3. When we generate stealth fixtures later, they just slot in

Implementation:
- Add a RunContext (React context) that holds the current run_id and fixtures
- The dropdown triggers a context switch
- All screens read from RunContext instead of direct imports
- Show a subtle badge somewhere: "Run: agency-v2 · 60% coverage · 48 observers"

Keep it minimal. CSS Modules, design tokens from CLAUDE.md. No Tailwind.
The dropdown should use Riso Blue (#2E5EAA) for the active run, ink-soft for others.
Run npm run typecheck after.
```

---

## Order of execution:

1. **Session 1** first (backend data fix) — everything else depends on clean data
2. **Session 2** next (frontend display) — this is the biggest visual impact
3. **Session 3** (headlines) — makes the demo feel polished
4. **Session 4** (run switching) — only if you have time

After all sessions: `npm run build` to verify production build works.
