# B140: the reign titles in a hoard record when an edge was open

A hoard is a sample of the coin in circulation when it was sealed. Coin reaches a place only while the
edge to its issuer is open, so the mix of issues in a hoard dates that edge. After 1127 the Song-Jin
edge was cut from both sides while the Southern Song kept casting. Script
`experiments/b140_hoard_vintage.py`; record `results/b140_hoard_vintage.json`.

## 1. The quantities

    S_h = Southern Song coins / Northern Song coins in hoard h
    Q_h = Southern Song coins cast after the cut / Southern Song coins cast before it
    rho = median S_h at the destination / median S_h inside Southern Song, same window; rho_Q likewise

The rival, outflow as a property of the issuer, predicts `rho = rho_Q = 1`. `Q_h` compares two batches
of Southern Song coin of similar weight and copper, so a preference for good coin in hoarding cancels in
it. From 1180 the reverse of a Southern Song coin carries its casting year, so the stable Song cut of
1179-01-26 can be applied coin by coin.

## 2. Dating

`T_h` is a lower bound on burial: the latest first-cast year among the coins present. A Jin, Liao or
Xixia hoard is dated only by coins the Song cut does not touch (Jin: Zhenglong 1158, Dading 1178, Taihe
1204; Xixia: Tianqing 1194, Huangjian 1210, Guangding 1211). Dating a Jin hoard by its latest Southern
Song coin would select on the outcome and pins every Jin hoard at 1178. The Jin bound is looser than the
Song one, and on the rival's reading a looser bound pushes Jin `S_h` up, toward `rho = 1`. Main window
`T_h >= 1204`; second window 1160-1189.

## 3. Readings

