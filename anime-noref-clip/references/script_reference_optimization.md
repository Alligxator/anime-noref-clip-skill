# Reference Script Optimization

Run this gate after `script_variants.json` and before final `script.json` or `final_shots.json`.

The goal is not to invent a new plot. The goal is to delegate writing-style review to the `content-style-system` skill, then use its result to select or rewrite the candidate that is strongest while still fully source-supported.

This is a hard copywriting gate. The active row 11 goal must say that the final script copy is being written or rewritten with the `content-style-system` writing skill. Do not satisfy this gate by locally writing a review JSON, stamping `content_style_skill`, or manually copying Obsidian guidance into `anime-noref-clip`.

For now, anime script optimization uses one common Obsidian reference file:

`/Users/gxator.alli/Documents/Obsidian/content-style-vault/30-style-families/viral-video-script/categories/anime-clip/script-optimization-reference.md`

When the writing task needs a stronger short-video hook or rhythm reference, `content-style-system` may also read the Obsidian good-sample anchor `thai_food_1000m_viral` in:

`/Users/gxator.alli/Documents/Obsidian/content-style-vault/50-samples/viral-video-script/good-samples.md`

Use that Thai food clip only as a pacing, hook, and information-progression reference. Do not transfer food-video facts, prices, objects, locations, or claims into anime scripts.

Do not ask the writing skill to load multiple anime preset pages for one optimization pass.

## Delegation Boundary

`anime-noref-clip` owns:

- source evidence, visual tags, `story_evidence_pack.json`, source blocks, shot reports, and retention constraints
- storing the `initial_story_seed.json` and canonical `story_atoms.json` returned by `content-style-system`
- resolved story-style preset from `references/story_styles.json`
- workflow-state validation and final artifact checks
- saving the returned review as `script_reference_review.json`

`content-style-system` owns:

- routing to `viral-video-script -> anime-clip -> index + single common script-optimization reference`
- reading Obsidian writing-library files
- writing the initial story in task `anime_clip_initial_story_write` before hooks, retention brief, or script variants
- comparing candidate scripts to style rules and reference examples
- optionally reading `thai_food_1000m_viral` as a cross-domain hook/rhythm sample when the requested script needs a more viral short-video cadence
- identifying AI tone, rhythm, weak hook, style drift, and unsupported-claim issues
- returning the selected or rewritten script recommendation

Do not duplicate Obsidian file-selection logic in this skill. Pass the resolved style and evidence bundle to `content-style-system`; let that skill read the anime-clip index, the single common anime optimization reference, and its normal base files. The resolved preset is input metadata and may provide `story_styles.json` fallback examples; it is not a separate Obsidian preset page.

## Delegation Prompt Contract

Ask `content-style-system` to run `anime_clip_reference_review` with:

- resolved `decisions.story_style`, `decisions.story_style_label`, and `decisions.story_style_preset`
- relevant `script_style_guide.example_lines` and `script_style_guide.bad_good_examples` from `references/story_styles.json`
- `retention_brief.json`
- chosen hook from `hook_candidates.json`
- `initial_story_seed.json`
- `story_atoms.json`
- `source_blocks.json`
- `shot_block_report`
- every candidate in `script_variants.json`
- transcript/dialogue/visual-tag evidence needed to verify claims

The request should explicitly ask the writing skill to produce JSON-compatible content for `script_reference_review.json`.

Also save `content_style_execution_log` with the prompt summary, skill name, task name, source bundle paths, references read, result path, and any fallback references used. This log is gate evidence that the writing skill was invoked.

The row 11 request must also ask `content-style-system` to verify that the selected or rewritten final script inherits the story direction, claim boundaries, and source-evidence mapping from `initial_story_seed.json`. A script candidate that bypasses the early seed or introduces a new story premise must fail even if its prose style is strong.

The row 11 request must also ask for a sentence-level source map for the final script recommendation. Each final script sentence needs a `source_time`, `source_shot_ids`, `plot_function`, and `tts_budget_sec`. This is not subtitle timing; it is the pre-TTS contract that keeps copy rewrites bound to source material and prevents later alignment from stretching one rewritten sentence across the wrong shots.

Do not accept "看图写话" as plot narration. The writing skill must identify visual-caption-only lines: lines that merely describe the frame without explaining cause, choice, consequence, danger, relationship shift, question, or payoff. The selected or rewritten script must have `visual_caption_line_count=0`.

## Review Schema

Write `script_reference_review.json` with this minimum shape:

