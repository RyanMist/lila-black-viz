# Three Insights — LILA BLACK Player Data

---

## Insight 1: Player retention collapsed 88 % in five days

**What caught my eye**
Opening the Event Map and cycling through the five individual dates (Feb 10 → Feb 14) is almost shocking. The scatter density drops so fast it looks like a bug before the numbers confirm it.

**The concrete numbers**
| Date | Unique human players |
|------|---------------------|
| Feb 10 | 98 |
| Feb 11 | 81 |
| Feb 12 | 59 |
| Feb 13 | 47 |
| Feb 14 | 12 |

That is an 88 % drop across 796 total matches and only five days of live data.

**Is this actionable?**
Yes — and it is the most urgent signal in the dataset.

*Metrics affected:* D1 / D3 / D5 retention, daily active players, match fill rate.

*Actionable items:*
- Audit the new-player funnel: does the first session give a player enough agency to want to come back? (Map the Event Map for first-session-only players and compare kill/loot/death ratios to returning players.)
- Check matchmaking queue times for Feb 11–14: if lobbies took too long to fill, players quit before the match started and those events never landed in the dataset.
- Instrument a re-engagement prompt after the first session — even a simple "you ranked X out of Y today" push notification.

**Why a level designer should care**
If players are not returning, their routing feedback is almost entirely first-impressions data. A level designer using this tool to balance spawn density or loot placement is, unknowingly, optimising for a cohort that never reached match 3. The heatmaps for Feb 10 (n=98) and Feb 14 (n=12) will look very different — make sure any tuning pass labels which day's data it is based on.

---

## Insight 2: PvP is virtually non-existent — the game plays like PvE

**What caught my eye**
The Event Map's Kill marker layer is very sparse. Switching the filter to show only human Kill events (untick Bots under Players) and the map goes almost blank. The raw count made me re-check the filter code twice.

**The concrete numbers**
Across all 796 matches and 89,104 events there are **5 human Kill events** in total.
For comparison, there are 4,431 BotKill events.
The human kill-to-bot-kill ratio is **0.1 %**.

**Is this actionable?**
Yes — the finding is ambiguous on intent, which makes it worth a design conversation, not just a tuning pass.

*Metrics affected:* PvP engagement rate, player encounter rate per match, session length (PvP-driven tension extends sessions; its absence may shorten them).

*Actionable items:*
- **If PvP was intended:** check lobby fill. With only 12 human players active on Feb 14, most lobbies would have had 1 human — you can't have a PvP encounter with yourself. Increase human player density per lobby before concluding map design needs to change.
- **If PvP avoidance is the meta:** verify map design supports that intentionally — safe extraction corridors, enough cover to disengage, loot density that does not force players into the same room. Use the Heatmap's Kill Zones layer to see whether the 5 kills cluster in chokepoints (unintended funnel) or are spread across the map (intentional risk/reward).
- **Either way:** add a "player encounter" event (players within N metres of each other without a kill) so future datasets can distinguish "no PvP by choice" from "no PvP because no one else was there".

**Why a level designer should care**
Map layout is built around anticipated player interactions. If the implicit assumption was that players would fight each other over extraction routes, but the data shows zero PvP, every chokepoint and cover decision needs to be re-evaluated. This single number invalidates a large class of level-design assumptions.

---

## Insight 3: GrandRift and Lockdown have 3× the storm death rate of AmbroseValley

**What caught my eye**
Switching the Heatmap to the "Storm Deaths" layer and toggling between maps — AmbroseValley shows a thin scatter near one edge; GrandRift and Lockdown show dense clusters near two or three map edges each.

**The concrete numbers**
| Map | Total deaths | Storm deaths | Storm death rate |
|-----|-------------|-------------|-----------------|
| AmbroseValley | 3,941 | 133 | 3.4 % |
| GrandRift | 1,996 | 192 | 9.6 % |
| Lockdown | 2,271 | 208 | 9.2 % |

GrandRift and Lockdown kill players via storm at nearly three times the rate of AmbroseValley.

**Is this actionable?**
Directly — this is the most level-design-specific finding in the dataset.

*Metrics affected:* per-map session completion rate, storm-death frustration signals (if player feedback data exists), effective playable zone area.

*Actionable items:*
- Open the Heatmap "Storm Deaths" layer for GrandRift and Lockdown and identify the specific edges where the clusters are densest. Those are the locations where the storm boundary is leaving players with insufficient escape time or too few viable routes.
- Cross-reference storm death clusters with the "High Traffic (All Movement)" heatmap. If high-traffic zones are adjacent to high-storm-death zones, the map is funnelling players into storm range — either widen the extraction corridor or shift a loot anchor point inward to pull players away from the boundary earlier.
- Consider adjusting storm shrink timing or the shape of the final safe zone on those two maps. AmbroseValley's lower rate suggests its storm geometry is better calibrated — use it as the reference when tuning the other two.

**Why a level designer should care**
Storm deaths caused by poor map geometry are frustrating in a way that player-vs-player deaths are not: the player had no counterplay. A spike in storm deaths on specific maps is a leading indicator of negative word-of-mouth and accelerated churn — which, given insight #1 above, this game can ill afford right now.