**B140-1** (instrument): on noiseless synthetic hoards `S_h`, `Q_h` and `rho` agree with their closed forms
to `1e-15`; a hoard-level bootstrap passes a cut world and does not pass a same-stock world; 16 seeded
faults are caught. Every coin label in the transcribed tables maps except one "unknown". Row 7 of Sato's table
(Chong'an) prints thirty coins with no name after the Xining pair, inside the Northern Song bracket, and reaches
its printed total of 1,227 only with them; they are read as Northern Song coin (`S_h` 0.0404).

**B140-2** (known answer): Suzuki 1992, table 4: Northern Song 17 of the top twenty in Japanese hoards.

**B140-3a** (printed): Jin territory has no hoard with a per-type table and `T_h >= 1204` yet. The one Jin
candidate, Beijing Youanmen (Li Wei, Zhongguo qianbi 2013-6), is a scatter in river silt with Taihe coins,
so `T_h >= 1204`; collectors counted Dading about 4,000, Taihe about 150 and Daguan ten-cash about 70, and the
types they list include no Southern Song coin. It is a list, not a per-type table. `rho` is printed and not
set against the rival: its denominator, Northern Song coin, is stock that Jin took by conquest and Xixia had
gathered before 1127, so a low `rho` follows on the rival's premise too. Only coin cast after the border
carries the border.

**B140-3b** (rival, unread): Southern Song territory now has six hoards with a per-type table in the window;
Jin territory has none, and `rho_Q` sets Jin against home, so it stays unread. The Jin side is empty by the
reach of the dating clock: after Dading (1178) Jin cast coin only once in quantity (Taihe, 1204), and across
Miyake's national census 59 hoards have Zhenglong or Dading as their latest Jin coin and one has a later one
(Zhongguo lishi wenwu 2004-3). A Jin hoard sealed after 1204 therefore dates to 1178 unless it holds Taihe or
a late Xixia coin. Two such hoards are on file, neither with a count by Southern Song type: Beijing Youanmen
(Taihe) and Ganquan Shehegou in Shaanxi (Xixia Huangjian, 1210), whose 284 Southern Song coins among 28,104
are of the types Jianyan, Shaoxing, Qiandao and Chunxi and none later (Qianbi kaogu wenxian xulu p.382; Sun
Bin, Song shi yanjiu luncong 27, 2020, p.51). The objects:

| hoard | destination | T_h | Southern Song | cast 1163-1210 | cast from 1180 |
|---|---|---|---|---|---|
| Helanshan Dafenggou | Xixia | 1211 | 7 | 0 | 0 |
| Helanshan Yushutai | Xixia | 1211 | 22 | 0 | 0 |
| Wuwei Normal School | Xixia | 1211 | 8 | 0 | 0 |
| Chong'an Ximen | Southern Song | 1253 | 42 | 29 | 26 |
| Qidong Taihetang | Southern Song | 1260 | 47 | 16 | 9 |
| Jurong Chuncheng | Southern Song | 1265 | 502 | 144 | 153 |
| Le'an Gongxi (Wutou) | Southern Song | 1265 | 825 | 348 | 422 |
| Pingxiang Xiashi | Southern Song | 1265 | 171 | 79 | 100 |
| Pingxiang Dawangping | Southern Song | 1265 | 84 | 43 | 68 |

**B140-3c** (rival, grid B): coin types cast after the border, read as a share. Most reports of the period
list the types found without counting them, so presence is what most of them carry, and a count where
there is one. A cut edge still leaks: border trade, money changing and people carrying coin let a few late
coins across, so a single coin at a destination decides nothing; what is read is whether the late share at
the destinations reaches the share at home.

Eighteen Southern Song hoards in the window (six with counts, twelve with type lists) all hold Southern Song
types cast from 1180. Where counted, the share of coins cast 1180-1210 among those cast to 1210 runs from
0.116 (Jurong) to 0.667 (Dawangping). The three Xixia hoards, sealed after 1211, hold 37 Southern Song coins
and none cast after 1162: a late share of 0. On the rival's premise, at the lowest home share, a share this
low has probability 0.0102.

The verdict is read on the reign-type basis, which also takes in a Jin-territory hoard that gives types and a
total but no count by year: Southern Song coins of the types first cast 1190-1210 (Shaoxi, Qingyuan, Jiatai,
Kaixi, Jiading) against every Southern Song type first cast to 1210. At home that share runs from 0.136
(Qidong) to 0.714 (Dawangping). Ganquan Shehegou in Shaanxi, Jin territory, dated 1210 by a Xixia Huangjian
coin, holds 284 Southern Song coins of the types Jianyan, Shaoxing, Qiandao and Chunxi and of no later type
(Qianbi kaogu wenxian xulu p.382; Sun Bin 2020 p.51). With the three Xixia hoards, 321 Southern Song coins
at the destinations and none of the late types; on the rival's premise the probability is 3.65e-21.

Printed and not counted: Beijing Youanmen, a collectors' list with no Southern Song type; and a hoard of over
2,100 kg found at Sanyuan, Shaanxi, in Jin territory, in 1983, where among coins picked from the part that
went into private hands were a Xixia Tianqing (1194) and a Chunxi coin with back 7, cast in 1180. Its `T_h`
is 1194, below the window, it has no table, and one coin is what a cut edge lets through. Three more Jin
hoards, dated by their Jin coins to 1178, list Southern Song types cast after the cut without counts:
Linru, Henan (Chunxi backs 1181 and 1185, Shaoxi back 1190), Xiaoyi, Shanxi (Jiading, 1208-1224, among
115,500 coins), Weishan, Shandong (Chunxi with back years, "a few of each") and Qinyang, Henan (Chunxi backs
7 to 13, 1180-1186). None has a count by year; none is dated into the window.

The same edge read the other way: Jin banned coin leaving its territory from 1198. Of the eighteen Southern Song
hoards in the window, fifteen hold Jin coins cast before 1198 (Zhenglong, Dading); none holds Taihe (1204). Jin cast
little between the end of Dading and Taihe, and Taihe is a ten-cash coin, so this direction has little
power.

In the second window eleven Jin hoards and no Southern Song one: the Jin tables count Chunxi without back years,
so they count no coin cast from 1180, but two reports name back years after the cut among those Chunxi:
Dingxing Xiaodian (backs 11, 12 and 14, 1184-1187, among nine) and Huolu Zhangjiazhuang (backs 8, 9, 10 and
"1" as printed, from 1181, among 22 of 1,555 Southern Song coins); the type lists above name a few more.
At most 40 Chunxi stand among 2,715 Southern Song coins in these eleven tables (1.5%). Coins cast 1163-1178 are
present (Huolu 54, Xiaodian 18 with those nine, Laizhou 17), which fits the Song cut of 1166, its
lifting in 1167 and the stable cut from 1179.

**B140-9** (rival, unread): the same mechanism before 1127. Each group of Northern Song reign titles has a
share of the Northern Song coin in a Xixia hoard, and it is set over the group's share in a reference stock. Niu
Dasheng (Ningxia shehui kexue 1986-2) read the Xixia hoards this way: how much of each coin reached Xixia turned
on the state of relations, the output of that coin and how strictly the ban on coin leaving Song was kept. The
groups follow the five Song-Xia wars (1040-44, 1064-67, 1071-82, 1096-99, 1114-19). A coin is dated no finer than
its reign title, so a group is a set of titles, its label gives their casting span, and "war" or "peace" names the
state of the edge over most of those years:

| group | titles: casting years (war years among them) | share of the group's coin cast in war years, each title spread evenly over its years [lowest, highest any spread allows] |
|---|---|---|
| A peace 1004-1053 | Jingde 1004-1007 (0 of 4); Xiangfu 1008-1016 (0 of 9); Tianxi 1017-1021 (0 of 5); Tiansheng 1023-1031 (0 of 9); Mingdao 1032-1033 (0 of 2); Jingyou 1034-1037 (0 of 4); Huangsong 1039-1053 (5 of 15) | 0.12 [0.00, 0.36] |
| B war 1040-1048 | Kangding 1040-1040 (1 of 1); Qingli 1041-1048 (4 of 8) | 0.50 [0.00, 1.00] |
| C peace 1054-1063 | Zhihe 1054-1055 (0 of 2); Jiayou 1056-1063 (0 of 8) | 0.00 [0.00, 0.00] |
| D war 1064-1085 | Zhiping 1064-1067 (4 of 4); Xining 1068-1077 (7 of 10); Yuanfeng 1078-1085 (5 of 8) | 0.70 [0.11, 1.00] |
| E peace 1086-1097 | Yuanyou 1086-1093 (0 of 8); Shaosheng 1094-1097 (2 of 4) | 0.15 [0.00, 0.29] |
| F war 1098-1100 | Yuanfu 1098-1100 (2 of 3) | 0.67 [0.00, 1.00] |
| G peace 1101 | Shengsong 1101-1101 (0 of 1) | 0.00 [0.00, 0.00] |
| H late 1102-1126 | Chongning 1102-1106 (0 of 5); Daguan 1107-1110 (0 of 4); Zhenghe 1111-1117 (4 of 7); Chonghe 1118-1118 (1 of 1); Xuanhe 1119-1125 (1 of 7); Jingkang 1126-1126 (0 of 1) | 0.25 [0.00, 0.57] |

On an even spread the two counted steps, D to E and F to G, each go from a group cast mostly in war years to one
cast mostly in peace years. The tables do not date a coin inside its title: if all Yuanfu coin was cast in 1100,
group F holds no war coin and the step out of it is no war-to-peace step.

The rival puts every ratio at 1, or lets it fall with vintage if the flow simply ended; it does not let a group
cast mostly in peace rise above the mostly-war group before it. The hoard is the unit. A hoard counts once: as
rising when every counted step of it rises, as falling when none does; the steps of one hoard come from one set
of counts and are not separate trials. The rival's bound for a hoard is one half, or the share of the other
hoards that rise if that is higher. Every hoard rising with a probability below 0.05 gives B, every hoard falling
with one below 0.05 gives C, anything else is left unread; three hoards give at best 0.125, and 5 would be
needed. Two reference stocks are read and the cell is claimed only if they agree: the common stock (the Northern
Song coin of the Jin-territory and Southern Song-territory hoards with a table, 482,834 coins) and the
Southern Song home stock (46,919 coins). A hoard that is part of a stock is taken out of it before it
is set against it.

| reference stock | Xixia | Jin territory | Southern Song territory | Liao |
|---|---|---|---|---|
| common stock | 6 of 6 steps, 3 of 3 hoards | 18 of 34 steps, 5 of 18 hoards | 13 of 18 steps, 6 of 9 hoards | 0 of 4 steps, 0 of 3 hoards |
| Southern Song home stock | 2 of 6 steps, 0 of 3 hoards | 10 of 34 steps, 1 of 18 hoards | 9 of 18 steps, 2 of 9 hoards | 0 of 4 steps, 0 of 3 hoards |

Against the common stock all six counted steps rise in the three Xixia hoards. Against the same stock both steps
rise in 6 of the 9 Southern Song-territory hoards and in 4 of the 16 Jin-territory hoards that
have both. Nine tenths of the common stock is Jin-territory coin, and one hoard, Shijiazhuang Huolu
(201,194 coins), is 42% of it; without that hoard the Xixia count is 5 of 6 steps, 2 of 3 hoards.
Against the Southern Song home stock 2 of the six steps rise, which is the rate of the Jin-territory hoards
against that stock (10 of 34). The two references do not agree, and three hoards cannot reach 0.05: the
cell is not claimed. In the Liao hoards (Song and Liao were at peace throughout) the ratio only falls with
vintage.

| group | pooled, common stock | Dafenggou | Yushutai | Wuwei | Dafenggou, home stock | Yushutai | Wuwei |
|---|---|---|---|---|---|---|---|
| A peace 1004-1053 | 1.16 | 1.20 | 1.08 | 1.36 | 1.46 | 1.31 | 1.65 |
| B war 1040-1048 | 0.17 (1 coin) |  | 0.45 |  |  | 0.25 |  |
| C peace 1054-1063 | 1.50 | 1.52 | 1.44 | 1.68 | 1.66 | 1.57 | 1.83 |
| D war 1064-1085 | 0.90 | 0.87 | 0.97 | 0.79 | 0.87 | 0.97 | 0.79 |
| E peace 1086-1097 | 1.01 | 1.03 | 1.00 | 0.92 | 0.88 | 0.85 | 0.78 |
| F war 1098-1100 | 0.81 | 0.79 | 0.86 | 0.61 | 0.69 | 0.75 | 0.53 |
| G peace 1101 | 0.96 | 0.95 | 0.94 | 1.12 | 0.69 | 0.68 | 0.81 |
| H late 1102-1126 | 0.44 | 0.31 | 0.57 | 0.78 | 0.23 | 0.41 | 0.57 |

Hoard by hoard, the three Xixia hoards placed among the hoards of each home territory. Each cell gives the
territory's median (and its number of hoards), how many of its hoards lie beyond each Xixia hoard, and the exact
chance that three hoards drawn from all of them rank at least that far out:

| measure | Xixia | Jin territory | Southern Song territory |
|---|---|---|---|
| coins of group E over coins of group D | 0.470, 0.411, 0.464 | 0.384 (18); 3, 5, 3; 0.062 | 0.460 (9); 4, 7, 4; 0.636 |
| coins of group G over coins of group F | 2.650, 2.386, 4.000 | 2.439 (16); 7, 8, 2; 0.244 | 2.704 (9); 5, 6, 0; 0.364 |
| share of group A in the Northern Song coin | 0.357, 0.321, 0.404 | 0.318 (18); 1, 8, 0; 0.040 | 0.256 (9); 0, 1, 0; 0.009 |
| share of group C | 0.061, 0.058, 0.067 | 0.052 (18); 2, 5, 2; 0.040 | 0.038 (9); 1, 1, 1; 0.032 |
| share of group H (low side) | 0.030, 0.054, 0.074 | 0.080 (18); 1, 3, 6; 0.050 | 0.143 (9); 0, 0, 0; 0.004 |

On the two counted steps the Xixia hoards lie inside the range of the Jin-territory hoards and are not separated
from them (0.062, 0.244). What separates is the age of the coin: the group cast 1102-1126 is lower in each
Xixia hoard than in every Southern Song-territory hoard (0.004), and the groups cast before 1064 are higher than
in all but one. An older stock at this destination follows on both readings (a flow that thins with vintage; an
edge cut more often as the wars came closer together and routed through Jin after 1127), so it is no cell.

The step out of group B is not counted. That group is one coin, the Qingli ten-cash piece (1 Xixia coin where
the common stock's share gives about 6), scarce in the north whatever the border did, and the step out of it
rises in 9 of 10 Jin-territory hoards set against the Southern Song home stock, so it separates nothing. The late
group is low in every Xixia hoard (0.44 pooled): little open time before 1127, and after 1127 the route ran through
Jin, whose bans on coin leaving its territory cut it. The groups follow the wars rather than the trading posts'
openings alone: under the Song shi account of the posts (closed from early Jiayou to 1067) the Jiayou coin, at
1.50, falls in a closed spell, and a closed post without war moved the trade into smuggling (Chen Xu 2005). Two
hoards sealed under the Northern Song (Lincheng, 307 coins; Miluo, 4,107) are in neither stock.

**B140-5**: twelve Japanese hoards, `T_h` 1265 to 1470: `S_h` 0.015 to 0.059; Southern Song coin cast from
1180 two to three times that cast before; Ming coin 4.9% to 6.6% from 1408, 0.4% at Akaiwa Nakaya (1470).

**B140-6**: Jin's own coin is 0 to 1.2% of Jin hoards: 0.2% to 0.4% dated by Zhenglong, 0.2% to 1.2% by Dading.
Penglai Xingwu is left out: its entry says the coins run down to Jin and names no Jin coin.

**B140-8**: median copper, Northern Song 65% to 70%, Southern Song 56% to 63% (Zhou 2004; Wang et al.
2005); 19 Northern Song coins from the Wuzhou mint site 61.8%. Melting by copper raises `S_h`, against the
prediction; `rho_Q` cancels it.

## 4. Carriers

Sato 2021 (Komazawa Shigaku 95), table 3, a transcription of Miyake 2005's hoard tables, where an
original report exists it replaces the row (Jiutai Kalun, Wenwu 1985-1; Shunping Anyang primary school,
Miyake 2004 table 1); Quzhou Kaixianyuan (Kaogu 1983-9) and Mashan Changtun (1997), printed and excluded
as a temple deposit and a hand-picked sample, and Jilin Dazheng cun, excluded as a collector's hoard with
every type near 3% (Yin Yushan, Kaogu 1988-2; Miyake, Zhongguo lishi wenwu 2004-3, which also gives the
national census of latest Jin coins); Gifu Prefecture (2017), Akaiwa (2013), Maruko (1988),
Shinori (1973) for Japan; the Qianbi kaogu wenxian xulu (Zhongzhou guji 2005) for the per-type counts of
Jurong Chuncheng, Le'an Gongxi, Pingxiang Xiashi and Pingxiang Dawangping, of the Jin-territory hoards
Penglai Xingwu, Qianxi Changlingfeng (replacing its swapped Sato row), Huixian, Kedong Fu'an, Kangping
Biantaizi and Donggou Majuanzi, and for the Jin-territory type lists; the reports of Anji, Dongguan, Shaoyang, Qidong Xiaoping, Nanning and Linru (Kaogu, Zhongyuan wenwu); Suzuki 1992; the alloy sets of Zhou 2004, Wang et al. 2005 and the Guangxi
Museum volume 17 (tables 7 and 8); the Song and Jin decrees from the Song shi, Jin shi and Qingyuan
tiaofa shilei.