```json
{
  "resolved_story_style": "style_05_highlight_segment_selection",
  "style_label": "Highlight Segment Selection",
  "content_style_skill": "content-style-system",
  "content_style_task": "anime_clip_reference_review",
  "obsidian_references_used": [
    "/Users/gxator.alli/Documents/Obsidian/content-style-vault/30-style-families/viral-video-script/categories/anime-clip/script-optimization-reference.md"
  ],
  "fallback_references_used": [
    "references/story_styles.json#styles/style_05_highlight_segment_selection/script_style_guide/example_lines",
    "references/story_styles.json#styles/style_05_highlight_segment_selection/script_style_guide/bad_good_examples"
  ],
  "candidate_reviews": [
    {
      "variant_id": "A",
      "style_fit": "pass",
      "source_support_risk": "low",
      "ai_tone_issues": [],
      "rhythm_issues": [],
      "unsupported_claims": [],
      "recommended_rewrite_actions": []
    }
  ],
  "selected_variant_id": "A",
  "final_rewrite_actions": [
    "compress generic explanation",
    "replace unsupported motive with visible action"
  ],
  "selection_rationale": "Best style fit with zero unsupported claims and clean source-block binding.",
  "initial_story_seed_inheritance": {
    "source": "analysis/initial_story_seed.json",
    "passed": true,
    "missing_seed_claims": [],
    "new_unseeded_claims": []
  },
  "sentence_source_map_audit": {
    "passed": true,
    "missing_sentence_maps": [],
    "stale_time_maps": [],
    "tts_budget_warnings": []
  },
  "plot_explanation_audit": {
    "passed": true,
    "visual_caption_lines": [],
    "rewritten_to_causality": [
      {
        "before": "白色舱门旁有一个人影。",
        "after": "门里还有人没出来，求救声把外面的人拖回舱口。"
      }
    ]
  },
  "revised_script": null,
  "checks": {
    "style_fit_passed": true,
    "unsupported_claims_count": 0,
    "initial_story_seed_inherited": true,
    "sentence_source_map_passed": true,
    "tts_budget_passed": true,
    "plot_explanation_passed": true,
    "visual_caption_line_count": 0
  }
}
```

## Review Rules

- Fail the gate if `content-style-system` reports any selected-script claim that is not supported by footage, dialogue, subtitles, frame tags, or already accepted story atoms.
- Fail the gate if the selected script does not inherit `initial_story_seed.json` or if it introduces a new story premise not present in the early seed.
- Treat AI-tone, rhythm, weak-hook, and style-drift findings from `content-style-system` as required rewrite actions before final script selection.
- Prefer a simpler source-supported line over a more dramatic unsupported line.
- Preserve the resolved preset. Do not turn a `style_05` highlight segment into a `style_01` nonlinear teaser unless the user changes the story style.
- Review rhythm before shot mapping: each script unit should be short enough to bind to one source block or adjacent block pair.
- Review sentence mapping before shot mapping: each final script sentence must be covered by `sentence_source_map`, and each map must point to the exact source material window the sentence is allowed to narrate.
- Review plot explanation before copy approval: rewrite visual-caption-only sentences into source-supported causality, consequence, danger, relationship shift, or question. Do not pass a script just because every sentence names a visible object.
- Keep technical shot thresholds in `workflow_state.json` and QC reports. Do not copy them into the general Obsidian writing rules.

## Final Script Sentence Map

When the selected or rewritten script is saved to `script.json`, every `script_units[]` entry must include:

```json
{
  "unit_id": 4,
  "text": "门里还有人没出来，外面的人只能退回舱口。",
  "source_time": [916.958, 922.171],
  "evidence_shots": ["shot_0289", "shot_0290"],
  "plot_role": "danger_reversal",
  "sentence_source_map": [
    {
      "sentence_id": "u04_s01",
      "text": "门里还有人没出来，外面的人只能退回舱口。",
      "source_time": [916.958, 922.171],
      "source_shot_ids": ["shot_0289", "shot_0290"],
      "plot_function": "danger_reversal",
      "tts_budget_sec": 4.2,
      "source_evidence": ["visible person at hatch", "dialogue: get me out"]
    }
  ]
}
```

`source_time` at the unit level is the outer bound. `sentence_source_map[].source_time` is the narrower sentence-level bound used for script-to-shot mapping and post-rewrite TTS pacing. If row 11 changes sentence boundaries, wording, order, or line count, regenerate the map instead of preserving the old one.

## Workflow State Contract

After the review passes, set:

- `artifacts.script_reference_review = "script_reference_review.json"`
- `artifacts.content_style_execution_log = "review/content_style_execution_log.json"`
- `checks.content_style_skill_invoked = true`
- `checks.script_reference_review_done = true`
- `checks.script_reference_review_candidate_reviews_done = true`
- `checks.script_reference_review_references_recorded = true`
- `checks.script_reference_style_fit_passed = true`
- `checks.script_reference_unsupported_claims_count = 0`
- `checks.script_reference_initial_story_seed_inherited = true`
- `checks.script_sentence_source_map_done = true`
- `checks.script_sentence_source_map_coverage_passed = true`
- `checks.script_sentence_tts_budget_passed = true`
- `checks.script_plot_explanation_passed = true`
- `checks.visual_caption_line_count = 0`

Only then select final `script.json`, map `final_shots.json`, and run `retention_qc.json`.
