# B160: India, November 2016 — one withdrawn note, two paths, and an exchange cap that narrowed in steps

RECORD: `results/b160_exchange_deposit.json`
SCRIPT: `experiments/b160_exchange_deposit.py` (`--selftest`, 23 checks); sources fetched by `experiments/b160_fetch.py`
DATA: `data/raw/b160/` (text snapshots with fetch time and SHA-256; see `data/SOURCES.md`, section B160)

## 1. The carrier

On 8 November 2016 the ₹500 and ₹1,000 notes lost legal tender status. From 10 November a holder had two ways to
turn a withdrawn note into something that still worked:

- **exchange** it for cash over the counter, capped per person, with proof of identity;
- **deposit** it into a bank account, with no cap (accounts without complete KYC were limited to ₹50,000).

Both paths credit the face value. The exchange cap moved in steps, each fixed by a Reserve Bank circular:

| Date | Step | Source |
|---|---|---|
| 2016-11-10 | exchange up to ₹4,000 per person | circular DCM (Plg) 1226, 2016-11-08 |
| 2016-11-13 | ₹4,500, "immediate effect"; separate queues for exchange and deposit | DCM (Plg) 1272 |
| 2016-11-15 | indelible ink on the right index finger, metro cities first | DCM (Plg) 1280 |
| 2016-11-18 | ₹2,000, "only once per person" | DCM (Plg) 1302 |
| 2016-11-25 | no exchange at bank counters after midnight of 24 November; Reserve Bank counters continue "upto the current limits per person" | DCM (Plg) 1391; press release 2016-2017/1317 |

So the exchange edge narrowed and, at bank counters, was then cut, while the deposit edge stayed open. The framework's
reading of a quantity limit is that it leaves the price where it is and changes who can get through (a bound above zero
narrows an edge; a bound of zero deletes it). This station reads the flow on the narrowed edge.

## 2. What the Reserve Bank printed

Banks reported daily on a form with two rows, "Exchanged in Cash" and "Deposits into Account" (circular DCM (Plg) 1264,
2016-11-11, Annex 6). The Reserve Bank published the two rows apart in two press releases:

| Release | Window | Total | Exchange | Deposits | Withdrawn by the public |
|---|---|---|---|---|---|
| 2016-2017/1265, 2016-11-21 | 10–18 Nov | 5,44,571 | 33,006 | 5,11,565 | 1,03,316 |
| 2016-2017/1349, 2016-11-28 | 10–27 Nov | 8,44,982 | 33,948 | 8,11,033 | 2,16,617 |

(₹ crore.) To find every release that carries the split, all 740 press releases from 8 November 2016 to mid-January
2017 and the 110 circulars of the same period were opened; 78 concern the withdrawn notes, and these two are the only
ones that print exchange and deposits apart. From 8 December the releases print notes issued to the public, and on
13 December the deputy governors gave notes returned to the Reserve Bank and currency chests (₹12.44 lakh crore by
10 December), a different object.

## 3. Criteria and readings

Criteria come in kinds: `instrument` asks whether the figures were read as printed, `premise` asks whether the carrier
gives the object the readings need, and `own_reading` is a reading this station registers. There is no rival criterion:
a scalar price field puts one price on both paths and says nothing about how flow splits between them, and the
framework gives no opposite point prediction on that cell.

| | criterion | reading |
|---|---|---|
| PASS | B160-1 `instrument` **parts add to the total** | 10–18 Nov: residue 0; 10–27 Nov: residue 1 crore, the rounding of three figures to whole crore |
| PASS | B160-2 `instrument` **release words are report rows** | "exchange amounted to" and "deposits amounted to" are the "Exchanged in Cash" and "Deposits into Account" rows; both releases name the counters of the Reserve Bank and of the banks |
| PASS | B160-3 `premise` **two cumulative points** | 850 pages read, 78 on the withdrawn notes, two with the split (prid 38643, 38727) |
| PASS | B160-4 `own_reading` **dose table** | 10–18 Nov (9 days): exchange 3,667.3 crore a day, deposits 56,840.6; days at ₹4,000: 3, at ₹4,500 without ink: 2, with ink: 3, at ₹2,000 once per person: 1. 19–27 Nov (9 days): exchange 104.7 a day, deposits 33,274.2; ₹2,000 with ink at all counters: 6 days, Reserve Bank counters only: 3 days |
| PASS | B160-5 `own_reading` **who gets through, not how much each carries** | daily exchange fell by a factor of 35.04 (35.02 to 35.06 under crore rounding). The amount per counter event can fall at most from ₹4,500 to one ₹500 note, a factor of 9, so the number of counter events fell at least 3.89-fold; if everyone exchanged the cap in force and the first segment's flow came on its ₹4,000 and ₹4,500 days, 15.6 to 17.5-fold. Events: 7.33 to 66.0 crore in the first segment, 0.471 to 1.884 crore in the second |
| PASS | B160-6 `own_reading` **the deposit path** | exchange share of notes tendered: 6.06% then 0.31%. Deposits' own daily flow fell too (ratio 0.585): cumulative deposits rose, the flow did not. Had exchange fallen like deposits it would have been 19,321.6 crore; the shortfall, 18,379.6 crore, is 6.1% of second-segment deposits |

The selftest plants a wrong input for every flag and checks that it flips; eight deliberate faults in the
implementation (hard-wired flags, a one-release premise, the bound taken against the wrong cap, the ink date ignored,
deposits not differenced) are each caught.

## 4. Reading

The narrowed edge did not carry the same flow at a lower amount. Per-event amount can account for at most a factor of
nine of the thirty-five; the rest is fewer people getting through. That is the form the framework gives a positive
bound: same price, different reach. Withdrawals from accounts rose from the first segment to the second (1,03,316 to
1,13,301 crore), so the accounts that took the deposits were in use.

## 5. Scope

- Each segment holds more than one regime (cap level, once-per-person, ink, closure of bank counters). The fall belongs
  to these steps together; how much each step carries is not separable on two cumulative points.
- Deposits slowed as well. Whether the exchange shortfall moved into deposits cannot be separated from the general
  slowing of tenders; the shortfall is small against the deposit flow, so the deposit path had room for it.
- The two paths deliver different things (cash against an account balance with a weekly cash withdrawal limit of
  ₹24,000 from 13 November); the readings depend only on both crediting face value.
- Banks reported daily; only two cumulative points were published, so the daily shape is not read.
- The last three days of the second segment had Reserve Bank counters only; their share of the 942 crore is not printed.
