# STS2 Behavior Questions For User

## Q1. AoE damage should use what planner abstraction?

- Scope: a class of cards
- Sample cards:
  - `AstralPulse` / Astral Pulse
  - `DramaticEntrance` / Dramatic Entrance
  - `DaggerSpray` / Dagger Spray
- Raw text:
  - `Deal {Damage:diff()} damage to ALL enemies.`
  - `Deal {Damage:diff()} damage to ALL enemies twice.`
- Possible interpretations:
  - treat as single-target proxy damage against the current planner enemy
  - add true multi-enemy state and AoE semantics
  - keep unimplemented until planner supports multiple enemies
- Preferred option:
  - keep unimplemented until there is an explicit AoE abstraction
- Why uncertain:
  - current engine state has one `enemy_state`; collapsing AoE to one enemy may overestimate kill pressure and distort planning
- Impact:
  - a large class of attack cards

## Q2. Random-target cards can be approximated or must remain exact?

- Scope: a class of cards
- Sample cards:
  - `Ricochet`
  - `RipAndTear`
  - `BouncingFlask`
- Raw text:
  - `Deal {Damage:diff()} damage to a random enemy {Repeat:diff()} times.`
  - `Apply {PoisonPower:diff()} Poison to a random enemy {Repeat:diff()} times.`
- Possible interpretations:
  - map them as deterministic single-target actions against the current enemy
  - model expected-value damage/debuff
  - keep unimplemented until randomness/targeting is explicit
- Preferred option:
  - keep unimplemented
- Why uncertain:
  - target randomness interacts strongly with enemy count and kill ordering
- Impact:
  - a visible but still bounded class of attack and debuff cards

## Q3. Persistent trigger powers should be mapped now or deferred?

- Scope: a class of cards
- Sample cards:
  - `Afterimage`
  - `Caltrops`
  - `Juggernaut`
  - `Arsenal`
- Raw text:
  - `Whenever you play a card, gain {AfterimagePower:diff()} Block.`
  - `Whenever you gain Block, deal {JuggernautPower:diff()} damage to a random enemy.`
- Possible interpretations:
  - add a small set of persistent trigger builders now
  - support only deterministic self triggers, defer random ones
  - keep power triggers out of scope until a broader trigger design is agreed
- Preferred option:
  - support only deterministic self triggers after user confirms the trigger abstraction boundary
- Why uncertain:
  - some powers are straightforward, but mixing them with random targets and external resources quickly expands the event model
- Impact:
  - many power cards and some relic-like effects

## Q4. How should STS2-specific resource systems be abstracted?

- Scope: multiple classes of cards
- Sample cards:
  - `BallLightning` / orb channel
  - `Afterlife` / summon
  - `Bulwark` / forge
  - `BorrowedTime` / doom
  - `Venerate` / stars
- Raw text:
  - `Channel 1 Lightning.`
  - `Summon {Summon:diff()}.`
  - `Forge {Forge:diff()}.`
  - `Apply {DoomPower:diff()} Doom to yourself.`
- Possible interpretations:
  - add placeholder counters only for display/statistics but not planner semantics
  - add one subsystem at a time starting from highest card count
  - keep all of them unimplemented until a resource roadmap is chosen
- Preferred option:
  - defer until you choose a resource priority order
- Why uncertain:
  - these mechanics are central to character identity and should not be flattened casually
- Impact:
  - over one hundred remaining cards

## Q5. Temporary buffs like “this turn” should be represented how?

- Scope: a class of cards
- Sample cards:
  - `Anticipate`
  - `FeedingFrenzy`
  - `CrushUnder`
- Raw text:
  - `Gain {DexterityPower:diff()} Dexterity this turn.`
  - `Gain {StrengthPower:diff()} Strength this turn.`
  - `All enemies lose {StrengthLoss:diff()} Strength this turn.`
- Possible interpretations:
  - encode them as buffs/debuffs with end-of-turn expiry
  - approximate them as permanent for the current turn only in the simulation branch
  - keep unimplemented until temporary stat lifetimes are explicit
- Preferred option:
  - add explicit turn-scoped modifiers only if you want temporary stat cards prioritized next
- Why uncertain:
  - current engine stores plain counters and does not track expiry for generic stat modifiers
- Impact:
  - several common and uncommon attack/skill cards

## Q6. In-hand passive curse/status effects belong in executable coverage or not?

- Scope: a class of cards
- Sample cards:
  - `Burn`
  - `Decay`
  - `BadLuck`
- Raw text:
  - `At the end of your turn, if this is in your Hand, take {Damage:diff()} damage.`
- Possible interpretations:
  - model them as passive triggers loaded into the deck runtime
  - keep them non-executable because they are not player actions
  - split catalog coverage from playable-action coverage
- Preferred option:
  - keep them out of executable action coverage for now, but possibly load them as passive metadata later
- Why uncertain:
  - they affect planning, but not through legal card-play actions
- Impact:
  - curse/status realism and end-turn evaluations

## Q7. “Return this to your hand next turn” should be handled as executable now?

- Scope: a small class of cards
- Sample cards:
  - `Bolas`
  - `ThrummingHatchet`
- Raw text:
  - `Deal {Damage:diff()} damage. At the start of your next turn, return this to your Hand.`
- Possible interpretations:
  - add delayed self-return with card identity tracking
  - approximate by drawing a replacement copy
  - keep unimplemented
- Preferred option:
  - keep unimplemented until card-identity return semantics are agreed
- Why uncertain:
  - current scheduler supports delayed effects, not delayed movement of a specific spent card instance
- Impact:
  - a small but nontrivial delayed-value attack group
