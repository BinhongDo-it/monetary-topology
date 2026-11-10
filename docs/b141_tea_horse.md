# B141: Ming tea for horses, one horse and two prices

The tea-horse offices bought horses for tea at a price the state wrote down; private tea bought them at
the private market's price, and the state cut the private channel by statute. Script
`experiments/b141_tea_horse.py`; record `results/b141_tea_horse.json`.

## 1. The square

Office `j`, year `t`, grade `g`; official price `x(j,t,g)` and private price `y(j,t,g)` in jin of tea:

    square = ln y - ln x     on pairs matching place, period, grade and tea
    rival  = 0               a horse has one price in tea, whoever buys it

A feature a record does not state matches nothing: two records silent on the grade are not thereby of one
grade. A quote is good to half the last place of the unit it is printed in (three bao is 125 to 175 jin), and
a pair reads non-zero only when the two printed intervals share no value.

Units: one jin is 16 liang; a bao is 50 jin and a yin two bao (Hongwu 4). The bi changed weight and every
reading is kept: early Ming 7 jin (10 in Wang Qi's edition); from Zhengde 10 (1515), 330 bi to 1,000 jin,
3.03 jin of tea each (6.25 jin gross); from Longqing 5 (1571) at most 7 jin; early Qing 10 jin. The square
is read under each of the three readings and left unread where they disagree.

## 2. Readings

**B141-1** (instrument): units, grades, pairing, the printed interval of a quote, the dose encoder, the
intake comparison and the check of the posted prices agree with their known answers on synthetic records;
15 seeded faults are caught, among them reading 堪中马 ("a horse fit to be taken") as the middle grade,
pairing two records that are both silent on a feature, taking half a jin as the last place of a quote counted
in bao, reading one weight of the bi alone, and letting a quota into the count of horses taken.

**B141-2** (known answer): the oft-cited Hongwu price 120/70/50 is Taizu shilu 196, 1389, at Yazhou for
the Changhexi merchants, with a third grade of foals and the clause that merchants who do not wish may
refuse. The Qin-He price recalled in 1409 is 80/60/40.

**B141-3** (rival, unread): no official and private price match on all four features. One bound: Li
Dongyang, in an essay of about 1471-72, puts the private price between 80 and 200 jin. One ungraded
estimate: 1466, Ganzhou, a good horse for 100 jin of tea and 15 shi of barley.

**B141-3b** (rival, grid B): the sign of the gap, read from dated statements. No source gives the size of
the gap between the channels; the sources state its direction again and again. With the private channel
open, sellers leave the office, "the horse grows dear and tea cheap", office tea loses its value; with it
cut, tea grows dear at the border and the horses come. Both report one sign: the private channel pays the
seller more than the office does. On the rival's premise the seller is indifferent between the two, and
such reports carry no common sign.

Twenty-four statements read in the original (the Veritable Records, Yang Yiqing's memorials, the Huang Ming
jingshi wenbian, the Jiubian kao), in 22 different years from 1397 to 1597, across seven reigns: Hongwu,
Xuande, Zhengtong, Chenghua, Hongzhi, Jiajing, Wanli. None goes the other way. The unit is the reign, the
coarsest the sources allow; at one half per reign the rival's probability is 0.0078 (by year it would be
2.4e-7; taking 1435 with the Zhengtong reign gives six reigns and 0.0156). Twenty-one open the channel and
three cut it (1473, 1503, 1504). Three carry a year that is inferred or a span: Li Dongyang's essay (about
1471-72, from its account of the Ordos), the Jiubian kao (about 1541, the year of the book) and Zheng Luo's
memorial (1590-91). Later compilations saying the same (the Mingshan cang, the Ming shi, the
Wanli Shaanxi gazetteer at second hand) are printed and not counted, as is one entry of 1433 that states
no sign. This reads the sign only; the size of the gap is B141-3 and stays unread.

**B141-4**: realized official price, tea paid over horses taken, in the north-west: 28.7 (1380), 29.0
(1392), 37.0 (1398), 36.1 (1410), 84.4 (1435), 42.6 (1447), 86.9 (1508). At Diaomen, Sichuan, the same
channel paid about 962 jin a head in 1387, 1,800 before the posting of 1389, and 1,186 in 1409 when "the
tea ban slightly relaxed", ten times the posted 120. Horses by enforcement segment, what was taken and what
was due kept apart:

| segment | enforcement | horses taken | due or quota (listed, not compared) |
|---|---|---|---|
| 1393-1449 | gold tallies, death penalty, patrol monthly to 1435 and once in three months from then | campaigns of 13,518 (1398) and 13,000 (1435), one every three years: about 4,500 and 4,300 a year; parts: Hezhou 6,500 of 7,700 due (1432), five wei of the Xining side 2,946 (1447) | tally levy 14,051 every three years, arrears collected the next year |
| 1449-1502 | tallies stopped, patrol once in three months, then messengers and censors by turns, a censor a year from 1478 | 840.5 a year (5,043 in 1497-1502) | |
| 1503-1535 | a censor-in-chief in charge, the 1505 penalty, a tea-patrol censor | 2,488, 6,343, 4,298, 5,948 (1503-1506): 19,077 in four years, 5.67 times the six years before; about 9,000 in 1508 | |
| 1536-1644 | merchant tea opened inland; quotas | 6,370 (1571, four offices) | 4,800 (1556), 9,600 (1601), 9,724 a year before the Liao war as recalled in 1626, 11,088 at the end of Chongzhen, "in arrears every year" |

The comparison is of horses taken by the three offices: every year of 1503-1506 and both tally campaigns
stand above the 840.5 a year of 1497-1502. A censor stated the fall in 1502 (Xiaozong shilu 194): in early
Chenghua "ten thousand a year", of late "not one in ten" (other copies: "not two in ten"), laid to the ban on
private tea not holding and to merchant tea.

**B141-5**: the posted prices, each checked against its record (the record opened, the figures and the year
in it, dated rows in order). Top grade, in jin: 40 (1383), 80 (Hongwu, recalled in 1409), 60 (1410), thirty
more on a request (1435), 100 (1490), 120 (early Shunzhi). Li Dongyang's essay of about 1471-72, set as a
Hanlin examination, has the price still at 80/60/40 and proposes 200/100 with the reason written out: if
they covet the high price, private trade cannot run. No count of horses taken by the three offices stands
between 1435 and 1497, so whether the raising of 1490 came close upon a fall is not read from counts; the
statements are the essay and the censor's of 1502. The count after the raising of 1490 is the lowest on
file, and it rose when Yang Yiqing tightened enforcement from 1503, at a realized price near 87 jin. The
gold tallies' end has three primary dates (1406, 1416, 1449); the two Yongle dates are followed by the
1435 reissue, so 1449 can be a second stop, and Yang's "nearly sixty years since the tallies were
abolished" (1504) points to it. The three chains agree from 1449.

**B141-6** (bookkeeping): 108 horse-count and price records, each with its source; private prices found
in no Ming period.

## 3. Carriers

Ming shilu (Academia Sinica edition); Da Ming huidian (Zhengde and Wanli); Ming shi, bingzhi and shihuo
zhi; Yang Yiqing, Guanzhong zouyi, juan 3; Mazheng ji; Qinbian jilue; Yongzheng Shaanxi tongzhi and
Qianlong Gansu tongzhi; Tani Mitsutaka 1966, Shirin 49.
