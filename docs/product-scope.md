# Product scope

## Product vision

LifeLenz-AI aims to help people understand personal wellness patterns using their own
longitudinal lifestyle data. It will organize records over time, establish individual
baselines, and turn measured changes into explainable observations. The product is intended
to support reflection and informed habit tracking, not clinical interpretation.

## Problem statement

Personal wellness data is often difficult to use effectively:

- Records are fragmented across apps, devices, spreadsheets, and notes.
- Individual metrics are presented without enough historical or cross-category context.
- Generic targets and advice may not reflect a person's usual range or goals.
- It is difficult to inspect how sleep, activity, hydration, mood, energy, and stress vary
  together over time.
- Automated observations often do not expose the evidence or reasoning behind them.

LifeLenz-AI is intended to provide a coherent, personal-baseline-first view while keeping
the source data and calculation logic visible.

## Intended users

Initial users may include:

- People who already track lifestyle habits
- Fitness and wellness enthusiasts interested in longer-term patterns
- People consolidating manually recorded or exported wellness data
- People interested in personal trends and self-reflection rather than clinical diagnosis

These groups describe likely use cases, not a fixed commercial demographic or a claim that
the product currently serves every tracking workflow.

## Initial user scenarios

The MVP is intended to support scenarios such as:

- Reviewing whether recent sleep duration is below the user's established baseline
- Understanding whether activity has been consistent across recent weeks
- Comparing recorded hydration with a user-defined personal goal
- Observing whether recorded higher-energy days also contain better sleep measurements,
  without claiming that one caused the other
- Producing a weekly wellness summary whose observations link back to measurements,
  calculations, and deterministic rules

These observations describe associations, differences, and trends in the available data.
They must not imply causation or clinical significance.

## MVP scope

The first viable product is planned to include:

- Manually entered or imported structured wellness records
- Sleep records
- Activity records
- Hydration records
- Basic nutrition records
- Body measurements
- Mood, energy, and stress records
- Personal profiles and goals
- Personal-baseline analytics
- Trend and statistical summaries
- Deterministic, explainable insights
- Wellness summaries

Data import in this scope means support for explicitly defined structured formats. It does
not imply automatic compatibility with every external platform.

## Explicit non-goals

The initial product will not provide:

- Medical diagnosis or disease prediction
- Medication advice or treatment plans
- Emergency guidance
- Clinical decision support
- Direct wearable integrations in the first milestone
- Automated ingestion from every wellness platform
- Causal health claims based on observed associations
- A replacement for advice from qualified healthcare professionals

## Safety boundary

LifeLenz-AI operates on the general-wellness side of a clear boundary. It may summarize
user-provided lifestyle records, compare them with the same user's history or goals, and
describe non-causal patterns. For example, it may state that recorded sleep was lower than
a personal baseline during a selected period and show how that result was calculated.

It must not interpret a pattern as a symptom, assign a diagnosis, estimate disease risk,
recommend medication or treatment, or tell a user how to handle an emergency. Wellness
output should use neutral language and direct medical questions to qualified professionals.
Urgent situations require appropriate local emergency services, not product output.

## Product principles

### Personal-baseline first

Prefer comparisons with a person's own sufficient history and stated goals over generic
population thresholds. Clearly identify when there is not enough data for a useful baseline.

### Explainability by design

Every generated observation should identify its supporting data, period, calculation or
rule, and relevant uncertainty. An unexplained conclusion is not an acceptable insight.

### Privacy-aware architecture

Minimize the data required for each capability, keep ownership boundaries explicit, and
make future storage and retention choices deliberate. These are design requirements; the
current foundation does not yet claim implemented privacy or security controls.

### Conservative language

Describe what the records support. Avoid causal, diagnostic, prescriptive, or alarmist
wording, especially when data is sparse or incomplete.

### Progressive complexity

Begin with validated records, deterministic calculations, and testable rules. Add more
complex techniques only when they solve a demonstrated problem and can be evaluated safely.

### User-controlled data

Users should be able to understand what data is used and control future input, correction,
export, and deletion workflows. Those controls will be specified alongside the interfaces
and persistence mechanisms that implement them.
