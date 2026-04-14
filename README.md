# Hammer-Reversals
Hammer and Shooting star reversal

Core Architecture
​Dual-Timeframe Strategy: It uses the 1-Hour candle as the Anchor (looking for a Hammer or Shooting Star to establish structure) and the 15-Minute candle as the Trigger (looking for a V-Flip breakout to confirm momentum).
​Woodie’s Level Intelligence: It specifically hunts for reversals at S1, R1, and the Woodie Pivot Point (PP).
​💎 ELITE: Reversals at S1/R1.
​🥇 PRIME: Reversals at the Woodie PP.
​Dynamic Trade Planning: Every alert automatically calculates a structural Stop Loss and two Woodie-based Targets (T1 & T2), eliminating guesswork during fast moves.
​🛡️ Automated Management
​9 EMA Trailing Exit: Once in a trade, the bot ignores the "noise" and rides the trend. It only signals an exit when a 15-minute candle closes across the 9 EMA, allowing you to capture massive "runners."
​Position Tracker: The script "remembers" active trades via active_positions.json, so it can manage your exits even if you aren't watching the terminal.
​Fail-Safe Engine: It silences API errors, handles rebranded tickers (like LTF and IDFCFIRSTB), and uses a safe-fetch wrapper to ensure the scan of all 200+ F&O stocks completes smoothly every 15 minutes.
​📊 Feedback Loop
​Weekly Trade Summary: Automatically logs every completed trade, calculating total Points Captured and Percentage Gains.
​ML Data Logging: Records the "DNA" of every signal (Volume Delta, Zone, and Timeframe context) so you can review which setups are performing best over time.
