# LinkedIn post (draft, ~150 words)

What happens to the Treasury bill market when a stablecoin runs?

I built an agent-based stress test, calibrated to the USDC (March 2023) and USDT (May 2022) episodes, and let it run on an issuer the size of today's largest. Three things surprised me:

1. The issuer sells almost no bills. Redemptions are throttled by processing capacity and funded by maturing bills, so the hit to the market is demand withdrawn at auction, not a fire sale. Peak impact on 3-month yields: about 20 bp.

2. Size is the problem. Under square-root price impact the 25 bp mark is crossed at 1.4-2x today's size and 50 bp at 5.5-8x. Under linear impact, both already today.

3. Cash buffers protect the Treasury market; NAV-based redemption protects holders; redemption fees protect nobody.

Working paper, code and every table reproducible in one command: [link]. All inputs are flagged for verification; this is a stress-testing tool, not a forecast. Feedback very welcome.

#stablecoins #Treasury #financialstability #agentbasedmodeling
