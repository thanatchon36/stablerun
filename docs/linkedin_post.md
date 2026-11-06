# LinkedIn post

Image: `docs/assets/linkedin_card.png` (1200x675, rebuilt from `results/tables` by `scripts/make_linkedin_card.py`).

---

What happens to the US Treasury bill market when a stablecoin runs?

Stablecoin issuers now hold well over $200 bn of Treasury bills, and the GENIUS Act pushes their reserves further
into bills of 93 days or less. So I built an agent-based stress test to find out: heterogeneous holders who exit on
private signals, a visible depeg and what their peers do; a redemption queue that only authorised redeemers can
join; a secondary market where arbitrageurs turn discounts into redemptions; an issuer that pays through a
liquidation waterfall; and a bill market that absorbs outright sales and withdrawn auction demand. Calibrated to
USDC in March 2023 and USDT in May 2022.

Three results I did not expect:

1. The issuer sells almost no bills. Redemptions are throttled by processing capacity and paid out of maturing
bills, so the Treasury market loses a buyer at auction rather than facing a seller in a fire sale. Peak impact on
three-month yields at today's size: about 20 bp. The issuer's own fire-sale loss is negligible because bill
duration is tiny.

2. Size is the problem, and the threshold is not far. Under square-root price impact the 25 bp mark is crossed at
1.4-2x today's largest issuer and 50 bp at 5.5-8x. Under linear impact, both are crossed already today.

3. The levers do different jobs. A 20-30% cash buffer removes the Treasury-market footprint but does nothing for
the run; redeeming at net asset value instead of par halves the depeg; redemption fees change nothing. The single
most important unknown is how much redeemed cash returns to bills through money market funds.

Working paper, code and every table and figure reproducible with one command:
https://github.com/thanatchon36/stablerun

Caveats up front: the institutional inputs are flagged for verification, the model fits redemption volumes well
and price troughs less well, and it is a stress-testing tool, not a forecast. Feedback very welcome.

#stablecoins #TreasuryBills #FinancialStability #AgentBasedModeling #Fintech #GENIUSAct

---

## Short version (~90 words)

When a stablecoin runs, what happens to Treasury bills?

I built a calibrated agent-based stress test to find out. At today's size, a run on the largest issuer moves
three-month bill yields by about 20 bp, and the issuer sells essentially no bills: the market loses a buyer at
auction, not a seller in a fire sale. At 1.4-2x today's size the 25 bp mark is crossed; cash buffers protect the
Treasury market, NAV redemption protects holders, fees protect nobody.

Paper + fully reproducible code: https://github.com/thanatchon36/stablerun

#stablecoins #TreasuryBills #FinancialStability
