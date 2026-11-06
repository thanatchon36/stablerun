# LinkedIn post

**Image:** `docs/assets/linkedin_poster.png` (portrait 4:5, 2160 x 2700, the format that fills the most of a phone
screen in the feed), rebuilt from `results/tables` by `scripts/make_linkedin_poster.py`. A 16:9 alternative is
`docs/assets/linkedin_card.png`.

**Alt text for the image:** Poster for the working paper "When Stablecoins Run". A run on an issuer the size of
today's largest raises three-month Treasury bill yields by about 21 basis points while selling no bills; instead,
$63 billion of maturing bills are not rolled over. The 25 basis point mark is crossed at 1.4 to 2 times today's
size. Panels show the model's pipeline from holders to the bill market, one simulated run day by day, peak yield
impact against issuer size, and the effect of four policy levers.

Every number below is in the paper and on the poster. Post the links as the first comment.

---

## Post (English, about 2,700 characters)

What happens to the US Treasury bill market when a major stablecoin runs?

I built a 10,000-agent simulation to find out, and ran it 83,500 times.

The short answer: the danger is not the fire sale everyone expects. It is the buyer that quietly disappears.

Stablecoin issuers have become large holders of T-bills, and the GENIUS Act pushes their reserves further into bills of 93 days or less. So the question is no longer whether a run reaches the Treasury market, but how, and how hard.

Inside the model:
• 10,000 holders who exit on private signals, the depeg and what their peers do
• a secondary market where arbitrageurs buy discounted tokens and redeem them at par
• a redemption queue throttled by processing capacity
• an issuer that pays through a waterfall: cash, repo, fund shares, maturing bills, then sales
• a bill market with permanent and temporary price impact
Calibrated to two real runs: USDC in March 2023 and USDT in May 2022.

Three findings:

1. The fire sale never comes.
A run on an issuer the size of today's largest lifts three-month bill yields by about 21 bp, yet the issuer sells no bills at all. Payouts are throttled and funded by maturing bills, so the market loses a buyer at auction ($63 bn not rolled over) instead of facing a seller.

2. Size is the problem, and the line is close.
Under square-root price impact, the 25 bp mark is crossed at 1.4 to 2 times today's size and 50 bp at 5.5 to 8 times. Under linear impact, both are crossed already today.

3. Each lever protects someone different.
In a solvency run at five times today's size with fast redemption rails, a 30% cash buffer cuts the bill-market footprint from 41 to 15 bp and outright sales from $153 bn to zero, yet does nothing to stop the run. Redeeming at net asset value instead of par lifts the price trough from $0.75 to $0.83. Redemption fees barely matter.

The biggest unknown: how fast redeemed cash flows back into bills through money market funds. If it goes to bank deposits instead, the footprint quadruples.

Everything is open: a 23-page working paper, code that rebuilds every table and figure in one command, all 10,000 baseline paths on Hugging Face, and a DOI on Zenodo. Links in the first comment.

Caveats up front: some institutional inputs are flagged for verification, the model fits redemption volumes better than price troughs, and it is a stress test, not a forecast.

If you work on stablecoin reserves, money markets or Treasury market plumbing, I would value your critique. Where would you push the model next?

Personal research; views are my own.

#Stablecoins #TreasuryBills #FinancialStability #AgentBasedModeling #GENIUSAct

---

## First comment (links)

Paper (PDF): https://github.com/thanatchon36/stablerun/raw/main/paper.pdf
Code: https://github.com/thanatchon36/stablerun
Data: https://huggingface.co/datasets/thanatchon36/stablerun
DOI: https://doi.org/10.5281/zenodo.23996044

---

## Post (Thai)

ถ้า stablecoin รายใหญ่เกิด run ขึ้นมา ตลาด T-bill ของสหรัฐฯ จะเป็นอย่างไร?

ผมสร้างแบบจำลองที่มีผู้ถือเหรียญ 10,000 รายเพื่อหาคำตอบ และรันไปทั้งหมด 83,500 รอบ

คำตอบสั้นๆ คือ อันตรายไม่ได้อยู่ที่ fire sale อย่างที่หลายคนคาด แต่อยู่ที่ "ผู้ซื้อ" ที่ค่อยๆ หายไปจากตลาด

ทุกวันนี้ผู้ออก stablecoin กลายเป็นผู้ถือ T-bill รายใหญ่ และ GENIUS Act ยังผลักให้ทุนสำรองไปอยู่ใน T-bill อายุไม่เกิน 93 วันมากขึ้นอีก คำถามจึงไม่ใช่ว่า run จะกระทบตลาดพันธบัตรหรือไม่ แต่คือกระทบผ่านช่องทางไหน และแรงแค่ไหน

ในแบบจำลองมี
• ผู้ถือ 10,000 ราย ที่ตัดสินใจถอนจากสัญญาณส่วนตัว ราคาที่หลุด peg และพฤติกรรมของคนรอบข้าง
• ตลาดรองที่ arbitrageur ซื้อเหรียญราคาต่ำแล้วนำไปไถ่ถอนที่ par
• คิวไถ่ถอนที่ถูกจำกัดด้วยกำลังการประมวลผลของผู้ออก
• ผู้ออกที่จ่ายเงินตามลำดับ: เงินสด, repo, หน่วยลงทุนกองทุนตลาดเงิน, T-bill ที่ครบกำหนด แล้วจึงขายพันธบัตร
• ตลาด T-bill ที่มี price impact ทั้งแบบถาวรและชั่วคราว
calibrate กับเหตุการณ์จริง 2 ครั้ง คือ USDC เดือนมีนาคม 2023 และ USDT เดือนพฤษภาคม 2022

สามข้อค้นพบ

1. Fire sale ไม่เคยมาถึง
run ของผู้ออกที่ใหญ่เท่าเจ้าใหญ่ที่สุดในวันนี้ ดันอัตราผลตอบแทน T-bill อายุ 3 เดือนขึ้นราว 21 bp แต่ผู้ออกไม่ได้ขายพันธบัตรเลยสักดอลลาร์ เพราะการจ่ายเงินถูกจำกัดด้วยคิวและใช้เงินจากพันธบัตรที่ครบกำหนด ตลาดจึงเสียผู้ซื้อในการประมูล (ไม่ rollover 63 พันล้านดอลลาร์) แทนที่จะเจอผู้ขาย

2. ขนาดคือปัญหา และเส้นอันตรายอยู่ไม่ไกล
ภายใต้ square-root price impact ผลกระทบทะลุ 25 bp เมื่อผู้ออกใหญ่ขึ้น 1.4 ถึง 2 เท่าของวันนี้ และทะลุ 50 bp ที่ 5.5 ถึง 8 เท่า ถ้าเป็น linear impact ทั้งสองเส้นถูกข้ามไปแล้วตั้งแต่วันนี้

3. เครื่องมือแต่ละตัวปกป้องคนละกลุ่ม
ใน solvency run ที่ขนาด 5 เท่าของวันนี้และไถ่ถอนได้เร็ว cash buffer 30% ลดผลกระทบต่อตลาด T-bill จาก 41 เหลือ 15 bp และลดการขายพันธบัตรจาก 153 พันล้านดอลลาร์เหลือศูนย์ แต่หยุด run ไม่ได้เลย การไถ่ถอนตาม NAV แทน par ยกราคาต่ำสุดของเหรียญจาก 0.75 เป็น 0.83 ดอลลาร์ ส่วนค่าธรรมเนียมไถ่ถอนแทบไม่มีผล

ตัวแปรที่สำคัญที่สุดที่แบบจำลองตอบเองไม่ได้ คือเงินที่ถูกไถ่ถอนไหลกลับเข้า T-bill ผ่านกองทุนตลาดเงินเร็วแค่ไหน ถ้าเงินไปอยู่ในเงินฝากธนาคารแทน ผลกระทบจะเพิ่มเป็นสี่เท่า

ทุกอย่างเปิดหมด: working paper 23 หน้า โค้ดที่สร้างทุกตารางและทุกกราฟใหม่ได้ด้วยคำสั่งเดียว Monte Carlo baseline ครบ 10,000 เส้นทางบน Hugging Face และ DOI บน Zenodo ลิงก์อยู่ในคอมเมนต์แรกครับ

ข้อควรระวัง: ข้อมูลเชิงสถาบันบางส่วนยังต้องตรวจสอบกับแหล่งต้นทาง แบบจำลองจับปริมาณการไถ่ถอนได้ดีกว่าจุดต่ำสุดของราคา และนี่คือ stress test ไม่ใช่การพยากรณ์

ใครทำงานด้านทุนสำรองของ stablecoin กองทุนตลาดเงิน หรือโครงสร้างตลาดพันธบัตร ยินดีรับคำวิจารณ์ครับ คิดว่าควรต่อยอดแบบจำลองไปทางไหนต่อดี?

งานวิจัยส่วนตัว ความเห็นเป็นของผมเอง

#Stablecoins #TreasuryBills #FinancialStability #AgentBasedModeling #GENIUSAct

---

## Short version (English)

What happens to Treasury bills when a major stablecoin runs?

I built a 10,000-agent simulation, calibrated to USDC 2023 and USDT 2022, and ran it 83,500 times.

• At today's size: bill yields up about 21 bp, with no bills sold. The market loses a buyer at auction, not a seller in a fire sale.
• At 1.4 to 2 times today's size, the 25 bp mark is crossed.
• Cash buffers protect the Treasury market, NAV redemption protects holders, fees protect neither.

Paper, code, data and DOI in the first comment.

#Stablecoins #TreasuryBills #FinancialStability
