# Measurement conventions: run through this before reporting any number

> **[2026-08-18] The trap ledger is kept in two books, one per arm.** This is the
> book for the simulation arm (`monetary-topology`), and it covers **how this
> code and these measurement practices will bite you**.
> **The data traps of the empirical arm (`topology-fingerprints`) are in a
> separate file**, `topology-fingerprints/docs/MEASUREMENT_FINGERPRINTS.md`,
> covering **how that data will bite you** (ICIO benchmark-year seams, the
> absence of an official Japanese chronology, the illusion of a century-long WID
> panel, and so on).
> **The two books do not cite each other and do not share a numbering scheme.
> They are told apart by filename.**
>
> （**2026-08-18：坑账按臂分两本。** 本文件是模拟臂（`monetary-topology`）的那一本，
> 管的是**这套代码与测量实践**会怎么咬你。
> **实证臂（`topology-fingerprints`）的数据坑另在**
> **`topology-fingerprints/docs/MEASUREMENT_FINGERPRINTS.md`**，
> 管的是**那批数据**会怎么咬你（ICIO 的基准年接缝、日本没有官方年表、
> WID 的百年面板是假象……）。
> **两份互不引用，不交叉编号，靠文件名区分。**）


> **[2026-08-19] Within this arm there is a third file, and it is the raw log
> rather than a third book.** The failure modes below are stated in
> general form with one instance each. The fifty numbered incidents they were
> distilled from are in **[`b8_pitfalls.md`](b8_pitfalls.md)**, every one of them
> paid for by at least one full scan of the archives. Roughly two thirds of those
> fifty are about measurement practice rather than about Fannie Mae's files, so
> that file is worth reading even by someone who will never open a mortgage
> archive. **It has its own numbering, frozen because entries are cited by number
> from outside this repository, and it does not share a scheme with this file.**
>
> Until 2026-08-19 that log was not in this repository, **so the four documents
> that cite it by number were citing something no reader of this repository could
> open.** Moved here for that reason.
>
> （**2026-08-19：本臂之内还有第三份，那是原始记录不是第三本账。** 下面各条是
> 抽象化的失效模式，各带一个实例；它们被蒸馏自的五十条具体事故在
> **`b8_pitfalls.md`**，每一条都至少花掉过一次全扫。**那五十条里约三分之二
> 不是 Fannie 文件专有的**，是测量实践本身的病。**它自带编号并且冻结**，
> 因为仓库外有四份文档按号引它。
> 2026-08-19 之前那份记录不在本仓库里，
> **于是按号引它的四份文档，引的是本仓读者打不开的东西。挪出来就是为了这个。**）


> **Scope of this file.** This is the project's record of measurement traps: each entry is a
> failure mode with an instance in this repository, followed by the checklist to run before
> reporting a number and one meta-rule.
>
> **Every failure mode below stands on its own instance**, which is in this
> repository and can be checked against the record. Nothing here rests on anything
> that is not here.

（度量约定：报任何数之前先过这一遍）

> **Bilingual by design.** This file was written in Chinese and translated. The
> English is the working text; the original Chinese follows each block in
> parentheses so that no rule loses its edge in translation. Where the two
> disagree, the Chinese is the original.
>
> （**双语是有意的。** 这份文件原文为中文，此处为翻译。英文是工作文本，每段之后的
> 括号内保留中文原文，以免规则在翻译中失去锋利。两者不一致时，以中文为准。）

**Applies to every stage.** This file was generalised from **eleven**
measurement-validity failures that occurred consecutively inside one session.
Not one of the eleven was a fact about the world. Every one of them was **a
disagreement between what a measurement was named and what it measured**.

（**适用于全部阶段。** 这份文件是从一个 session 里连续发生的**十一次**度量效度失败归纳出
来的。十一次里没有一次是关于世界的事实，每一次都是**度量的名字和度量的内容不一致**。）

The reason for writing it down is concrete: the **name** of a criterion survives
compression between sessions and the criterion's **validity conditions** do not.
The name is one line. The validity conditions are a long tail: "this number is
what its name says only once holding period is controlled for, only when grouped
by tier, only when the loop sum carries the same dimension as the quantity it is
compared against". The name goes into the hand-off document; the long tail does
not. So the next session implements a thing with that name, and then finds a
78.7% error.

（写下来的理由是具体的：判据的**名字**能通过 session 之间的压缩，判据的**效度条件**不
能。名字是一行字，效度条件是一条长尾——「这个数只有在控制了持有期、只有在按档位分组、
只有在圈和与被比较的量同量纲时，才是它名字所说的东西」。名字进交接文档，长尾不进。所
以下一个 session 会去实现一个叫那个名字的东西，然后发现误差 78.7%。）

**This file is that long tail.**　（**这份文件就是那条长尾。**）

---

## Failure modes, each with an instance in this repository
（失败模式，每一种都有本仓库的实例）

**The numeral left this heading on 2026-08-16.** It said "nine", then "ten", and
each move was an edit whose only purpose was to keep a count in sync. A number in
a heading is a second copy of what the list below already states, and the copy
drifts. **Modes are numbered inside the list and the count is carried nowhere
else.** Distinguish two things that were being conflated by one numeral: the
**modes**, which are kinds and are numbered below, and the **instances**, of
which one session produced eleven. Nothing below is rewritten; new modes are
appended.

（**2026-08-16，数字从这个标题里拿掉。**它先写「九」后写「十」，每次改动的唯一目的都是
让计数对上。标题里的数字是下面那张表已经说过的东西的第二份拷贝，而拷贝会漂。
**模式在表内编号，计数不再出现在任何别处。**这个数字此前混着两样东西：**模式**是种类，
在下面编号；**实例**是次数，一个 session 出过十一次。下面的内容不重写，新模式照旧追加。）

### 1. Window error　(five instances, and the fifth is a guard's own label)　（窗口错，五次，第五次错在守卫自己的标签上）

**Symptom**: the size or the sign of the number is decided by **how long a
stretch was measured** rather than by the mechanism.

（**症状**：数字的大小或符号由「量了多长一段」决定，而不是由机制决定。）

| Instance（实例） | What went wrong（错在哪） | 原文 |
|---|---|---|
| A3-4 v1, 78.7% error | The loop sum is a **per-trade** quantity, and it was fitted against an exponent **in time**. | A3-4 v1，误差 78.7%：圈和是**每笔交易**的量，却去拟合**对时间**的指数 |
| A3-4 v2, sign flipped on 4 of 5 seeds | The four-cycle **enters and leaves at the same points**, while an agent who trades less holds each unit longer, so appreciation swamps the terms. | A3-4 v2，符号 5 个种子翻 4 个：四圈是**同进同出**的，而交易少的人每笔持有更久、涨幅盖过条款 |
| A5-4, "crossing at round 1" | The origin of the series sits two steps away from the configured value, so the configured value was never observed. | A5-4「第 1 轮穿越」：序列的原点比配置值远两步，配置的值从未被观测 |
| A6-1, tail slope `+1.1e-05` while the support fell 27% | The slope answers "is it still contracting". The question was "did it contract". | A6-1，尾部斜率 `+1.1e-05` 而支撑集掉 27%：斜率答「还在不在收缩」，问题是「收缩过没有」 |
| A5 cap probe, an arm printed `INERT` | The comparison was of **opening allocations** and the word carried no time. The same arm was bitwise identical in all thirty opening cells and different in all thirty at the end of the run. | A5 上限诊断印 `INERT`：比的是**开盘分配**，而那个词不带时间。同一条臂在三十个开盘格上逐位相同，在三十个跑完格上全部不同 |

**Rule**: **write down the time quantifier in the claim first, then choose the
window.** "Per trade", "per period", "cumulative" and "end of period against
opening" are four different quantities. If the claim is "per trade", the
denominator of the measurement must be the number of trades and not the number
of rounds.

（**规则**：**先写下主张里的时间量词，再选窗口。** 「每笔」「每期」「累计」「期末对开
局」是四个不同的量。若主张是「每笔」，度量的分母必须是笔数不是轮数。）

**And the rule binds a guard's output as tightly as a criterion's.** The fifth
instance is not a mismeasurement: the arrays compared were the right arrays and
the comparison was correct. What carried no time quantifier was **the word
printed over it**. `INERT` is a verdict about whether a switch reaches code, and
a switch can reach no code on the first day and a great deal of it over three
hundred rounds. A guard that prints an unqualified verdict is asserting a
quantifier it did not check, and the reader has no way to see that from the
output. **Scope the word, or compare at every time the word claims to cover.**

（**而这条规则约束守卫的输出，和约束判据一样紧。** 第五个实例不是量错了：比的数组是对的，
比法也是对的。**没带时间量词的是印在它上面的那个词。** `INERT` 是一个关于「开关有没有接到
代码」的判词，而一个开关完全可以第一天碰不到任何代码、三百轮里碰到很多。守卫印一个不带
限定的判词，就是在断言一个它没有查过的量词，而读者从输出里看不出这件事。**要么给那个词
加作用域，要么在它声称覆盖的每个时点上都比一遍。**）

### 2. Granularity error　(one instance, and the deepest)　（粒度错，一次，但最深）

**Symptom**: a **per-unit** quantity is set against a **portfolio-level** one.

（**症状**：把一个**每单位**的量拿去对一个**组合层面**的量。）

**Instance**: the loop sum is the return of one round trip on **a single unit**;
net worth is **the whole portfolio**. An agent holding 23 units moves only 1/23
of it in one round trip, so the fitted exponent comes out smaller by a factor of
the portfolio size.

（**实例**：圈和是一次往返在**一个单位**上的回报；净值是**整个组合**。持有 23 个单位的
人一次往返只动 1/23，拟合出的指数因此小一个组合规模的倍数。）

**Rule**: **the denominator has to be the same thing on both sides.** Per unit
against per unit, per agent against per agent. Ask the question again after any
change to the mechanism, for example after removing a holding cap: removing the
cap is exactly what broke the correspondence here, and nobody noticed.

（**规则**：**两边的分母必须是同一个东西。** 每单位对每单位，每人对每人。改了机制（比如
去掉持有上限）之后要重新问一遍这个问题——这次就是去掉上限把对应关系打断了而没人注意。）

### 3. Aggregation error　(one instance)　（聚合错，一次）

**Symptom**: the two sides collapse a set of numbers into a single number in
different ways.

（**症状**：两边用不同的方式把一组数塌成一个数。）

**Instance**: the four-cycle is stated **in logs**, while collapsing a set of
agents into one class used the **arithmetic** mean of γ. `log(mean) ≠
mean(log)`, which left a 31% error having nothing to do with the mechanism.

（**实例**：四圈在**对数**里陈述，而把一组主体塌成一个类时用了 γ 的**算术**均值。
`log(均值) ≠ 均值(log)`，留下 31% 的误差，与机制无关。）

**Rule**: **aggregate on whichever scale the claim is stated on.** A claim made
in logs takes the geometric mean. And **the weighting has to match on both
sides**: if one side averages over trades, the other cannot average over nodes.

（**规则**：**在哪个尺度上陈述，就在哪个尺度上聚合。** 对数里的主张用几何均值。而且**两
边的加权必须一致**——一边按笔数平均，另一边就不能按节点平均。）

### 4. Stratification error　(three instances, the third found by a later criterion in the same stage)
（分层错，三次，第三次是被同一阶段后写的判据抓到的）

**Symptom**: what should have been held fixed was not, so what got measured is
the thing that moved.

（**症状**：没把该固定的东西固定住，于是量到的是没固定的那个。）

| Instance（实例） | What went wrong（错在哪） | 原文 |
|---|---|---|
| A3-3, drift 0.583 | Constancy was not grouped by **tier**, so the entire drift is tier changes. | A3-3 漂移 0.583：常数性没按**档位**分组，漂移全是换档 |
| A3-5, sign reversed | `open_tiers` changes the **threshold** and the **bidding pool** at once, so what was measured is the price response and not access. | A3-5 符号相反：`open_tiers` 同时改**门槛**和**竞标池**，量到的是价格反应不是准入 |
| A6-9's curve, top end | The curve sweeps `λ` at a **fixed** `R`. A6-21 then measured `R* = λ`, so the levy's strength relative to each cell's own critical rate was sweeping in the **opposite** direction: `R = 0.005` is five times critical at `λ = 1e-3` and one twentieth of it at `λ = 0.1`. The two cells that closed at high `λ` were read as *too much absorption* and were *too small a tax*. Scaled to `R = λ`, the band is the whole scanned decade and more absorption is monotonically better. | A6-9 曲线的上端：曲线在**固定** `R` 下扫 `λ`，而 A6-21 后来量出 `R* = λ`，所以税相对于每格自身临界率的强度是**反向**在扫的：`R = 0.005` 在 `λ = 1e-3` 是临界的五倍，在 `λ = 0.1` 是二十分之一。高 `λ` 关闭的那两格被读成*吸收太多*，实际是*税太小*。按 `R = λ` 缩放之后，带是整个扫描数量级，而且吸收越高越好 |

**Rule**: **move one thing at a time; where moving one is impossible, decompose
the compound operation and report the parts separately.** If a switch
necessarily changes two things, as `open_tiers` does in A3-5, then the arm with
**the other one frozen** has to be run alongside it, both reported, and the
difference between them is itself the result.

（**规则**：**一次只动一个东西；动不了一个的，把复合操作拆开单独报。** 若一个开关必然改
两样东西（如 A3-5），就必须同时跑「另一样被冻住」的那一臂，两个都报，差值本身是结果。）

**And the third instance says something the first two do not: the two
things that moved together were not both parameters.** One was `λ` and the
other was *what `R` means*, which nothing in the sweep named because it was
not measured until A6-21. A sweep can be stratified by a quantity that has
no variable of its own, and the only defence is to ask what each cell's
control variable is **in its own units** before reading the row.
`docs/a6_siphon_cost.md` §20.1 and §20.7.

（**第三个实例说了前两个没说的：一起动的那两样东西并不都是参数。** 一个是 `λ`，另一个
是**`R` 意味着什么**，而扫描里没有任何东西给它命名，因为它要到 A6-21 才被量出来。一次
扫描可以被一个自己没有变量的量分层，唯一的防御是在读那一行之前先问：这一格的控制变量
**用它自己的单位**算是多少。见 `docs/a6_siphon_cost.md` §20.1 与 §20.7。）

### 5. Population error　(four instances, two of them consecutive)　（人群错，四次，其中两次连续发生）

**Symptom**: the two groups being compared are selected **on an outcome**, and
the treatment changes that outcome.

（**症状**：比较的两组是**按结果**选出来的，而处理会改变那个结果。）

| Instance（实例） | What went wrong（错在哪） | 原文 |
|---|---|---|
| A5-1/A5-2, 0% across the whole grid | Participation measured at the end of the period measures **survival** and not entry. | A5-1/A5-2，全网格 0%：期末测参与率，量的是**存活**不是进场 |
| Rent sweep v1 | The set of "never-holders" moves with the rent rate. | 租金扫描 v1：「从不持有者」这个集合随租金率改变 |
| Rent sweep v2 | Pinning the population to the `rent=0` set still fails: some of them **acquire units at other rates and are therefore on the receiving side of the rent**. | 租金扫描 v2：把人群固定到 `rent=0` 那批仍不行——其中一些在别的费率下**买到了单位，于是是收租方** |
| **A3-8's paired population** (2026-08-13) | The set is `cycles > 0` in **every** cell, which is an outcome. What it leaves is the top eighth of the production layer by centrality, band `[86.8, 100]` over twenty seeds, and `gate_spread` disperses terms **along** centrality. The peripheral tercile trades zero times in every cell **including the null**, so the gate is not what removed it. **The inertness that was inferred from this in 2026-08-13, that the gate reads zero because its treatment barely varies here, was measured in 2026-08-27 and is false**: the gate moves 19.4 nodes' cycle counts against the other channel's 16.8 and 74.0 total absolute cycle change against 85.6, **86 per cent of it**. The selection-on-an-outcome defect stands; **the inference from a narrow band to an inert treatment does not**. Failure mode 78. | `a3_asset_channel.md` §5.3, `experiments/a3d_gate_margin.py` |

**Rule**: **the population has to be defined by the state before treatment, or
matched by node.** Matching is the strongest form: the same node is compared
against itself across the two arms. Where stratifying on an outcome is
unavoidable, **stratify inside each arm separately** and report the transition
matrix (holds in both arms / holds in one only / holds in neither), rather than
imposing one arm's strata on the other.

**And a second half, rewritten on 2026-08-27 after the fourth instance was
measured: to decide whether a treatment is inert on the measured population,
measure what the treatment does to the mechanism. Do not read it off where the
population sits.** Take the two cells that differ only in that term and count
how many units it moves and by how much. That is two subtractions, and it is a
direct measurement. The variation range over the population is still worth
printing and it is still not the verdict: **a narrow range is not an inert
treatment**, and on the fourth instance the range was narrow and the treatment
was doing 86 per cent of the other channel's mechanical work. Swept along the
knob that widens the population, the treatment is inert at the **wide** end and
not the narrow one, because an admission rule has nothing left to ration once
nearly everyone is in. The first three
instances remain what they were, a population that moves with the arm, and the
defect there is selection on an outcome rather than anything about variation.
Failure mode 78.

（**规则**：**人群必须由处理之前的状态定义，或者按节点配对。** 配对是最强的：同一个节点
在两臂之间比它自己。若必须按结果分层，则**在每一臂内部各自分层**，并报出转移矩阵（两
臂都持有／只有一臂持有／都不持有），而不是把一臂的分层套到另一臂上。

**后半条 2026-08-27 改写**（原文是「报任何处理效应之前，先报处理变量在被测人群上的变异
范围」，第四个实例量出来之后不成立）：**要判一个处理在被测人群上是不是惰性的，量处理对
机制做了什么，不要看人群站在哪。** 取只差那一项的两格，数它动了多少个单元、动了多大。
两次相减，而且是直接测量。**变异范围照旧值得印，照旧不是裁定**：范围窄不等于处理惰性，
第四个实例上范围就是窄的，而那个处理在做另一条通道 86% 的机械功。前三个实例不变，
它们是人群随臂移动，病灶是按结果选样，与变异无关。见失败模式 78。）

### 6. Tolerance error　(one instance)　（容差错，一次）

**Symptom**: a question about magnitude asked at machine precision.

（**症状**：用机器精度去问一个关于量级的问题。）

**Instance**: the support of the no-access arm is constant at 200.0, `y[-1] <
y[0]` flips on the last floating-point digit, and so the whole arm returns "no
solution". **The result A6-3 itself predicted was destroyed by rounding.**

（**实例**：无 access 臂的支撑集恒为 200.0，`y[-1] < y[0]` 在浮点末位上翻掉，于是整臂返
回「无解」——**A6-3 自己预测的那个结果被舍入毁掉了**。）

**Rule**: **the tolerance has to be the same order of magnitude as the effect
being measured.** The contraction measured here is 27%, which is what makes a 1%
tolerance meaningful rather than concealing. Write down what the tolerance is
relative to at the same time as writing down the tolerance.

（**规则**：**容差要和被量的效应同量级。** 这里被量的收缩是 27%，1% 的容差因此有意义而
不是遮掩。写下容差时一并写下它相对什么。）

### 7. Guard error　(seven instances in one stage, and the worst was silent)　（守卫错，一个阶段里七次，最坏的一次没出声）

**Symptom**: the measurement is right and **the thing that was supposed to check
it** is wrong. A guard is itself a measurement, of the pipeline rather than of
the world, so every failure mode above applies to it. It gets its own entry
because a broken guard does not look like a broken number: it looks like
nothing, or it looks like a result.

（**症状**：度量是对的，而**本该检查它的那个东西**是错的。守卫本身也是一次度量，量的是流水线不是世界，所以上面每一种失败模式都适用于它。单列出来是因为坏掉的守卫不长得像坏掉的数字：它要么什么都不像，要么长得像一个结果。）

| form（形态） | instance（实例） |
|---|---|
| **silent when it should speak** | A3b's collapse guard said "the three arms differ" when every printed number was identical. B6's path reconciliation accepted a **back fill** as a forward fill, because its rule referred to "the previous published value" and before a currency's first publication there is none, so the branch fell through |
| **speaks when nothing is wrong** | `fetch_cip` compared a source hash against a stored file carrying an extra sentinel line, and cried on every run |
| **vacuous** | B4-4's criterion had a side that never occurred in the sample. B6's XLSX-against-API agreement looked like a zero calibration and tests only the delivery path: two routes to one record say nothing about the collection |
| **domain set by the sample it was written on** | B6's plausibility band was `(1, 1e6)`, written when the stage held two currencies, and rejected two of the eleven added later. Its provisional-row rule required a forward fill, true of six files downloaded in one minute and false of the next thirty-three. Its coverage check asserted every currency starts on the window's first day, and one joined twelve days late |
| **message conflates two states** | B6's export loader reported "the directory is empty" when the directory held six files whose names it did not accept |
| **computed on a different population from the thing it guards** | A6's noise floor ran on 2012–2025 while the signal ran on 2000–2025 |

**Rule**: **write down what the guard would say if the thing it guards were
broken, and what it would say if the guard itself were broken, and check that
those are different sentences.** Then check the guard on a case it should
reject, not only on the data in hand.

（**规则**：**写下「被守卫的东西坏了它会说什么」和「守卫自己坏了它会说什么」，确认这两句话不一样。** 然后拿一个它**应该拒绝**的样例去试它，不要只拿手上的数据试它。）

**The silent hole is the dangerous one and it deserves its own sentence.** A
guard that cries is found in a day. A guard that is vacuous is found when someone
asks what it would take to fail it. **A guard with a hole produces a plausible
downstream result**: B6-8, a registered criterion, failed on eight of 5 382
observations, in one currency, in one contiguous stretch, with a clean story
about a stale row. Every part of that was manufactured by rows the guard had let
through. It was found because the fetcher, on a different machine, refused the
same currency for an unrelated reason.

（**沉默的洞才是危险的那一种，值得单独一句。** 乱叫的守卫一天就被发现；空转的守卫在有人问「怎样才能让它失败」时被发现。**带洞的守卫会产出一个看起来完全合理的下游结果**：B6-8 这条登记判据在 5382 个观测里失败了 8 个，集中在一个货币、一段连续日期上，还配着一个关于陈旧行的干净故事。那全部是守卫放进来的行造出来的。它之所以被发现，是因为取数脚本在另一台机器上因为一个无关的理由拒绝了同一个货币。）

**And one instance in the other direction, because a file of failures teaches the
wrong lesson.** B6's path reconciliation caught, on its first real run, a
disagreement nobody had anticipated: the export's last row is provisional, and
the API had published a value for that day in the hours after the download. It
said so, refused to proceed, and named the row. That is what these are for.

（**还有一个方向相反的实例，因为一份全是失败的清单会教出错误的结论。** B6 的路径对账在第一次真跑时抓到了一个没人预料到的分歧：导出文件的尾行是临时的，而 API 在下载之后的几小时里发布了那天的值。它说了出来、拒绝继续、并点了名。守卫就是干这个的。）

### 8. Membership error　(four instruments, found three days apart)　（成员错，四个工具，隔三天各抓到一次）

**Symptom**: a quantity whose real counterpart is assessed on a **measured
magnitude** is instead keyed on a set of node indices **fixed at construction
time**. The arithmetic is correct, the variable names are honest, and nothing in
the run looks wrong. What has quietly changed is what the number is *about*: it
reads as an economic property that agents have, and it is an address they were
assigned.

（**症状**：一个在现实里按**测得的量**征收／发放的量，被挂在**构造时定死的一组节点下标**
上。算术是对的，变量名是诚实的，运行起来没有一处看着不对。悄悄变掉的是这个数**关于
什么**：它读起来像主体拥有的一种经济性质，实际上是它被分配到的一个地址。）

**This mode was written after the same defect was found in two unrelated stages
within three days**, which is why it gets an entry rather than a line in the
stratification error above. It is not a slip in one place. It is what happens
whenever a layer index is in scope and a quantity needs a population.

（**这一条是在三天内于两个互不相关的阶段抓到同一个缺陷之后写的**，所以它单列而不是并进
上面的分层错。它不是某一处的手误，而是只要层籍下标在作用域里、而某个量需要一个人群，
这件事就会发生。）

| Instance（实例） | What went wrong（错在哪） | 处置 |
|---|---|---|
| A6 的税基 | The levy fell on `_l1_idx`, twenty node indices fixed at construction, not on whoever held most. No real net wealth tax uses fixed membership. | 加 `LevySpec` 开关，默认仍是层制所以既有结果逐位不动，另一支按门槛累进 |
| A6 的返还端 | `holdings[_l2_idx] += total / _l2_idx.size`. **The correction above was applied to one side of the instrument only.** Under the threshold base the payers are recomputed from measured holdings every round while the recipients are still the fixed set, so at steady state 56 of the 180 recipients are also payers and 4 financial-layer nodes below the threshold pay nothing and receive nothing. | **未处置**，见下 |
| A3-6 与 §12.6 的两点画面 | Every holder is a financial-layer node and no production-layer node holds, so "holder against non-holder" is also "layer 1 against layer 2". | `a3_asset_channel.md` §6.4b：诊断跑完，形状归因不成立 |
| A3 的租金负债 | `renters = (held <= 0) & _is_production`. Liability keyed on the layer index, receipts keyed on holding. A financial-layer node holding nothing pays no rent; a production-layer node holding nothing pays every round. | 同上，已记未改 |
| A3 的开盘价款与残量 | `_prior_owner_weights` routes both to `~_is_production`, weighted by opening claims. | 同上；docstring 里有辩护，形状仍是这一类 |

**Rule**: **tell position apart from quantity.** Layer as position, meaning who
has which edges, is the framework's own object and does not move: a household
does not become a bank by getting rich. Any **liability, receipt, eligibility or
population** whose real counterpart is assessed on an observed magnitude has to
be recomputed from that magnitude. Where it is keyed on an index set instead,
that is a modelling choice and has to be **registered as one**, not left on the
page to read as a fact. And when one side of a two-sided instrument is
corrected, **check the other side in the same edit**: the A6 rebate survived
§16.4 by being three lines further down.

（**规则**：**把位置和量分开。** 层籍作为位置，即谁有哪些边，是框架自己的对象，不动：
家户不会因为变富就成了银行。任何在现实里按可观测量征收／发放的**负债、收入、资格、
人群**，都必须从那个量重算。挂在下标集上的，那是一个建模选择，必须**作为建模选择登记
下来**，而不是留在纸面上让人读成事实。还有，一个双边工具改了一边，**同一次编辑里就要
查另一边**：A6 的返还端能在 §16.4 里活下来，只是因为它在三行之后。）

**And the same file shows what the rule looks like when it is followed.**
`mechanisms._rematch` pairs agents on a key built from normalised holdings and a
uniform draw, and the docstring says it "has no access to `self._is_layer1`, so
any tendency of households to form within a layer is derived rather than
imposed". `_is_layer1` appears in that method exactly once, on the line *after*
the matching, to **measure** the cross-layer rate. That is prediction A4-6's
entire content, and it is only a prediction because the mechanism was denied the
index it would have been tempting to use.

（**同一个文件里也有这条规则被遵守时的样子。** `mechanisms._rematch` 用归一化持有量和一
个均匀抽样构成配对键，docstring 明写它「拿不到 `self._is_layer1`，所以家户在层内形成的
倾向是推出来的不是强加的」。`_is_layer1` 在那个方法里只出现一次，在配对**之后**那一行，
用来**测量**跨层率。这就是预测 A4-6 的全部内容，而它之所以能算预测，正是因为机制被拒绝
使用那个用起来很顺手的下标。）

**The sweep, 2026-08-13.** Every line in `src/monetary_topology/` that reads a
layer index or a fixed node set was enumerated and classified: **73 sites, 45
position, 19 measurement, 9 mechanism.** The 45 are the graph's wiring, the spec
accessors, the propensities and the opening allocation, all of which define
position and are the framework's own object. The 19 report a series over a fixed
index set, which is sound arithmetic with a reading hazard attached: a series
named `layer2_holdings` is the holdings of a fixed set of addresses, and
`effective_support_l2` is reach into that set, neither of which is "the
households'" if a member of the set has since become rich. The 9 mechanism sites
are the four instruments in the table above, and only the A6 rebate is
uncorrected.

（**2026-08-13 的普查。** `src/monetary_topology/` 里每一行读层籍下标或固定节点集的地方
都被枚举并分类：**73 处，45 处位置，19 处测量，9 处机制。** 那 45 处是图的接线、spec 的
下标访问器、消费倾向与开盘分配，全都在定义位置，是框架自己的对象。那 19 处是在固定下标
集上报一条序列，算术没问题但附带一个读法风险：叫 `layer2_holdings` 的序列是一组固定地址
的持有量，`effective_support_l2` 是对那一组地址的触达，如果集合里有成员后来变富了，两者
都不叫「家户的」。那 9 处机制就是上表的四个工具，其中只有 A6 的返还端还没处置。）

---

### 9. Record error　(one instance, and it is the meta-rule's first specimen)　（记录错，一次，而且是那条元规则的第一个标本）

**Symptom**: a file in `results/` is not a reading of the code in the same
commit. The arithmetic is right, the file is well formed, every criterion in it
is correctly evaluated, and every verdict it carries is the verdict the current
code also reaches. What has changed is **which economy it is a reading of**.

（**症状**：`results/` 里的一份文件，不是同一次提交里那份代码的读数。算术是对的，文件是
良构的，里面每条判据都被正确评了分，而且它带的每一条判词与当前代码得到的判词都一样。变
掉的是**它是哪一个经济的读数**。）

**Instance**: `results/a5_reachability.json`. The commit that restated stage A3
added `rent_rate = 0.05` as a default-on mechanism, and stage A5 runs entirely on
A3's machinery. A5's existing record was carried into that commit without the
stage being re-run. Record and code therefore entered the repository together
and disagreed from the first day, and the disagreement survived five further
commits. Running the current code with `rent_rate = 0` returns the stored file's
numbers to every printed digit; at the registered default it returns different
ones.

（**实例**：`results/a5_reachability.json`。重述 A3 的那次提交把 `rent_rate = 0.05` 作为
默认打开的机制加了进来，而 A5 完全跑在 A3 的机器上。A5 已有的记录被原样带进那次提交，阶
段没有重跑。于是记录与代码同次入库、从第一天起就不一致，并且熬过了此后五次提交。当前代码
把 `rent_rate` 设为 `0` 就逐位复现存盘文件的每一个打印数字，用登记的默认值则不然。）

**Why nothing caught it, and both halves are needed.** The commit preserved the
opening construction, so every construction-time quantity in the file still
reproduces bitwise, and a file in which half the numbers reproduce exactly does
not look like a file that is wrong. And the stage is in neither
`scripts/run_all.py`'s experiment list nor the continuous integration reruns, so
no comparison between record and code was ever performed.

（**为什么没被抓到，两半缺一不可。** 那次提交保住了开盘构造，所以文件里每一个构造时的量
仍然逐位复现，而一份有一半数字精确复现的文件看起来不像一份错的文件。以及，这个阶段既不在
`scripts/run_all.py` 的实验清单里，也不在持续集成的重跑里，所以记录与代码之间从来没有被
比对过。）

**How it was found, and this is the part that generalises.** Not by a guard,
because there was none. Not by a human noticing a number that looked wrong,
because none did. It was found by **re-running the stage on unchanged code and
comparing to the file**. That is a third route, and for this class it is the only
one, because the failure is invisible from inside the file.

（**它是怎么被抓到的，能推广的正是这一段。** 不是靠守卫，因为根本没有守卫。也不是靠人看
出某个数不对，因为没有一个数看着不对。是靠**在代码不动的情况下重跑阶段、再与文件比对**。
这是第三条路，而对这一类失败它是唯一的一条，因为这个错误从文件内部看不见。）

**What it costs.** No verdict: the criteria pass and fail identically under both
settings. A reading: the stage's own sections decompose a ratio into a numerator
and a denominator, and **the sign of the denominator's move differs between the
two settings**. A conclusion drawn from that decomposition is a conclusion about
the economy the record was taken in, which is not the economy the repository now
describes.

（**代价是什么。** 不是判词：两种设置下判据的过与败完全相同。是读法：该阶段自己的小节把
一个比值拆成分子与分母，而**分母那一项移动的符号在两种设置下不同**。从那个分解里得出的
结论，是关于记录被采下时那个经济的结论，而那不是仓库现在描述的经济。）

**The exposure, counted rather than estimated (2026-08-15).**
`render_results.py` globs `results/*.json`, drops the off-parameter and smoke
runs by filename and the writer-declared diagnostics by field, and turns every
survivor into a heading in `RESULTS.md`. That survivor set is **twenty-four
records, and eight of them have no job in `run_all.py`**: `a3_asset_channel`,
`a3b_construction`, `a3c_load_bearing`, `b2_placebo_pool_width`, `b3_cip_slice`,
`b4_directed_edges`, `b5_friction`, `b5_p2p`. **The first of those is A3**, the
stage every A-track claim about compounding rests on, and the stage whose own
restatement produced the instance above. It is in exactly the position A5 was in.

`tests/test_runner_covers_every_record.py` is the ratchet: the eight are named
with their reasons, the list is checked in both directions so it cannot outlive
them, and a ninth cannot be added silently. **Naming them does not fix them.**

**2026-08-21, the selection above moved, then the guard went with it.**
`RESULTS.md` is now kept by hand and there is no renderer. The ratchet was first
re-grounded on its own copy of the three filters, verified to return the same 76
records as before, and then retired the same day. **Two counts settled it.**
The allowlist held **51 of those 76 records, 67.1 per cent**: an exception list
carrying two thirds of its population is not an exception list. And
`a5_reachability.json` **has a runner job**, so the guard would not have fired on
the incident above, which is its own founding case: A5's record was carried
forward without being re-run, and this guard asks whether a job exists, never
whether the record matches the code that wrote it. Its own history records the
count assertion drifting four times, 8 to 16 to 18 to 19 to 40 to 47, each drift
found by someone happening to run it. **The exposure this section counts is
real and is now uncovered; nothing here claims otherwise.**

（**这个敞口是数出来的，不是估的（2026-08-15）。** `render_results.py` 扫
`results/*.json`，按文件名去掉离参与冒烟跑、按字段去掉写入者自己声明的诊断，剩下的每一份
都变成 `RESULTS.md` 里的一节。剩下的是**二十四份，其中八份在 `run_all.py` 里没有任何
job**。**第一份就是 A3**，A 轨关于复利的每一条主张都站在它上面，而上面那个实例正是它自己
的重述造成的。**它现在所处的位置，和 A5 刚才一模一样。**
`tests/test_runner_covers_every_record.py` 是那道棘轮：八份逐个具名带理由，清单双向校验
所以不会比理由活得更久，第九份加不进来而不出声。**点名不等于修好。**）

**The rule**: **a stage that nothing re-runs does not have a record, it has a
memory.** When a default on shared machinery moves, the stages standing on that
machinery are the ones whose stored numbers are now about a different economy,
and the ones outside the runner are exactly the ones that will not say so. The
operational form is the same one this project gives for call sites: **before
moving a default, enumerate every stage that constructs from
the object it belongs to, and re-run all of them.** Putting the stage into the
runner is the durable version of that, because it does not depend on anyone
remembering to enumerate.

（**规则**：**没有东西重跑的阶段，它没有记录，它只有记忆。** 当共用机器上的某个默认值移
动时，站在那台机器上的阶段，其存盘数字就已经是关于另一个经济的了，而在 runner 之外的那
些，恰恰是不会说出这件事的那些。可操作的形式与本项目对调用点给的那
条相同：**移动一个默认值之前，先枚举所有从它所属对象构造的阶段，并且全部重跑。** 把阶段
放进 runner 是这条的耐久版本，因为它不依赖任何人记得去枚举。）

---

### 10. Calibration error　(one instance, and it decided a stage's headline)　（校准错，一次，而且它决定了一个阶段的头条）

**Symptom**: a criterion compares two numbers, and **only one of them was ever
shown to be readable**. The comparison then reports a disagreement that may be
about the instrument rather than about the world.

（**症状**：一条判据比较两个数，而**只有其中一个被证明过可读**。于是这条比较报出的分歧，
可能是关于仪器的，不是关于世界的。）

**The instance.** Stage B7 registers a gate, B7-0: lay a constructed field of
known matrix rank on the observed design and check that the estimator reads the
rank back. It was run three times on the **fine** class grid, at two draw counts
and under both nulls, and passed nine of nine each time. Criterion B7-6 then
compared the fine grid's answer, `2`, against a **coarse** grid's answer, `1`,
and failed.

Collapsing nineteen class levels to six changes the class count, the distinct
classes per cell and the whole co-occurrence structure. **It is a different
design, and it had never been gated.** §3.6's own words for B7-0b are that
"without it an observed `1` could be a second dimension this design cannot
resolve" — which is exactly the number B7-6 was treating as evidence.

The gate was then run on the coarse grid (B7-6r) and it passed, at both draw
counts. So the disagreement is real and B7-6's failure stands. **That outcome
does not retire the rule.** It was decided by a run that only happened because
someone noticed the asymmetry, and it could have gone the other way.

**Correction, 2026-08-16, and the rule comes out stronger.** The coarse grid this
instance is about **was not the regulator's bucket scheme**. The class levels were
stored alphabetically and read positionally, so that grid merged the wrong classes
and put `<20%` in the same group as `49`; see failure mode 12. On the corrected
partition the coarse grid reads `2`, the same as the fine grid, and **B7-6 does
not fail. The disagreement was not real.**

What this mode is about is a **comparison arm that was never gated**, and the
correction adds that it was also never checked. An ungated comparison arm computed
on a scrambled index went through a gate, a re-gate built specifically to test it,
a third grid built as its complement, and two published claims. **The instance is
a better example of the mode than it was, not a worse one**, and the rule below is
unchanged.

（**2026-08-16 更正，而规则反而更强了。** 这条实例说的那张粗格**不是监管机构的分桶方
案**：层级名字按字母序存、按位置读，那张格子合并错了类，把 `<20%` 和 `49` 放在同一组，
见失败模式 12。在修正后的划分上粗格读出 `2`，和细格一样，**B7-6 不失败，那个分歧本来
就不存在。** 这一条讲的是**一条从未被上闸的对照臂**，更正补上的是它也从未被核对过。规则
不变，实例比原来更典型。）

**Rule**: **every design a number is read from needs its own calibration, and a
comparison arm is not an exception.** A criterion of the form "two constructions
must agree" is only as strong as the weaker construction's licence, and a stage
that gates its primary arm and not its control has not gated anything.

（**规则**：**每一个被读数的设计都要有自己的校准，对照臂不是例外。** 形如「两种构造须一
致」的判据，其强度不超过较弱那一边的许可；只给主臂上闸、不给对照上闸的阶段，等于没上闸。）

**Two sub-rules, both found in the same round.**

**10a. The constructed calibration field must match the observed spectrum's
shape, not only its total energy.** B7's calibrator scales the constructed
interaction to the observed one's Frobenius norm and then splits that energy
roughly evenly across its directions. The observed spectrum runs `1.4674`
against `0.7544`, about two to one. So every gate in that stage established that
its design resolves an **evenly split** field of the right total size, and none
of them established that it resolves a skewed one. The gate is weaker than it
reads.

（**10a. 构造校准场须匹配观测谱的形状，不只匹配总能量。** B7 的校准器把构造出的交互项缩
放到观测项的 Frobenius 范数，然后在各方向间大致均分。观测谱是 1.4674 对 0.7544，约二比
一。所以该阶段每一道闸证明的都是「这个设计能分辨一个**均分**的、总量正确的场」，没有一道
证明了它能分辨偏斜的。闸比它读起来要弱。）

**10b. A boundary calibrated on constructed designs is neither an upper nor a
lower bound until the sufficient statistic is known.** B7 swept a **fill** rate
on constructed designs and read a usable-regime boundary off it. The real design
sat above that boundary and passed. But constructed designs at the *same* fill
failed, in two of five seeds, because they carried three hundred cells against
the real design's `326,872`. **Fill was not the sufficient statistic; the
co-occurrence counts were.** Read as a ceiling, that sweep would have killed the
stage on evidence that could not support it.

（**10b. 在构造设计上标定的边界，在充分统计量未确认之前，既不是上界也不是下界。** B7 在
构造设计上扫了**填充率**并从中读出一条可用区边界。实测设计落在边界之上并通过了闸。但同一
个填充率的构造设计在五个种子里有两个失败，因为它们只有三百个 cell，而实测设计有 326,872
个。**充分统计量不是填充率，是共现计数。** 把那张扫描表当天花板读，会在支撑不了的证据上
判这个阶段死。）

**A related shape worth naming, because it is not an error.** B7 put its ordering
into what the code can do rather than into anyone's discipline: the design-audit
file imports no estimator, the gate file cannot read the observed field, and the
rank file refuses to compute an estimate unless the gate cleared. A stage whose
step order is enforced by imports cannot have its steps run out of order by
someone in a hurry.

（**一个值得命名的相关形态，因为它不是错误。** B7 把次序放进代码能做什么里，而不是放进
谁的纪律里：设计审计那个文件不 import 估计量，闸那个文件读不到观测场，读秩那个文件在闸没
过时拒绝计算。一个步骤次序由 import 关系强制的阶段，没法被赶时间的人乱序执行。）

---


---

### 11. Spending on a determined arm　(three instances in one stage)　（在已定死的臂上花钱，一个阶段里三次）

**Symptom**: an arm is run whose possible outputs, enumerated in advance, contain
exactly one that is not already implied by what is known, and that one output
would be a bug report rather than a measurement.

（**症状**：一条臂被跑了，而它事先可枚举的全部可能输出里，只有一个不是已知信息的推论，
而那一个输出是 bug 报告，不是测量。）

**The instance.** Stage B7 registered a criterion that a gate's verdict must
agree at **two draw counts**, fifty and two hundred, and ran every gate twice.
That is hours of a loaded machine, three times over for three class grids.

`_null_seeds` takes the first `d` seeds in order from the parent generator, so
the `d = 200` seed set **contains** the `d = 50` seed set. `null_max` is a maximum
over a superset, therefore **monotone non-decreasing in `d`, exactly, with no
probability in the statement**. The rank is the count of eigenvalues above it,
therefore **monotone non-increasing in `d`, exactly**. So the second run could do
only one thing: lower a rank.

It did not, and it could not have. Measured, `null_max` went `0.38171` to
`0.38920`, **two percent for four times the draws**. The drop needed to move the
fine grid's rank was to `0.75439`, ninety-eight percent. Reverse-engineering the
null's own distribution from those two order statistics gives a mean of `0.35224`
and a standard deviation of `0.01435`, so the drop required **twenty-eight
standard deviations**, which a maximum over `d` draws reaches at `d` of about
`10^171`.

**So the outcome set had two members and no third.** Same rank: implied in
advance, information zero. Lower rank: at twenty-eight sigma that is a broken
`_null_seeds` or a broken maximum, which is a unit test's job. The rank could not
rise; that is the theorem.

**Rule**: **before spending on an arm, enumerate its possible outputs and strike
the ones already implied. If what remains is only "the code is broken", it is a
unit test, and a unit test belongs on a synthetic fixture that runs in seconds,
not on the full sample for half a day.**

（**规则**：**在一条臂上花钱之前，先枚举它可能的输出，划掉已经被蕴含的那些。如果剩下的
只有「代码错了」，那它是单元测试；单元测试该跑在几秒钟的合成样例上，不是跑在全样本上半
天。**）

**11a. `N` repetitions cannot resolve a rate below `1/N`.** B7's rewritten gate
runs twenty repetitions per arm and reports a failure rate. On an arm whose
deciding eigenvalue sits twenty percent from the null with a repetition-to-
repetition spread of half a percent, the implied per-repetition failure rate is
far below `1/20`, so those twenty repetitions measure nothing about the rate and
only test the code. **Run a few, report the margin in standard deviations, and
spend the repetitions where the implied rate exceeds `1/N`.** `1/N` is the
resolution of `N` trials and comes from the construction, exactly as the nominal
size `1/(d+1)` does. Neither is a chosen number.

（**11a. `N` 次重复分辨不了低于 `1/N` 的比率。** 判决量离零假设二十个百分点、重复间散
布半个百分点的臂，其隐含单次失败率远低于 `1/20`，那二十次重复测不出比率，只测代码。**先
跑几次，报边距的 sigma 数，把重复花在隐含率高于 `1/N` 的地方。** `1/N` 是 `N` 次试验的
分辨率，和名义大小 `1/(d+1)` 一样由构造给出，都不是选出来的数。）

**11c. Do not fix a draw count or a repetition count in advance, and in any
follow-on task restructure them for efficiency rather than inheriting them.** More
draws and more repetitions are not better. **The right number is the smallest that
still settles the question**, and every one above that is spent on nothing.

（**11c. 不要事先把抽样次数或重复次数钉死，在后续任务里按效率重构而不是照抄。** 抽样
更多、重复更多不等于更好。**正确的数是仍然能结掉这个问题的最小那个**，超过它的每一次
都花在了什么都没有上。）

**Reference value: five repetitions.** Above **ten** on a homogeneous arm is
**forbidden outright unless there is a real reason stated in the same breath.**
Homogeneous means what it meant on 2026-08-16: twenty repetitions returning the
identical integer with a spread under one percent, twice over. **Five would have
shown that.** The reason must be a property of the arm, not a feeling about
rigour.

（**参考值：五轮。** 同质化的臂上超过 **十轮**，除非同时给出实在的理由，否则**彻底
禁止**。同质化的含义就是 2026-08-16 那天的样子：二十次重复返回同一个整数、离散度不到
百分之一，而且两条臂都是。**五次就看得出来。** 理由必须是这条臂的某个性质，不是一种
关于严谨的感觉。）

**If the purpose is verification, shrink hard.** A run that exists to confirm
something already argued needs enough repetitions to detect a broken code path and
no more, and 11a says how many that is: `N` repetitions cannot resolve a rate below
`1 / N`, so if the first few agree with a spread far below the margin, the rest
measure nothing and only test the code.

（**如果目的只是验证，就极速缩小。** 一次为了确认已经论证过的东西而存在的跑，只需要
足以发现代码坏掉的重复次数，不需要更多；11a 说了那是多少。）

**What this cost, measured rather than asserted.** An afternoon of a loaded
machine bought a two-hundred-draw confirmation of an outcome that was fixed in
advance by `28` sigma. The draws were not wrong; they were spent on a question
that was already closed.

（**这一次的代价是量出来的，不是断言的。** 一个下午的满载机器，换来一次对「事先由 28 个
sigma 定死的结果」的两百抽样确认。那些抽样本身没有错，只是花在了一个已经结掉的问题上。）

**11b. An arm whose answer is forced by its own construction is not an arm.**
After B7's calibration was corrected to set a constructed field at the design's
**own** observed eigenvalues, the coarse grid's rank-two arm would construct a
second direction at the coarse grid's observed `lambda_2`. That `lambda_2`
already sits below the coarse grid's own null, which is why the grid reads rank
one. The arm would then be asking whether a design can resolve a thing it has
already failed to resolve, and the answer is a property of the question.
**Before an arm is paid for, check that both of its outcomes are reachable.**

（**11b. 答案被自己的构造逼出来的臂，不是臂。** 校准改成按设计**自己**的观测特征值定标
之后，粗格的 rank 2 臂会把第二方向构造在粗格自己的 `lambda_2` 上，而那个 `lambda_2` 本
来就在粗格自己的零分布之下，这正是它读出 rank 1 的原因。这条臂问的是「一个设计能不能分
辨它已经分辨不出来的东西」，答案是问题本身的性质。**付钱之前，先确认这条臂的两种结局都
到得了。**）

---


---

### 12. Alignment error　(one instance, and it survived a day, two gates and three deductions)　（对齐错，一次，而它熬过了一天、两道闸和三条推断）

**Symptom**: two orderings are assumed to correspond and the assumption is never
checked. One is a list of names, the other a set of integer codes, and something
reads `names[i]` as the name of code `i`. The arithmetic is correct, every count
is right, and the object is quietly about something other than what its name says.

（**症状**：两套顺序被假定对应，而这个假定从没被检验过。一边是名字的列表，一边是整数编
码，某处把 `names[i]` 当成编码 `i` 的名字来读。算术是对的，计数全对，而这个对象悄悄地
关于另一件事，不是它名字说的那件。）

**The instance.** Stage B7 assigns each DTI class level a code by **first
appearance in the CSV files** and stored the level names as `sorted(...)`, which
is **alphabetical**. `coarse_classes` and `complement_classes` then read that list
positionally. The grid the pre-registration calls "the regulator's own bucket
scheme" therefore merged four published buckets with ten integers and put `<20%`
in the same class as `49`.

（**实例。** B7 阶段按**在 CSV 里第一次出现的顺序**给每个 DTI 层级编码，而把层级名字按
`sorted(...)` 也就是**字母序**存下来，`coarse_classes` 和 `complement_classes` 再按位置
去读那个列表。于是预注册里称为「监管机构自己的分桶方案」的那张格子，把四个发布桶和十个
整数合并在一起，并且把 `<20%` 和 `49` 放进了同一类。）

**Why nothing downstream could catch it.** The scrambled partition still has six
groups, because fourteen positions carry bare integers whichever levels sit in
them. The group count is right, the fill is right, the loan counts are right,
**every criterion in the pre-registration is satisfiable and every gate passes.**
It survived criterion B7-6, a re-gate B7-6r built specifically to check that grid,
a third grid B7-10 built as its exact complement, three registered deductions
built on the pair, and two published claims.

（**为什么下游抓不到。** 打乱的划分仍然是六组，因为不管哪些层级坐在那些位置上，字母序里
带纯数字的位置永远是十四个。组数对、fill 对、贷款数对，**预注册里每条判据都可满足，每道
闸都过。** 它熬过了判据 B7-6、专为检查那张格子而建的复闸 B7-6r、作为它精确补集而建的第
三张格子 B7-10、建立在这一对之上的三条注册推断，以及两条已发布的结论。）

**Rule**: **when a list is read positionally against another object's codes, the
correspondence is an assumption. Construct it in one place, or print it.**
Constructing it in one place is the real fix: whatever assigns the codes should
return the names in the same call. Printing it is the cheap version and it is what
caught this one.

（**规则**：**当一个列表被按位置对着另一个对象的编码读时，这种对应是一个假定。要么在一
个地方一起构造，要么把它印出来。** 一起构造才是真修：谁分配编码，谁就在同一次调用里返
回名字。印出来是廉价版，而抓到这一次的正是它。）

**12a. Print the membership of every grouping before computing on it.** Not the
count. The contents. **A scrambled partition is invisible in a count and obvious
in a list.**

（**12a. 在对任何分组开算之前，把它的成员印出来。** 不是计数，是内容。**打乱的划分在计
数里看不见，在列表里一眼就看见。**）

**12b. A name asserts a membership and cannot verify it.** B7's §3.8 argues at
length that both boundaries of the coarse grid are the regulator's and that this
project chooses neither. That was true of the intent and false of the code for the
whole time it stood. **Prose about a mapping is not a test of the mapping**, and
the more careful the prose, the more it is trusted in place of one.

（**12b. 名字是对成员的断言，不能验证成员。** B7 的 §3.8 长篇论证粗格两个边界都是监管机
构的、本项目一个都没选。这话对于意图是真的，对于代码在它成立的全部时间里都是假的。**关于
一个映射的散文不是对那个映射的检验**，而散文越严谨，它越会被当成检验来信任。）

---

---

### 13. Criterion shape error　(seven instances in one stage, five written in one day)　（判据形状错，一个阶段里七次，其中五次是同一天写的）

**Symptom**: the criterion is not wrong about the world. **Its shape is wrong.**
It takes a quantity that carries estimation error and compares it to a line, and
the line has no width, or the rows are not disjoint, or the threshold is anchored
on something the run happened to produce.

（**症状**：判据对世界的判断没错，**它的形状错了**。它拿一个带估计误差的量去对一条线，
而那条线没有宽度，或者各行不互斥，或者阈值锚在这次跑碰巧产出的东西上。）

**The seven, all from stage B7, and the last five written on 2026-08-16.**

| what it said | why the shape is wrong |
|---|---|
| the gate's verdict must agree at **two draw counts** | the null maximum is monotone in the draw count by construction, so the second count could only lower a rank and the margin was `28` sigma. Hours, for an outcome fixed in advance |
| **three repetitions, all three must return the constructed rank** | a rate estimated with three trials, thresholded at one. A design whose true rate is `0.9` fails `27%` of the time. It killed a criterion on a one-in-three floor blip |
| two designs are the same when their cell sets have **symmetric difference exactly zero** | an exact-match test on `326,872` elements at threshold zero. Cannot separate three cells from three hundred thousand, and the quantity it stands in for is the co-occurrence counts |
| a bound table compared to `S(a,a)` with **exact inequalities** | fired on a margin of fourteen parts in a hundred thousand, against two bounds that were themselves defective |
| a table whose first row read "at **either** bracket" and whose third read "the brackets **disagree**" | not disjoint. Both fired and they said opposite things |
| a control requiring **direction 1** to carry, because "both grids read at least rank one" | a quantifier error. Rank one means **some** direction carries and says nothing about which |
| a test asking whether the observed direction is `46` | `46` was what the constructed run happened to lead on. **The test was anchored on a result** |

**Against those seven, what actually caught the errors in the same stage was five
things and every one of them prints an object rather than thresholding a number**:
the partition's membership, the eigenvector loadings, the loans per cell-class
entry, the off-diagonal correlations of `S`, and a self-check performed on request.

（**对着这七条，同一个阶段里真正抓到错误的是五件事，而且每一件都是把一个对象印出来，
不是给一个数卡阈值**：分组的成员、特征向量载荷、每个 cell-class 条目的贷款数、`S` 的
非对角相关，以及被要求时做的一次自检。）

**What this stage's record supports**: on the seven instances above, a criterion
that put a threshold on an estimated quantity did not do the job it was written
for. The two that worked were of one of two other shapes:

1. **structural** and about the code rather than the world: did every arm finish,
   is this decomposition an identity to `1e-16`, does this design's group count
   match its level count;
2. **a printed number with a reading declared in advance**, and no line drawn
   across it.

（这一阶段的实测是：判据落在两种形状里的一种时它有用 —— 一是**结构性的**、关于代码而
不关于世界的（每条臂跑完没有、这个分解是不是恒等式到 `1e-16`、这个设计的组数和层级数对
不对）；二是**一个印出来的数，外加一条事先声明的读法**。落在第三种形状上的那五张，
一次都没防住。）

**13a. Declared readings work; thresholds do not, and this stage tested both.**
Five registered outcome tables in B7 were built on wrong inputs or on rows that
were not disjoint and **protected nothing**. But the two that were well formed,
`§3.24`'s and `§3.25`'s, fired correctly and settled the stage. **The failures were
failures of construction, not of the principle**, and the construction that fails
is always the one with a line in it.

（**13a. 事先声明读法有用，卡阈值没用，而这个阶段两样都测过。** B7 里有五张注册的结果
表建在错输入上或者行不互斥，**一次都没防住**；而形状写对的那两张（§3.24 与 §3.25）正
确触发并且结掉了整个阶段。**失败的是构造不是原则**，而失败的构造里总有一条线。）

**13b. Pre-registration's value is as a record, not as a protection.** Those five
tables were all declared before their runs and all five were useless as gates.
What registration did do is make each failure visible and datable: keeping
`§3.9`-`§3.12` whole under a VOID marker is what let the pre-fix numbers be
retrodicted from the bug, which is how the bug was confirmed. **On this stage's evidence, registration
earned its keep as a record and not as a gate.**

（**13b. 预注册的价值是作为记录，不是作为保护。** 那五张表全是跑前声明的，作为闸门
五张全废；它真正做到的是让每次失败可见、可标日期。**为留记录而注册，不要指望它保护
你。**）

---

### 14. Unexamined residual　(two instances, an hour apart, both leaning the same way)　（残差没查错，两次，隔一小时，而且两次偏同一个方向）

**Symptom**: a leftover is reported as having **no candidate explanation**, and the
most ordinary candidate was available and simply not written down. The defect is
not that the leftover is unexplained. It is that **"I did not think of one" was
reported as "there is not one"**, and those are claims about two different
objects: the person and the world.

（**症状**：一块剩余项被写成「没有候选解释」，而最平凡的那个候选一直在手边，只是没写下来。
毛病不在于剩余项没被解释，而在于**把「我没想到」报成了「没有」**，
这两句讲的是两个不同的对象：人，和世界。）

**Both instances are from B7-16 on 2026-08-16, and both are in this file's author's
own text.**

| what was written | the candidate that was available |
|---|---|
| `v1` regressed on the class main effect `m` and its slope `m'` leaves `R^2 = 0.634` with a residual **still ordered in DTI**, reported as having no candidate explanation | if the interaction is a **smooth family of curves in DTI**, then `m` and `m'` are two elements of a smooth basis and nothing says the family's modes are spanned by them. **An ordered residual is what a smooth structure predicts** after regressing on two smooth functions. It is the signature, not the anomaly |
| in the same paragraph, that residual was said to be "what B7-17 is for" | B7-17 correlates a class's `gamma` across adjacent years in the same tract, which is a question about **time**. The residual is a question about the **shape of a loading** in one cross-section. They were joined because both were unexplained, and **"both unexplained" is not a relation** |

**What each one costs.** The first made a finding sound larger than it is, which is
the direction that gets a stage reopened for nothing. The second attached an unrun
arm to a question it cannot answer, and that arm costs a twenty-minute parse, so
the misattachment would have spent it on the wrong object.

**The rule.**

> **Before writing that something has no candidate explanation, write the most
> boring candidate down and say why it is not enough. If it cannot be written,
> that says the search has not happened, not that the explanation does not exist.**

**Same family as the reachability rule** (fingerprints ledger discipline 15, which
asks whether each mapped outcome still has probability mass): that one governs
**branches**, this one governs **residuals**, and both are satisfied by
substituting what is already in hand and doing the arithmetic. Cheap both times,
skipped both times.

**One thing worth recording separately**: both instances lean the same way, toward
making the leftover more mysterious. **A same-direction pair is a tendency and not
a coincidence**, and it is the reason this mode is written as its own entry rather
than folded into mode 13.

（**两次都偏向把剩余项说得更神秘。方向一致的一对不是巧合，是一种倾向**，
这也是这一条单独立目而不是并进第十三种的理由。）

### 15. Generalisation error　(one instance, and the generalisation was chosen because it used more of the data)　（推广错，一次，而那个推广正是因为「用上了更多信息」才被选中的）

**Symptom**: a quantity with one unambiguous meaning in a poor setting is carried
into a richer one where **two different objects answer to its name**. The richer
version is picked, and it is picked for the reason that makes it wrong: it is the
one that uses the extra structure. The two agree exactly where the setting is
poor and diverge exactly where it is rich, **that is, on the part of the data the
move was made in order to exploit**. Nothing about the code looks wrong. The name
is the same, the formula is a textbook formula, and the arithmetic is exact.

（**症状**：一个在贫瘠设定里含义唯一的量，被搬进一个更丰富的设定，
而在那里**有两个不同的对象都叫这个名字**。丰富版被选中，而选中它的理由正是它错的理由：
它是那个「用上了新结构」的版本。两者**恰好在设定贫瘠处相等，恰好在设定丰富处分歧**，
也就是在「当初做这次搬迁正是为了利用」的那部分数据上分歧。
代码没有一处看着不对：名字一样，公式是教科书公式，算术精确。）

| Instance（实例） | What went wrong（错在哪） | 原文 |
|---|---|---|
| B10 `b10_support.py` v1, `b1_directed` | `b1` on an undirected graph is the cycle space, and that is what `H^1(G)` means. Moving to the observed **directed** transition graph, the version that uses the direction is the digraph's circulation space, and it counts a reciprocal pair `u -> v`, `v -> u` as `2 - 2 + 1 = 1`. **An out-and-back is not a cycle**: `b1_theorem.md` §5's scoping block says so in as many words, *on a two-position graph {rent, own} an out-and-back walk sums to zero by antisymmetry and is not a cycle at all*. The two definitions coincide on every graph with no reciprocal edges, and reciprocal edges are the whole reason the transition data is worth having. | B10 `b10_support.py` v1 的 `b1_directed`：无向图上 `b1` 是环空间，那正是 `H¹(G)` 的意思。搬到观测到的**有向**转移图上，「用上方向」的那个版本是有向图的循环空间，它把互相的一对 `u→v`、`v→u` 算成 `2−2+1 = 1`。**往返不是环**，`b1_theorem.md` §5 的 scoping block 原话就是这句。两个定义在任何没有互相边的图上重合，**而互相边正是这份转移数据值得要的全部理由** |

**How it was caught, and it is the only reason it was caught**: both versions
printed side by side, and on grid g3 the walkable count came out **larger** than
the undirected one. A walkable cycle is a cycle, so that ordering cannot hold.
**A quantity printed alone cannot violate an ordering it was supposed to
satisfy.** The generalisation had been introduced by the same author in the same
file's §16.6, with a sentence that asserted the ordering without checking it.

（**它是怎么被抓到的，而这也是它被抓到的唯一原因**：两个版本并排印出来，
在网格 g3 上「走得完的」那个数**大于**无向的那个。走得完的环是环，那个序不可能成立。
**一个单独印出来的量，违反不了一条它本该满足的序。**
这个推广是同一个作者在同一份文件的 §16·6 里引入的，
那里那句话**断言了这条序而没有检查它**。）

**Rule**: when a quantity is generalised into a richer setting, **write down the
ordering or equality that must hold between the old form and the new one, print
both, and check it in the code.** Two forms of the same name in one output is not
redundancy, it is the only place the substitution can be caught, because every
other symptom of this mode is invisible: the name is right, the formula is
standard, the arithmetic is exact, and the number is plausible.

（**规矩**：一个量被推广进更丰富的设定时，**先写下新旧两式之间必须成立的序或等式，
两个都印，并且在代码里检查它。** 同一个名字的两种形式同时出现在输出里不是冗余，
**它是这一模式唯一能被抓住的地方**，因为这一模式的其他每一个症状都是隐形的：
名字对，公式标准，算术精确，数字看着也合理。）

**A note on where the check belongs.** `b10_support.py` now computes the invariant
`b1_walkable <= b1_undirected` inside the estimator and prints a loud line if it
fails, rather than leaving it to a reader who happens to compare two columns. The
proof is one line: the walkable cycles are the cycle spaces of **vertex-disjoint**
subgraphs, hence independent subspaces of the whole cycle space. **An invariant
with a one-line proof belongs in the code, not in a document**, because the
document is read once and the code runs every time.

（**关于这道检查该放在哪。** `b10_support.py` 现在把不变式
`b1_walkable <= b1_undirected` 算在估计量内部，不成立就大声印一行，
而不是留给一个碰巧去比两列的读者。证明只有一行：走得完的那些环是**顶点不相交**
子图的环空间，故是整个环空间的独立子空间。
**一条证明只有一行的不变式该进代码不该进文档**，因为文档只被读一次，而代码每次都跑。）

## The checklist before reporting a number　（报数之前的清单）

Answer each of these before any number goes into `results/` or into a
conversation:

（任何数字进 `results/` 或进对话之前，逐条回答：）

1. **What is the time quantifier in the claim?** Does my window agree with it?
   （**主张里的时间量词是什么？** 我的窗口和它一致吗？）
2. **Is the denominator the same thing on both sides?** (per unit / per agent /
   per trade)
   （**两边的分母是同一个东西吗？**（每单位／每人／每笔））
3. **Do the two sides aggregate the same way?** (arithmetic or geometric, and on
   what weighting)
   （**两边的聚合方式一致吗？**（算术／几何、加权口径））
4. **Have I held fixed what should be held fixed?** Is there an operation that
   changes two things at once?
   （**我固定住了该固定的吗？** 有没有一个操作同时改了两样东西？）
5. **Is my population defined by the state** before **treatment,** or selected on
   an outcome? **And does the treatment vary over that population?** A treatment
   that disperses along a dimension the measured population barely spans reads
   as zero, and that zero says nothing about the mechanism.
   （**我的人群是按处理**之前**的状态定义的吗？** 还是按结果选的？**以及，处理在这个
   人群上有变异吗？** 一个沿某个维度分散的处理，若被测人群在那个维度上几乎不变，它必然
   读作零，而这个零不携带关于机制的信息。）
6. **Is my tolerance the same order of magnitude as the effect being measured?**
   （**我的容差和被量的效应同量级吗？**）
6b. **Has every design I am reading a number from been calibrated, including the
   control arm?** And does the calibration field have the same **shape** as the
   observed one, not merely the same total size?
   （**我读数的每一个设计都校准过吗，包括对照臂？** 以及，校准场和观测场的**形状**一致
   吗，还是只有总量一致？）
7. **Is there an arm whose true value should be zero, or should not move,
   running the same machinery?**
   （**有没有一个「真值应当是零／应当不动」的臂，跑同一套机器？**）

8. **Would this guard say something different if the guard itself were broken?**
   Have I run it on a case it should reject?
   （**如果守卫自己坏了，它说的话会不一样吗？** 我拿一个它应该拒绝的样例试过它吗？）

9. **Is this number keyed on a set fixed at construction time?** If it were
   recomputed from the measured magnitude its real counterpart is assessed on,
   would it change? And if this is one side of a two-sided instrument, is the
   other side keyed on the same kind of thing?
   （**这个数是不是挂在一个构造时定死的集合上？** 如果改成按它在现实里所依据的那个可测
   量重算，它会变吗？如果它是一个双边工具的一边，另一边挂的是不是同一类东西？）

10. **Is this stage in the runner?** If nothing re-runs it, its stored file is a
    memory of some earlier code and not a reading of this code. And if a default
    on shared machinery has moved, which stages stand on that machinery, and were
    they re-run?
    （**这个阶段在 runner 里吗？** 如果没有东西重跑它，它存盘的那份是对某一版旧代码的
    记忆，不是对这一版代码的读数。以及，如果共用机器上的某个默认值动过，有哪些阶段站在
    那台机器上，它们重跑了吗？）

11. **What can this arm return, and which of those does it already imply?**
    Strike the implied ones. If the only survivor is "the code is broken", it is a
    unit test and it belongs on a fixture, not on the full sample. And can both of
    its outcomes actually be reached, or does its construction force one?
    （**这条臂可能返回什么，其中哪些是它已经蕴含的？** 划掉被蕴含的。如果只剩下「代码
    错了」，那它是单元测试，该跑在样例上而不是全样本上。以及，它的两种结局真的都到得了
    吗，还是它的构造逼出了其中一种？）

12. **Is any list here read positionally against another object's codes?** If
    so, were the two constructed together, and have I printed the correspondence?
    A grouping's contents, not its count.
    （**这里有没有哪个列表是按位置对着另一个对象的编码读的？** 如果有，这两者是不是在
    一起构造的，我有没有把对应关系印出来？分组要看内容，不是看计数。）

13. **Is any claim here taken from another document's summary of a third
    document?** Then read the third. A summary that carried a caveat and lost it
    on the way here is the common case, and the claim usually gets **stronger** at
    each hop because a hedge is the first thing a paraphrase drops. Stage B7 did
    this on 2026-08-16, in three hops, and arrived at the reverse of what the
    original said.
    （**这里有没有哪条主张是从另一份文档对第三份文档的转述里拿来的？** 有就去读第三
    份。转述带着 caveat 而 caveat 在路上掉了，是常见情形，而且主张往往每转一手就更
    **强**一分，因为释义最先丢掉的就是限定。B7 阶段 2026-08-16 这么做过，转了三手，
    到手的结论和原文相反。）

Item 7 is the only one **designed to catch an error rather than to avoid one**:
A5-6's zero calibration was the only one of the eleven caught by an automatic
guard, and the other ten were all caught by a human inspecting a number that
looked wrong. **A zero calibration is standard equipment on every new carrier,
not an option.**

（第 7 条是唯一一条**设计出来专门抓错**的：A5-6 那条零标定是本 session 十一次里唯一被自
动守卫抓到的，其余十次全靠人工审视异常数字。**每个新载体标配零标定，不是可选项。**）

---

14. **Am I about to write that something is unexplained?** Then what is the most
    boring thing that would produce it, and why is that not it? A residual that is
    left over after fitting two functions, and that still has structure, is the
    **expected** shape when the truth is a smooth family and the two functions are
    two of its modes. Write that down and rule it out, or do not use the word.
    （**我是不是正要写「这一块没有解释」？**那么，最无聊的那个解释是什么，
    它为什么不成立？拟合了两个函数之后剩下的、还带结构的残差，在真值是一族光滑曲线、
    而那两个函数是其中两个模态时，**本来就该长成那样**。把它写出来并排除掉，
    否则不要用「没有解释」这个词。）　→ 第十四种失败模式

15. **Is this property written twice on the object, and am I reading the weaker
    statement?** A file name against the page's own title, a directory listing
    against a content hash, a table header's first row against its second, a
    whole headline against the clause that governs the noun. **The outer layer is
    always the easier one to read, which is why it is the one that gets read**,
    and every one of these produces output in a plausible range rather than an
    error. Four of them sat in one stage's pipeline at once, and one of them
    would have made a replication criterion pass at one hundred per cent by
    construction. Ask which of the two statements is the authority before either
    is read, and print the pairs.
    （**这个属性在被读的对象上是不是写了两遍，我读的是不是弱的那一遍？**
    文件名对页面自己的标题，目录列举对内容哈希，表头第一行对第二行，
    整条标题对带着名词的那个分句。**外面那一层总是更容易读，所以它总是先被读**，
    而这四种全都产出落在合理区间的东西，不报错。一个站的管道里同时坐着四个，
    其中一个会让一条复验判据以百分之百通过，而那是构造出来的。
    在读之前先问哪一处是权威的，并且把成对的两处印出来。）　→ 失败模式 87

## One meta-rule　（一条元规则）

**A self-check catches self-contradiction and does not catch coherent drift.**
That all eleven were caught in-house is precisely what says they were all of the
self-contradicting kind: numbers that did not add up, signs that flipped. The
dangerous ones are the drifts that are **internally coherent**. They raise no
error. They quietly answer a different question.

（**自查抓得到自相矛盾，抓不到自洽的漂移。** 十一次全部被自己抓到，恰恰说明它们都是自相
矛盾型的（数字对不上、符号翻转）。真正危险的是那些**自洽的**漂移——它们不会报错，只会
安静地回答一个不同的问题。）

Two ways at them, **both scoped as of 2026-08-16**, because the unscoped versions
cost a session apiece and were paid on every change rather than on the ones that
could carry a drift.

**One: route the judgement to a model holding a different context (a review
session). Trigger: a conclusion is about to enter the manuscript.** Not once per
station. A station that stays inside the ledger has not yet been read by anyone
who could be misled by it, so the review buys nothing there.

**Two: a written list of everything changed but believed not to matter. Trigger:
the change touched `src/`.** A change confined to `experiments/` reaches one
station by construction, so the list would enumerate a scope the file path
already states. The most dangerous deviation is never the one that was recorded;
it is the one judged irrelevant and therefore never written down, and that
asymmetry lives in shared machinery, where "irrelevant" is a claim about stations
I was not thinking about.

（对付它们有两个办法，**2026-08-16 起两个都带触发条件**，因为不带条件的版本每次各花一个
session，而且是在每一次改动上付，不是在可能载有漂移的那些改动上付。）

（**其一：把判断路由到一个 context 不同的模型上（复核 session）。触发条件：某条结论
即将进原稿。**不是每站一次。还留在台账里的站，尚未被任何会被它误导的人读到，复核在那里
买不到东西。）

（**其二：列出「我改了但认为不影响」的清单。触发条件：改动碰了 `src/`。**只改
`experiments/` 的改动按构造只到一个站，清单会去枚举一个文件路径已经说明的作用域。
最危险的偏离从来不是被记录下来的那个，是被判为无关紧要因而没写的那个，而这个不对称
只住在共享机器上，那里的「无关」是一句关于改动者当时没在想的那些站的断言。）

**Failure mode 9 is that meta-rule's first specimen, and it is a specimen of the
second trigger specifically.** It raised no error, every verdict it carried was
correct, and it quietly answered a question about an economy the repository had
already stopped describing. The eleven instances counted at the top of this file
were all of the self-contradicting kind and all found in-house by inspection;
this one was found only by re-running.

**What it establishes is scoped too (2026-08-16).** The commit that restated A3
turned on a `rent_rate` default in shared machinery, and A5 ran on that
machinery. **A stage re-runs when a default under it moved, not because a round
ended.** The earlier phrasing here, "re-running a stage whose code has not
changed is not a redundant action", read as a standing obligation to re-run
everything, and that is not what mode 9 shows. The scoping rule with the checkable
The scope marker is checkable without any external document: `experiments/*.py` is single-station and
`src/monetary_topology/*.py` is shared. This file does not keep a second copy of it.

（**第九种失败模式是那条元规则的第一个标本，而且专门是第二个触发条件的标本。** 它不报错，
它带的每一条判词都是对的，它安静地回答了一个关于仓库早已不再描述的那个经济的问题。
本文件开头计的十一次实例全部是自相矛盾型、全部靠人工审视在内部抓到；这一次只能靠重跑抓到。）

（**它确立的东西同样带作用域（2026-08-16）。**重述 A3 的那次提交在共享机器上打开了默认的
`rent_rate`，而 A5 整个跑在那台机器上。**一个阶段要重跑，是因为它脚下的默认值动过，
不是因为一轮结束了。**这里原来的写法「重跑一个代码没有变过的阶段，不是一个多余的动作」
会被读成「随时都该把所有东西重跑一遍」的常设义务，而那不是第九种失败模式所证明的。
作用域判别式本身是可查的，不依赖任何外部文档：`experiments/*.py` 是单站的，
`src/monetary_topology/*.py` 是共享的。本文件不另存一份拷贝。）

---

## 结果缓存与它的标签（2026-08-17 设计定案）

**问题。** B8 有五个站各自从核心表重建同一条流水线：`disc_of_row`、
`row_residuals`、`find_loops`、`loop_sums`。一遍是 1.7 亿行的四次扫描，
里面最贵的 `contract_payments` 是几百万个合同段的 Python 循环，
**每一次重跑任何一站都再付一次**。缓存的东西很小：六档八万多个环、
几十个字段、几兆。它替掉的是一次全档扫描。

### 一、缓存不是文件名，是内容寻址

**一份过期的缓存比没有缓存坏。** 本仓库的坑表大半是「曾经为真、后来还在被读」，
所以一个只按档名做键的缓存是制造这类缺陷的机器。

键是**产出这些数字的全部函数源码的哈希**，加上曲线规则与核心表 schema。
改动其中任何一个，标签就变，缓存重建，**没有人需要记得去失效它**。
标签存在数据旁边、加载时核对；过期或缺失时 `load` 抛错，绝不返回旧数。

**清单必须是整模块，不是这份文件恰好调到的函数**：往下三层的辅助函数一样承重，
而按函数点名的清单会过期。**产出缓存的那个模块自己也必须在清单里**
（第一版漏了，于是新加一个写进缓存字段的函数时标签纹丝不动）。

### 二、数字没变而标签变了，怎么办

散文改动（docstring、注释、空白）会推动源码哈希，于是一次注释改动就要
重扫 1.7 亿行。这是纯损失。**三条路，只有两条能走。**

| 方案 | 判定 |
|---|---|
| **无条件 retag**：一个把现有缓存里的标签改写成当前值的开关 | **禁止。** 它是一个撒谎按钮：用在真改动之后，会静默污染全部下游数字，而且事后无从分辨。这正是标签存在所要防的那一类缺陷，加了个按钮 |
| **哈希 AST 而不是源码**：`ast.parse` 之后剥掉 docstring 节点再 `ast.dump` | **走这条。** 注释与 docstring 改了标签不动，**因为它们本来就不可能改动数字**。这不是开关，是一个正确的等价关系。约十行 |
| **`retag --verified`**：真改了代码但相信数字没动时，先重算再逐位比对，只有全等才改写标签 | **保留，作为兜底。** 它要付一次重算，所以救不了散文改动那个场景，但它是「我改了真代码且认为数字不变」唯一诚实的走法 |

**AST 方案的唯一附带条件，记在这里**：若将来有代码去读自己的 docstring 来决定
一个数（`inspect.getsource`、`__doc__`），AST 哈希就不再覆盖它。本仓库
现在有两处用 `inspect.getsource`（标签自身、自检里的存在性断言），
**都不产出数字**，所以条件成立。**这一条要跟着 AST 方案一起走**，
它是这个方案在什么条件下正确的说明，不是脚注。

### 三、为什么这一条值得单独写下来

**「省时间」不是理由，「不撒谎」才是。** 缓存的收益是运行时间，
而运行时间在本项目里从来不是瓶颈；真正的成本是**每一次不必要的重建都在训练人
把重建当噪声**，而一个被当成噪声的信号，在它真的该响的那一次也不会被听见。
无条件 retag 走得更远：它把「标签动了」这个信号直接接到人的判断上，
**而人的判断正是标签存在所要替代的那个东西**。

**元规则的实例。** 上一节写「自查抓得到自相矛盾，抓不到自洽的漂移」。
一个手动 retag 之后的缓存是**完美自洽的**：数字之间互相对得上，
每一条自检都过，只是它们回答的是上一版代码的问题。
**这是那条元规则能举出的最干净的一个例子。**

---

## 失效模式 16：文本替换的补丁，没匹配上不是错误而是静默的空操作
## Failure mode 16: a patch applied by text substitution, where a miss is a no-op and not an error

**实例（2026-08-17，`b10_o18_assistance.py` 的 `--age-split`）。**

给一个已有脚本加一个新维度，改动是用一段文本替换脚本打进去的：一处替换插入
计算 `two_by_two` 的代码块，另一处替换在写盘的字典里加上 `"two_by_two_age_code":
two_by_two`。**第二处匹配上了，第一处没有。**

替换脚本随后跑了 `ast.parse`，**通过**。
`ast.parse` 检查的是文法，而**一个未定义的名字在文法上完全合法**，
它只在运行到那一行的时候才是 `NameError`。

于是缺陷一路活到：**扫完 74,937,616 行 perf、印完全部读数、
写盘那一刻才炸。** 全部计算作废，一次全扫的时间是纯损失。

### 为什么它不属于已有的任何一条

- 它不是「判据不可能失败」（模式 11 那一族）：这里根本没有判据。
- 它不是「取不到误报成不存在」：数字一个都没产出。
- **它是一个工具的失败模式：`str.replace` 匹配不上时返回原串，不报错。**
  一个「应当改而没改成」的补丁，与一个「不需要改」的补丁，**在返回值上不可区分。**

### 两条处置，都要

**一、文本替换必须断言它改动了东西。**

```python
before = s
s = s.replace(old, new, 1)
assert s != before, f"replacement did not match: {old[:60]!r}"
```

**没有这一行的替换脚本，等于把「改没改成」交给运气。**

**二、语法检查不是验证，调用才是。**

`ast.parse` 能证明文件能被解析，**不能证明任何一行会跑。**
凡是新加的代码路径，**自检里必须有一个用例真的调用它**，
而且**调用到它的打印与序列化**，因为这一次炸的正是序列化那一行。

修复之后加的用例长这样：构造一个假的累加器，调 `two_by_two_table`，
核四个格子加起来等于总数，**然后真的调 `print_two_by_two`，
再把结果 `json.dumps` 一遍**。三步里任何一步缺席，这个缺陷都还在。

### 一条更一般的

> **一个补丁的正确性有两层：它写对了没有，和它装上了没有。**
> **语法检查只看第一层。而第二层的失败在本项目里更贵，
> 因为它总是在最长的那条路径的末尾才现形。**

**与结果缓存那一节同族**（§「结果缓存与它的标签」）：那里的危险是
「代码动了而数字没重算」，这里的危险是「代码没动而以为动了」。
**两者都是源码与它所产出的东西之间的对应关系失效，方向相反。**

---

## 失效模式 17：结局映射用合取的支写成，于是它不是一个分割
## Failure mode 17: an outcome map written as conjunctive branches, which is not a partition

**实例（2026-08-18，B10 §10·9 的 `--grid-k`，连着两次，同一个器具）。**

**第一次**（§10·9·8）：四支里第一支写「实测随账龄下降」，而「下降」没说清是**逐格**还是**净额**；
第一支与第三支还重叠（「两者都下降」与「两者都下降且实测在同一侧」可以同时为真）。
实测是净额下降而逐格不单调、且始终在预测的同一侧，**没有一支唯一地接住它。**

**第二次**（§10·9·9）：第一支写成「不再同号大偏 **且** 点预测落在 ±2 个百分点内」。
实测**前半成立**（偏差从 −11.6 缩到 −7.6，不再在 −10 以下）而**后半不成立**（预测高出 6 到 8 个百分点）。
**四支一支都落不进去。**

### 为什么它不属于已有的任何一条

- **不是 11 那一族（判据不可能失败）**：这里判据完全可能失败，而且它确实失败了。
- **不是 13（判据形状错）**：形状是对的。符号判据与点预测都是合法的判据形状，
  **坏的是把它们组装成支的那一步。**
- **它是结局映射的失败，不是判据的失败。** 判据说了话，**而没有一支接得住那句话**，
  于是裁词只能靠跑完之后的自由裁量——**而那正是预注册要消掉的东西。**

### 三条处置，都要

**一、支按一个变量分，不按几个条件的合取分。**

写 `A ∧ B` 与它的否定，实际上只切了两块；而人写的时候心里想的是四块
（`A∧B` / `A∧¬B` / `¬A∧B` / `¬A∧¬B`），**只写了对角线上的两块，另外两块无声地消失。**

**二、一次注册里有两个判据时，先写死哪个是主判据。**

支按**主判据**分，另一个（例如点预测）作为**同一支内部的加细**报出来，**不参与分支**。
B10 §10·9·9 事后正是这么裁的（主判据是符号，点预测降为加细），**但那是跑完之后才决定的，
所以它是自由裁量不是预注册。**

**三、器具若有臂，映射必须先说清两条臂落在不同支时判什么。**

**2026-08-19 追加，实例是同一族的第三次**（B10 §5·5）：主判据是「账龄 2–6 上 `obs − sim` 的符号」，
三支穷尽，**而器具有两条臂**（全部 / 过闸）。实测**全部臂五格同号为负（第一支），
过闸臂混号（第三支）**。注册里只写了「第一支落地要两条臂同号」，
**没写两条臂落在不同支时判什么，于是又一次没有支可落。**

> **一张按 `k` 支写成的映射，配上 `m` 条臂，实际的结局空间是 `k^m` 不是 `k`。**
> **只写 `k` 支就是又一次把对角线当成全集。**

**处置**：注册时就写死**哪条臂是主臂**（通常是未被选择的那条），
支按主臂分；**另一条臂的作用写成一道否决，不写成另一张表** ——
「主臂落第一支且副臂不反号，才认第一支；副臂反号则第一支不认，
**而此时落什么，也要现在就写下来**」。

**四、写完之后逐支代一遍。**

随手取三四个**可能的**实测形状，看每一个落进哪一支。
**落不进任何一支，或者落进两支，这张映射就还没写完。**
这一步花不到五分钟，而两次失败各花掉一次全档扫描的机会成本。

### 一条更一般的

> **一个预注册的全部价值，在于跑完之后不需要再做判断。**
> **一个不是分割的结局映射，把那个判断原封不动地退回给跑完之后的人，**
> **而那时他已经看过数了。**

**与第 13 种的关系**：13 管的是**一条判据自己写坏了**，17 管的是**几条各自写对的判据被组装坏了**。
**装配也是构造，装配也会错。**

---

## 失效模式 18：对着一个已经没有生产者的数做交叉核对，那不是交叉核对
## Failure mode 18: a cross-check against a number whose producer no longer exists

**实例（2026-08-19，B10 §5·4 的 `--zero-upb`）。**

注册时写了一道硬闸：新器具必须读到 **1,192,198 / 144,719 / 975**，
「对不上说明人群不同，那时本节其余读数一律不引」。
实测 **1,192,244 / 144,761 / 1,016**，差 **+46 / +42 / +41**。闸响了。

**然后发现它不可能过**：`grep -rn '1192198|144719' experiments/*.py results/*.md`
在整个仓库里只找到一处，**就是新器具自己打印器里的那句提示**。
**那三个数出自一次没有留下代码、也没有留下结果件的临时扫描。**

**于是这道闸只有两种结局：不等，或者碰巧相等。它不能被判。**
差在哪里查不出来，因为对面没有第二份实现可以逐项对。

### 对照，同一种写法在可复现的对面上就工作

同一轮里，B10 §10·9 的表 C 用一模一样的写法对着 `b10_o18_null.py`
读到 **10,247,131 / 4,901,368，逐位精确**。
**差别不在判据的写法，在对面有没有代码。**

### 为什么它不属于已有的任何一条

- **不是 11 那一族「判据不可能失败」**：这一条是反的，**判据不可能被判**。
  它可以响，而响了之后没有下一步。
- **不是 17「结局映射不是分割」**：映射本身是分割，
  **坏的是那道闸的前提——它假定对面那个数可复现，而这个假定没有被写下来，也没有被检查。**
- 它是**参照物的失效**，不是判据的失效，也不是映射的失效。

### 两条处置，都要

**一、交叉核对必须点名生产者，不能只点名数。**

注册一道对着别处某个数的闸时，**同一行要写出那个数是哪个脚本、哪次运行、哪份产物给的**。
写不出来，**那道闸就不该被注册成闸**，只能注册成一句「与某处的记载并排印，两组都留档」。

**一之补，2026-08-19：点名生产者是必要不充分，两侧还得跑在同一个人群上。**

**实例（同日，B10 §5·5·6）。** 注册一道闸时点名了生产者
（靶子 12.1420%，出自 `results/b10_zero_upb.json`，`--zero-upb`），**第一条处置做到了**。
**可两侧的人群不同**：靶子量在「全部账龄 0 的贷款」上，不反解不过闸；
而模拟那一列跑在「反解成功的贷款」上，还带着反解误差。
**于是那一列在 `θ = 0` 上量出来的是闸的通过率（`1 − 0.7369 = 0.2631`，逐位对上），不是摊还表。**

**对照**：同一个人写的 grid-k 表 C 逐位精确（10,247,131 / 4,901,368），
**因为它把对面的人群谓词逐字复刻了一遍**（`not (a0 >= 8 and age >= 8)`）。
**差别不在点没点名生产者，在有没有复刻人群。**

> **注册一道对照闸时，同一行要写三样：那个数是谁产的、跑在哪个人群上、
> 本器具怎么复刻那个人群。三样缺一样，那道闸就还不是闸。**

**二、写不出生产者的对照，读法要跟着降级。**

降级之后的读法是：**新器具的读数以它自己的人群定义为准，不作旧数的复现引**；
旧数加指针留档；**两组并排，不裁哪一组对**，除非旧数那一侧被重新实现。

### 一条更一般的

> **一个数的可引用性，不在于它被写在哪份文件里，在于它的生产者还在不在。**
> **无代码的数可以当历史留档，不可以当闸的另一侧。**

**与第 13、17 两种的分工**：13 是一条判据自己写坏了，17 是几条写对的判据被组装坏了，
**18 是判据与组装都对，而它要比对的那个东西已经不存在。**


## 失效模式 19：标签表的定义域比解析器的窄，而那一档值只在没跑过的档上出现
## Failure mode 19: a label table narrower than the parser that feeds it, where the uncovered value occurs only on archives nobody has run

**实例（2026-08-19，B12 在 `b10_holonomy_ladder.anchor_states` 上）。**

`b8_core.as_delinq` 把 `00`–`98` 送到整数，三个哨兵送到 253／254／255，
**而两位字符串 `"99"` 送到字面 `99`**。取标签的那一段写的是

```python
ok = dq <= 98
lab[ok] = np.char.zfill(dq[ok].astype(str), 2)
for v, name in bf.SENTINEL.items():
    lab[dq == v] = name
```

**`99` 既不在 `<= 98` 里，也不是哨兵，于是整行留成 `None`。**
下游一个 `sorted()` 抛 `TypeError`，**而在别的写法下它会静默地成为一个未命名状态。**

### 它为什么活了下来：输入集从来没有走过那一支

| 档 | `[99,252]` 里的行数 |
|---|---|
| 2002Q1 | 647 |
| 2006Q1 | 2,199 |
| 2007Q1 | 1,883 |
| 2012Q1 | 90 |
| 2017Q1 | 1 |
| **2019Q1** | **零** |

**`b10_holonomy_ladder.py` 只在 2019Q1 上跑过**（它的记录文件里只有一档），
**B12 到此为止的每一道闸也只在 2019Q1 上跑过**（那一档是类数复现的锚）。
**两个站，两份独立实现，同一个盲点，因为它们共享同一个输入档。**

> **缺陷不是没有被检查，是那一支从来没有被输入走到过。**

### 为什么它不属于已有的任何一条

- **不是 16「文本替换的补丁没匹配上」**：这里没有补丁，代码从第一版就是这样。
- **不是 9「记录错」**：记录与代码一致，一致地漏了同一档值。
- **不是 8「成员错」**：量挂的不是构造时下标，挂的是解析出来的值，**只是值域没盖全。**
- **不是 5「人群错」**：两组不是按结果选的。
- 它是**定义域不合**：**两段代码对同一个字段的取值范围有两套理解，而它们没有对过。**
  加上**输入集单一**，于是不合的那一档从不出现。

### 三条处置，都要

**一、值域从解析器取，不要手写常量。**

标签表的边界写成 `dq < min(SENTINEL)` 这种**由解析器的约定推出来的式子**，
不要写 `<= 98` 这种**记住的数**。**两处各写一遍就是两个会分头漂的真值。**

**二、留不下标签的行必须抛，不许静默。**

```python
missing = int(sum(1 for x in lab if x is None))
if missing:
    raise RuntimeError(...)
```

**一个 `np.empty(dtype=object)` 默认装满 `None`，而 `None` 会一路走到很远的地方才出声。**

**三、任何「只在一个档上跑过」的器具，在被第二个站引用之前，先在第二个档上空跑一次。**

**空跑不必读数**，它只需要走完取标签那一段。**代价是几十秒，而它挡掉的是一整轮返工。**

### 一条更一般的

> **测试覆盖率说的是「哪几行被执行过」，它不说「哪几种取值被输入过」。**
> **一个字段有 256 个可能取值而你只跑过一个档，那么你验的是那个档的取值分布，不是那段代码。**

**同一天在同一批代码上查到第二处，形状相同**：
`b10_support_fannie.states_of` 的标签表 `labels = [f"{i:02d}" for i in range(99)]` 之后接
`labels += [SENTINEL[253], ...]`，于是**下标 99 既是字面 `99` 的位置，也是 `ODD253` 的位置**，
`code[delinq == 253] = 99` 把两条路送进同一格。**五档共 4,820 行。**
**两处都是同一个 `99`，而它们是各自独立写错的。**

**与第 1、16 两种的分工**：1 是窗口取错了范围，16 是一次改动没落上，
**19 是两段代码对同一个字段的值域各自有一套理解，而输入集恰好从不让它们碰面。**

---

## 失效模式 20：选支的变量是一个计数，而结局的处置需要被计数对象的身份
## Failure mode 20: the branch is chosen by a count, but its landing needs the identities of the things counted

**实例（2026-08-19，B10 §8·14 在 Freddie 的 perf 侧）。**

注册的变量是「**行为像零息余额的列有几条**」，四支：一列 × 三种签名，加一支「两列或更多」。
**第四支的处置写的是**「C13 的对应物存在，照 Fannie 的写法排掉双载贷款，并印被排掉的笔数与占比」。

实测：三十五列里 **十三列** 过了那条读法。**十三 ≥ 2，第四支按字面落地。**
**而处置执行不了**：它要「双载贷款」，那需要知道是**哪两列**，**而一个计数不带身份。**

### 病灶是读法里的一个「或」

读法写的是「多数为零 **或空白**、少数为正、为正时互异值多」。

| | `col 12` | 处置栏那一族（十一列）|
|---|---|---|
| 空白行 | **0** | **74,918,072** |
| 读零 | 74,258,200 | 0 到 3,295 |
| 读负 | **0** | 4 到 19,328 |

> **「多数为零」与「多数为空白」在结构上是相反的两件事。**
> 前者说「**这个字段每一行都报，而这一行没有余额**」；
> 后者说「**这个字段只在一件罕见的事情发生时才写**」。
> 一个「或」把它们并成一个条件，于是**整块只在处置行才写的字段都过了**。

**若当时写的是「多数为零，且从不空白」，过的恰好一列，而那正是实质上对的那一支。**
**判据与实质之间隔的就是那一个「或」。**

### 为什么它不属于已有的任何一条

- **不是 17「合取的支不成分割」**：本条的四支是一个分割，穷尽，不重叠。
  **支没写错，是支选出来之后用不了。**
- **不是 11「判据画在估计量上」**：计数不是估计量，读法里也没有阈值。
- **不是 5「人群错」**：人群是全部行，没有选择。
- **不是 19「值域不合」**：那一条是代码叫不出某个取值的名字；本条每个取值都读得出来。
- 它是**变量与处置不匹配**：**变量把对象压成了一个基数，而处置要的是对象本身。**

### 三条处置，都要

**一、结局的处置若点名了对象，变量就必须携带那些对象。**

一个「有几个」的变量只能支撑「有没有」那一类处置。
**要「拿它们去做某件事」，注册时就得写成「哪几个」，并要求器具印出名单。**
**写完结局映射之后，逐支问一句：这一支落地了，我手上有没有执行它所需要的东西。**

**二、「多数为 A 或 B」这种读法，先问 A 与 B 在结构上是不是同一件事。**

**零与空白不是。** 缺席有两种：**一种是「报了，是零」，一种是「没报」。**
把它们并进一个条件，读法就同时收下了两族形状相反的列。
**一般地：一个用「或」连起来的条件，要给每一支各代一个反例试试它收不收。**

**三、读法里要有一条「反向不可能」的条件，因为正向条件都可以被巧合满足。**

余额**不为负**就是这样一条：它排掉的不是「像不像」，而是「**可不可能是**」。
**那十三列里有六列读负，其中两列负得超过八成**（98.42% 与 83.05%）。
**一条结构上的不可能，比三条「看起来像」更管用。**

### 一条更一般的

> **一个判据有两个部分：选哪一支，和落地之后干什么。**
> **两个部分必须用同一批对象说话。**
> **前一半用基数、后一半用身份，那不是判据松，是判据的两半接不上。**

---

## 失效模式 21：单侧的判别式——只检验了一个身份，把它的否定当成「什么都不是」
## Failure mode 21: a one-sided test — only one identity is checked, and its negation is read as "none of them"

**实例（2026-08-19，B10 §8·14·6·5 在 Freddie 的 orig 侧）。**

要在 31 列里认出到期日列。**注册的锚点是一个不变性**：
按期限分层之后，`月差(该列, 首个报送期) − 期限` 的顶桶偏移**在每一层相同**。
分支写死为三支：恰好一列全等／**没有一列全等 ⇒「maturity 那一路不存在」**／多于一列全等。

实测：外观筛出两列，**两列都不全等**（互异顶偏移 234 与 27，在 264 个层上）。
**第二支落地，而它的措辞是「不存在」。**

### 两个不变性是一对，而锚点只写了一个

| | **A：顶偏移恒定** | **B：顶偏移 ＋ 期限 恒定** |
|---|---|---|
| **orig col 2** | 1 / 264 层，74.188% 的贷款 | **220 / 264 层，99.993% 的贷款** |
| **orig col 4** | **220 / 264 层，99.993% 的贷款** | 1 / 264 层，74.188% 的贷款 |

> **A 恒定 ＝ 这个日期是从到期日量起的。**
> **B 恒定 ＝ 这个日期是从起息侧量起的。**
> **两个都是身份，而且它们是互补的一对。**
> 锚点只写了 A，**于是 B 那一列在 A 上不成立，被读成「什么都不是」。**

**最要紧的一点**：**B 这个身份在注册的说明文字里被点过名。**
原文写的是「一个不相干的 YYYYMM 列（**比如首次付款日**）会把质量摊在几十个桶上」。
**点了名，当成了背景说明，没有写成一个检验。**

### 为什么它不属于已有的任何一条

- **不是 20「变量是计数而处置要身份」**：这里变量确实带身份（逐列印了名字）。
  **问题在检验的覆盖，不在变量与处置的接口。**
- **不是 17「合取的支不成分割」**：三支是一个分割，穷尽，不重叠。
- **不是 11「判据画在估计量上」**：全等是结构的，没有阈值。
- **不是 19「值域不合」**：每个取值都读得出来。
- 它是**假设空间没覆盖**：**注册只把一个假设写成了检验，而备择假设是已知的。**

### 三条处置，都要

**一、写完一条判别式，先问一句：这一条不成立的时候，还有什么别的可能，
而那些可能我是不是也该测。**

**只测一个假设的检验，能说的只有「这一个不成立」，说不了「什么都不成立」。**
**分支的名字若写成后者，那个名字就比检验强。**

**二、说明文字里点过名的备择假设，必须升格成检验。**

注册里的散文常常已经把备择假设想清楚了（「比如首次付款日」）。
**凡是在注册里被命名的候选，都要在同一份注册里有一行属于它自己的判据。**
**没有那一行，它就只是一句让人放心的话。**

**三、一对互补的身份，要并排测并排印，读法是「哪一个成立」而不是「A 成不成立」。**

并排之后判据变成一个比较（`A 的荷载` 对 `B 的荷载`），**而比较不需要刻度**，
这与「不许在估计量上画线」正好一致。
**并排还白送一样东西：两列各自落在互补的一边，本身就是一次交叉核对。**

### 一条更一般的

> **一个检验只能否证它自己写下来的那个命题。**
> **把「这个命题不成立」读成「这一类东西不存在」，中间少了一步，
> 而那一步是「我把这一类的其他形状也测了」。**


---

## 失效模式 22：死链——检查的谓词是「有没有这个词」，而缺陷是「这条路径解不解析得开」
## Failure mode 22: a dead link — the check's predicate is "does this word appear", while the defect is "does this path resolve"

**实例一，便宜的那个（2026-08-22，`experiments/ftt_avail.py`）。**
文件头写着 `载体选型 §9 draws the line this sits on`。
`载体选型` 是一份不发表的内部件，**这一行对任何读者都打不开**。
提交前的自查是一张禁用词表，**一条都没命中**，
因为它查的是词，而这个目标名一个表上的词都不含。

**实例二，贵的那个（同日数出来）。**
`docs/b8_inputs_availability.md` 与 `docs/b10_freddie_availability.md`
**2026-08-18 挪出仓库**。指向这两份的指针，**在 `origin/main` 上有 28 个文件、35 处**：

| 目标 | 文件 | 处 |
|---|---|---|
| `b8_inputs_availability.md` | 14 | 16 |
| `b10_freddie_availability.md` | 13 | 18 |
| `B14_设计_v1.md`（中文档名） | 1 | 1 |

**这 35 处在已发布的树上活了四天**，而那四天里提交前的自查**每一次都跑了，每一次都通过**。

### 病灶：谓词的类型不对

**禁用词是字符串自己的属性**，`in` 就判得出来。
**死链是字符串与文件系统之间的关系**，`in` 判不出来，**只有把路径拿去解析才判得出来**。
**一条检查只能发现它的谓词能表达的东西**，所以查多少遍都一样。

**而制造这个缺陷的那个操作，构造上不会经过缺陷落地的地方。**
挪走一份文件，动的是那一份；指向它的 N 处在另外 N 个文件里，
**挪动这个动作一处都不碰。** 于是它必然留下 N 个死链，且必然不报。

### 第二层：改了写盘器不等于改了产物

上面那 27 处里，绝大多数在 `results/` 的产物里。
**写盘器 2026-08-19 就改对了**（改成「the B8 inputs register」这样的自述句），
**产物一处没动**，因为**没有任何东西会自己重新生成一个产物**，
而部分重跑永远碰不到它没跑的那些。

**`scripts/run_b8_package.py` 里有一个 `--check-pointers`，跑一下就会把 27 处全部列出来。**
四天里没有人跑过它。**一个要人记得跑的检查，等于没有检查** ——
与「早停比记得看可靠」、与「只数过一次、没有变成检查的计数」是同一条。

### 中文档名让它更瞎一档

`B14_设计_v1.md`、`载体选型` 这一类的目标名，
**连「路径长得像路径」这个形状都要靠正则认出中文字符才看得见**。
纯 ASCII 的目标至少还会被「这个字符串里有 `docs/`」这种粗筛扫到。
**这是纪律 21 那一族的第四例**：工具在纯 ASCII 上正常，有中文时才失效，
**所以它总是在自查看起来最干净的那一刻失效。**

### 为什么它不属于已有的任何一条

- **不是 16「文本替换没匹配上是静默空操作」**：这里替换命中了它的目标。
  **漏的是替换的作用域**——写盘器改到了，产物不在作用域里。
- **不是 9「记录错」**：那一条里记录与代码不一致会让**数**变。
  **这里一个数都没变**，变的只是一句指路的话，**所有诊断量正常**
  （范畴错误第十二式那一族：**打印对象，不打印计数**）。
- **不是 19「值域不合」**：每个字符串都读得出来，读出来也都是合法的字符串。
- 它是**谓词类型错**：**用一个关于字符串的检查，去守一个关于引用关系的不变量。**

### 三条处置，都要

**一、挪一份文件的位置，当场解析指向它的每一条路径。**
**触发器是「挪动」这个动作本身，不是下一次自查。**
挪动是唯一一个知道「这份文件曾经在哪」的时刻，
**过了那一刻，就只剩下全盘扫描这一条路。**

**二、提交前的自查加一步：解析，不是查词。**
遍历会进仓库的候选文件，把每一个 `docs/….md`、`results/….json`、`experiments/….py`
形状的引用拿去盘上解析，解析不到的报出来。
**实测 576 个文件几秒钟**，且它**不需要知道禁用词表**，
所以将来挪走的任何一份文件都被它守着，不必逐份登记。
**正则要显式带上中文字符类**，否则中文档名的目标漏掉。

**落地为 `scripts/check_dead_links.py`，2026-08-22。第一次跑就还了本**：
本条上面那两批修完之后，它又报出 **64 处**指向不发表工作件的引用，
**全部在已发布的树上**。

> **【2026-08-27】那 64 处全部结清，剩下 5 处是这个检查自己记着的噪声**
> （两处跨行折断的引用尾巴、一处描述文件族的通配、两处运行时才写出的产物路径）。
> **结清的方式六十四处一模一样**：那句话本来就把教训写在原地，
> 于是把读者打不开的那个文件加节号去掉，教训留下。
> **一个读者打不开的引用从来没有承载内容，承载内容的是它周围那句话。**
**这一批不是本轮修的那一批**，与它们无关，是同一个谓词错在另一族目标上的同样结果 ——
**这正说明为什么这一条要落成一个跑得起来的检查，而不是一次扫描的结论。**

**三、写盘器和产物是两件东西，报「改好了」之前先说清改的是哪一件。**
**改产物不改写盘器，下一次重跑打回原形；改写盘器不改产物，产物一直是旧的。**
两件都改完，还要**拿产物去比对写盘器现在会拼出来的那个字符串**——
比对通过才说明重跑会复现这个文件，而不是改动它。
**2026-08-22 这 27 处就是这么结的**：逐份比对写盘器的字面量，全部相等，一个数没动。

### 一条更一般的

> **一条检查只能发现它的谓词能表达的东西。**
> 禁用词表的谓词是「这个字符串里有没有这个词」，
> 死链的谓词是「这个字符串在盘上解不解析得开」。
> **前者永远查不出后者，跑多少遍都一样，而且每一遍都会报「干净」。**

## 失效模式 23：两个游标同步走，于是可枚举的组合数是最小公倍数，不是乘积
## Failure mode 23: two cursors advanced together, so the reachable pair count is a least common multiple and not a product

**实例（2026-08-23，`src/monetary_topology/network.py`）。** 两处按边数加边的
循环，写法一样：

```python
for i in range(spec.financial_to_intermediate_edges):
    a[payers[i % payers.size], buyers[i % buyers.size]] = 1.0
```

**两个下标共用同一个 `i`**，于是走到的格子只是那张 `payers × buyers` 表上的一条
对角线，长度 `lcm(len(payers), len(buyers))`，而不是 `len(payers) * len(buyers)`。

| 参数 | 两侧大小 | 表上的格子 | 实际能到 |
|---|---|---|---|
| `financial_to_intermediate_edges`，中间块 20 | 20 × 20 | 400 | **20** |
| `financial_to_intermediate_edges`，中间块 30 | 20 × 30 | 600 | **60** |
| `downward_edges`，家户 180 | 20 × 180 | 3,600 | **180** |

**读数上的样子**：中间块 20 时，把参数从 20 调到 40，`M/R`、支撑集、工资支付率
全部**逐位相同**。那不是机制饱和，是一条边都没加进去。

**这一次没有咬到任何读数。** A2 与 A2c 用的是中间块 30，封顶 60，两站都只扫到 30，
逐个验过 0 到 60 每一个值实际加进去的边数都等于设定值。A8 用同一个中间块，同一张网格。
**报在这里是因为它下一次会咬**：谁把中间块设成 20，或者把参数扫过封顶，
拿到的就是一段假平台。

### 病灶：一个游标被两个坐标共用

**`i % n` 与 `i % m` 不是两个自由的下标，它们是同一个数的两个像。**
`i` 从 0 走到 `k`，走过的点集是那条对角线上的 `min(k, lcm(n, m))` 个格子。
要遍历整张表，第二个坐标必须**独立于**第一个前进（`i // n` 而不是 `i % m`），
或者两个坐标各拿一个游标。

**它安静的原因是参数名。** 这两个参数叫「边数」，而它们确实在小值上加进去了
那么多条边，**前 `lcm` 条完全正确**。缺陷只在越过封顶之后才显形，
而没有任何东西会在越过时出声。

### 为什么它不属于已有的任何一条

- **不是 12「对齐错」**：那一条里标识符与被索引对象的顺序不一致，**身份错了**。
  这里每一条边的两端都是对的，**少的是本来该存在的另外那些边**。
- **不是 19「值域不合」**：参数的每一个值都合法，`__post_init__` 只要求非负，
  而封顶之上的值确实是非负的。
- **不是 11「在已定死的臂上花钱」**：那一条是跑之前就能从构造推出结果。
  这一条**跑之前推不出来**，要么读代码看见共用的 `i`，要么跑两个值比对。
- 它是**参数的名义定义域宽于它的有效定义域**，而两者之间没有任何检查。

### 三条处置，都要

**一、凡是用一个计数器给两个坐标取模的地方，写出它的有效上限。**
上限是 `lcm`，不是乘积。**写进那个参数的注释里**，因为读参数的人看的是注释，
不是循环体。

**二、扫一个「数量」参数之前，先量它实际加进去了多少。**
一行代码：把生成的对象数一遍，对着设定值比。**这是「打印对象，不打印计数」在
参数侧的同一条** —— 这里要印的对象就是「实际生成的边数」，而所有下游读数都正常。

**三、发现封顶之后，先查已跑的站有没有扫过它。**
查法是拿每个站的扫描范围对着它自己构型下的 `lcm` 比。
**2026-08-23 这一次查完是干净的**，两个用它的站都在封顶之下。
**先查再改**：如果读数没被污染，那这是一条坑账，不是一次返工。

### 一条更一般的

> **一个参数的名义定义域是它的类型允许的值，有效定义域是构造能区分的值。**
> 两者不等的时候，超出的那一段不报错、不警告、不改变任何输出，
> **它只是让曲线平掉，而平掉看起来像饱和。**

---

## 失败模式 24：平序列的 argmin 等于视界，而它看起来像一个转折点

**买来的**：2026-08-23，A10 的事件时刻。

在十七条臂上读每个序列的 argmax／argmin，八条补给臂的支撑集谷与总量峰**全部落在
第 299 轮**，八比八，而不补给的八条落在内部（104 到 286）。
**看起来是补给让经济不触底，不补给让它触底后转向。干净得可疑。**

**它不是。** 把轮数拉到 600、1200、2400，那两个时刻除以视界**恒等于 `1.000`**。
序列几乎是平的（2400 轮里支撑集从 13.99 走到 13.73），
**平序列的 argmin 就是最后一格，跟机制无关**。

**抓住它的是把控制臂放进同一张表。** 完全没有写销的控制臂读出一模一样的
`1.000 / 1.000 / 0.997 / 1.000`。**那一格立刻说明这不是机制。**

### 三条处置

**一、报任何 argmax／argmin 之前，在两个视界上各跑一遍。** 位置随视界成比例移动
就是没有内点，不是「还没到」。

**二、把不该有该效应的那条臂放进同一张表。** 这一条比看序列本身便宜，
而且它抓的是「这个统计量在这个载体上有没有指称」，不是「这次跑对不对」。

**三、`N 比 N` 的干净分割，第一反应是查构造不是报规律。**
第 11 条禁 `N 次全票通过`的**判据**形状；这一次同一个陷阱出现在**读数**里，
而读数不受那条约束，所以只能靠这一条。

### 一条更一般的

> **一个模型如果没有外生的时间刻度，它的轮次上的先后在世界上没有指称。**
> A2／A10 那条线的轮次是流算子的迭代，没有日历、没有带日期的冲击，
> 所以那里读不出事件顺序**不是失败，是那个量没有接到载体上**。
> 同一件事 A8 §8 在它自己的载体上也读到过。**两个载体两次。**

---

## 失败模式 25：网格上的中位数会藏掉稀疏事件，而每个诊断量都正常

**买来的**：2026-08-23，A12 的写销臂。

A12 的摘要表按臂印中位数。`writeoff` 臂的中位累计销毁是 `0.0`，
与什么机制都不开的 `off` 臂在每一列上读数相同，
**于是这被报成了「写销在这个载体上从来没触发过，A12 的写销臂是空转」。**

**逐格数一遍：45 格里 10 格触发**，销毁 1175 到 5532，`M/R` 从 66.02 砍到 10.76。
**中位数落在没触发的那 35 格里。**

而且那 10 格的四面同现状态**一格没变**（False→False、True→True），
**所以 A12-4 那句「写销不破坏覆盖」是真的，只是它的依据不是「没发生」。**

### 处置

**一、按组汇总一个稀疏事件的时候，报触发格数，不报中位数。**
A12 的打印表与 A12-7 都是为这条加的。**一条从来不触发的臂靠不触发通过每一条判据。**

**二、这是「打印对象，不打印计数」的对偶**：那一条说不要用计数代替对象；
**这一条说不要用中位数代替计数**。两条都指向同一件事 ——
**汇总统计量在稀疏或异质的格子上没有信息。**

**三、与失败模式 1 同族**（逐类每个 cell 的观测数，印最小的那三个）：
**平均量在不完整设计上没有信息。** 这次是中位数，对象是「事件发生了几次」。

## 失败模式 26：把一个计数按规模缩放，而注册的量是一个份额

**买来的**：2026-08-23 到 08-24，A2 的自主边网格搬去别的载体尺寸。

`financial_to_intermediate_edges` 是**边数**。A0b 注册的预言是**份额**：
中间块开局流入里，来自上层的那一份。**两者不是一回事，而它们长得像一回事**，
因为在一个固定的载体上，份额是边数的单调函数，于是网格点的顺序、疏密、
两端的位置全部对得上，**唯独换了载体之后对不上**。

**换载体时手边有两个显然的比，两个都是错的。** 节点数从 200 到 1000 是 5 倍，
两个块之间可能的边数是 25 倍。**实测解出来的倍率从底端的 2.0 走到顶端的 4.3**，
既不是 5 也不是 25，**也不是任何一个常数**：注册网格
`(0, 1, 2, 3, 5, 8, 12, 20, 30)` 在 1000 节点上是 `(0, 2, 5, 8, 15, 28, 45, 72, 128)`。
200 到 400 那一段是 1.0 到 1.8。

**为什么它不会自己暴露**：按任何一个比缩放出来的网格，**跑出来仍然是一条平滑
的、单调的、两端行为正确的曲线**。所有形状统计量正常，所有守恒判据通过，
所有的面照常出现和消失。**变的只有曲线画在哪一段份额上**，而那正是被注册的东西。

### 处置

**一、载体一换，先问「注册的是哪个量」，再问「这个量对新载体怎么算」。**
注册的是份额就解份额：每个网格点单独二分一次，落在它原来的份额上。
单调加整数正好是二分的形状，成本是每点十几次图构造。
**先粗扫再线性细扫那种写法在 1000 节点上是近千次图构造，跑不完。**

**二、解出来的值要读回去核，不要假定目标达到了。** 一个载体能达到的份额有上界
（两块之间的边数有限）。注册网格顶端那个 0.3111 在 200 节点上到得了，
在 1000 节点上 130 条边也到不了。**返回的是上界而不是解的时候，函数不会报错。**

**三、这是失败模式 9（固定绝对门槛 × 异质分布）的构造侧对偶。**
那一条说门槛是绝对量而分布是异质的；**这一条说参数是计数而主张是份额**。
两条的判别式相同：**这个数字在两个载体上指的是同一件事吗。**

## 失败模式 27：一个符号判据在曲线穿零的地方就是一个零宽度严格不等式

**买来的**：2026-08-24，A12 的覆盖判据在 200 与 1000 两个载体上给出相反的裁定。

A12 的四个面全部写成**符号**，设计件里那句话是
**「方向，零阈值，没有可调的数」**，理由是清单第 11 条禁止在估计量上画线。
面三是三个合取：`M 升`、`gini 末 > gini 开`、`资源取值数为一`。
第一个与第三个在两个载体上恒真，**判定完全落在第二个上**。

**两个载体给出相反的答案**：`floor` 臂在 200 节点上四面同现的网格位是**空**，
在 1000 节点上是 **[1]**，于是承重判据 A12-4 从 FAIL 翻成 PASS。

**把 `gini 末 − gini 开` 沿网格印出来，答案就在那里：**

```
floor  200 : +0.0508  -0.0945  -0.1857  -0.2672  -0.3057 ...
floor  1000: +0.0493  -0.0015  -0.1388  -0.2158  -0.2956 ...
                       ^^^^^^^
```

**两个载体上是同一条曲线**，只是零点从位 0 与位 1 之间挪到了位 1 与位 2 之间。
位 1 在 1000 节点上读 `−0.0015`，逐个 elasticity 是
`+0.0061 / +0.0036 / −0.0058 / −0.0050 / −0.0066`。
**两格在零上面，三格在零下面，而整条曲线的量级是 0.3。**

**判定翻转靠的是一格里的两个格点落在一条穿零曲线的正侧。曲线本身没有动。**

### 处置

**一、「没有阈值」不等于「没有那条线」。线画在零上。**
一个符号判据在被测量远离零的地方是稳的，**在它穿零的地方精确地退化成
清单第 11 条禁止的零宽度严格不等式**。清单第 11 条列的那些坏形状里，
零宽度严格不等式是靠「不要写 `!= 0.0`」来防的，
**而符号判据把同一条线藏在了「方向」这个词后面。**

**二、判别式，跑前可用**：**这个符号量在网格上穿零吗。**
穿零就在穿零那一格附近**印曲线，不印符号**，让读的人看见零点在哪。
不穿零就随便用，符号是这时候唯一该用的形状。

**三、这一次没造成损失，因为两个载体都跑了。** 只跑一个载体的时候，
拿到的是一个 PASS 或者一个 FAIL，**而两者都会被当成关于机制的读数**。
**第二个载体在这里干的事就是失败模式 25 里「打印对象」干的事**：
它把一个二值裁决还原成一条曲线。

**四、与失败模式 9 同族**（固定绝对门槛 × 异质分布）：
那一条说门槛是绝对量而分布是异质的；**本条说门槛是零而被测量正好经过零**。
两条的解药相同：**看被测量离那条线有多远，远就用，近就印曲线。**

## 失败模式 28：一条判据在上一条读数之后登记，于是继承了它的形状，而另一支不可达

**买来的**：2026-08-23 登记，2026-08-24 发现。A12-5。

A12-4 读到「生存线那条臂四面同现的边集是空的」。由此登记的 A12-5 问：
**转移能不能把它补回来**，判据写成 `hits["floor+transfer"] 非空`。

**而四个面里的面三要求末 gini 高于开局 gini，转移是对金融层收税、按人头发给生产层，
压低集中度是它的定义性动作。** 事后数：两个载体、两对臂、90 个配对格，
`gini 末 − gini 开` 的范围是 **−0.20 到 −0.86，一格都没有落在正侧**。
**那条判据的 PASS 支从来不存在。**

**它是怎么溜进来的**：它没有自己选形状，**它继承了 A12-4 的形状**（「这条臂的边集非空吗」）。
上一条读数把问题问成了那个样子，下一条就照着那个样子问了。
**而那个形状对 A12-4 自己的臂是可达的**（生存线不必然压 gini，它冻结节点，
末 gini 走哪个方向要看被冻的是谁），**对转移臂不是**。

### 处置

**一、事后可机械检出，一行代码：对每个候选判定量，数它在配对格上的方向（降／平／升）。
单向的那个是被构造锁死的。**
A12-5 重写之后带了这个自检：`gini_close` 在两个载体上都读 `45/0/0`，
于是它被排除在判定之外、只印不判；`support_ratio` 在 1000 节点上读 `45/0/0`，
于是在那个载体上被剔除并报出来。**剩下没有可判定量的时候，判据读第三态，不读 FAIL。**

**二、跑前的问法**：**这条判据要判的那个量，和这条臂要开的那个开关，是同一件事吗。**
是就换量。**拿集中度去判一个再分配装置，等于问一个装置是不是它自己。**

**三、承接上一条读数去登记新判据的时候，形状要重新选，不要继承。**
上一条的形状是为上一条那条臂选的。

**四、与失败模式 27 是一对。** 27 说线画在零上而被测量正好经过零；
**本条说线画对了而被测量根本到不了线的另一侧。**
两条的解药相同：**先看被测量在这个设计上能走到哪里，再决定判据。**

**五、汇总量在这里又骗了一次**（失败模式 25 第三例）：
退出节点数的中位在两条臂上都是 `165`，看起来转移一个人都没动，
**而逐格是降 11、平 12、升 22。**

## 失败模式 29：用成员资格实现一个行为，于是那个行为拿到了它不该有的性质

**买来的**：2026-08-24，生存线。

要建模的是「掉到生存线以下的人」。实现是**把节点从图上摘掉**：
`_alive = False`，不再作为交易对手。而支出是 `propensity × holdings × alive`，
所以摘掉的同时支出归零。工资那一侧默认不切，**于是它继续领工资**。

**合起来是：一直领薪水，一分不花，永不回来。**

**这三条一起，现实里没有对应的人。** 饿到生存线以下的人没有存款；失业的人依旧消费只是少消费。
而这个节点保留全部存量、消费归零、且不可逆。

### 它造成了什么

**逐格量**：165 个节点在第 5 轮之前全部摘掉，此后它们手里的 claim
**每轮线性 `+4.0`，一直到第 300 轮**，末值 `1202.4`，
**占末轮全部 claim 的 85.6%**。人均从 `0.057` 涨到 `7.287`，**128 倍，全部发生在摘掉之后**。

末分布：前 20 名 `23.8%`，**21–100 名 `75.5%`**。
**于是整个站读出「货币扩张利好中层」，而那个「中层」就是这 165 个只进不出的账户。**

**还是一个泵**：内生发行盯的是**活跃**流入，摘掉的人不算活跃，于是它印钱；
钱顺工资边流给那 165 个人；他们不花；活跃流入更低；印更多。**M 涨 14.1 倍，
其中 85.6% 停在死端。**

### 判别式

**一个行为写进成员资格，就会连带拿到成员资格的性质。**
成员资格是二值的、通常是吸收的、而且一刀切到 100%。
**行为不是**：支出倾向是一个率，可以是 0.3 也可以是 0.9，随时可回。

**动手前问**：这一步要改的是「它还在不在这个市场里」，还是「它花多少」。
**是后者就不要碰成员资格。**

### 处置

**支出改成一条消费规则，成员资格不动**：低于线的节点留在图里，
支出取 `min(need, holdings)`，不看流入。于是它继续消费、消费得少、吃老本。
**吸收壁不需要**：存量归零的节点自然花不出去，入边回来自然不在线下。

**改完之后**：那批人的末存量从 `1202.4` 掉到 `0.2`（占 `0.1%`），
`M` 增从 `14.1` 倍掉到 `1.7` 倍，`Δgini` 从 `−0.3086` 翻到 `+0.0344`，
**与什么机制都不开的对照臂 `+0.0328` 几乎重合**。

### 同族

**与失败模式 9（固定绝对门槛 × 异质分布）反向同族**：那一条说门槛是绝对量而分布是异质的；
**本条说被改的量的类型选错了** —— 要改一个率，却动了一个布尔。

**与范畴错误第五式（记账区位）是同一件事在代码侧的样子**：
测量量落在账户体系的错误表区，这里是**操作落在对象的错误属性上**。

## 失败模式 30：两条注册判据互为补集，只有一条能成立，而没有人乘出来

**买来的**：2026-08-24，A5。**同一站上出现了两次，形状完全一样。**

| 作废的 | 它的补集 | 同一份证据 |
|---|---|---|
| **A5-3** 良性侧的份额应当上升 | **A5-4** 良性侧不是均衡 | A5-4 读到 12/12 seed 穿过门槛、0.0% 的后续轮回到线下。**良性的终态不存在，份额就没有东西可以升上去** |
| **A5-6** 冻价之后漂移应当消失 | **A5-7** 分母自己就穿过门槛 | **两条读的是同一次冻价跑。** A5-6 报 `654.51%` 对 `1%` 的门槛，A5-7 报 12/12 穿过。**那是同一个数，主张反号** |

**两对都是注册的时候写下去的，两对都跑完才发现。**

### 判别式，跑前零成本

**把注册表上每一条判据的主张写成一句话，两两问：这两句能同时为真吗。**

`n` 条判据是 `n(n−1)/2` 次比对，A5 有八条，也就是二十八次，**每次是读两句话**。
**这一步不需要数据、不需要跑、不需要任何估计。**

**尤其要查的两种配对**：

1. **一条说某个东西是均衡，另一条说在那个均衡上某个量该往某个方向动。**
   不是均衡就没有终态可以动。
2. **两条读同一个开关的同一个设定**，一条要它有效果、一条要它没效果。
   A5-6 与 A5-7 就是这一对：`eta = 0` 那条臂，一条要漂移消失，一条要漂移还在。

### 处置

**判 VOID，不判 FAIL，数字全留，裁决归它的补集。**
`FAIL` 说的是看过了不成立；这里的情况是**这条判据从注册那天起就没有可成立的世界**。

### 与失败模式 28 的关系

**28 是继承了上一条判据的形状，于是继承了一个不可达的分支；本条是同时注册的两条互斥。**
**两条的解药是同一个动作**：把每条判据的可达分支写出来，
**28 是对着数据写，本条是对着别的判据写。**

## 失败模式 31：在不平衡的图上均匀抽边，抽出来的不是均匀的边

**买来的**：2026-08-16 量到，2026-08-24 处置。A7。

A7 的 shortcut 按一个概率对**每一个有序对**独立抽。听起来是中性的。
**在 20/180 的图上它不是。** 纯组合，零数据：

| 落点 | 占有序对 | `s = 0.01` 上实测加了几条 |
|---|---|---|
| 生产层内部 | **80.95%** | **282** |
| 向上（生产→金融）| 9.05% | 45 |
| **向下（金融→生产）** | 9.05% | **21** |
| 金融层内部 | **0.95%** | **2** |

**问题在第三行。** `NetworkSpec.downward_edges` 默认是 0，
**它自己的 docstring 写着「Zero is the framework's own specification」**。
而 `s = 0.01` 那一格加了 21 条向下的边。
**A0-6 量过一条向下的边值多少**：生产层入流 `17.7007 → 48.3919`，**2.73 倍**。

**所以每个 `s > 0` 的臂同时动了两样东西**，而这一站把结果读成了密度的效果。

### 判别式

**一个「均匀」的随机化，均匀在什么单位上。**
按有序对均匀，就不是按边的种类均匀；按节点均匀，就不是按度均匀。
**块的大小不等的时候，这两个永远不是同一件事。**

**跑前可算，一次乘法**：把每一类落点的有序对数除以总数，
对着这一类落点在框架里是不是被设成零。**有被设成零的，这个随机化就在推翻它。**

### 处置

**加一个作用域参数，把数量配平、只动落点。**
`NetworkSpec.shortcut_scope`，五个取值（`all` 默认即注册行为，加生产内／金融内／向下／向上）。
**数量从同一次抽样里取**，所以四条臂与注册臂逐条配平，**只有落点不同**。

**实测配平结果**（`seed=0`，`s=0.01`，注册臂加 350 条）：
生产内 350、向下 350、向上 350，**金融内 260**。
**金融内那一格饱和了**：20 个节点只有 380 个有序对，装不下 350 条以上的匹配数量。
**不 raise，装多少算多少，短了多少靠数它实际加了几条边看出来**，
因为那个短缺本身就是一条读数。

**与失败模式 9 同族**（固定绝对门槛 × 异质分布）：
那一条说门槛是绝对量而分布是异质的；**本条说随机化是均匀的而块的大小是异质的**。
两条的判别式相同：**这个数在两个块上指的是同一件事吗。**

## 失败模式 32：拿内存里的对象去比一份写盘时四舍五入过的记录

**买来的**：2026-08-24，A7 的第 19 条核对。**代价两分钟，差点报出一次假的不一致。**

核对「默认路径逐位复现」的时候，跑了一行 `row()`，与 `results/a7_continuous_c.json`
里同一行比，**八个字段不同**，其中包括 `graph`。看上去像改动破坏了默认路径。

**印出来一看**：

```
记录 centrality_sd  0.1529909868
现跑 centrality_sd  0.15299098675432232
```

**是同一个数。** 写盘器有一个 `_clean`，按派生文件纪律第 5 条把每个浮点走一次
显式格式串再写。**记录是圆过的，内存里的不是。**
套上同一个 `_clean` 再比，**八个字段一个都不差。**

### 判别式

**比对之前先问：这两个对象经过的变换一样吗。**
一边来自 `json.loads`，另一边来自函数返回值，**中间隔着写盘器**。
**写盘器做过的事，比对之前要补做一遍。**

### 为什么它危险

**它的失败方向是「报出问题」而不是「漏掉问题」**，所以不会被沉默地放过，
**但它会让人去改一份本来是对的代码**。当时排的下一步就是去查
`shortcut_scope` 哪里破坏了默认路径，**而那里没有东西可查**。

**隔离它只要一步**：拿改动前那份代码跑同一次比对。
**旧代码给出完全相同的八个不同字段**，于是问题不在改动里，只可能在比对里。
**先隔离，再排查。**

## 失败模式 33：拿旧载体的极值点当新载体的角落探针

**买来的**：2026-08-24，A2d 的资产臂。**代价是一个错了两倍的数，而那个数当时已经被写进一份省钱方案里提了出去。**

问题是「五个站的集中度读数都做在没有资产层的载体上，要不要各加一条资产臂」。
提出的省钱办法是**角落探针**：不跑整张网格，只跑几个极值角，
把差别量出来，然后挂一行带数字的作用域。

**在 A2d 上试了**：取那份记录里 σ 的最大最小格与结构的最大最小格，四个角，
在两个载体上各跑一次。读出 σ 张成 `0.006645 → 0.015829`，倍率 `23.5 → 9.7`。

**整张网格跑出来是 `0.006645 → 0.031873`，倍率 `23.5 → 4.83`。**
**低估了一倍。**

### 为什么

**那四个角是在旧载体上找到的极值点。** 换了载体之后，极值点自己动了：
资产层给截留率一个可以停进去的东西，于是 σ 网格上**别的格**变成了新的极值。
**在旧极值上取样，量到的是旧极值之间的差，不是新载体上的张成。**

### 判别式

**探针要在被探的那个载体上找极值，不能继承。**
一个只跑几个角的方案，**只在极值位置本身不随处理变化时才成立**。
**处理如果会重排格子之间的顺序，角落探针就不是探针，是四个任意点。**

**跑前可问，零成本**：这个处理有没有可能改变哪一格是最大的。有可能就跑全网格。

### 与失败模式 1 同族

失败模式 1 说**平均量在不完整设计上没有信息，要看最坏那一格**。
**本条说最坏那一格自己会动**，所以「先找出最坏那一格再只跑它」这个省钱法，
在处理会重排顺序的时候不成立。

**这一次没有造成损失，因为那个省钱方案被否掉了，跑的是全网格。**

## 失败模式 34：自查扫的是那个词的中文，而仓库里活着的是它的英文译法

**买来的**：2026-08-24，一次例行的提交前自查。

提交前的那组自查里有两行是词表：一个不发表的内部用词，扫中文写法零命中；
一个内部目录名，照它的写法扫，零命中。**两行都过了很多轮。**

**这一次把同一个词的英文译法一起扫进去，命中八处**，
分布在四个站点脚本里：一处是章节标题，
一处是被自查第 8 条按子串断言的键，其余是正文里的 `the first sheet's ...`。
**另有两处指针直接写着那个不发表的目录名，本来就该被第二行抓到，
而它们活着是因为自查扫的范围只到已跟踪文件，这两个脚本当时还没 `git add`。**

### 判别式

**一个词如果有对外与对内两个名字，自查要扫的是对外那一侧会出现的形态。**
内部叫甲、对外叫乙的映射，作用就是让甲不出现在对外的地方；
**而扫甲只能证明甲没出现，证明不了甲的译法没出现。**

**问法，零成本**：这个内部词写成英文会是什么样，那个字符串在仓库里有几处。

### 与失败模式 21 同族

那一条说**工具在纯 ASCII 上正常，在有中文要报的时候才失效**，
所以它总是在自查看起来最干净的那一刻失效。
**本条是它的镜像**：自查只认中文，于是英文那一侧从来没被看过，
**而对外可见的恰好是英文那一侧。**

### 处置

四个脚本的正文改成「预注册」的对应英文，`b17c` 的章节标题与自查第 8 条的键
**同一次改**，改完把那一条的断言原样重放一遍确认仍然成立
（它是子串测试，两侧同改，读数不动）。
**扫描范围同时从已跟踪文件改成「工作树减去 gitignore 减去 `.expired`」**，
未跟踪不等于不进仓库，它只等于还没 `git add`。

## 失败模式 35：冒烟跑和正式跑写同一个路径，于是验代码就是毁记录

**买来的**：2026-08-24。为了验一条新臂的代码，用 `--rounds 30 --seeds 2` 跑了一次 A13，
**那个脚本无条件往 `results/a13_mobility.json` 写盘**，
于是 300 轮 5 种子那份注册记录被一份 30 轮 2 种子的冒烟结果盖掉。
**盘上没有备份，git 里也没有**（那份记录当时还是 untracked，`git add` 还没做）。

### 为什么它绕过了所有防线

**「不删东西」那条纪律管的是删，而这是写。** 覆盖不经过任何删除调用，
`rm`、`unlink`、`rmtree` 一个都没出现，**所以按删除写的检查一条都不会响**。

**参数改的是网格，不是路径。** `--rounds` 与 `--seeds` 存在的意义就是让人跑小一点，
**而它们不改写盘的位置**，于是「跑小一点看看代码对不对」这个最常见的动作，
默认后果就是把大的那份换成小的那份。

**`--asset` 改路径，`--rounds` 不改。** 同一个脚本里已经有一个开关会换文件名，
**这让写盘位置看起来是跟着参数走的，而其实只跟着那一个开关走。**

### 判别式

**一个脚本如果既是正式跑的入口又是冒烟跑的入口，问：这两种跑写不写同一个路径。**
写同一个路径就必须有一个不写盘的开关，**而且默认跑要写、冒烟跑要显式说不写**，
不能反过来 —— 反过来会让正式跑忘了加开关而什么都不落。

### 处置

`experiments/a13_mobility.py` 加 `--no-write`：印表、印判据、返回退出码，不落盘。
**这一族的每个站点脚本都该有它**，尤其是记录还没进版本控制的那些。

**恢复靠重跑**：种子固定，同一份代码同一组参数逐位复现（轮内确定性本仓实测过，
A1d 在两台机器上九条判据 detail 逐字相同）。**代价是一次跑，不是不可恢复。**

### 第二例，2026-08-25：写这条的人当天又犯了一次

A15 的脚本加写盘那一步，`--smoke` 与正式跑指向同一个 `RECORD`。
跑一次冒烟，**四行的记录就坐在注册路径上，看起来像一次读数**。
**这一条已经写在这里了，而写它的人在同一个 session 里照样撞上去。**

**所以判别式要往前挪一格**：不是「跑之前想想会不会覆盖」，
是**加写盘这行代码的时候，同时决定减量跑写哪儿**。
写盘的路径与跑的规模是同一个决定的两半，分开做就必错一次。

### 仓库自己早有答案，而新写的人不知道

修的时候第一版是给冒烟件加 `.smoke.json` 后缀并写进 `.gitignore`。
**改完才发现 `.gitignore` 里早有 `results/subset/` 这一族**，
而它旁边那段注释给的理由比后缀强：

> 目录就是分隔，一个冒烟跑永远不会被读成某个站的记录；
> **而且减量跑要提交** —— 一个跟全量对不上的冒烟跑属于历史，不属于被丢掉。

后缀方案漏掉的正是最后那半句：**加进 `.gitignore` 等于把不一致的证据扔了。**

**判别式**：**要给一类产物新开一条命名或忽略规则之前，先 grep `.gitignore`
和 `results/` 看这一类有没有既有落点。** 新开一条的成本不是那一行，
是从此有两套约定，而下一个人只会看见其中一套。

### 与失败模式 5 的关系

那一条说下载来的数据视同不可再生。**本条说算出来的记录不是不可再生，但它也不是免费的**，
而真正要紧的差别是：**下载的数据有取数脚本的断点续传护着，算出来的记录什么都没有。**

## 失败模式 36：先决条件问「这个量存不存在」，而判据要的是「这个量估不估得出来」

**买来的**：2026-08-24，B18。

那一站的先决条件写得很清楚：**`A_s` 是不是恒等于零**。跑出来不恒零，
分位从 `p10 0.0004` 到 `p90 0.0528`，最大一份 `0.3893`，**闸门记 PASS，写得没错**。

**而两轴要的都是符号**，`|A_s|` 的中位数只有 `0.0073`。
真正该问的下一句是：**每份合约的这个符号估不估得出来。**
数出来是 **0 份 / 295 到得了两个标准误**，放宽到一个标准误也只有四份。

**病灶不在那个先决条件写错了，在于它答完之后没有人问下一句。**

### 判别式

**一个先决条件如果形状是「这个量不是常数」，它保证的只是变异存在，
不保证变异能被这份数据分辨。** 判据的单位是符号或方向的时候，
**跑前必须再问一次「一份观测的这个符号，se 是多少」**，而那通常是同一份缓存上的一遍扫描。

### 为什么 `se` 不能从观测数取

**缺失是成段发生的**：一个报价缺席三百秒给出三百个高度相关的快照。
**独立单位是段不是秒。** 拿 3,895,656 个快照当 `n` 是自由度虚高。
数出来的段数中位是 **2** —— 一份典型合约整天只发生过两次缺席，
**所以那个看起来很大的 `A_s` 是从个位数个独立事件里算出来的。**

**最干净的一行**：`|A_s|` 全场最大的那份是 `−0.3893`，
**由每侧一段构成**，`se` 是 `0.5306`。**最大的那个数是最不可信的那个。**

### 与失败模式 1 同族

那一条说平均量在不完整设计上没有信息，要看最坏那一格。
**本条说存在性检查在符号型判据上没有信息，要看每个单位的 `se`。**
两条的解药一样：**印对象，而且印的是对判据承重的那个对象。**

## 失败模式 37：一个绝对路径不被当成链接，所以没有东西去解析它

**买来的**：2026-08-24，实证臂两份**已提交**的模块。

`ri_lp_panel_dq.py` 与 `ri_lp_panel_evade.py` 的第 4 行都写着
一个带盘符的 Windows 绝对路径，指向一个名叫「预注册」的目录，作为「本模块执行的那份预注册在哪」的指针。

**盘上没有这个目录。** 真正的预注册在另一处，名字也不是这个。
**两份都跟踪着，活了很久，没有任何东西报过。**

### 为什么它躲过了所有检查

**死链检查认的是仓库内的相对路径。** 一个绝对的 Windows 路径不匹配那个形状，
**所以它根本没被当成一个链接**，没有东西去解析它，也就没有东西发现它解析不了。

**而机器相关那一条当时只写在派生文件纪律里，没有一行 grep 在跑它。**
加上盘符那一行之后，同一次扫描在三个地方命中，**其中两处就是这两份**。

### 判别式

**凡在仓库内的文件里写出一个路径，只有两种合法形状：**

1. **仓库内的相对路径** —— 死链检查管得着，它坏了会被报出来；
2. **不写路径，整句改写成自述句** —— 「判据写定于某日，跑后一条未改」这种。

**中间那一类一律不许出现**：绝对路径、外部路径、指向不发表位置的路径。
它同时踩三样 —— **机器相关、指向不发表的东西、而且没有任何东西验证它存不存在。**

### 与失败模式 34 同族

那一条说自查扫的是那个词的中文而仓库里活着的是它的英文。
**本条说检查认的是相对路径而仓库里活着的是绝对路径。**
**两条都是「检查的形状与被查对象的形状不重合」**，
也就是范畴错误第六式落在自查工具上。**解药一样：先问被查的东西长什么样，再写检查。**

## 失败模式 38：一条新检查不标定就写进规矩，头两版一版 93% 假阳性一版 99%

**买来的**：2026-08-25，给提交前自查加「盘符」那一行的时候。

要查的东西很清楚：仓库内的文件不许出现带盘符的绝对路径。写正则写了三版：

| 版本 | 529 个候选文件上的命中 | 真 | 病 |
|---|---|---|---|
| 字母 冒号 反斜杠 | 27 | 2 | 字符串里的换行转义全中，`"...:\n"` |
| 字母 冒号 分隔符 … 分隔符 | 216 | 3 | **URL 也是这个形状**，`https://host/path/` |
| **前面没有字母的单个字母 ＋ 冒号 ＋ 反斜杠** | **3** | **3** | 无 |

**第三版是标定出来的，不是想出来的。** 盘符的形状是**前面没有字母**的单个字母，
而 `https` 的 `s` 前面有 `p`，`"bill:\n"` 的冒号前面有 `l`。**那个否定环视就是全部区别。**

### 为什么这件事值一条

**假阳性多的检查会被豁免掉，而豁免表一长，这条检查就等于没有。**
本仓已经有两个实例：渲染器的 `diagnostic_only` 字段，
每个新站开工第一件事就是给自己办豁免；`run_all` 的记录棘轮，
豁免表装着 76 条承重记录里的 51 条，**67.1%**。
**一张装着三分之二人口的例外表不是例外表。**

**所以一条新检查的成本不在写它，在于它第一次跑出来的假阳性数。**
27 个假阳性会让下一个 session 直接把这行注释掉。

### 判别式

**一条检查写进清单之前，先在整个语料上跑一遍，数真阳性与假阳性。**
**零成本**：语料就在盘上，跑一遍是几秒钟。
**而它抓到的三处全部是真的**：一处带着用户名，两处是已提交的 `cd` 注释，
还有一处指向一个盘上根本不存在的目录（失败模式 37）。

---

## 失败模式 39：一套中文编号转写成英文之后，和另一套编号住进了同一个命名空间

B14 的设计件用「甲N」给一整套跑前条款编号（`§7·补2·甲1` 到 `甲20`）。
这些条款写进英文脚本的时候，**「甲」被转写成了 `A`**，于是脚本里出现
`Registered in the design file, section 7 supplement 2, A16` 这样的句子。

**而 `A1`–`A20` 同时是 A 轨的站名。** 改之前 `b14_recheck.py` 里写的是
`Design file A5 clause 1`，**而 A5 是一个活着的站，有自己的记录 `results/a5_reachability.json`**；
同一个文件里还有 `A2` `A3` `A4` `A6` `A8` `A9` `A10` `A11`，**每一个都同时是一个真站名**。

### 为什么没有任何东西报警

**因为两边都是对的。** 每一处 `A<N>` 在它自己的文件里都指向正确的对象，
读的人也不会读错，**错的只有跨文件的那一步**：谁去 grep 一个站名，
拿回来的是两套编号混在一起的结果。

2026-08-25 实测：全仓 `\bA([1-9]|1\d|20)\b` 命中 **3096 处**，
其中 **173 处**（25 个 `b14*` 文件）是甲N，**2923 处**是 A 轨站名。
**开新站的时候才撞上**：接下来那几个号各自命中十几到二十几处，全部在 b14 里，
于是「下一个站号是几」这个问题查不出答案。**具体是哪几个号不写在这里**：
写下来它们就会出现在对那些号的 grep 里，而那正是本条要挡的东西
（失败模式 34 同源：一条描述失败的记录不该复制它描述的那个字符串）。

### 补漏是怎么被找到的：第一遍扫描的目录清单漏了仓库根目录

第一遍扫的是 `experiments` `docs` `src` `results` `scripts` 五个目录，**而 `RESULTS.md` 与 `README.md`
住在根目录**。于是那一遍报「非 b14 文件一处未动」，读起来像扫完了，
**实际上它连这个仓库最要紧的两份文件都没打开。**

**判别式**：一次扫描报了「零命中」或「一处未动」的时候，
**先问它的文件清单是怎么来的，再信那个零。** 目录白名单尤其危险，
因为漏掉的目录不会报错，它只是不出现。

**与失败模式 38 同族**：那一条是检查本身没标定，本条是**检查的作用域**没标定。
两条合起来：**一条新检查要同时给出它的假阳性率和它的覆盖面，两个数都没有就不要信它的结论。**

### 判别式

**凡是把一套中文编号转写进英文的地方，先问「转写出来的那个前缀，另一套编号在不在用」。**
甲乙丙转成 A B C 尤其危险，因为 A B C 本身就是本项目两条轨的前缀。

### 与 `D` 前缀那次是同一笔账

本项目的纪律表一律加 `D` 前缀，理由就是 `纪律 15` 与另一套编号里的第 15 条撞过车。
**这一次是同一个形状的第二次现身，而且这一次跨了语言。**
解药也一样：**加前缀，不改编号。**

### 处置

2026-08-25 裁定：173 处一律改写为 `B14_A<N>`。
**记录件一并改**（8 个 `results/b14*.json` 与 1 个 `.md`，共 29 处），
理由是不改的话下一个 session 读记录会拿到一个已经不存在的编号。
**补漏一轮**：文件名不以 `b14` 开头、而引用甲N 的另有 14 处 ——
三个 `l2_*` 脚本共 12 处（它们复用甲11 的窗口与分段），
以及 `RESULTS.md` 的 `B14-20` 那一行 2 处。**那一行尤其要紧：
同一份 `RESULTS.md` 里 `A11` 同时指 A 轨的生存线站和甲11，这就是本条的病灶在旗舰件上的现身。**
**改完复核：A 轨站名 2909 处逐位不变。**
设计侧的中文「甲N」本来就不撞，原样保留，只加了一块编号映射说明。
改动前的文本就地留档，加 `.expired` 后缀。

**顺带记一条**：`甲7` 是空号，设计件里从来没有过。**编号有洞不是错**，
写下来是为了下一个 session 不去补它。

---

## 失败模式 40：脚本没有 argparse 守卫，喂一个它不认识的开关它就跑默认动作

失败模式 35 的第三个实例，形状换了一层。

2026-08-25 为了确认重命名没有弄坏自检，同一条命令喂了三个脚本 `--self-check`。
**`b14_ordertype_sens.py` 与 `b14_legb_gate1.py` 用 argparse，认得的是 `--selftest`，
于是拒跑并印出用法。`b14_verdicts.py` 没有那道守卫，`--self-check` 被忽略，
它跑了默认动作，重写了 `results/b14_stage_two.json`。**

### 这一次没赔钱，而它凭的不是设计

**重写出来的文件与备份逐字节相同**（备份做同样的重命名之后比对，`True`），
所以这次反而白得一次确定性核对。**但那是运气**：同一条命令，
换一个吃随机种子或吃时钟的脚本，赔的就是一份记录。

### 判别式

**一个脚本能不能被一个打错的开关跑起来，跟它自检写得多好没有关系。**
问的是：**没有参数的时候它干什么。** 默认动作是写盘就是这一条。

### 与失败模式 35 的关系

35 说的是**冒烟跑与正式跑写同一个路径**，解药是 `--no-write`。
**本条说的是连「跑」这个决定都不是有意的。** 两条叠起来的处置是同一个：
**写盘要显式开关，不写盘是默认。**

### 处置

暂不改 `b14_verdicts.py`（B14 已收口，改它要重跑）。
**登记在这里，下一次动 B14 的时候顺手加 argparse 守卫。**
本轮的操作纪律：**要试自检就单个脚本单条命令跑，不要 for 循环喂同一个开关给一批脚本。**

---

## 失败模式 41：可达性核对做在判据的分支上，而目标是一个合取，合取本身不可达

**买来的**：2026-08-25，A15-4。

那一站的主问题是「有没有某个机制子集，让三个不平等口径朝三个方向走」，
目标形状取自 1929：**顶端百分位跌、顶端十分位涨、基尼涨**。
两个载体上跨 1,260 个臂-格，答案是**零**。

**而那个零跑之前就定了。** 把目标拆成三个两两条件：

| 条件 | `n=200` | `n=1000` |
|---|---|---|
| `top10` 涨 且 `gini` 涨 | 344 | 349 |
| **`top1` 跌 且 `gini` 涨** | **0** | **0** |
| **`top1` 跌 且 `top10` 涨** | **0** | **0** |

`top1` 跌的那 266 / 259 格里，**另外两个也全在跌，一格例外都没有**。
27 种符号三元组只出现 4 种。**目标是三个条件的合取，而其中两个各自就是零。**

### 为什么 `D15` 没拦住

**那张可达性表核的是判据的分支，不是目标的分量。**
写的是「不含离场的组合产出 → 未知，主问题；质量在坏账与重连上」——
**那是一句关于哪个机制可能做到的话，不是一句关于那个符号组合到不到得了的话。**
机制的故事永远讲得通，而合取可以同时不可达。

### 判别式

**判据的目标如果是一个合取，可达性要逐个分量核，不能核合取本身。**
一个合取的每个分量看起来都平常，而它们的交集可以是空的，
**并且这件事在写下判据的那一刻就是可算的**。

**这一次算它的成本是零**：A12 的两份记录早就在盘上，四个字段齐全，
**一次 `groupby` 就出来了，而它是跑完之后才算的。**

### 同一站当天的第二例，而这一次探针先跑了

A15-7 的载体在设计件里写的是完全图，理由是「级联全有全无的地方，
一个水平量有最远的路可跌」。**那个理由是关于机制的，不是关于可达性的**，
与本条上面那个漏检同一个形状。

**这一次先花了三次跑做探针**：完全图 `need = 0.20` 时 `starved` 末 **0**，
`need = 1.00` 时 **200**，两档下 `reversible` 开与关返回的账单序列**逐位相同**。
**要么没人掉线，要么全掉，全掉之后没有入流可恢复。** 载体当场换掉。

**三次对八十次。** 判别式因此可以写成一句操作：
**判据落到一个新载体上之前，先在那个载体上跑最少的几次，
看被判的那个量在两个结局分支上各取什么值。** 两个分支取同一个值，就换载体。

### 与失败模式 36 同族，位置不同

36 说先决条件问「这个量存不存在」而判据要的是「这个量估不估得出来」。
**本条说判据的目标存不存在这个问题，要拆到分量上才问得对。**
两条合起来：**跑之前要能说出「什么样的数据会让这条判据命中」，
并且要在手上的数据里数一遍那样的数有几个。数出零，这条判据就不该跑。**

### 第三例，2026-08-25 同日，而这一次错的是网格不是合取

同一站的目标，`top1` 跌而 `gini` 涨，在 1,260 个臂-格上是零，**于是被判成不可达**。
A16 在同一个载体上加了一条轴之后，**同一个形状出现了 21 次，其中一次在控制臂上**。

**差别是那 1,260 格把生存线钉在一个值上。** 拿来数可达性的网格，
**它自己就没有扫过决定这件事的那条轴**。

**判别式因此要再往前一步**：数一个目标可不可达之前，先问
**「手上这张网格扫过哪几条轴，没扫过的那几条里有没有一条是这个目标的开关」**。
本例里没扫过的那条是生存线深度，而它决定的是**离场人群带不带得走存量** ——
浅线上他们占总量 `0.33%` 进、`0.32%` 出，读数变成幸存者内部的再分配；
深线上他们冻结时握着 `94.16%`，三个口径一起塌。**同一个载体，两个 regime。**

**外加一条**：那个被判不可达的网格，**正好落在台账已知被人工制品主导的那一档**
（冻结存量，A11 分离实验与 A12-6 都量过）。**在一个已知有人工制品的格上量可达性，
量到的是人工制品的可达性。**

### 这一次的零仍然有产出，但它的对象换了

**读数从「哪个机制子集产出分歧」变成「这个载体只有一个集中过程」**：
`gini` 涨 ⟹ 三个都涨（344/344、349/349），`top1` 跌 ⟹ 三个都跌（266/266、259/259）。
**三向分歧在构造上要求至少两个互相独立的集中过程，而这里只有向上渗漏这一个。**
**不可达的零仍然是关于载体的信息，只是不许当成关于框架的信息。**

---

## 失败模式 42：把相关重复当独立样本数，一到两个种子的差别就成了 13 比 1

**买来的**：2026-08-25，A16-7。

那一站在一个深度上数某个符号形状的命中率，逐朝向报出来是
**`debtor` 13/30、`mutual` 6/30、`creditor` 1/30、控制臂 1/5**。
读起来像 `debtor` 把频率翻了倍而 `creditor` 把它压到六分之一。

**那 30 是 6 个 rate 配置 × 5 个种子，而 6 个配置跑在同一批种子上。**
按（朝向, 种子）拆开之后：`debtor` 的 13 格落在 **3 个种子**上，
`mutual` 的 6 格落在 **1 个种子**上，`creditor` 与控制臂各 1 格也在**同一个种子**上。

**独立种子上的计数是 3/5 对 1/5。一到两个种子宽，五个种子上分不开。**

### 为什么它读起来像效应

**因为分母是对的。** 30 个格确实跑了 30 次，每次都是一次真实的模拟，
**没有任何一步是错的**。错的只有把这 30 个数当成 30 次独立抽签来读。
一个种子上如果命中，它在那 6 个 rate 上大概率一起命中，
**于是一个种子进来就带 6 格，而另一个种子不命中就带 0 格**，
比率因此按种子跳而不是按格跳。

### 判别式

**数一个比率之前，先问这些重复是不是同一批种子上的同一件事。**
可机读的做法：**把命中按（臂, 种子）去重再数一遍**，两个数差得远就说明分母是虚的。
本例里 13 去重之后是 3。

**同一句话的另一面**：扫参数不是重复。参数轴回答「这个量随参数怎么变」，
**它不给比率提供独立样本**，而比率要的是种子。

### 与第 11 条那条「N 次全票通过」同族

那一条说三次试验估一个比率再卡在 1 上，一次地板抖动就杀掉判据。
**本条说的是反方向的同一个病**：样本量看起来够大，而有效样本量是 5 不是 30。
**两条合起来：任何一个比率，先报它的有效样本量，再报它本身。**

### 这一次没有付出代价，靠的是另一条轴

那个 13 比 1 差点单独开一站。**结掉它的是一次为别的目的做的扫描**：
生存线细扫每个深度每条臂只跑一个 rate、五个种子，
于是同一件事在那里读出来是 2/5 对 0/5，**当场看得出来是一到两个种子的事**。
**一条独立的轴比一次更仔细的阅读更管用。**

---

## 失败模式 43：网格扫了一个机制的参数，却从来没有一格把那个机制关掉

**买来的**：2026-08-25，A16-7 与 A16-8。

那两条判据在生存线的八个深度上量出了一个符号形状出现在浅的一侧、消失在深的一侧，
并且给了一个机制解释：**浅线上离场的人带不走存量，读数因此变成幸存者内部的再分配**。
两侧的数都是真的：浅侧离场者占收盘存量 `0.3%`，深侧 `94%`。

**而那张网格里每一条臂都带着生存线。** 名字叫 `off` 的那条臂关的是**债**，不是生存线。
于是这一站从头到尾没有一格能回答「把生存线整个关掉会怎样」。

**另一站补上那格之后**：`need = 0`、`starved = 0` 的臂**照样产出同一个形状**，
读数与带生存线那几行几乎逐位相同（`0.8812` 对 `0.8813`、`0.1480` 对 `0.1480`）。
**零离场，所以它不可能是组成效应。** 那个形状是图在纯基线动力学下的漂移，
**而那条机制解释是把一个真实的相关读成了因。**

### 为什么它看起来很牢

**因为参数扫描给了一条漂亮的单调曲线。** 深度从 `0.02` 走到 `0.20`，
形状从 4/20 掉到 0/20，冻结份额从 `0.0004` 跳到 `0.94`，两件事在同一处转折。
**两个量一起动，而它们确实一起动**，只是都由第三样东西带着走。

### 判别式

**一个网格如果扫的是某个机制的参数，先问它有没有一格是那个机制关掉的。**
`rate = 0`、`need = 0`、`hubs = 0` 这样的一格，
**通常一格就够，而它是唯一能把「这个机制造成的」和「这个机制没关系」分开的那一格。**

**容易漏的形状**：网格里已经有一条叫 `off` 或 `control` 的臂，
**于是看起来有对照了**，而它关的是另一个机制。**对照要按名字对得上被扫的那一维。**

### 与失败模式 41 同族

41 说数可达性的时候，网格没扫过决定目标的那条轴。
**本条说的是网格扫了那条轴，但那条轴的零点不在网格上。**
**两条合起来：一条轴要么不在网格里，要么在网格里而缺了它的零点，两种都会让读数指错因。**

---

## 失败模式 44：两批跑并进同一个记录，而没有字段能把它们分开

**买来的**：2026-08-25，A15。

一个脚本先跑 80 行定点重复，再跑 70 行浅生存线，然后 `rows = rows + shallow`
写进同一个记录。**两批的臂名、`f2i`、`elasticity` 在四个臂上完全重合，
而它们唯一的差别是生存线深度，那个数不在任何字段里。**

实测：150 行里 **20 行的键重复**，`(arm, f2i, elasticity, seed)` 各出现两次，
**而记录里没有任何东西说哪一行属于哪一批。**

### 判据算对了，记录写错了

**判据是在内存里各自那批上算的，所以裁定没问题。**
坏掉的只有落盘那一份：下一个 session 打开 `runs` 会看到 20 对同键不同值的行，
**而它没有办法知道该信哪一行。**

### 判别式

**一个脚本如果把两批跑写进同一个 `runs`，先问：把这两批的行混在一起之后，
每一行的键还唯一吗。** 不唯一就必须加一个字段把批次写进去。
**「我在内存里分得开」不算数，记录是给别人读的。**

### 处置

两批各加 `batch` 与 `floor_need` 两个字段，排序键加 `batch`。
**加字段之后要重跑一次**，因为已落盘那一份没有这两个字段。

---

## 失败模式 45：一条「定向」规则遇上一块度是硬编码的构造，定向就变成确定性的

**买来的**：2026-08-26，A17-4b。

那条臂要复现一个已知结论的另一半：这类图**对随机断链稳健、对定向打枢纽脆弱**。
做法是按「边的两端谁的度大」排序，先切枢纽相关的边。

**跑出来五个种子搁浅的是同一批节点 id，交集是满的。**
它们的开盘出度**全是 81**，而其余一百七十个节点是 **3 到 18**。

那三十个节点是**工资支付方**，而它们的出度是**建图时给的**：
每个支付方在构造阶段就连到全部接收方。**那个度不是抽出来的，是写死的。**

**所以那条排序永远先命中同一批节点，「定向」这个词在这里没有随机性可言。**
搁浅数与种子无关不是稳健性，是**排序规则遇上一个「有一块的度是硬编码的」构造**的算术后果。

### 为什么它读起来像一个结果

**因为它单调而且好看。** 份额从 0.10 走到 0.70，搁浅数 5、9、13、15、17、19、21、25、29，
一条漂亮的直线。**跨五个种子完全一致，读起来像「这个结论非常稳健」**，
而它其实是「这个结论一次都没有被抽样检验过」。

### 判别式

**任何按度排序的规则，先印出被选中那批的度，和全图的度直方图。**
两者差一个数量级就说明有一块的度不是抽出来的，**而那一块会永远排在最前**。

**可机读的版本**：**同一条规则在不同种子上选中的集合，交集有多大。**
交集是满的就不是定向，是点名。

### 与失败模式 43 同族

43 说网格扫了一个机制的参数却没有一格把它关掉。
**本条说的是网格里那一维根本没有变异**，因为被扫的量在构造里是常数。
**两条合起来：一维要么没被扫，要么被扫了而它在这个构造里不会动，两种都会让读数指错因。**

### 处置

**这条臂不撤，改口径。** 它测的是**「先切工资通道的边」这一个有名字的干预**，
读数对那个干预成立。**它不是文献那个泛指的「定向打枢纽」**，
而那个泛指版本在这个载体上做不出来，因为这里的度不是自由抽的。
**改的是这条臂在说什么，不是它跑了什么。**

---

## 失败模式 46：`argmax` 指进一堆并列的 ulp，于是一个字段永远指着噪声

**买来的**：2026-08-26，A18_B1（第 19 条对 `ResupplySpec` 的核对顺手撞出来的旧账）。

A18 每条逐轮曲线记三个数：首次移动的轮次、单轮最大变化、**那个变化发生的轮次**。
前两个有守卫（`_first_move` 用 `1e-9` 的容差），**第三个没有**：

```python
i = int(np.argmax(d))
return i + 1, float(d[i])
```

**宽容臂的 `M/R` 在三百轮里是平的。** 稳定化规则从不触发，
序列一直坐在开盘值上，**它的最大单轮变化是一个 ulp，`3.33e-16`，
而 8 到 11 个轮次并列在那个值上**。`argmax` 取并列里的第一个。

**于是那个字段是一组无法区分的 ulp 里的一个下标。**
它复现不了任何东西；模型任何地方动一个末位它就跳到别的轮次；
**而当作轮次号去读的时候，它说伤害来得晚，事实是伤害根本没来。**

**同一形状的第二处**：核销关着的臂上 `written_off` 恒为零，
299 个轮次全部并列在 `0.0`，`argmax` 返回 0，记录里于是写着
**「最大核销跳幅在第 1 轮」，而那条臂一笔核销都没有。**

### 它为什么活下来

**因为它在有内容的那些格上是对的。** `exit` 臂的 `M/R` 真的从 1 走到 17.45，
第 5 轮那个跳是真的，五个种子全是第 5 轮。**读记录的人先看见的是那几行。**
这与失败模式 9 是同一个形状的浮点版：**同一条固定门槛，在有变异的单位上有信息，
在没变异的单位上是噪声**，而它总是在看起来最干净的那一半先通过。

### 判别式

**任何 `argmax` / `argmin` 出来的下标，先问「最大值有几个并列」。**
可机读：`(d == d.max()).sum()`。**大于一就说明这个下标不是一个读数，是一次任意选择。**

**加强版**：`argmax` 出来的下标，配一条**它所索引的那个量本身够不够大**的守卫，
容差用同一份代码里别处已经在用的那个，**不要新造一个常数**（`D5`）。

### 处置

`_largest_jump` 在 `d.max() <= tol` 时返回 `-1`，与 `_first_move` 同一约定同一容差。
**六条判据的裁定逐条不变**（实测），所以这是一次判据形状修正，直接改字。
**判别式是改完重跑读数变不变**：一个字节没变的，改的就不是自由度。**结果件那一条读数开作废栏**，因为读数变了：
不是「早崩对慢漂」，是「崩」对「什么都没发生」。**改正后的读数比原来强。**

---

## 失败模式 47：规矩 19 的核对读的是「跑核对那一刻已经存在的记录」，而同一天新写的记录不在里面

**买来的**：2026-08-26，与 46 同一次。

`edge_cut` 与 `hub_debt` 进 `network.py` 那天，第 19 条的核对跑了两次，
逐字段比了 `a12`、`a11`、`a16` 的记录，**全绿**。

**`a18_policy_paths.json` 是同一天写的，而且是在那两次核对之后写的。**
于是它从来没有被任何一次核对读过。**它带着 51 个对不上的字段活了一天，
而每一次核对都报「全部路径复现」。**

### 判别式

**核对器的文件清单是怎么来的？**
写死的一张表 → 新记录永远进不去，而**新记录正是最可能出问题的那些**。

这与「一次扫描报零，先问它的文件清单是怎么建的」是同一条
（本轮改名那次，`git ls-files` 漏掉未跟踪文件是同一个形状）。

### 处置

`scripts/check_default_off.py` 现在带 `--only` 与 `--slice`，
**加一条路径就是加一个函数**，A18 已加。
**开关加进 `network.py` 的那一轮里新写的每一份记录，都要进这张表。**

**顺带一条工程的**：Cowork 那台 Linux VM 上，
`nohup` 加 `setsid` 加 `disown` 的后台进程**活不过一次工具调用**，
父调用返回时整棵进程树被收走，日志留下一个零字节的文件，
而 `pgrep -f <脚本名>` 会匹配到**它自己那条命令行**，于是报「还在跑」。
**判别式**：用 `ps -eo pid,etime,args | grep "[c]heck"`（把首字母括起来，
不让模式匹配自己），或者干脆别开后台，**把长跑切片成每片装得下一次调用的大小**。

---

## 失败模式 48：确定性的代码，不可移植的读数 —— 连续量喂进一道离散门槛的地方

**买来的**：2026-08-26，A18 B 臂。**它不是 bug，两台机器上的代码各自逐位复现自己。**

一份在 Windows 上写的记录，在 Linux 上重跑，**120 格里 2 格对不上**，
都在同一个参数点：`drawdown` ／ 生存线 `0.50` ／ rate `1.0`。
一格的 `below_close` 差 **21 个节点**（153 对 132），
另一格只差连续量（`resupplied` 差 `3.03` / `2760`，即 `1.1e-3`）。

**梯度量出来的边界**（对开盘持有量施加相对扰动，看 `below_close` 何时翻）：

| 种子 | 无扰动 | 1e-16 | 1e-14 | 1e-12 | 1e-10 | 1e-8 | 1e-6 |
|---|---|---|---|---|---|---|---|
| 0 | 139 | 139 | 139 | 139 | 139 | **151** | 151 |
| 1 | 132 | 132 | 132 | 132 | **153** | 153 | 153 |
| 2 | 153 | 153 | 153 | 153 | 153 | 153 | 153 |
| 3 | 153 | 153 | 153 | 153 | 153 | 153 | 153 |
| 4 | 154 | 154 | 154 | 154 | 154 | 154 | 154 |

**单点一个 ulp 什么都不动**（先试的是 `np.nextafter` 单节点扰动，轨迹逐字节相同）。
**要到 `1e-10` 才翻，而且五个种子里只翻两个。**

### 病灶：一个连续量喂进了一道离散门槛，而门槛后面接着一次重整化

生存线把「持有量低于 need」变成一个布尔。**布尔一翻，那个节点退出这一轮的路由，
其余的边重整化，于是每一个节点的入流都变了。** 所以一个 `1e-10` 的差
不是被平均掉，是被**一次离散事件放大**，再经三百轮传播。

**同一个模型在别处不这样**：A18 的 A 臂 120 行跨平台逐字段相同，
a12 的 1125 行、a11 的 270 行、a16 的 380 行也都相同。
**差别在于那些格没有坐在门槛上。**

### 判别式

**问这个读数是不是一个计数，而这个计数是不是由一个连续量过一道门槛得来的。**
是 → 它在门槛附近不可移植，**而「附近」有多近要量，不能猜**。

**可机读的版本，而且这就是解药**：**把开盘状态按 `1e-10` 相对缩放重跑一遍，
印出哪些格的计数动了。** 一次扫描，成本等于把网格跑第二遍。

### 处置：加一次测量，不加豁免表

`experiments/a18_policy_paths.py` 的 **A18_B6**：每个受判的格子按
`BOUNDARY_EPSILON = 1e-10` 重跑，**印出动了的格**，三态零阈值，
全表进记录的 `boundary_scan` 字段。

**为什么不是豁免表**：本仓库已经埋掉两张例外表（渲染器的 `diagnostic_only`
与 runner 棘轮的豁免清单），**两张都是因为例外装进了多数人口**。
**一份自己说得出哪些读数可移植的记录，比一份默认全部可移植的记录值钱。**

`1e-10` 是**量出来的，不是选的**：它是上面那张梯度里真正够到边界的最小值。
**它不是容差，没有任何东西在它上面通过或失败**（第 11 条）。

### 与「派生文件的写盘纪律」第 5 条同源，位置不同

那一条说的是**文本**：浮点按显式格式串写盘，免得 BLAS 之间的末位差变成文本 diff。
**本条说的是读数**：同一个末位差在门槛附近变成一个整数差，
**而整数差不会被任何格式串挡住。** 两条合起来 ——
**跨机器要对的不只是文件的字节，还有读数所处的位置离门槛有多远。**

---

## 失败模式 49：一个会被削顶的量，只记了削完的那一半，于是「约束咬没咬住」不可观测

**买来的**：2026-08-26，A18 B 臂的 `retain` 分支开工前。

`_resupply_flow` 算的是缺口，付的是 `min(每人应摊, 该人手里有的)`。
**它记了付出去的 `_resupplied`，没记要求的那个缺口。**
于是记录里读不出「债权人有没有被卡住」，而**整条囤积臂能不能成立就转在这个量上**：
如果缺口从来都被足额满足，那么注资对直接救助渠道零贡献，
这条臂的答案就是构造逼出来的（第 12 条），不该开。

**量出来约束咬得很紧**：覆盖率 `0.25` 到 `0.92`，
最深那格债权人**付不出所要的四分之三**。**臂成立。**
但这个判断是从外面重算一遍才拿到的，**记录里没有它**。

### 同一份代码在别处是对的

`NetworkHistory` 有 **`wage_owed` 和 `wage_paid` 两条**，
`wage_funding_ratio` 就是它们的比，docstring 还写着这条序列是 H1 的对象。
**工资通道记了两半，救助通道只记了一半。**
`_hub_debt_blocked` 是中间态：记了**被挡住的次数**，没记被挡住的**金额**。

### 判别式

**凡是形如 `min(应付, 能付)` 或 `clip` 的地方，问记录里有没有 `应付`。**
只有 `能付` 的话，**「这个约束咬没咬住」就是不可观测的**，
而那通常正是下一个问题要问的量。

**可机读的版本**：搜 `np.minimum(` 与 `np.clip(` 落在会写进记录的路径上的地方，
逐个看两个操作数有没有各自留下一个字段。

### 处置

`network.py` 加 `_resupply_asked` 计数器（只在开关开着时累加），
A18 记 `resupply_asked` 与 `funded_share` 两个字段。
**这是完整性要求的落地，不是新判据**：没有任何东西在这两个数上通过或失败，
它们是给下一个问题用的。

---

## 失败模式 50：离散阈值把末位差反向放大回连续量，于是**计数没动而其余全动**

**买来的**：2026-08-26，A18_B 的记录跨机器重跑。**与 48 是同一个环的两个方向。**

48 说的是「连续量喂进一道离散门槛 → **计数**不可移植」。
本条说的是**反过来那半**：门槛的输出又回到连续量上，
于是**计数纹丝不动，而其余每一个数都动了**。

实测：Windows 写的记录在 Linux 上重跑，`issuance` 臂差 **1e-7 到 7e-4** 相对量，
而同一格的 `below_close` **完全相同**。同机两跑逐位相同，所以不是随机。

**病灶是那个反馈环**：补血 → 持有量 → 支出 → 入流 → **线下集合（布尔）** → 缺口 → 补血。
**末位差每轮被一个布尔四舍五入一次**，三百轮之后长到第四位有效数字。
`creditors` 臂没有这个环（不造 claim，不回补），所以它跨机器逐字段相同。

### 判别式

**这个读数所在的量，是不是被一个每轮重算的布尔喂回来过？**
是 → 它的低位不可移植，**而「多低」要量**。

**可机读的版本，也是解药**：**把开盘状态按 `1e-10` 相对缩放重跑一遍，
逐字段报相对变动。** 一次扫描，成本等于把网格跑第二遍。

### 处置：让记录自己说它哪些读数可移植

`A18_B6` 扩成两半：离散那半问计数动不动，连续那半**逐字段**报最大相对变动。
20 格小网格实测：

| 字段 | 最大相对变动 |
|---|---|
| `payer_holdings_delta` | **8.7%** |
| `support_close` | 0.55% |
| `resupplied` / `resupply_asked` | ~0.2% |
| `funded_share` / `gini_close` / `recapitalised` / `mr_close` / `volume_total` | 0.03%–0.06% |

**不要报「最差那一个字段」这一个数**：它会被最接近零的那个字段占据
（此处是 `frozen_close`，深生存线上读 `0.30`，相对变动 42%，
那是两个小数之比不是读数）。A17-8 撞过同一个形状并且拒绝了同一类数字。

### 一条正面的：按量级写的结论扛住了

`A18_B3` 的头条（出钱者净亏占毛额 `0.4%`）**正架在最不可移植的那个字段上**。
但结论写的是「远低于 1%」而不是一个点值，
`0.4% × (1 ± 8.7%)` 仍然是 `0.4%`，**结论稳。**
**按量级写、不按点值写，这一条纪律在这里第一次自己付了钱。**

---

## 失败模式 51：一个从字段重建行的核对器，每加一个字段就得改一次，而没有东西提醒你

**买来的**：2026-08-26，一个下午漏两次。

`check_default_off.py` 原来的做法是**把记录里的每一行按字段重建成一次调用**再重跑比对。
`ResupplySpec` 加 `funding` 那次，核对器没把 `funding` 传回去，
于是所有 `issuance` 行被当成 `creditors` 重跑，**报 472 个字段不符**。
加 `retain` 那次一模一样，**报 129 个**。

**两次都不是模型错，是核对器少传了一个参数。**
而它长得像模型错 —— 差异报在模型的字段上。

### 判别式

**这个检查有没有「把被检对象重新构造一遍」这一步？**
有 → 它和被检对象之间存在一份**必须手工同步的参数清单**，
**而清单漂了没有任何东西会报**（第 19 条那条 `NetworkSpec.replace()` 是同族）。

### 处置：把重建那一步整个去掉

规矩 19 问的是「新开关默认值下旧数字还在不在」，
**而各站本来就要重跑**。所以正确的流程是：

```
--snapshot   动共享模块之前，把 results/*.json 拷一份
             干活，跑站
--diff       之后，逐字段比两份 JSON
```

**不跑任何仿真，而且严格更强**：两份 JSON 直接比**没有重建这一步**，
也就没有这个漏法。原来那个重跑模式留着当没跑站时的兜底。

**一条保险不能省**：**一份没动过的记录，和一份「重跑了且一样」的记录，长得一样。**
所以 diff 必须**逐个点名文件时间早于快照的记录**，报成「未重跑，本次没测到」，
不许算进干净的那一堆。**这就是失败模式 47。**

### 顺带买到的第三件

第一次跑 diff 报**四份记录变了、十二个字段，新旧值都是 `nan`** —— `nan != nan`。
那些 `nan` 是真读数（没有分母的比值，如实报了），**所以改比较函数，不改记录**。
**凡是逐字段比较两份记录的地方，先问 NaN 怎么算。**

---

## 失败模式 52：判据本来就在记录里，而摘要却是靠重跑仿真算出来的

**买来的**：2026-08-26。**这一条不是别人的错，是本轮自己一直在犯的。**

`run_all.py` 有两个模式，而**贵的那个被当成了唯一的那个**：

| | 干什么 | 成本 |
|---|---|---|
| 默认 | 每个站当子进程重跑一遍，各自写记录，然后印判据摘要 | 分钟到小时 |
| **`--skip-done`** | **记录已经在盘上的站不跑，直接读那份记录**，判据摘要照出，那一列印 `READ` | **一秒** |

**实测**：`--skip-done` 全表 **160/165，四个预期失败，约一秒，零次仿真。**

**成因**：**判据是从行算出来的，而行就在记录里。** 所以任何「印一张判据表」的动作**不需要跑任何东西**。
一个靠重跑来出摘要的工具，是在**重新推导一件已经写下来的东西**。

### 重跑到底买到什么

**只有一样：规矩 19 的答案** —— 改了代码之后旧数字还在不在。**别的什么都不买。**

**而且它要跑的集合远小于「全部」。** 同日数出来：

| | |
|---|---|
| 表里的站 | **44** |
| 直接 import `monetary_topology.network` 的 | **22** |

**动 `network.py` 影响不到另外 22 个**（B 轨、A0、A1），重跑它们是纯浪费。

### 判别式

**一张摘要里的每个数，是从盘上的东西读出来的，还是现算的？**
读出来的 → 那个摘要不需要跑任何东西。
现算的 → 问它现算的输入是不是也在盘上。

### 处置

`run_all.py` 加了 **`--touched PATH`**：给它一个改过的源文件，
**它只跑脚本里够得到那个文件的站，并把丢掉的逐个点名**。

```
--touched src/monetary_topology/network.py   → 25 个里 21 个，点名丢掉 A0 A0b B1 B1H
--touched experiments/a18_policy_paths.py    → 25 个里 5 个，点名丢掉另外 20 个
```

**这条规矩本来就在**（「改了 `src/` 就去看谁 import 了改动的那个符号；只改了
`experiments/` 就到此为止」），**它一直靠人记着，而它可以让脚本算。**
**丢掉的必须点名不许只报个数**，理由与本文件里每一条「不许静默跳过」同源。

---

## 失败模式 53：一张对照表按错的变量索引 —— 累积的单向量没有稳态

**买来的**：2026-08-26，A18_F1。**是被一个问题问出来的，不是被跑出来的**：
「这张表是给某一个国家用的，还是别的开关随便设它也好用？」

`A18_F1` 印的是「停泊率 → 停泊存量份额」，**而它被当成停泊率的性质写了出去**，
连同一句「谁有那个数字自己来落点」。

**量了一遍，答案是两半，而且两半都出人意料：**

**一半是好消息 —— 政策开关那一侧它真的通用。** 停泊率钉在 `0.002`，
基准份额 `0.3082`，逐轴换：出资路线 `0.99×`、生存线深浅 `1.01×`／`1.09×`、
救助力度 `1.02×`／`0.98×`、留存 `0.88×`、**核销打开 `1.00×`（一位不差）**。
**每一条政策开关都动不到十分之一。**

**另一半是这条坑账：动它的那两样都不是政策。**

| 换什么 | 对基准 |
|---|---|
| **跑 150 轮** | **0.59×** |
| **跑 600 轮** | **1.53×** |
| **停泊的是受注集合** | **0.33×** |
| 停泊的是所有人 | 1.22× |

**跑多少轮那一条是结构性的**：停泊单向、不回头，**所以停泊存量只增不减，
份额一路朝 1 爬，根本没有稳态。** 于是「份额」不是停泊率的性质，
**是「停泊率 × 时间」的性质**，而按停泊率单独索引的表
**会请读者拿一个数字来对，却不必对上第二个索引**。

### 判别式

**这个量有没有稳态？** 没有 → **它的水平不是参数的性质，索引里必须带时间。**

**可机读**：把这个量在几个不同轮次上读出来。**几个读数不收敛，就是没有稳态。**
本条的实例：同一个停泊率在第 50、150、299 轮读 `0.065 / 0.186 / 0.312`。

**同族的一句**：一个**单向累积**的机制（停泊、核销、退出）产出的**存量**量，
默认就该怀疑它没有稳态；**双向的（会到期、会回来）才可能有。**
`ParkSpec` 的 docstring 里那句「单向，这是极限情形」当时是设计说明，
**它现在有了一个可测的后果。**

### 处置

`A18_F1` 的表改成**按停泊率 × 轮次两维索引**，六个轮次从同一批跑里读出来，
**零额外仿真**（`parked` 与 `total_claims` 本来就是逐轮序列）。
`RESULTS.md` 里那张敏感度表**一并印出来**，让读者看得见哪些轴不用管、哪两轴要管。

**不改的是那句「落点是读者的活」。** 改的是**把落点需要对上的东西说全**。

---

## 失败模式 54：模型测得干净的量要求同时跑两条政策，而任何一段历史只跑一条

**买来的**：2026-08-26。**被两个设计问题逼出来的**：跨国比得了吗、同国跨年比得了吗。
**两个都量了，两个都不行，而且是因为互补的理由。**

### 跨国：有对照，没有数量

处理变量是「是否在某一套救助方案里」。**世界上的取值是五个**
（ENAP 编码的正是五个欧元区国家）。本仓库已经关过一个同形的站：
制度类型覆盖**二十国**、80% 功效需要**五十国**，判词是
「不是样本不够，是该处理变量所在的世界里国家总数就不够」。**五是那个二十的四分之一。**

**而且那几国不是一根轴上的几个取值，是多维空间里的几个点**：
初始条件、方案规模、银行体系结构、外部环境同时不同。**功效无限也归不了因。**

### 同国跨年：有数量，没有对照

形状上更合身：**同一个结构上的一个比值**，而不是不同结构之间的水平比。
闸零也不咬，因为处理变量变成了一个**连续量**（停泊份额）在一国内反复测量。

**但量出来信噪比接近 1。** 把同一条跑在六个日期上读（这正是同国跨年的形状），
按停泊份额分箱：

| 份额箱 | 每轮流量均值 | 同箱内散布 |
|---|---|---|
| 0.0 | 68.24 | 1.3% |
| 0.2 | 67.61 | 3.1% |
| **0.4** | 65.37 | **7.8%** |
| 0.6 | 63.86 | 5.6% |
| 0.8 | 61.71 | 3.7% |

**份额从 0 到 0.8 流量总共掉 9.6%，而换条路径到同一个份额流量差最多 8%。**

**还有两条**：独立窗口天花板（结论 53）—— 连续政策时期状态跨期携带，
独立窗口撑死三四个；以及**同时性** —— 那些政策是一起发生的，
**而这个模型的全部价值就是把它们分开，同国跨年把它们原样绑回去。**

### 一般的那一句

**本模型测得干净的量是两条臂的比值**（换 10 倍停泊率、6 倍轮次，比值只差 **1%**），
**而它要求同一时刻跑两个不同的政策。任何一段真实历史只跑其中一条。**

> **跨国有对照没有数量，同国跨年有数量没有对照。**

**这不是本模型的毛病，是「模型对历史做映射」这件事本身的形状**，
只是现在有本仓库自己的数字撑着：**`1%` 对 `8%`**。

### 判别式

**这个模型读得最干净的量，是一个对照量还是一个水平量？**
对照量 → **它要的那两个臂，现实里同时存在吗？** 不存在 → 别拿历史去对它，
**对得上的只有方向和数量级，而那不需要多个国家也不需要多个年份。**

### 处置

**已有的写法就是对的尺寸**：单个比值、方向 ＋ 数量级、第三层指针，
明写映射未测、留给做实证的人。**再加第五第六个事件指针买不到任何东西**，
因为限制不在事件数量上，在于**对照臂在现实里不同时存在**。

---

## 失败模式 55：一个不平等统计量算在「还在交易的」加「已经冻住的」两群人上，读出来的是快照什么时候拍的

**买来的**：2026-08-26，A11。**代价是一条挂了两天的开口**
（「这个跌幅里有多少是退出、多少是累积，尚未分离」）。

A11 的 registered arm 用 `exit`：跌破生存线的节点冻在图里，
**不再交易，但手里的 claim 原样留着**。收盘 Gini 算在全部 200 个节点上，
底线 0.5 时读 **0.9367 → 0.7139**，一个 0.22 的「改善」。

A12 早就有第二条规矩 `drawdown`：节点留在图里，花 `min(need, holdings)`，
**把自己花到零再停**。**同一张网格上把两条规矩都跑一遍，按种子配对**：

| 图 | 底线 | 规矩 | ΔGini（全体） | 冻结份额 | 饿死数 |
|---|---|---|---|---|---|
| 分层 | 0.5 | `exit` | **−0.2229 ± 0.0023**，5/5 负 | 39.7% | 182.4 |
| 分层 | 0.5 | `drawdown` | **+0.00024 ± 0.00001**，5/5 正 | 0.21% | 172.0 |
| 完全 | 1.0 | `exit` | **+0.9822 ± 0.0003** | 100% | 200 |
| 完全 | 1.0 | `drawdown` | **−0.0027 ± 0.0002** | 0% | 0 |

**饿死的人数两条规矩差不多**（182 对 172），**两条规矩在谁走这件事上一致**，
**分歧全在走的时候手上那笔 claim 去了哪。** `drawdown` 下它被花掉，冻结份额剩千分之二，
**Gini 一动不动**。所以：**跌幅里退出贡献 0，冻结贡献全部。**

**而 `exit` 那个数的符号由图决定，不由机制决定。**
同一个开关同一个深度，分层图读 **−0.22**，完全图读 **+0.98** ——
后者整群人全冻住，**这个统计量连交易对象都没有了**。
**一个能在两个方向上各跑掉大半个量程的量，报的是快照拍摄时刻。**

### 判别式

**这个统计量的分母里，有没有已经不参与被测过程的单位？**
有 → 它读到的移动里有一份是**成分**，而成分那一份的大小与符号
**由「什么时候停止参与」决定，不由分布决定**。

**两个便宜的检查，都是一遍扫描：**

1. **印停摆那群人占多少**（本例 `frozen_share_close`）。
   接近零 → 成分那一份可以忽略；**上到四成 → 报出来的移动基本就是它。**
2. **换一条只改「停摆之后 claim 怎么处理」的规矩，别的一个字不改，再读一次。**
   两条读数差三个数量级 → 原来那个数不是分布结论。

### 与既有条目的关系

**是范畴错误第六式的一个实例**：判据的作用域（全体节点）
与被测对象的作用域（还在交易的节点）不重合。
**也和失败模式 29 同源**：那一条说「用成员资格实现一个行为，
它就继承了成员资格的性质 —— 二值、吸收、全有全无」，
**本条说的是这个继承会一路走到聚合统计量上，并且在那里改换符号。**

### 处置

**加两个字段，不动任何已有的数**：`frozen_share_close`（停摆那群人持有的份额）
与 `gini_close_trading`（只算还在交易的那群人）。
**两个记录各加 180 处，已有值零处移动**（第 19 条，`--diff` 核对）。

**第二个字段印出来但不判。** 它算在一个越缩越像的集合上
（200 个降到 18 个，而剩下的按构造就是分布的顶端），
**「变平等」和「剩下的人互相像」在它上面读不开**。
**它在这里是因为冻结份额只是分解的一半**，不是因为它自己能承载判定。

**A11 的四条判据两条规矩下全过**，因为它们读的是分层饿死率和完全图对照，
**没有一条穿过冻结那群人的持有量**。**这不是运气**：判据形状写对的时候，
承重的东西不会挂在一个成分统计量上。

## 失败模式 56：把一个机制映射到一个不承载它的载体上，而实跑照跑，于是读数被写成「预言被证伪」

**病灶**：设计从一个已有机制出发，把它映射到一个实证载体上去测。
本仓的实例是 `a3_asset_channel.md` §3 的门 `claims_i ≥ γ^gate · P_q(0)`：
**门槛随价格动**，一次上涨机械地把节点挤出去，§6.4d 那个从 `5.80` 到 `0.00`
的坍缩就是这个机制在跑。映射到的载体是 ETF 一级市场，
而那里被当作对应物的门是 **Authorized Participant 资格，一纸合约，行情动它不动**。
于是那次实跑量到的是**这个门不呼吸**，不是那个机制成不成立。

**它危险的地方不在成本，在记账。** 那次跑产出一个方向明确的读数
（零变动日占比在压力期下降，十一支里十支），落进注册的第三格。
**如果那一格被写成「预言被证伪」，下一个人读到的是「这件事测过了而且反了」，
而实际情况是「这件事还没被测过，并且这个载体上不该这样测」。**
两句话给出的下一步动作相反：前者叫人别做，后者叫人换载体。
**写错的那一版会让别人重复同一个错误**，所以这一条的代价不止一次跑。

**判别式，跑前零成本**：**要测的那个门，在这个载体的规则原文里随不随价格动？**
读合约、资格表、规则手册、章程，**不读数据**。
「AP 资格是一纸合约」这件事，读一份 Participant Agreement 就知道，
**不需要 404 个交易日**。

**同一条线上的第二例**：同一个门想映射到房贷的 LTV，
而 Servicing Guide 里根本没有 LTV 这条资格线，
**规则手册在读第一笔贷款之前就把答案定死了**。同样读规则原文就能挡下，同样没读。

**正确的定性长什么样**，见 [`b9_zero_holonomy.md`](b9_zero_holonomy.md) §27.3：
**检验本身是好的，载体没有它要问的那个对象。**
这仍然是一次测量的结论，而且它比一个未经检验的「映射成立」的假设更值钱，
因为它是由一个**本来可能反向**的预言挣来的。

**要什么样的载体才承载这一类门，三条，后两条是这条坑立起来之后接着推出来的：**

1. **门槛随价格动，而且随的是别人的价格。** 原式 `claims_i ≥ γ · P_q(0)` 的右边
   **不是主体 i 的属性**。门槛若是主体自己的市值，处理组会与该主体自身的价格维度
   完全共线，这一点在一次实际核算里读到过：那样定义的处理组代数上等价于
   「市值低于总资产」，也就是低市净率。
2. **那道门不能自己就是资本约束。** 一道按资本配额的门与套利资本受限**是同一个对象
   的两个名字**，任何量上都不会符号相反。§27.5 登记的两个候选各踩一边：
   回购折扣率与保证金随价格动**而它就是资本约束**；按规模缩放的合格投资者门槛
   不是资本约束**而它的门槛是法定的，不动**。
3. **被这道门约束的资金要大到效应可测。而第三条与第一条在实践中对立。**
   一次核算读到的形状：用市值做分母的合规名单是**指数公司的商业产品**，门呼吸，
   但被它约束的资金在任一市场里占比都小；用总资产做分母的是**监管机构的官方名单**，
   绑定整个市场，而它选总资产**正是因为要名单稳定**，而名单稳定就是门不呼吸。
   **谁需要这个名单稳定，谁就会选不呼吸的分母。**

**三条同时成立的门，到这条坑写下来为止一个都没找到，而障碍是结构性的不是运气。**

**与失败模式 33 同族，位置不同**：33 是拿旧载体的极值点当新载体的角落探针，
本条是拿旧载体的**机制**当新载体的被测对象。
两者都是把一个载体的性质搬到另一个载体上，而没有先核对那个性质在新载体上存不存在。

**与范畴错误第六式同族，方向相反**：那一式是判据的作用域与被测对象的作用域不重合，
本条是**被映射的机制在载体上没有对应物**。前者判据错，后者对象错。

**规矩那一侧已升格为 `D23`（闸零之二），跑前零成本、可一票否决。**

## 失败模式 57：一个读数对着两个不同的零，而汇总时只带上了仪器那一个

**病灶**：一个非零读数通常同时对着两个零，它们是不同的对象。

| 零 | 回答什么 | 是什么 |
|---|---|---|
| **仪器的分辨率下界** | 这个非零**读得出来**吗 | 一个测量事实 |
| **某个对手理论的点预言** | 这个非零**推翻了什么** | 一个理论事实 |

**两个都要报，而汇总件容易只带上前一个。** 前一个是本站自己算的，带单位，
可以写成「X 倍」，出现在每一节；后一个住在导言里，是一句话。

**本仓的实例，代价是整批误记。** 站点文档从来没有认错对手：
[`b1_setup.md`](b1_setup.md)、[`b4_directed_edges.md`](b4_directed_edges.md) 的零假设对象表、
[`b8_fannie_slice.md`](b8_fannie_slice.md) 都写着**若条款是位置上某个标量之差，
不管合同改动多大，环都返回零**；[`b3_cip_slice.md`](b3_cip_slice.md) 逐字把单一标量称作 the null。

**而同一批文件里 `floor` 出现 116、63、32、16 次，那句对手陈述各出现三到七次。**

于是汇总层带上去的是「对着测量底 `4.18e+06` 倍」，**而不是「一个预言精确零的对手
在这里错了」**。前者读作「读得出来」，后者读作「推翻了什么」。
**七个载体的核心读数因此被整批记成「与普通微观结构叙事重合」，
而那一族叙事根本不否认非零，它们解释非零的来源** ——
那是承认了主张之后的次级争论，不是对同一个主张的反对。

**判别式，报数之前问一次：**

> **这个非零，除了大于仪器的底，还大于谁的预言？**

**答得出名字，就把名字写进汇总。答不出来，那这个读数确实只是「读得出来」。**

**处置，两条：**

1. **站件里两个零分开写，各带各的名字**，不要让理论那一个只在导言出现一次。
2. **汇总件必须带上理论那一个。**「对着测量底 X 倍」单独出现在汇总里，就是这条坑的形状。

**与失败模式 56 同族，位置相反**：56 是把一个测量写成了对预言的裁决，
本条是把一个对预言的裁决写成了一次测量。**两条都改变读数的证据地位而不改变任何数字。**

---

## 失败模式 58：在纸上把一项设成零，然后据此收口 —— 而那一项是原稿标为承重的那一项

**病灶**：一个和有三项。你查得出其中一项为零，**就宣布整个和为零并收口**。
而剩下两项住在一个假设里，那个假设**原稿自己标着「这里就是全部的经济学」**。

**这条不是「要更严谨」，恰恰相反：严谨在下面每一次里都站在错误的那一边。**
每一次收口都是保守的、都写得像在守纪律，而每一次都错。

### 形状

`b1_theorem.md` §8 的 A1 说，agent 边带权 `t ≠ 0` 时方块和是

```
w_a(i,j) − w_b(i,j)  +  t_ab(j) − t_ab(i)
```

**同一个订单簿只让第一项为零。** 后两项要**两个位置顶点上的 agent 边权重相等**才相消。
而 §8 同一段写着：非零和**仍然证明 `ω` 不恰当，Corollary 1 完好无损**，
**不成立的只有归因**。

### 本仓的实例，一天之内四次，同一个站

| 收的什么口 | 设成零或不可得的那一项 | 推翻它的那份文件 |
|---|---|---|
| 方块退化，`index ≡ 0` | `t_ab(j) − t_ab(i)` | `b1_theorem.md` §8 A1 稳健性段 |
| 定理 5 的界恒真 | 把四个顶点塌成两个，即两条 agent 边 | 同上 |
| 载体收口不开站 | 上面两条 | 上面两条 |
| **「非零部分不在任何报价上」** | **`ŵ_a − ŵ_b` 的可观测性** | **一份权益分派实施公告** |

**第四次尤其要记**：那个量不在任何**报价**上，**它在公告上，而且比报价硬** ——
同一只股票同一天，内地机构代扣 `0%`、北向 `10%`、南向个人持 H 股 `20%`，
**逐类印在分派公告里，率由财税〔2014〕81 号与〔2016〕127 号定死。**

### 判别式

> **宣布一个量为零或不可得之前，先问它有没有一份写着它的文件。**
> 法条、章程、费率表、招募书、分派公告、交易所规则、原稿的某一节，都算。
> **「报价里没有」不等于「没有」。**

### 与相邻两条的关系

- **失败模式 56**（把机制映到不承载它的载体上）：那一条是**载体真的不承载**。
  **本条是载体承载，而你在纸上把它算没了。** 两者外观相同，代价相反。
- **失败模式 57**（一个读数对着两个零）：那一条管**报数**时漏掉一个零。
  **本条管收口时凭空造出一个零。**

### 操作要求：查全部输入，不是查到想要的那个就停

**本条的用途就是翻掉被没出处的数关掉的站。** 一个否定若建立在一个取出来的数上，
它不承载任何东西。**唯一的要求是查全部输入。**

B19 的受约束资金原取 450 亿（三次「上界取法」，零份文件）；
查到的是美国上市合规股票 ETF 逐只 AUM，纯美股口径 **37 亿**，含共同基金与专户
**约 100–120 亿**。**而受约束资金在带宽的分子上，所以查文件把闸二推得更难过**，
比值从 `6.1` 走到 `3.7` 而不是走到 `1`。

B19 三个输入全查了，其中两个各往相反方向动，
**只查一个就停会得到相反的结论 —— 那是把工具用坏了。**

---

## 失败模式 59：「取保守的那一端」用在一个比值的两边，含义相反，而两边都被记成保守

**病灶**：一道闸是一个比值。它的输入有几个，你不确定每个的值，
于是对每个都「取保守的那一端」。**而那些输入坐在除号的两边**，
所以同一个动作在一半输入上是保守，在另一半上是宽纵，**两边都被写成保守。**

### 本仓的实例

B19 的闸二是 `Z90 x se 下界 / 门槛带宽`，三个输入：

| 输入 | 坐在哪 | 往大取的效果 | 原件当成 |
|---|---|---|---|
| 受约束资金（进带宽的分子） | **比值的分母** | 比值**变小，更容易过** | **保守** |
| 持股变动的离散度 | 比值的**分子** | 比值变大，更难过 | 保守 |
| 合规子集占比（进带宽的分母） | 比值的分母 | 比值变小，更容易过 | 未考虑 |

原件写着「这三个上界每一个都取的是宽的那一边，**实际比 6.1 倍更差**」。
**那句结论是对的，而它对的理由不是写它的人以为的那个** ——
更差不是因为把上界取宽了，**是因为那个量取宽会让闸门更容易过，
而当时把它当成了保守动作。**

三个输入后来全部查过或量过（ETF 逐只 AUM、合规名单、13F 四十八个季度），
**比值从 `6.1` 走到 `16.6`。**

### 判别式

> **不要问「哪一端更保守」。问「把这个数往大取，判据往哪边动」。**

一个比值判据里，保守的方向**由输入坐在除号哪一边决定**，不由「取上界」这个动作决定。

**处置**：判据的每个输入旁边标两样 —— **它在公式的哪一侧**，
以及**取值区间的哪一端是宽纵的那一端**。两端算出来的比值**跨过判定线**，
就不许下裁定，先去查那份文件（失败模式 58）。

---

## 失败模式 60：把标准差当噪声的度量，而那个量是厚尾的，于是闸门的分子被尾巴定死

**病灶**：一道闸把「噪声」放在分子上，而噪声用标准差度量。
**被量的那个量是厚尾的**，于是标准差由尾部的少数观测定死，
**而闸门要保护的是中位数那个观测。**

### 本仓的实例

13F 机构持股的季度环比变动，48 个季度、每季一万四到两万只证券：

| 统计量 | 中位（跨季度） | 读作 |
|---|---:|---|
| `sd(dlog)` | **1.1245** | 一个季度动 `+208%` 那个量级 |
| `iqr(dlog)` | **0.1744** | 中间一半的票只动 `±9.1%` |

**差 6.4 倍。** 原因是申报层面的小额头寸：一份把 100 股改成 10,000 股的申报
给出 `dlog = 4.6`，而它对任何一只票的持股结构没有意义。

**闸二取的是标准差，而它保护的是「一只典型的票上，效应能不能从噪声里读出来」。**
稳健等价物是 `iqr / 1.349 = 0.1293`。

### 判别式

> **闸门的分子上放一个离散度之前，先把这个量的 `sd` 与 `iqr` 并排印出来。
> 差三倍以上，标准差就不是这道闸要的那个数。**

**这一条只说用哪个统计量去填那个门槛，不改门槛本身。**
本例里换成稳健版之后闸门更难过（`5 pp` 换成 `6.5–9.0 pp`），
**而换成稳健版是因为它对，不是因为它往哪边动。**

---

## 失败模式 61：一个量在两个函数里有两种朝向，两边都对，而没有任何东西能看出一个裸浮点数朝哪边

**B21 付的账，2026-08-27。**

`fx_daily()` 返回的是「每港元多少人民币」，两个调用方各自去倒数。
`main()` 倒了（写成 `1 / e`），`match()` 没倒（直接拿去比）。
于是那道检验拿**港元每人民币**的隐含比值去对**人民币每港元**的汇率，
`1.1 / 0.9 ≈ 1.22`，全部落在容差外，**1,840 对里判掉 1,515 对**。

**两种写法都是对的，这就是全部问题。** 汇率这种量没有自带朝向，
`0.9` 和 `1.11` 是同一个事实的两种拼法，而程序里没有任何东西分得出来 ——
类型一样、量纲一样、都是正数、连数量级都只差一点点。

**它怎么被发现的，值得单记一笔**：不是靠断言，是靠一个**本来就该不动的量动了**。
对照组（2014 年后、未被钉住的那些对）的「隐含比值 / 实测汇率」
在这次改动前是 `p10 0.987 / 中位 1.003 / p90 1.023`，改完变成
`p10 0.660 / 中位 0.797 / p90 0.997`。**那个中位数是 1.003 这件事，
是这份数据自己的性质，与这次改了什么无关**，所以它一动就是改坏了。

> **判别式：凡是有倒数、有正负号、有基准年、有「每单位什么」的量，
> 朝向写进一个带名字的函数里，别处一次都不许倒。**
> 一个量在代码里出现两种拼法而两种都说得通的时候，
> **迟早有一处忘了转，而它不会报错。**

**配套的读法**：改一段管道的时候，先挑一个**这次改动理应完全不碰**的量，
把它印在前后两次输出里。动了就是改坏了，**而这比任何断言都便宜**，
因为它不需要事先想清楚哪里会坏。本例里那个量是对照组的中位数 1.003。

**与失败模式 22 同族**（一个字段两种类型而所有消费者只判真值）：
那一条是类型没有东西守，这一条是**朝向**没有东西守。
两条的解药是同一个：**把没人守的那个属性放进一个有名字的地方。**

---

## 失败模式 62：为了修一个配对错误去调容差，而错的是配对的顺序不是容差

**同一天同一站，紧接着上一条。**

Anhui Expressway 的 H 股分红比 A 股早两三个月，2006 年 A 腿有两笔、H 腿一笔。
按日期就近配，那笔 H（`0.3265`）被三月那笔 A（`0.3625`）抢走，隐含 `0.901`；
**它真正的对家是七月那笔 A（`0.28`），因为 `0.28 × 1.166 = 0.32648`，逐位对上**。

**容差连着调了三版**：先是固定带 `0.90–1.40`，`0.901` 在带内；
再是对实测汇率的相对容差 `8%`，实测偏离 `7.0%`，还在带内；
再是拿汇率自己在这个间隔上的漂移分位数当带。**第三版才有用，而它的用处是失败**：
把「隐含比值超出汇率实际走过的区间」那个超出量排序印出来，是

    0.013  0.015  0.020  0.027  0.035  0.046  0.059  0.082  0.110  0.124  0.187 … 9.14

**连续的，没有断点。** 没有断点就没有地方可切，**任何一刀都是分析者切的，不是数据切的**
（第 11 条）。三版容差都是在估计量上画线，而画线这件事本身就是错的。

**真正的病灶是配对的顺序，不是配对的判据。** 就近配的代价不是「多一行错标的」，
**是偷**：那笔 H 被抢走之后，七月那笔 A（正好钉在 `1.166`、正好是需要重建的那一笔）
配不上任何东西，于是**掉的是一次修正，不是一个比值**。

**改法里一个阈值都没有**：把公司内所有候选对按「隐含比值离一个比值可能取的值有多远」
排序，最贴的先结。Anhui 七月那对得分 `0.000`，在三月那个候选被考虑到之前就已经出池。
**没有任何一对因为得分被丢掉**，得分作为一列写进表里，
要干净子集的读法自己去切。**全流程唯一还在做判定的，是「等于 1.166」这个精确匹配。**

> **判别式：一条容差改了三次还堵不住同一个个案的时候，别改第四次。
> 去看那个个案是怎么被选中的。**
> 尤其是**贪心**选出来的东西 —— 贪心的错不显示为「这一条判错了」，
> 显示为**别的地方少了一条**，而少的那一条不会自己报到。

**与失败模式 58 同族**（在纸上把一项设成零然后据此收口）：
那一条是把一个量当成零，这一条是把一个**排序**当成不重要。
**两条的形状一样：承重的东西被当成了背景。**

---

## 失败模式 63：判据的分辨率比被测对象粗，于是它去指控数据，而数据是对的

**B21 付的账，2026-08-27，同一天里连着两次。**

要判「这个分红有没有被正确地还原成公告值」，用的尺子是**中国 A 股按每 10 股公告**
这条事实。第一版写成**两位小数**，结果读出来 `13.6%` 的分红不在格子上，
**而不在格子上的名单第一行是工商银行 `18/22`、中国移动 `9/9`、中海油 `8/9`。**

**这几家公司的分红公告不可能有问题。** 病在尺子：中国的银行常按
**三位小数**公告（工行的 `每10股派3.064元`）。改成三位之后，
不在格子上的从 `13.6%` 掉到 `6.9%`，那批巨头全部回到格子里。

**判别式**：一个判据把**最不可能出错的那个对象**判成出错的时候，
**先怀疑判据的分辨率，不要先怀疑对象。** 这与失败模式 9（固定绝对门槛 × 异质分布）
同族但位置不同：9 说的是门槛在异质分布上会偏，本条说的是
**格点判据的格距比对象的真实格距粗，于是真实值全部落在格与格之间。**

**同一天的正面用法，说明这不是「格点判据不能用」**：
同一把尺子换成三位之后，**结掉了另一个悬着的问题** ——
「分红当天的拆股算不算」，算它 `209` 个落在格子上、不算它 `134`，`238` 个有争议的样本。
**先前用另一个判据（比值等不等于 `1.166`）问同一个问题，两种约定只差一对。**

**那次的失败有原因而且可以事先看出来**：`1.166` 那个判据只有 `300` 对样本贴着它，
而争议样本里只有二十来个在其中，**一个 300 对里动 20 对的效应，
在一个本来就只报「贴不贴」的判据上读不出来**。
**换成公告格点之后样本从 20 变成 238，因为格点是每一笔分红都有的性质，不是一个子集的性质。**

> **判据选得对不对，先算它的样本量：这个判据能看见几个受影响的对象。**
> 看得见二十个的判据分不开一个八十个的效应，**而它不会报错，它会给一个差一对的数。**

---

## 失败模式 64：「这一列是算出来的所以不可靠，那一列是原始的所以可靠」——公告一查，正好反过来

**同上，B21 的中兴通讯。**

H 腿 2014 年前的分红是供应商拿 A 腿数字乘 `1.166` 造出来的（见失败模式 58 那一族的口径条目），
**所以整节都是在「修 H 腿」这个前提下写的**：造出来的那一列是坏的，原生的 A 腿是好的。

中兴对不上，第一反应是 H 腿缺了一次拆股。**去查公告之后，反过来了。**

公告的每 10 股派息是 `2.5 / 1.5 / 2.5 / 3 / 3 / 3 / 2`（2006–2012）。

- **H 腿七年里五年精确复现公告值，误差 1/10,000**，用的就是它自己文件里的拆股加那个 `1.166`。
  差掉的 2011 年是因为那年常数换成了真汇率（`1.166 / 1.203 = 0.969`，读出来 `0.9755`）。
- **A 腿七年一年都对不上**，需要的额外因子逐年是 `1.5 / 1.5 / 15÷14 / 1 / 1.5 / 1 / 1`。
  **单一一次漏记的拆股会让某个日期之前每一年都差同一个因子、之后都不差。这不是那个形状。**

**所以造出来的那一列在算术上忠实于公告，原生的那一列不是。**

> **一个数是「算出来的」还是「报上来的」，不说明它对不对。**
> 前者可以忠实地算错的输入，也可以忠实地算对的输入；
> **要判的是它对不对得上一个独立的第三方记录，不是它的来路。**

**与失败模式 58 同族，位置相反**：58 是把一项设成零然后据此收口，
本条是**把一项设成可信然后据此定位错误**。**两条都是先假定再动手，都要靠去查一份文件才翻得过来（`D26`）。**

---

## 失败模式 65：把分解出来的一个分量指名成一个已知机制，而没有量那个机制自己的尺度

**B21 付的账，2026-08-27。一个比值就能拦住，而那个比值不需要任何新数据。**

一个恒等式把面板方差劈成两半：**日间的共同项**与**日内的截面离散**。
劈得干净，加一个常数到某天每一对上，离散变动 `1.110e-16`。

**然后写了一句多余的话**：「共同项**就是**货币楔子」，理由是资本管制的楔子
对所有对都一样，所以它落在共同项里。**前半句对，后半句是它的逆命题，不成立。**
楔子在共同项里，不等于共同项是楔子。

**安慰剂当场杀掉它。** 五个货币事件上共同项的跳变落在自己历史的
`14.4 / 25.2 / 25.3 / 38.2 / 39.1` 百分位，**一个都没到中位数**；
而同一批日子上**楔子自己**跳在 `99.8 / 95.8 / 90.2`。**刺激是真的，反应不在那里。**

**原因是一个数**：楔子的标准差 `0.00423`，共同项的 `0.13512`，**比值 `3.1%`**。
共同项由整体 A/H 溢价主导，跟着股市走。**在 3% 的尺度上，它当不了共同项。**

> **判别式：把一个分量指名成某个机制之前，先量那个机制自己的方差，
> 除以那个分量的方差。** 两个标准差相除，通常两条序列都已经在盘上。
> **小两个数量级的东西，不管它在不在里面，都不是它。**

**这与第 13 条第 4 步同源**（花钱之前先把乘积写出来）：
那一条说的是**成本**乘出来只要四个已知数，本条说的是**尺度**除出来只要两个。
**两条都是在动手之前用已有的数做一次算术，而两次栽的地方都是没做那次算术。**

**要记的是它毁掉了什么，以及没毁掉什么**：
**恒等式那一半完好**，因为它只要求楔子是**共同的**，不要求它是共同项的**全部**。
于是「截面离散不可能是资本管制的楔子」照旧成立，**而「共同项是楔子」以及
建立在它上面的那一层外部对照，一起作废。**

**一条排除不是一次归因。** 这一层原来自称产出「弱归因」，
**它实际产出的是一条排除**，而排除也值钱，只是不能写成归因。

---

## 失败模式 66：拿一个筛选条件冒充另一个，而那个数是真的，所以什么都不会报

**B21 付的账，2026-08-27，理 `D25` 第 1 问的时候顺手查出来的。**

一臂要一个控制组：**没被纳入互联互通标的的 A/H 对**。
设计件写的是「`203` 对减 `149` 对的差，`54` 对」。

**那两个数都是真的，而且都是本件自己数出来的。**
`203` 是页面列出的 A+H 对，`149` 是**恒生沪深港通 AH 溢价指数的成分数**。
**差出来的 `54` 对是「不在那个指数里」，不是「不在通里」。**
指数另有市值、流动性、上市年限的门槛，**三条都与可达性无关**。

**为什么它躲过了所有检查**：两个数都对，减法也对，
**结果的量级也合理**（五十几对当控制组听起来很正常）。
**错的只有那个差的含义**，而含义不进任何一个断言。

> **判别式：一个筛选出来的集合，要问「这条筛选规则是不是我要的那条」，
> 而不是问「这个数对不对」。** 数对了正是它危险的原因 ——
> **一个真数用错地方不会报错。**

**同族三条，位置不同**：
- **范畴错误第六式**：判据的作用域与被测对象的作用域不重合；
- **失败模式 22**：一个字段两种类型而消费者只判真值；
- **本条**：**一个集合，两条筛选规则，而两条都产生合理的基数。**

**三条的共同解药还是打印对象**：把那 `54` 个代码印出来，
去逐个问「它在通里吗」，一眼就知道那不是通标的名单。
**印计数看不出来，因为计数是对的。**

---

## 失败模式 67：先决条件比它守的那一臂还贵，而排序看不出来，因为便宜的那一步长得像第一步

**B21 付的账，2026-08-27。**

第二层缺一份**互联互通标的名单**：三家交易所公布，**免费**。
于是这一臂看起来卡在一次便宜的采购上。

**推到底之后不是。** 这一臂的股票级内容全部在**买卖价差**里
（转手成本 = 公布费率 + 该股价差，而费率按笔不按股票）。
**所以在名单能派上用场之前，先要知道价差的跨股票离散够不够大**，
**而那要报价数据 —— 本站早先因为贵而搁置的那一类。**

**便宜那一步的正确位置是第二，不是第一。** 按原来的排序会先把名单取回来，
**然后才发现没有东西可以喂给它。**

> **判别式：一次采购之前，问「拿到它之后，下一步要什么」。**
> 下一步要的东西如果更贵，**这次采购就不是第一步**，
> 它是第二步，而第一步还没付钱。

**为什么这个排序天然会写反**：先决条件是用来**挡住**主实验的，
所以直觉上它排在前面；**而成本上它可能排在后面**。
**「逻辑上在前」和「成本上在前」是两个序，而它们不总是同一个。**

**与第 13 条第 4 步同源而位置不同**：那一条说花钱之前先把乘积写出来（四个已知数相乘），
**本条说的是先把依赖链写出来**，**看那条链上最贵的一环在哪儿**。
两条都是动手之前的一次算术，两条都不需要任何数据。

**这一轮的正面产出**：日线上估价差的那次跑**没有给出「够不够」，
给出的是「这个器具答不了这个问题」**，而那同样值回票价 ——
**它把一次看起来便宜的采购挡在了一次昂贵的采购后面。**

**改记 2026-08-27（同日）**：**本条的一般教训成立，本条在 B21 的实例不成立。**
那条依赖链的第一环写的是「要报价数据才判得了价差」，**而它判得了，不要报价** ——
内地的跳是固定的 `0.01` 元，`0.01 / P` 就是相对价差的精确下界（失败模式 68）。
**于是名单重新变回第一步，而且是唯一一步。**
**留着本条**，因为「逻辑上在前」与「成本上在前」是两个序这一点没有被推翻，
**被推翻的是那次对成本的估计**。

---

## 失败模式 68：一族器具全部失败，被写成了这个问题答不了

**B21 付的账，2026-08-27，而且是同一天里先写错再改对的。**

要量 A 股价差的跨股票离散。**四个器具，全部败**：

| 器具 | 怎么败的 |
|---|---|
| Corwin–Schultz (2012) | 每条腿压平 `40.7%` 的窗口 |
| Abdi–Ranaldo (2017) | **更糟**，`52.5%` 的月估计非正，中位腿读 `0.0` |
| Amihud (2002) | 不压平，**但对成交额秩相关 `-0.958`**，同一个测量做了两遍 |
| 零收益日占比 (Lesmond 1999) | 不压平，**但对 Amihud 秩相关 `+0.011`**，毫无关系 |

**第一次的裁定写的是「不可判，要报价数据」。那是把器具的失败写成了问题的性质。**

**四个一起失败之后才看出它们共有一条假设**：
**日内区间里含有价差的信息**。而 A 股日内区间两三百个基点、价差个位数基点，
**信噪比约 1:100，这一族器具在这里必然全灭。**

**写出那条共有假设，就能去找一个不用它的器具。**
内地两个板的最小报价单位是**固定的 `0.01` 元**，
于是价格 `P` 的股票，**相对价差不可能低于 `0.01 / P`** ——
**一条公布的规则加一次除法，精确、股票级、不可能返回负值。**
跨股票 `sd` `0.00099`，是要比的那个共同项的 `0.234`。

**地板只是地板这个缺口，也不用报价**：Harris (1991) 的末位数字聚集度，
只用收盘价。用满每个跳的股票 0/5 占比读 `0.200`；实测中位 `0.2219`，
`89/202` 落在均匀 ±0.02 内，**聚集度对对数价格 `+0.6882`、对跳地板 `-0.5009`** ——
**跳咬得住的地方正是地板高的地方**，那个反例被拒绝。

> **判别式：一族器具全部失败的时候，先写出它们共有的那个假设，
> 再去找一个不用那个假设的器具。**
> **在写出那条假设之前，不许把「不可判」记到问题头上。**

**与 `D26` 同源而更进一步**：`D26` 说宣布一个量不可得之前先问有没有一份文件写着它。
**本条说那份文件可能不写这个量本身，写的是一条把它夹住的规则** ——
**规则比数字常见得多，而且免费。**

**顺带一条**：本条用的正是**范畴错误第九式正着用**。
那一式说「固定绝对门槛 × 异质分布」会毁掉统计量；
**这里是同一个机制被当成信号源** —— 固定的跳 × 异质的价格，
**制造出的正是要找的那个股票级异质性。**
**一个失效模式反过来用就是一个器具。**

---

## 失败模式 69：三个理由按成本从贵到便宜依次被发现，而最便宜的那个是现成闸门本来就要问的

**B21 付的账，2026-08-27。本条不立新规矩，它记的是一条现成规矩没被跑。**

一臂的截面维死了三次，**而发现的顺序正好是成本的倒序：**

| 次序 | 死法 | 成本 |
|---|---|---|
| 一 | 控制组认错了：那批股票是**不在某个指数里**，不是**不在通里** | 一次查阅 |
| 二 | 流动性混杂：对数成交与对数溢价相关 `-0.5613`，四分位中位 `2.28× → 1.30×` | **一次跑** |
| **三** | **读资格规则**：「A+H 股」本身就是一个独立的合格类别，**203 对里 203 对合格** | **读一页网页** |

**第三个是决定性的，而且最便宜。** 它让前两个都变成多余 ——
控制组认没认对不重要，因为**根本没有控制组**；混杂大不大不重要，因为**没有对比可做**。

**而闸零（`D18`）本来就要问这一句**：「这个处理变量的取值，在这个观测单位上总共有几个？」
**答案是一。整臂在设计件的第一行就该结束。**

> **判别式：一个闸门存在不等于它被跑了。**
> **写完一臂的设计之后，逐条对着闸门表打勾，不要凭印象说「过了」。**
> 这一臂的设计件里写了「必须先过 `D25` 第 1 问」，**写得很显眼，而闸零一个字没提**。
> **被点名的那道闸会被跑，没被点名的那道不会。**

**代价可量**：一次查阅加一次全样本跑，换来的结论与读一页规则完全相同。

**与第 13 条同源**（测量站的开工顺序：先描述对象再做检验）：
那一条说的是**站内**的顺序，本条说的是**闸门之间**的顺序。
**两条的形状一样：便宜的那一步排在后面，于是贵的那几步白做。**

**顺带记一条正面的**：同一天里，闸零刚被加上一句
「否掉之后再问：这个处理变量在**别的观测单位**上变不变」。
**这一节就是那句话的第一次使用，而它当场把整臂救了回来** ——
换到「交易所 × 日期」这个单位上，沪股通 2014-11-17 与深股通 2016-12-05 相隔 749 天，
**两个事件把两组的角色对调，固定组间差被设计本身吃掉。**
**一句补丁写下去当天就回本。**

## 失败模式 70：结果变量找不到的时候去找结果变量，而该做的是把对象摊开逐项清点

**B21 付的账，2026-08-27。这一条是正面教训，记的是那个便宜的做法。**

一臂卡在「结果变量未定」上，卡了三节。**期间做的事是去找一个会动的量**，
而正确的动作是**把要测的那个对象摊开，逐项问「这一项与类有关吗」**。

**摊开只有五项，逐项问完花了一次推导加一次查费率表：**

| 项 | 类相关吗 | 靠什么判 |
|---|---|---|
| 价格 | **否** | 同一个订单簿 ⇒ 价格部分对两个类逐项相同，**代数上抵消** |
| 经手费 `0.00341%`、证管费 `0.002%`、过户费 `0.001%`、印花税 `0.05%` | **否** | **公布的费率表：这四项按笔收，与持有人是谁无关** |
| 换汇 | 是，**但没有下标** | 那是共同项，已量过 |
| **股息代扣** | **是，且有下标** | 法条定死并逐类公告 ⇒ **这就是那条已经跑过的臂** |
| 资本利得 | **是，未测** | 法条给定，落差大一个量级 ⇒ 新候选 |

**五项里三项当场归零，剩下两项一项已测、一项是新候选。整条线结束。**

> **判别式：找不到结果变量的时候，不要继续找。**
> **把那个对象写成它的各项之和，逐项问「这一项与处理变量有关吗」。**
> **逐项清点是有限的，找结果变量是无限的。**

**为什么这个顺序天然会写反**：结果变量是**要报的东西**，所以注意力先落在它上；
**而各项之和是对象的内部结构**，看起来像是推导完之后才要碰的东西。
**实际上它排在前面，而且它便宜得多。**

**同一次里顺手撤掉一句说错的话，值得记**：先前写的是
「拿溢价当结果变量，要先论证它为什么该动」。**溢价不缺那个论证** ——
它本身就是一个环和，标量价格场预言它是零，实测 30% 到 130%。
**它不能当结果变量的理由完全是另一个：它在两个类之间逐项抵消，
所以在指标部分里恒等于零。**
**「要先论证」和「代数上不可能」是两句完全不同的话，而第一句听起来更谨慎。**

**与失败模式 68 同族**：那一条说一族器具全灭时先写出它们共有的假设；
**本条说一个对象测不了时先把它拆开。**
**两条都是把注意力从「要报的那个数」移回「这个东西是由什么构成的」。**

## 失败模式 71：两列数并排看起来是同一种东西，减一下得到负值，而负值不是反号是"那一列不咬"

**B23 付的账，2026-08-27，开站第一天。**

处理变量是「母国居民付的股息税」减「美国 ADR 持有人付的协定预提税」。
手上两张表：一张**非居民统计预提率**，一张**协定组合投资者率**。相减，得到

```
比利时 25   瑞士 20   澳大利亚 15   …   中国 0   荷兰 0   印度 −5   英国 −15
```

**英国那个 `−15` 第一眼像是类差反了方向：ADR 持有人比本地人多缴十五个点。**

**不是。英国对股息根本不预提**，统计那一列在英国身上是 `0`，
而协定的 `15%` 是一个**上限**，上限在没有税的地方**从来不咬**。
**真实带宽是零。**

**所以负值与零值落进同一格：构造上不可判**，而不是一个反号的读数。

> **判别式：两列数能相减，不等于它们是同一种东西。**
> **相减之前问一句「这两列各自是谁对谁收的税」。**
> 负值出现的时候，**先怀疑其中一列在那一行上不是约束，再怀疑符号真的反了。**

**这一条是印对象抓到的**：把两列并排印出来才看得出它们不同源。
**只印那个差值，`−15` 就会被当成一个反号读数，而反号读数在本项目里是要回原稿的那一格。**
**一个假的反号会让人去改理论。**

**同族**：范畴错误第四式（共享分母造出符号）说的是分母造符号，
**本条说的是"上限"与"实际税率"混在一列里造符号。**
**两条的解药一样：把构成那个数的两半分开印。**

**顺带记一条正面的**：同一次里还捞到一个方向问题并当场结掉 ——
那张协定率表是**美国对外国居民**的，而要的是**母国对美国持有人**的，方向相反。
**两者是同一个数**，因为美国税收协定第十条第二款乙项的组合投资者上限对两个缔约国对称。
**这一句写进了结果件**，否则下一个 session 会以为整张表方向错了。

---

## 失败模式 72：单边基准窗吃趋势，而它伪装成一个五 sigma 的事件效应

**B21 付的账，2026-08-27。**

要量除息日附近的异常成交量，用的是「事件窗 ÷ 该股自身基准」。
**基准取的是除息前 `60` 到 `11` 天，整段落在事件窗之前。**

**于是只要成交量有趋势，这个比值就吃趋势**，而 A 股成交量二十年涨了几个量级，
**被比较的两个时期趋势还不一样**。读出来的 DiD 是 `+0.1580`，**`4.5 sigma`**。

**改成两侧基准**（除息前后各取 `60` 到 `11` 天，一阶抵消局部趋势）**之后**：
主效应从 `+0.1270`（`5.0 se`）掉到 `+0.0351`（`1.5 se`），**三分之二是伪影**；
DiD 从 `4.5 se` 掉到 `2.2 se`。

**抓到它的不是任何断言，是把剖面印出来**：
单边版的读数在**从 −10 到 +10 的每一个 lag 上**都偏低 `12%` 到 `24%`。
**一个真的除息日效应不可能在除息前十天就出现。**

> **判别式：事件研究的基准窗要对称。**
> **单边基准把「事件窗与基准窗之间的趋势」整个算进事件效应里。**
> **而它不会报错，它会给你一个漂亮的 sigma 数。**

**同族，位置不同**：范畴错误第四式说共享分母造符号；
**本条说的是分母与分子在时间上不重叠，于是时间趋势变成了效应。**

**这一条同时是第 13 条第 1、2 步的实例，而那两步被跳过了**：
先量最坏那一格、再跑描述、看描述有没有已经回答了问题，**然后才做检验**。
**跳过的代价是一个 5 sigma 的伪影差点被写成读数。**

## 失败模式 73：法条给了端点，判据把它读成了方向

**B21 付的账，2026-08-27，复查两条声明方向的失败时查出来的。**

一条臂声明：某个制度开通之后，隐含税率**应当上升**，理由是它放进来的那一类缴 `20%`，
而原来那一类缴 `10%`。

**实测下降。而复查发现，同一部法条里那个制度还同时放进另一类，
持有满十二个月免征（`0%`）、不满十二个月 `25%`。**

**所以边际持有人是 `{0, 10, 20, 25}` 的混合，法条给的是端点不是方向。**
**上升这个方向是分析者加的**，而它被写成了跑前声明，看起来像是从法条推出来的。

**混杂检查先做了，而且它确认了那个读数**：怀疑两个时期公司池不同，
做同公司内做差（两侧都有事件的 82 家），**同一个方向而且更大**（`−0.0701`，`−1.9 se`）。
**读数是真的，坏的是读它的那条判据。**

> **判别式：声明一个方向之前，把那条法条（或那个理论）能给的东西写全。**
> **给了端点就只能报端点；方向要另有出处。** `D5` 说判据里每个数字须有理论出处，
> **方向也是一个数**（它是符号），**同样要出处。**

**处置**：判据记 **VOID**，读数原封留档，
另立一条法条真能支持的（隐含率落在端点之内），过。
**这不是把 FAIL 改成 PASS** —— 原读数一个字没动，而 VOID 标记说明它为什么不能当裁定读。
**判别式是「改判据之后重跑，读数变了没有」，答案是没有。**

**同一次复查里的第二条，形状不同而病同源**：另一条判据写的是 `变化 < 0`，
**零宽度严格不等式画在估计量上**（第 11 条禁的形状，不管往哪边出都禁）。
实测 `+0.0351` 对 `se 0.0233`，**`1.5 se`** —— **离零一个半标准误的读数是三态中间格，不是反驳。**

**两条合起来**：
- 一条是**法条给了端点、被读成方向**；
- 一条是**方向有出处、但判据没有宽度**。
- **共同点：一个不确定的读数被写成了一个确定的裁定。**

**对照组**：同一个站里另外两条声明方向的判据都活着，**因为它们有宽度** ——
一条对着法条给的带（落价比 `[0.10, 0.20]`），一条对着代数给定的形状（单调且不越过一）。
**带与形状都有宽度，方向没有。**

---

## 失败模式 74：把一个税率当成一个数，而它在别的国家是一条累进表

**B23 付的账，2026-08-27，开站第二天，而且是在取任何数之前。**

一套办法在 A+H 上跑通了：**法条给两个类定死不同的税率，于是类差是一个精确已知的非零数。**
把它搬到 ADR 载体上，做法照抄：拿母国居民的股息税减掉美国持有人的协定预提税。

**搬不动，而且原因在原载体上看不见。**

**A+H 那四个税率全是源泉扣缴的固定数**（`0 / 10 / 20 / 25`）——
**不看持有人的其他收入、没有档、没有裁量，所以"边际持有人的税率"是一个数。**

**居民股息税不是。** 实测英国：对美协定 `15%`，居民 `8.75%` ／ `33.75%` ／ `39.35%` 三档。
**类差是 `−24.35` 到 `+6.25`，带宽三十点而且横跨零。闸二在任何 `n` 下都过不了，
方向也定不下来。**

**更彻底的一格是抵免制**（澳大利亚、新西兰的 franking／imputation）：
**居民拿到的股息带公司税抵免，有效税率可以是零甚至可退税。**
**那里"居民税率"这个概念本身不成立**，不是数字不对。

> **判别式：把一条在 A 载体上跑通的办法搬到 B 载体之前，
> 逐个输入问「这个量在 B 上还是同一种东西吗」。**
> **一个税率在一处是源泉扣缴的常数，在另一处可能是一张累进表，
> 而两者在纸面上长得一模一样，都叫「股息税率」。**

**这一条与失败模式 71 同一天、同一站、同一形状**：
71 是两列数看起来同源而其实一列是上限；**本条是同一个名字在两处指两种东西。**
**两条的共同解药是把那个数的构成写出来，不要只写它的值。**

**成本**：本条在**取任何数之前**跑完，代价是两次查阅。
**若不跑，代价是按带宽排好候选表、取完价格、然后发现英国那一列的带横跨零。**

---

## 失败模式 75：把一套办法搬到新载体，搬的是它的**税率**，而让它成立的是**分割**

**B23 付的账，2026-08-27，开站第二天，在取任何数之前。**

A+H 上跑通了一条臂：两条腿的持有人被税法区别对待，**在除息日的落价比上做同公司内差**，
读出边际持有人的税率之差。搬到 ADR 载体上，做法照抄，**于是去找各国的居民股息税率。**

**查到一半才发现前提塌了，而塌的不是税率那一侧。**

**落价比臂要的是「两条腿的边际持有人不同」。**
**A+H 满足它，靠的是分割**：A 股对国际持有人基本关着，**而且两条腿不可互转**。
**ADR 不满足**：ADR 可以注销换回本土普通股，**套利把两腿钉在平价** ——
**一个投资者能在两腿之间低成本移动，两腿就不可能有不同的边际持有人。**

**所以那十一次查阅不是难，是没有用武之地。**

> **判别式：搬一条臂之前，先写出「它在原载体上为什么成立」，逐条问新载体满不满足。**
> **原载体上最显眼的那个特征（这里是税率之差）常常不是承重的那个。**
> **承重的是那个不显眼的（这里是分割）。**

**本条 2026-08-28 在类差这一族上升格为 `D30`，坑留在本表，规矩管跑前那一问。**
`D30` 的可机读形式是**数价格**：一条读类差的臂，要求两个类**各自有一个价格**，
**而且这两个价格之间没有低成本的互换**。本表这一条是通用形状（搬臂之前先写出它为什么成立），
`D30` 是它在这一族上的那一句。

**四个实例，两正两反：**

| 载体 | 几个价格 | 可互换吗 | 结果 |
|---|---|---|---|
| A+H | **两个** | **不可**，两腿不可互转 | **臂成立** |
| 一般 ADR | 两个报价 | **可**，注销换回本土股 | **套利钉平价，臂死** |
| 融券出借与代替股息 | **一个** | 同一只股票同一个价 | **连第二个报价都没有** |
| `Regulation T` 对组合保证金 | **一个** | 同上 | 同上 |

**后两个是 2026-08-28 按 `D30` 在取任何数之前关掉的**，
**而它们的法条侧都是干净的** —— `Treas. Reg. §1.861-3(a)(6)` 把代替股息按底层股息定源，
Reg T 与 `FINRA Rule 4210` 的四个门槛全部公布。
**公布得清清楚楚而读不出来，这就是本条与「查不到数据」不是同一件事的地方。**

**同一次里还看清一件事，值得单记**：
**A 股与 H 股不可互转这个事实，在本项目里出现过两次，含义相反** ——
先前写的是**障碍**（不可互转 ⇒ 没有强制溢价收敛的套利环 ⇒ 溢价不能当结果变量），
本节读出来的是**使能条件**（不可互转 ⇒ 两腿有不同的边际持有人 ⇒ 落价比臂才成立）。

> **一个载体的性质对一条臂是障碍，对另一条臂可能就是它成立的全部理由。**
> **写载体性质的时候，写它是什么，不要只写它挡了什么。**

**与失败模式 74 同一天同一站**：74 是同一个名字在两处指两种东西（税率）；
**本条是同一套办法在两处靠两样不同的东西成立。**
**两条的共同解药是把「为什么成立」写出来，而不是把「做了什么」抄过去。**

**同日补一例，同一条**：失败模式 71 写完几个小时之后，**在代码里又犯了一次。**
`b23_treaty_index.py` 的第一版把「这个上限咬不咬得住」写成 `落差 > 0 且 统计率 > 0`，
**漏了「上限要低于税率才咬」**，于是印度（统计 `20%`、协定上限 `25%`）被当成有五个点的楔子。
**而同一批数手算的时候是对的。**

> **写下判别式不等于代码里不会再犯**：写文字的时候在想那个量是什么，
> 写 `if` 的时候在想那个表达式怎么写。**两件事用的是不同的注意力。**
> **凡是「上限／下限／门槛」这类量，代码里写成显式的 `min`／`max` 或
> `ceiling < rate` 这种带名字的比较，不要写成一个差值再判正负** ——
> 差值把「谁是上限」这个信息丢了。

---

## 失败模式 76：一个载体的结构条件完全对，而世界上它的总量不够

**B23 的接续格，2026-08-27，在取任何数之前结掉的。**

找一个「两条腿不可互换」的载体来搬 A+H 那条臂。**找到了，而且结构条件比预想还干净**：
中国 A 股公司的境外 GDR，**证监会规则上市之日起 120 天内不得注销转换，之后双向可转** ——
**每个项目自带一个由法条定死、逐项目有日期的分割期。**

**闸零过：这样的载体真的存在。然后把乘积写出来，四个已知数：**

```
项目数 20 × 分割期 120 天 ÷ 365 × 年付一次 = **分割状态下 6.6 个股息事件**
借同一器具的每事件离散：se = 0.234，闸二 1.645 × 0.234 / 0.10 = **3.8，差四倍**
要过闸需要 97 个事件，按这个派息频率需要 296 个项目，**而世界上有 20 个**
```

> **判别式：结构条件对不对，和这个结构在世界上有多少个，是两个问题。**
> **前者过了会让人立刻想去取数，而后者是一次乘法。先做那次乘法。**

**这一条是闸零（`D18`）的第二种形态**：`D18` 问的是**处理变量有多少个取值**，
**本条问的是符合这个结构的载体有多少个**。
**两者都是纯计数、零数据、跑前可算，而且都能一票否决。**

**同一次里还有第二条独立的否决理由，也值得记**：
**那个分割期里测的是 B21 已经测过的同一条边**
（外国持有人的 `10%` 对内地持有人），**B21 用 2,297 个腿-年测过，这里有 7 个。**
**就算闸二过了，它也不产出新东西。**

> **两条独立的否决理由各自足够，而它们是同一次乘法顺手看出来的。**
> **算成本的时候顺便问一句「这个载体产出的东西，和已有的那个站有多少重叠」。**

**成本对比**：本节是一次查阅加一次乘法。
**不做的话，代价是取二十个薄流动性 GDR 的价格，然后发现只有七个事件。**

---

## 失败模式 77：拉宽人群让处理变量能变，而同一个旋钮把要读的效果一起抹掉了

**A3g 付的账，2026-08-27。这一条把一个两年前登记的载体要求精确化了。**

一条判据两年读不出来，诊断写的是**人群太窄**：被测集合是生产层中心性
第 `87` 到 `100` 百分位的 `41.6` 个节点，**而处理变量正是沿中心性分散准入的**，
那么窄的带上它几乎不变，**所以必然读作零，而那个零不携带机制的信息。**
当时留的载体要求是：**下一个 carrier 的人群不能是单层的八分之一。**

**照做了，用现成的旋钮把人群从 `18.4` 拉到 `200.0`（生产层共 `180`）。结果是：**

```
stretch    2.0    3.0    5.0    6.0    8.0   12.0   20.0   40.0
外围三分位  0.0    0.0    0.0    0.0    0.8   13.2   38.4   60.0     ← 处理能变了
效果      25.83  23.27   6.20   0.67   0.09  -0.01   0.08   0.08     ← 效果没了
```

**外围三分位第一次进人群是 stretch `8.0`，而到那时效果已经掉了 `277` 倍。**

> **两个要求沿同一个旋钮位于相反的两端。**
> **判别式：一个「拉宽人群」的方案，先问那个旋钮除了准入还控制什么。**
> **如果它同时控制被读的那个效果，拉宽人群与保住效果就是一件事的两面，做不到。**

**这不是那条判据败了，是这个载体读不出它。** 记不可判，三态中间格。

**载体要求因此从「人群不能是单层的八分之一」精确成**
**「准入的分散与效果的存在，不能挂在同一个参数上」** ——
**后者可机读、跑前可查，前者不可。**

**与范畴错误第六式同族**（作用域不重合），**位置更前一层**：
六式说判据与被测对象的作用域不重合，**本条说想去修那个不重合，
而修它的工具同时改掉了被测对象。**

**顺带一条关于本会话自己的**：同一个会话里**第三次**写出零宽度判据
（前两次：`变化 < 0` 的符号检验、声明一个法条没给的方向）。
**这一次是给一条自己刚写明「报不判」的曲线挂了一条单调性检验**，
**在同一份文件里自相矛盾，而且它在零附近的噪声上翻掉。**
**写完就删了，但值得记：零宽度这个形状会反复回来，因为它写起来最自然。**

## 失败模式 84：回写打在生成物上，而生成它的那行代码没动，下一次复跑抹掉回写

`D20` 要求改判之后**同轮回写源件**。C1 这一轮触发了它：一个原本计划的第二半被闸零否掉，
三处措辞要改 —— `RESULTS.md` 的站点节、`docs/` 的站点件、以及 `results/` 里的记录。
**三处都改了，回写动作对三处长得一模一样。**

**前两处是手写文件，改完就成立。第三处不是。**
`results/c1_gwp_holonomy.json` 由 `experiments/c1_gwp_holonomy.py` 生成，
而那句被改掉的话是**硬写在脚本的字符串常量里**的。改记录不改脚本，
于是**下一次复跑把它原样写回去**，`scoped_and_not_opened` 整个字段消失，
`diagnostic_reason` 退回旧版。记录从 9,956 B 变回 9,178 B。

**发现它纯属侥幸。** 那次复跑是为了别的目的做的（确认盘上那份记录仍是刚才那一份），
**没有任何检查会报这件事**：脚本正常退出、四条判据照常 PASS、
文件存在且是合法 JSON。**回写被静默撤销，而所有诊断量正常。**

> **判别式：`D20` 说「回写源件」，而对一份由脚本生成的文件，源件是写盘器不是那份文件。**
> **回写之前先问一句：这份文件是手写的，还是跑出来的。**

**与第 22 条同源，而且是它的另一半**：那一条说「改记录不改写盘器等于没改」，
讲的是字段类型；本条讲的是**回写**。**两条的病灶是同一个** ——
生成物看起来和手写件一样可改，而它的可改性只维持到下一次跑。

**必要条件是混装**：一次回写同时落在手写件和生成件上。
如果三处全是手写的，这个坑不存在；如果三处全是生成的，第一次复跑就全暴露了。
**恰好是两份手写加一份生成，才让盘上留下「两份文件说 A，记录说 B」**，
而**记录是别人 import 的那一份**。

**代价这次是零**，因为复跑是顺手做的。**处置照第 19 条办**：
改的是写盘器不是记录，改完连跑两次验逐字节相同（`10,119 B`，两次同 sha），
并确认两个字段都在、四条判据一条没动。

---

## 失败模式 85：在没有公共坐标系的载体上找不一致，找到的每一条同时是覆盖差异

C2 的前三支判据全部死在同一件事上，而它们看起来是三个互不相关的错误。

| 支 | 声称测 | 实际测到 |
|---|---|---|
| 学分数守恒 | 绕环单位数不闭合 | **恒等于 1**。单位是挂在课上的标量，任何由它构成的比值 telescope |
| 「同送一门接收课 ⇒ 两门课等价」 | 等价关系不传递 | **什么都没测**。衔接声明的是 `v(送) ≥ v(收)`，不等式推不出等式 |
| Ferrers 2×2（`a→p, a↛q, b↛p, b→q`） | 关系不可用标量表示 | **两所学院开的课不一样**。A 教数学 B 教西班牙语 |

**共同病因是标识符的作用域，不是三个判据各自写坏。**
实测：`courseIdentifierParentId` 发送侧 972 个，出现在两所以上学院的 **0** 个；
接收侧 633 个，出现在两所以上大学的 **0** 个。**两侧的编号都是机构本地的。**

于是「同一门课」这句话在这个载体上**说不出来**。而每一个替代说法
（同送一门接收课、同一个 Ferrers 格）都把「这两所机构不一样」编码了进去，
**跨机构的不一致读数与覆盖差异读数因此不可分离** —— 不是难分离，是同一个数。

> **判别式：在一个载体上找不一致之前，先问「要说『同一个东西』的时候，用的是谁的编号」。**
> **那个编号如果是机构本地的，任何跨机构的不一致都同时是一个覆盖差异，读数不承载主张。**
> **这一问是纯计数，零数据，在设计判据的时候就答得出来。**

**它伪装得很好，因为中间那个统计量会给出 100%。**
本轮「两院以上的格里，两院送的课集合不完全相同」读回 **432 / 432**。
那个 100% 不是发现，是 ID 方案逼出来的：两所学院永远不可能送出同一个课 ID。
**一个恒真的统计量读回满格，看起来和一个极强的发现完全一样。**

**代价这次是零**，因为它在数了一次 ID 共享率之后就结了；
**不数的代价是 18.66 GB 全量加一整轮分析，产出那个 100%。**

**解药是换一个真有公共词汇的量，不是换一个更精巧的判据。**
本载体上 GE area 有（IGETC 的 `1A`／`3B`、CSU GE 的 `A2`／`C1` 是全州共用编码），
课程 ID 没有。C2 因此重写在 area 上：同一门课被不同接收系统记进不同的 area，
**那是一个有共同参照系的多值**，与 C1 里同一吨甲烷在不同标准下算 21 还是 84 同形。

**与第 12 条同源**（答案被自己的构造逼出来的臂不是臂），
**与范畴错误第六式同源**（判据的作用域与被测对象的作用域不重合）：
判据要说的是课程之间的关系，而可用的编号只在机构内部有意义。
**三支里没有一支是被阈值抓到的，三支都是把对象印出来抓到的**，
第一支是把比值展开，后两支是数了一下 ID 的共享率。

---

## 失败模式 86：接口对不认识的参数不报错，返回另一份完整而合理的文档

ASSIST 的 `transferability/courses?listType=` 对无效取值**不返回错误**，
返回 `listType 0`（CSU Transferable）那一份。2026-08-27 实测：
请求 `Cal-GETC`（真类型，token 拼法不对）、`F2016` 与 `F2025`（假 token，
是本仓自己那个宽容解析器从 `begin.code` 里误捞出来的）、以及正确的 `CSUTC`，
**四次返回同一份 418,699 字节，sha256 前 12 位同为 `21adc73a7c91`**。

**这比返回错误页坏得多。** 错误页会在解析时炸；这份文档结构完整、字段齐全、
课程数合理（483 门），**任何形状检查、任何非空检查、任何「解析出多少条」的
自检都会通过**。区别只在响应体自报的那一个 `listType` 数字。

**若照请求时用的 token 命名文件，盘上会出现四个名字挂同一份数据**，
而后续分析读到的是「这四类的课程集合完全一致」——
**一个恒真的结论，看起来像一个极强的发现**（与失败模式 85 那个 432/432 同形）。

> **判别式：一个接口如果对无效参数返回 200，那么请求里的参数不是数据的标签，
> 响应里的自述才是。写盘之前拿响应自己报的身份与请求的参数核对，不对就不写。**

**这里还叠了一层：请求方的 token 与响应方的自述不是同一种类型。**
请求用名字（`IGETC`），响应用数字（`3`），映射只在 `areaTypes` 那份词汇表里。
本仓第一次核对时按字符串比，把六个**本来是对的**类型全判成了「没认」。
**核对本身也要过一遍类型，否则它会把正确的报成错误的，比不核对更贵。**

**处置**：`honoured()` 拿 `areaTypes` 给出的 `areaType` 数字比响应的 `listType`，
不符就不写盘；`transferability()` 在开扫之前先取词汇表，
**请求的 token 不在表里就直接停**，不进循环。

**与失败模式 22 同源**（一个字段两种类型而所有消费者只判真值）：
**坏掉的是对象的身份，而所有诊断量正常。**

---

---

## 失败模式 78：反驳说「这个零可能来自惰性处理」，而去修人群，不去量处理

**A3h 与 A3g 一起付的账，2026-08-27。两站同一天，一败一成，差别只在仪器。**

一条零域判据读出零。**反驳是**：被测人群站在一条窄带上，处理变量在那里几乎不变，
**所以那个零可能只是处理什么也没做，什么都证明不了。**

**这个反驳是对的形状**——惰性处理给出的零确实不承载信息。**错的是去回答它的办法。**

**第一次回答（A3g）：修人群。** 用现成的旋钮把被测集合从 18.4 个节点拉到 200.0。
**结果是同一个旋钮把要读的效果一起抹掉了**，效果掉 `277` 倍，
**判据在合格的人群上读不出来。记不可判。**

**第二次回答（A3h）：量处理对机制做了什么。**
取只差那一项的两格，数**循环数变了的节点、总 `|Δcycles|`、最大 `|Δ净值|`**：

```
                 gate 通道   terms 通道
循环数变了的节点     19.4       16.8
总 |Δcycles|        74.0       85.6      ← gate 是 terms 的 86%
最大 |Δ净值|      6.27e+02   5.76e+02
```

**处理不是惰性的。反驳当场不成立，判据可读，而人群一个字没改。**

> **判别式：「这个零可能来自惰性处理」要用处理对机制的作用来答，不要用人群的位置来答。**
> **前者是一个直接的测量；后者是一个关于处理为什么可能无效的间接论证 ——
> 而间接论证要修的时候，修它的工具会连带改掉别的东西。**

**代价对比**：A3g 是一个十点网格、四十次建模、一份结果件，产出不可判；
**A3h 是两格相减，产出一条可读的判据。**

**A3j 同日把这两次相减跑遍那条网格，答案是反的：**

```
stretch      1.0    2.0    3.0    4.0    5.0    6.0    8.0   12.0   20.0   40.0
人群        18.4   24.2   41.6   66.4   98.8  128.8  138.8  153.2  178.4  200.0
比值       0.748  1.069  0.864  0.926  0.943  0.805  0.492  0.678  0.000  0.000
```

**最窄的人群上 gate 在动，最宽的两端 gate 一个循环都没改。**
**惰性发生在人群宽的那一端** —— 一条分散准入的规则，要有人被它挡在外面才有作用，
**而到 `178.4 / 200` 的时候几乎所有人都已经进来了。**
**「人群窄 ⇒ 处理惰性」这个推论不只是没根据，它的方向是反的。**

**顺带一条同源的**：那个反驳还附带一个归因 ——
诊断件把 gate 归给**外延边际**（改变谁交易）。**实测它的外延效应是 2.2 进、0 出，
而它改了 19.4 个节点的循环数** ——**gate 在这里作用在内涵边际。**
**而整条「人群交集会把外延效应筛掉」的担心，正是建在那个归因上的。**
**归因错了，担心也就没有对象。**

---

## 失败模式 79：说一条向前注册的判据「还没打过分」，而盘上已经有人打过

**A3g 与 A3h 一起付的账，2026-08-27，由 A3i 抓到。**

**A3-8′ 是 2026-08-13 向前注册的判据。** A3g 的第一节标题写「它为什么两年没跑」，
A3h 第三节写「打分跑在种子 5–9 上」，**两句都把这条判据说成此前没被打过分。**

**盘上有一份已发表的文档说的是相反的话。** `docs/a7_continuous_c.md`
2026-08-15 把它作为 `A7-A-4` 打过分，**十三处提它，判的是 FAIL**。
**`grep "A3-8′" docs/` 会全部返回。两站都没跑这一下。**

**违反的是第 20 条**，而第 20 条当时的 grep 清单是「站名、载体名、要测的那个量的名字」。
**判据名不在清单上，于是清单被遵守了而问题照样发生。**
**向前注册的判据天生是旧的** —— 它写下来的目的就是让以后某个站去打分，
**所以「以后某个站」已经存在的概率，比一个新站名高。**

**代价不是错的读数，两站的数一个字节都没错。代价是框架**：
两站都把自己写成「这条判据第一次被打分」，**于是都没有去读 A7 已经量出来的那件事** ——
而 A7 §11.3 写着一句两站都需要的话：**`The clause that fails is sign stability.`**

**A3-8′ 是两个子句的合取，而定理只管其中一个。** 一旦分开数（A3i，57 个点，四个载体）：

```
序（定理管的那个）    loop 格 > gate 格     54 / 57
稳定性（定理没管的）  loop 格跨种子同号      9 / 57
gate 格跨种子同号                            0 / 57
```

**找到它比犯它更值钱**：分开数出来的读数比两站各自的读数都强，
**而这个读数一直躺在盘上，只差一次 grep。**

> **判别式：捡起一条向前注册的判据时，先 grep 判据名本身。**
> **注册的日期越老，它被别人打过分的概率越大，而注册件自己不会知道这件事。**

**与失败模式 64、`D26` 同族**：**宣布一个东西不存在之前，先去找写着它的那份文件。**
64 是数据的形态（假设造出来的那一列是坏的，而记录说反了），
`D26` 是量的形态（报价里没有不等于没有），**本条是判据的形态。**

---

## 失败模式 80：脚本印的比值是对的，而它的两个操作数是手打进正文的，错了一天

**2026-08-27，A3j 顺手抓到的，代价是七份文件里十三处数字。**

A3h 的记录里 `mechanical_ratio` 是脚本算的：`74.0 / 85.6 = 0.8644859813084113`。
**而正文、`RESULTS.md`、坑账、`docs/a3_asset_channel.md` 里写的是 `72.4 / 84.2`。**
`72.4 / 84.2 = 0.8598`，**和印出来的那个比值对不上，而没有任何东西会把这两者对一遍。**

**86% 这个数从头到尾是对的**，因为它是脚本算完直接写进 `criteria` 的 `detail` 里的。
**错的是它旁边那两个手打的操作数**，而**比值对、操作数错**这件事，
**在任何一份文件里单独读都看不出来** —— 要看出来必须去读记录，或者像 A3j 那样
**在别的地方把同一个量再算一遍**（A3j 在 `stretch = 3.0` 上重算，`74.0 / 85.6` 精确对上）。

**判别式**：**一段正文里，如果一个数是脚本印的、而它的分子分母是手打的，
那这三个数之间没有任何东西在守。** 与失败模式 22 同族（一个字段两种类型而所有消费者
只判真值）：**坏掉的是对象，而所有诊断量正常。**

**便宜的解药**：**要引一个比值，就把脚本印出来的那一行整句引过来，不要拆开重排。**
一旦拆开，分子分母就变成手打的了。

**这也是渲染器那节那笔账的另一面**（记录侧棘轮 2026-08-21 废掉时数出来的）：
「`RESULTS.md` 不是手写的」说的是文件不是内容 —— **`name` 与 `detail` 一直是人打的字符串**。
**本条是同一句话在相反方向的实例**：`detail` 这一次是脚本填的，**手打的是正文。**

---

## 失败模式 81：`unavailable` 这一个词，同时写给「离线跳过」和「取数失败」

**B24 第一版写完到撞上，隔了不到一小时，2026-08-27。**

汇率那一段对每个币种试两种拼写，一个都没成就写 `{"how": "unavailable"}`。
**而到不了这一步有两条完全不同的路：**

```
--offline 跑，缓存里没有这个符号   → 跳过，一次网络请求都没发出
在线跑，两种拼写都请求失败         → 发出了请求，源没答
```

**两条路写出同一个词，而它们对下一个读记录的人是相反的指令**：
前者要的是「换个模式再跑一次」，后者要的是「源不给，换源或者换设计」。

**发现它靠的是外部信息**：记录里 11 个币种全 `unavailable`，
而**缓存目录里一个汇率文件都没有** —— 因为 `fetch()` 只在成功解析之后才写盘。
**是那个「零个文件」把两条路分开的，不是记录本身。**

**与失败模式 22 同族，也与 `cuba_segments` 里那条同族**
（「一个护栏，它的输出在『全查过』与『一个没查』之间无法区分」）：
**坏掉的是字段的身份，而所有计数量正常。**

> **判别式：一个字段，如果它对「查过而且没有」和「根本没查」写出同一个值，
> 那就没有任何东西在守它。**

**处置**：逐次尝试都进记录（符号、结果、拿到几根），
顶层记 `mode` 与 `network: {reached, unreachable, skipped}`，
并加一条判据 `B24-0` 专门印这三个数。**改完离线跑一次，22 次尝试全部读作 `skipped, offline`，
与 `unreachable` 不再撞车。**

**这一条便宜是因为它当场就被抓到了。** 若没抓到，
下一个 session 读到「汇率不可得」会去换数据源，
**而真相可能只是上一次跑带了 `--offline`。**

---

## 失败模式 82：池中位数把一个 4.6 倍的效应抵消成 0.9 倍

**B24 当天，2026-08-27。它没有咬到人，因为逐对那张表就印在旁边。**

**问的是：日汇率的截断时点错位，在这个方块里占多大。**
**做法是同一场所两对相减，共用的那条汇率序列精确消掉。**

**池中位数**：消掉汇率 `244` bp，带着汇率 `219` bp。
**照这个数读，结论是「汇率不是主项，消掉它还更大」。**

**逐对**：零时钟间隔那一对（多伦多 `TD−BNS`），消掉汇率把 `59` 压到 `12.8`，**`4.6` 倍**。

**两个都对。** 时钟间隔大的场所上钟差远大于汇率项，
**两对相减只是把两份钟差噪声加在一起**，于是池里那些行把零间隔那一行的效应盖过去了。

> **判别式：一个统计量如果在池里有异质的第二项，池的中位数读的是那个第二项。**
> **要读第一项，得先取第二项为零的那一格 —— 而那一格必须跑前指名，不能事后挑。**

**本站跑前指名了**：多伦多的钟差是 `0.0` 小时，写在设计件 ② 的地板表里，
**理由是两个交易所同一口钟，不是因为它读数好看。**

**与「读流不读汇总」（B7-13）是同一件事的另一个位置**：那一条是二十行里第三行就该停，
本条是十六行里只有一行携带信息，**而中位数按定义读不到它。**

---

## 失败模式 83：留档的那一行和现行的那一行共用一个键，于是自减出一个精确的零

**B24，2026-08-27。本仓两条自己的规矩撞在一起，而撞出来的东西长得像战果。**

**上一轮发现 `PBR` 配错了腿**（它是普通股 `PETR3` 的凭证，被配了优先股 `PETR4`）。
**按不删的规矩，错的那一对留在名单里照常印，正确的那一行加进来。这一步是对的。**

**而按受托代码做键的那个字典，第二行把第一行覆盖了。** 后果三样：

```
Sao Paulo   PBR-PBR    1068     0.0 bp    ← 同一条序列减它自己
Sao Paulo   PBR-VALE   1068   815.4 bp    ← 印了两遍，都用错的那条腿
```

**那个 `0.0` 出现在一张「小数就是结论」的表里。** 这张表的全部意义是
「消掉汇率之后离散有多小」，而 `0.0` 是它可能出现的最漂亮的数，
**它旁边真正承重的那一行是 `12.8`。** 扫一眼的人会读到一个完美的确认。

**修正之后**：键改成两条腿的组合；同一个受托代码对两条本土腿的配对**点名不跑**
（那是另一个问题，它的差不是两个 claim 之间的离散）；每一行的标签带上两条腿。
**正确的那一行读 `103.9`，错的那一行读 `815.4`，两行都在，标签分得开。**

> **判别式：凡是「留档的行」与「现行的行」共存于同一张表，键必须能把它们分开。**
> **否则留档这个动作本身会污染读数，而不删是对的，键才是错的。**

**这条是本仓两条规矩的交互，不是任何一条自己的毛病**：
不删（第 5 条）保证坏的那一行还在，而它就必须配一个能区分它的键。
**与失败模式 22、范畴错误第十二式同族：坏掉的是对象的身份，而所有计数量正常** ——
`n` 是 `1068`，两行都对。


## 失败模式 87：同一件事在对象上写了两遍，而读的那一遍是弱的那一遍　(four instances in one stage, every one silent)

**2026-08-27，C3 取数与解析。四次，形状完全一样，全部无声。**
每一次，被读的那个东西**自己身上有两处陈述**说同一件事，
代码读了弱的那处，而强的那处就在旁边。
**四次都不报错，四次的产物都在合理范围内，四次都只能靠把对象印出来发现。**

| | 弱的那处（被读了） | 强的那处（就在旁边） | 结果 |
|---|---|---|---|
| 一 | 目录列举说盘上有 34 份页面 | 内容哈希说其中 24 份是 12 份 | 每一行进 CSV 两次 |
| 二 | 表头第一行 `院校｜文科｜理科` | 第二行 `计划数 投档比例 投出数 最高分 最低分` 各重复一遍 | 山东整省的分数读成计划数与投档比例 |
| 三 | 文件名写 `广东_2015_arts` | `<title>` 写「2015广东一本**理**第一志愿组投档分」 | 理科的表整张进了文科那一格 |
| 四 | 整条标题里出现「征集」 | 出现在哪个分句里 | 江西的主表被当成征集志愿表扔掉 |

**第一例最值得单独说，因为去重是写了的。** 解析器按
`(province, year, track, name)` 去重，而那个 `seen` 集合**每读一份文件重置一次**。
输入集合里同一份内容出现两次的时候，**逐文件去重按定义看不见它**。
表面上一切正常：每省的条目数看着像真实表格的大小，省份覆盖看着是全的，
北京大学在湖南文科出现在第 0 行和第 182 行，**两行的分数一模一样**。
真正致命的是它对下游的影响：湖南、浙江那一批 `both` 页面的
文科与理科**是同一批行**，于是「两个科类互相复验」这条判据
**会以百分之百通过，而它是构造出来的**。
**那本来会是整个站点看起来最强的读数。**

**第二例的产物全部在合理区间**：山东一本读出 100、105、120，
三位整数，落在分数的量程里，比大小也自洽。
它是 `投档比例`（105 表示 105%）和 `计划数`。
**表头跨两行而读表头的代码假定它跨一行**，
第二行的五个子标题在两个科类下各重复一次，
真正的 `最低分` 在组内第 5 个位置上。
组宽不是猜的，是 `len(子表头) / 轨道数`，
数据行与子表头的宽度差就是名称列的偏移，**两个数一除就出来了**。

**第四例是同族里方向相反的一个**：前三例是漏报，这一例是误报。
`2015江西一本院校投档线公布 21日征集志愿` 是主表，
后半句是「21 日开始征集志愿」这条新闻。**拿整条标题去匹配关键词，
把主表扔了**。解药是把匹配限制在**带着分数名词的那个分句**上，
海南那份 `海南高考本科一批征集志愿平行投档分数线` 的关键词就落在分句里面，仍然命中。

> **判别式：一个属性如果在被读的对象上不止一处写着，先问哪一处是权威的。**
> 文件名是外面贴的，标题是页面自己说的；目录是外面数的，字节是内容自己说的；
> 表头第一行是版式，第二行才是列。**每一次都是外面那一层更容易读，所以先被读。**

**它和失败模式 86 是一对。** 86 是接口对不认识的参数返回另一份完整文档，
判别式是「请求里的参数不是数据的标签，响应里的自述才是」。
**本条把它推广到不是接口的东西上**：文件、页面、表格、目录，
凡是能自述的对象，自述压过外部标注。

**四次都不是被判据抓到的，是被印对象抓到的**：
第一次印了同一个院校在同一格里的两行，第二次印了山东表的前四行，
第三次印了每份文件的 `(文件名, 标题)` 对，第四次印了全部 34 条标题与匹配结果。
**这是第 11 条那条战绩的第 N 次重复，代价这次是零，因为在跑判据之前就印了。**


## 失败模式 88：把一个键翻成另一个键，而新键不唯一，赋值静默留下最后一个

**2026-08-27，E1。代价是头条数字掉一半，而且没有任何东西报错。**

手上有一张按**院校代码**建的表，每条带一个 985/211 标记。要用的那张数据只有
**院校名**没有代码，于是把前者翻成 `{名字: 标记}` 去 join。

```python
tier = {v["name"]: v["tier"] for v in home.values()}     # 坏的
```

**324 个院校名被多于一个代码携带，其中 49 个的标记互相矛盾。**
多出来的那些代码是同一所大学的中外合作、定向、专项等招生渠道，
它们各有自己的代码而 `is_985` 是 0；`上海交通大学` 挂在八个代码上，
`北京航空航天大学` 挂在两个。字典推导式是**后写的赢**，
于是 `北京航空航天大学` 读成 `other`，
**北京的 985 席位从每万人 690.9 掉到 342.5**，
而院校数、席位总数、覆盖率、所有其它计数量**一个都没变**。

**为什么它躲得过检查**：join 本身成功率很高（名字对得上），
少的不是行而是**那一行的一个属性**；掉下去的又正好是最有名的那批学校，
所以「未匹配名单」里看不到它们——它们匹配上了，只是匹配到了错的那条。

**判别式，动手之前一行代码**：

```python
c = collections.Counter(v["name"] for v in home.values())
dup = {n for n, k in c.items() if k > 1}
bad = {n for n in dup if len({v["tier"] for v in home.values() if v["name"] == n}) > 1}
```

**新键重复多少次，重复里矛盾多少次。** 两个数印出来，再决定归并规则
（这里是取最强的标记，不是取最后一个）。

**与第 22 式同族**：那一条是一个字段两种类型而所有消费者只判真值；
本条是一个键两种取值而消费者用赋值。**共同点是归并规则被写成了赋值，
而赋值的语义是「最后一个」，那从来不是任何人想要的语义。**

**与第 87 式的区别**：87 是同一件事在对象上写了两遍而读了弱的那一遍，
错在**读的哪一处**；本条错在**写进新结构的时候把多对一压成了一对一**，
源头两处都读了，是压的时候丢的。

---

## 失败模式 89：类差大到值得测，就大到让处于劣势的那一类不再以那个形式存在

**2026-08-28，一次纯文件检查的产物，在取任何数之前结掉的。**

按「同一个底层、两个不可互换的壳」去找载体，找到一个，**四要件全对**：

- 爱尔兰注册的 UCITS 基金收美国股息按 **15%** 预提（美爱税收协定），
  **卢森堡注册按 30% 法定率**，卢森堡 SICAV 一般不享该协定；
- 两只都挂牌有价，都有公布的 NAV 与 TER；
- **两个壳之间不存在转换机制**，申赎各进各的篮子，**没有把两个价格钉在一起的套利环**；
- 量级 **15 个百分点乘股息率**，标普 500 按 2% 股息率约 **30 bp／年**。

**结构条件全对。然后去数，发现劣势那一侧不存在。**

在美国指数上，卢森堡注册的产品**全是互换复制**
（`Amundi-Core S&P 500 Swap UCITS ETF`，`LU1135865084`、`LU0496786574`，
名字里就带 Swap），而一份 2026 年的标普 500 UCITS ETF 全表**一只卢森堡基金都没有**，
原文逐字："All funds above are Irish-domiciled UCITS vehicles"。

**原因就是那 15 个百分点本身。** 互换按 `§871(m)` 的 qualified index 例外拿 **0%**，
于是市场的反应**不是给卢森堡实物基金一个折价，是不再发行它**。

> **判别式：那个分割是被强加的，还是被选择的？**
> **被选择的分割，劣势那一侧会退出，于是可观测量是一个零计数，不是一个价差。**

**三个实例排成一条线：**

| 载体 | 分割由谁定 | 结果 |
|---|---|---|
| A+H | **资本管制强加**，两边都跑不掉 | **活** |
| 境外 GDR 的 120 天不得转换期 | **证监会规则强加** | **结构对**，死在总量（失败模式 76）|
| ETF 注册地 | **发起人选择** | **劣势那一类退出**，只剩互换复制 |

**与失败模式 76 的区别，两条一起用**：
76 问「符合这个结构的载体世界上有几个」，**本条问「其中处于劣势的那一侧还在不在」**。
**76 数的是总量，本条数的是被测的那一侧。** 两个都是纯计数、零数据、跑前可算。

**这一条同时给这一族画了一个天花板**：
**读得出来的类差，只能是小到没有人费事去绕开的那些。**
大的那些不出现在价差里，**出现在产品目录的缺口里**。
**而那个缺口本身是一个读数** —— 它说这条边的成本高到足以重排产品结构，
只是它不是这套器具要的那个读数。

**成本对比**：本节是三次查阅。
**不做的话，代价是去取两组 ETF 的日频 NAV，然后发现配对表是空的。**

## 失败模式 90：一个为估计精度设的门槛，副作用是改变载体的同调，而每个质量指标都朝好的方向动

**形状**：筛掉样本薄的单元，是标准做法，理由正当。而当被测对象是这个载体的**拓扑**时，
筛选同时改的是图，**被筛掉的边可能正是承载那几维环空间的边**。

**实例**：一份日内报价缓存，载体是「挂牌的日历价差」构成的图，节点是 outright 合约。
写盘器有一个 `--floor`，只保留状态数达标的价差，注册值 2000。

| floor | 边数 | `b1` | `rank(d1)` | harmonic 维 |
|---|---|---|---|---|
| 2000（注册值） | 295 | 212 | 212 | **0** |
| 1000 | 341 | 252 | 250 | 2 |
| 600 | 375 | 282 | 282 | **0** |
| 500 | 390 | 295 | 294 | 1 |
| 100 | 433 | 329 | 324 | **5** |
| 1（全量） | 449 | 344 | 339 | 5 |

**在注册门槛下 harmonic 空间整个是零维，而全量下是五维。**
那五维住在被筛掉的那 154 条边上，而它们正是样本最薄的边：
支撑最强的十条，状态数在 97 到 675 之间。

**没有任何东西会报警**：过门槛的边样本更足、估计误差更小、
每一个质量指标都朝好的方向动。坏掉的是被测对象的拓扑，而拓扑不在质量指标里。

**它还不单调**：600 那一档掉回零而 1000 是二。所以「门槛越低维数越高」这个直觉是错的，
中间有洞，**没有单调性可以拿来插值或者外推**。

**判别式**：**筛选前后各算一次 `rank(d1)`，两行。** 若两次的 `E − rank(d0) − rank(d1)` 不同，
这个门槛就不是一个纯粹的质量选择。

**成本**：本节是两次 SVD，秒级。不做的话，代价是在一个零维的空间上找一个非零的分量。

**与第十二式同族**：那一式说标识符的顺序错了而所有计数量正常；
本条说被测空间根本不存在，而分解出来的另外两块加起来正好是一，看不出缺了什么。


## 失败模式 91：判一个子空间是不是零维，用了三个代理量，三个都骗过人

**形状**：目标是一个维数。维数要算秩，而算秩看起来贵，于是先找一个便宜的代理。
**三个代理依次上场，依次失败，每一次失败都在下一个载体上才暴露。**

**实例**，同一族载体上的三次：

| 代理 | 说法 | 反例 |
|---|---|---|
| **边密度** | 稠密图填得满，稀疏图填不满 | 密度 `0.9264` 的载体候选非零，密度 `0.9980` 的归零。**差 0.07 而结论相反** |
| **chordality** | 弦图的 clique complex 可缩，所以维数为零 | **充分不必要。** 那个密度 `0.9264` 的载体非 chordal，维数仍然是 **0** |
| **`\|T\|/b1`** | 三角形数对独立环数的比，比值小就填不满 | 比值 `2.85` 的载体归零，比值 `3.38` 的载体维数 **5**。**比值更小的那个反而是零** |

**唯一站得住的充分条件是 `\|T\| < b1`**，因为 `rank(d1) <= \|T\|`。
它便宜（`\|T\| = trace(A^3)/6`，一行），而且**只能用来确认非零，不能用来确认零**。
其余一切情形，**算 `rank(d1)`**。边数在几千以内时 Gram 矩阵是 `E x E`，秒级。

**判别式**：**要一个维数就把维数印出来。** 一个代理量能不能替代它，
在下一个载体上才知道，而那时已经据它做过决定了。

**自检有现成的一条**：`rank(d0)` 必须等于 `V − C`。这一条不花钱，
而它当场抓到过一次实现错误（对宽矩阵做 reduced QR，拿到的 `Q` 是满秩方阵，
把整个空间投掉了，维数读成 0，而正确值是 5）。


## 失败模式 92：一个决定输出的取数参数，既不在脚本的默认值里，也不在口径文件里，只在一份设计件的正文中间

**形状**：一个 scan 有若干必填参数。有默认值的那些进了代码，
**没有默认值的那个只在当初写设计的时候记在正文里**。
下一次跑的人从数据本身反推它，反推出一个看起来完全合理、而且能跑通的值。

**实例**：一个 pcap scan 的 `--groups`，收的是 multicast 的 `dst_ip:port` 列表。
正确值是四个地址，A feed 与 B feed 各两个。
从盘上的流量普查文件按端口号反推，只能推出 A feed 那两个 ——
**普查文件里两条 feed 的地址都在，但没有任何东西说这两条要一起给。**

**结果**：抓包是 A/B 去重的，两条流各留一部分包，漏掉 B feed 少 **0.85%** 的包。
共同的 295 个 symbol 里 **259 个行数不同**。

**为什么它不报警**：`resolved 433 of 433`，全部解析成功；扫描正常结束；
输出格式正确；文件大小合理；自检八条全过。**每一个可见的信号都是绿的。**
它是靠与前一次跑的输出逐字段比对才现形的，而那次比对本来是为了别的目的做的。

**判别式**：**一个取数脚本的每个必填参数，值要么写进脚本的默认值，要么写进口径文件。**
两处都没有的，就是下一次跑的人要去猜的那个。

**处置**：按口径纪律，取数参数进 `data/SOURCES.md` 对应那一节，与来源 URL、下载日期同处。

**成本**：本节是一次 grep。不做的话，代价是一次全量重跑加一次事后对账。


## 失败模式 93：一个三路分解的第三块读到零，被说成「这里没有那个结构」

**形状**：`gradient + curl + harmonic` 三块正交。第三块为零维是一句**关于三角形填不填得满环空间**
的话，而它听起来像一句关于**有没有环**的话。**两者可以同时为真而互相无关。**

**实例**：一族流量网络上 `harmonic` 维恒为零（`rank(d1) = b1`，九个载体逐个实测）。
**同一批载体上，梯度部分只占 4% 到 18%，非梯度的部分占 82% 到 96%。**
把第一句话不带限定地说出来，读的人会以为这些网络的净流基本是可积的。**正好相反。**

**判别式**：**报一个分解的某一块时，把三块的份额一起报。**
一块的维数与一块的份额是两个问题，而只报维数的句子会被读成关于份额的句子。

**同族的另一半**：本仓另有一族读数报的是**环和不为零**（某个可实现的环上 `ω != 0`）。
那与 `harmonic` 维是两个对象：**环和非零可以完全住在 `curl` 里**，
而那正是 `harmonic` 维为零的载体上会发生的事。**两族读数不可互相引用，也不可互相反驳。**

**成本**：本节是一句限定。不做的话，代价是一句写进对外件的、方向正好相反的话。


## 失败模式 94：一个统计量复现了，而它被当成证据的那个形状没有复现

**形状**：一个主张说「关系是台阶不是梯度」。证据是**两个中位数之比** —— 有某个属性的一组
对没有的一组，差好几个数量级。**那个比值复现得毫无问题，而台阶不复现。**
**两点分辨不出台阶与梯度**，因为任何足够陡的单调梯度都给得出同样的比值。

**要分辨，需要边界对**：最穷的**有**该属性者，对最富的**没有**该属性者。
梯度下富的那个留存更多，台阶下穷的那个更多。**这一对是唯一能分开两种形状的比较。**

**实例**：逐节点冲击（5 种子 × 1000 节点 × horizon 40，每个节点一次完整跑）。
两点统计逐臂复现，两组中位数差 **20 到 3,568 倍**。
而边界对读成台阶只有 **11 / 25** 个种子-臂格，梯度 14 / 25，某一条臂 **0 / 5**；
**两类在财富序上连成一块只有 2 / 25 格** —— 它们是交错的，
所以在这个人群上两种形状本来就分不干净。

**后果比读错一个数大**：一个建立在那个形状上的外部核验站，
**在被核验的那一侧就没有对象**。它不是「不可判定」（没跑过），
也不是「违反预言」（外部那侧没测），**是站不该立**。
**登记状态时这三者要分开写**，否则下一轮会把它当成一个待重开的欠账。

**原判定不动**：产生那个两点统计的判据保持它的门槛、作用域与裁决。
被推翻的只是「这个比值可以当成那个形状的证据」这一步。

**判别式**：**一个形状主张，要问它的证据是几个点。** 两个点给不出形状，
只给得出一个比值；形状要边界对，或者要整条剖面。

**成本**：本节是一次逐节点扫描。不做的话，代价是去买一份外部面板，
来核验一个模型不产生的形状。

---

## 失败模式 95：一个对称的二值变量，名字听起来能承载方向，而它按构造不能

**这一次没有付账，是跑前一次查证挡住的。写下来是因为挡住它靠的是想起来去查，不是任何机制。**

**形状**：设计要一个**方向**（谁在上、谁在下、往哪一边跨），
而载体里那个听起来对得上的变量是一个**对称的二值**（同／不同、有／无、变／没变）。
**对称的二值按构造不含方向**，而它的名字含。

**实例（2026-08-29，XC03 的印度载体）**：设计要区分 anuloma（高种姓男娶低种姓女）
与 pratiloma（低种姓男娶高种姓女），因为整条臂的赌注就落在这两者的不对称上。
IHDS-II 有一个变量，文献里叫 `ICmarriage`，中文写出来是「跨种姓婚姻」，
**名字完全对得上**。它的实际问法是合格妇女问卷的一道题：

> `Is your husband's family the same caste as your natal family?`

**只记丈夫（户）的种姓，妻子的娘家种姓不独立记录，只由这道题倒推「同／不同」。**
`同／不同` 关于交换双方是对称的，**anuloma 与 pratiloma 在它下面同一个取值。**
25,070 对夫妇里 1,079 对跨界（5.82%），**这 1,079 对分不出方向，一对都分不出。**

**判别式，跑前零成本**：

> **设计要的是方向、序还是等级？是 → 去看载体里那个量的取值集合，
> 不看它的名字，也不看文献怎么称呼它。取值集合在交换双方的互换下不变，它就不含方向。**

**同族，位置不同**：

- **第九式（固定绝对门槛 × 异质分布）** 说的是门槛与分布错位；**本条说的是变量的对称群与主张的对称群错位。**
- **失败模式 91（用代理量判维数）** 说的是代理量与目标量的关系没被验证；
  **本条更前一步：这里连代理都不是，是同一个词指了两个不同的对象。**
- **范畴错误第六式（判据的作用域与被测对象的作用域不重合）** 是它的上位；
  **本条是那一式在「变量能承载多少信息」这一维上的实例。**

**这一次的处置，值得照抄**：撞上之后**分成两件**，不整条毙掉。
赋 `C` 只要 `(性别, 种姓)`，两个输入都在，**主设计活着**；
毙掉的只有那条要方向的**前置检查**，它换了一个用组份额做基准的可做形状。
**一个变量不够，先问它卡的是主设计还是某一个检查。**

**成本**：这一次是一次 fetch。**没挡住的话，代价是按一个不含方向的变量设计整条臂，
跑完才发现两个分支在数据下是同一格**（`D15` 可达性，跑前算得出来的那一类）。

---

## 失败模式 96：值标签表印得完整，而那一列一个有效值都没有

**这一次也没有付账，是在买数据之前读文档读出来的。写下来是因为文档里承重的那一行，
恰好是排版上最不显眼的那一行。**

**形状**：数据字典把一个变量的取值、标签、含义印得完完整整 ——
六个或七个类别，每个都有名字 —— **看起来完全可用**。
而同一节里有一行小字写着这一列的有效样本数，**那个数是 0**。
**读文档的人会去读值标签表，因为那是整节里信息最密的地方**；
`Based upon N valid cases` 那一行看起来像页脚。

**实例（2026-08-29，XC03 的印度载体）**：一份公开使用版的家户面板里，
两个种姓分类变量的值标签表分别印着七类与六类，一个标签不缺：

```
GROUPS:  1 Brahmin  2 Forward caste  3 OBC  4 Dalit  5 Adivasi  6 Muslim  7 Christian,Sikh,Jain
         99 MASKED BY ICPSR    25470   100.0 %
         Based upon 0 valid cases out of 25,479 total cases.
```

**七个类别的频数全部是 0，整列被遮蔽。** 另一个变量同样，遮蔽 99.8%。
**而同一份文件里的第三个变量（把最上面那一类并进第二类的六分类版本）整列可用**，
25,470 / 25,479。**能用的和不能用的印在相邻两页，长得一模一样。**

**判别式，读文档时零成本**：

> **先读 `Based upon N valid cases`，再读值标签表。**
> **`N` 是 0、或者远小于总数的，那一列就不存在，无论标签印得多好。**

**一般化，比这个实例更有用**：**公开使用版对准识别符做遮蔽是通例，不是这一份的特殊情况。**
所以在买或下一份公开版数据之前，**凡是「这个变量要是有就太好用了」的那种敏感变量，
先查它在公开版里在不在**，不要查它在问卷里问没问 —— **问卷问了，公开版可以不发。**

**同一节还有第二个形状，同源，一并记**：**文献里报的合成变量，不一定在数据文件里。**
同一轮里，本仓从该调查的官方分析文档核到一个八分类变量与它的八个份额，
**并把它写进了取数校验清单**，而它在三本 codebook 里**零命中** ——
它是分析文档里的派生量，数据文件里只有六分类那一个。
**判别式：校验清单里的每一个变量名，都要在数据字典里 grep 到，再写进清单。**

**同族三条，位置不同**：

- **失败模式 91**：判一个子空间是不是零维，用了三个代理量 —— **代理与目标的关系没验证**。
- **失败模式 95**：一个对称的二值变量按构造不含方向 —— **变量的取值集合缺主张要的那一维**。
- **本条**：**变量的取值集合印在纸上，而数据里没有。**

**三条合起来一句话**：**名字对、标签对、文档对，三样都不等于那一列有数。**

**成本**：这一次是三次 `pdftotext` 加一次 grep。没挡住的话，代价是按一个不存在的分层变量
写完整条臂的判据，**下完几个 GB 的数据、读进来才发现那一列是空的**。

---

## 失败模式 97：用元数据推「哪一轮在前」，而数据里三个量都说反了

**这一条是付了账的**：错误的方向已经写进两份文件才被抓到。抓到它的不是复核，
是一次为了别的目的做的自洽性检查。

**形状**：一份两轮合并的面板，把其中一轮的变量加了前缀。**哪一轮带前缀，是合并脚本的选择。**
而变量标签里带着问卷编号，**那些编号确实能分辨两轮的问卷**，于是很自然地拿它去推前缀的含义。
**推出来的是反的。**

**实例（2026-08-29）**：一份 2005 与 2011-12 两轮的家户面板，变量成对出现，
一个带 `X` 前缀一个不带。标签里的问卷号分别属于两轮不同的问卷册，
按它推出「`X` ＝ 第二轮」。**写进了设计件与需求书。**

**数据里三个量说的正相反，而且互相独立：**

| 量 | 读数 |
|---|---|
| 受访女性年龄，无前缀减带前缀 | 中位 **+7.0**，均值 +7.26，N ＝ 25,479 |
| 花名册年龄，同上 | 中位 **+7.0**，均值 +7.26，N ＝ 25,478 |
| 丧偶人数 | 无前缀 **1,837**，带前缀 **798** |

**7 年正是两轮之间的间隔；丧偶只增不减。** 三个都说无前缀那一侧是更晚的一轮。

**问卷号那条线索本身没有错**，错的是**把它当成前缀归属的依据**。
**两件事之间没有必然联系**：合并脚本可以给任何一轮加前缀。

**判别式，零成本，用在任何前后／先后判断上**：

> **不要用命名约定、问卷编号、文件名或文档里的叙述去定「哪个在前」。**
> **用数据内部一个单调的量去定**：年龄、任何只增不减的状态（丧偶、退休、累计计数）、
> 任何带日期的字段。**一次 median，就定死了。**

**为什么这条值得单列而不是并进第 96 条**：96 说的是**文档描述的对象在数据里不存在**；
**本条说的是文档描述的对象存在，而它的方向被读反了。**
**前者读出来是空，会立刻发现；后者读出来全是数，看起来一切正常。**
**一个把前后读反的面板，每一个描述统计都正常，每一条差分的符号都是反的。**

**处置照 `D3` 第二格（代码 bug 修正）办**：**两个方向的措辞都留档**，
在原处改字并写明推翻它的是哪三个读数，**不留删除线**。

**成本**：这一次是两份文件里的四处措辞。**没抓到的话，代价是整条前后差分的符号反号，
而所有的样本量、缺失率、边际分布都正常。**

---

## 失败模式 98：带值标签的数值列，转成分类之后再转回数字，98% 的值被静默丢掉，而剩下的那些看起来完全正常

**这一条是当场付账当场抓到的，而抓到它的是一个范围检查，不是缺失率。**

**形状**：`Stata`／`SPSS` 的数值列常常挂着值标签。读的时候把标签转成分类（`pandas` 的
`convert_categoricals=True` 是默认），列里就变成了字符串；再拿它 `to_numeric`，
**只有那些标签恰好是纯数字的类别能转回来，其余全部变成缺失，而且不报错。**

**实例（2026-08-29）**：一列受教育年数，15 个值标签里 13 个带文字
（`none, <1 0`、`5th class 5`、`Secondary 10`、`Bachelors 15`），
**只有两个是裸数字**（`13.0`、`14.0`）。两种读法：

| 读法 | 非缺失 | 均值 | max |
|---|---|---|---|
| 转分类后 `to_numeric` | **2,987**（2.0%） | **13.53** | **14** |
| 直接读数值 | **150,860**（99.9%） | **5.85** | **15** |

**错的那一版没有任何一处刺眼。** 均值 13.53 年在任何报告里都读得过去；
`max = 14` 也读得过去；**98% 缺失甚至有借口** ——
调查里本来就有大量只问部分人的题，高缺失率是常态。
**唯一暴露它的是「均值 13.5 而这是全国样本」这个常识**，
而常识只在恰好知道该国教育水平的时候才起作用。

**判别式，两条，都是机械的**：

1. **要数值就用 `convert_categoricals=False`；要标签就不要拿它当数用。**
   **一列不能既当标签又当数。**
2. **交叉检验**：同一列用两种读法各数一次非缺失，**两个数应当相等**。
   不等就说明有静默丢弃，**差多少就是丢了多少**。

**这一条与前两条同族，位置不同**：

- **96**：文档描述的列在数据里是空的。**读出来全是缺失，会立刻发现。**
- **97**：列在、方向反了。**读出来全是数，描述统计全正常，只有差分的符号反。**
- **98**：列在、方向对、**值被静默筛掉，而剩下的那批自成一个看起来合理的分布。**

**元判别式，管这三条**：
**读进来的第一件事是把非缺失数、取值范围、唯一值个数印出来，跟文档报的对。**
**三条里每一条都会在这一步现形，而每一条都能躲过后面所有的判据。**

**成本**：这一次是一次重读。**没抓到的话，代价是整站的教育那一维跑在 2% 的样本上，
而那 2% 是按「标签恰好是裸数字」选出来的，是一个和教育水平强相关的选择。**

---

## 失败模式 99：`XOR` 定义的处理变量，只在两个成分各占一半时才与成分正交

**这一条当天犯了一次，当天抓到。抓到它的是打印分组的构成，不是任何判据。**

**形状**：一个处理变量定义成两个二值的异或，`C = A XOR B`。
设计文档里写着「`C` 只由交互项识别，两个主效应各自被自己那一项吸收」——
**那句话是对的，而它只在回归里成立。**
一旦把 `C` 当成一个分组变量、把四格塌成两组去比较，**`A` 和 `B` 的主效应立刻混进来。**

**算一次就看得见**：设 `P(A=1) = p`，`P(B=1) = 0.5`。则
`P(C=1 | B=0) = p`，`P(C=1 | B=1) = 1 − p`，
**两者之差是 `2p − 1`。只有 `p = 0.5` 时 `C` 与 `B` 正交。**

**实例（2026-08-29）**：`A` 是一个占人口 **72%** 的类别，`B` 是性别。
`2p − 1 = 0.44`，于是两组的性别构成是：

| | 组成 | 性别构成 |
|---|---|---|
| `C = 0` | A=0 男 7,851 ＋ A=1 女 18,523 | **女 70.2%** |
| `C = 1` | A=0 女 7,476 ＋ A=1 男 19,785 | **男 72.6%** |

**而结果变量（个人劳动收入）的性别差极大**：零值占比两组是 30.5% 对 19.8%，
Gini 0.7928 对 0.6497。**第一次跑出来的「两个 arm 差别很大」，读的是性别，不是 `C`。**

**判别式，跑前零成本**：

> **处理变量是异或、或任何两个变量的非线性组合时，先打印每一组里两个成分的边际分布。**
> **构成不相等，这个分组就承载着成分的主效应。**

**处置**：**永远在完整的格表上做，用交互项识别，不塌成两组。**
上面那个实例里，正确的量是 `(A=0 女 − A=0 男) − (A=1 女 − A=1 男)`，
**它把两个主效应都差掉，而它等于 2 倍的 `C` 效应**（若 `C` 效应在两层内一致）。

**与范畴错误第十一式的关系**：那一式说处理变量的变异层级低于观测单位的层级；
**本条说处理变量与它自己的成分不正交。两者都让一个看起来干净的对比装着别的东西。**

**成本**：这一次是一次重跑。**没抓到的话，代价是把一个性别差当成处理效应报出去，
而所有的样本量、平衡性检查、和两组的描述统计都正常** ——
**两组的种姓构成确实接近**（72% 对 70%），**不正交的是性别那一维，而它没有被列进平衡表。**

---

## 失败模式 100：几个各自独立的归档放在同一个目录，解压工具把它们当成一个多卷包

**这一条骗过了两层验证，而拆穿它只要一次 `cp` 到三个空目录。**

**形状**：同一个目录下放着几个各自独立的压缩包。某些解压工具（`unar`／`lsar` 一族）
在读其中一个时会去同目录寻找同伴卷，**于是把几个无关的包认成一个多卷归档**。
**后果不是报错，是每一个包都印出别人的内容清单。**

**实例（2026-08-29）**：三个不同年份的文档包放在一个目录里。逐个列清单：

```
codebook 2010.rar  (4,857,642 B) : RAR 5 (3 volumes)   → 五个 2010 的 PDF
codebook 2014.rar    (846,111 B) : RAR 5 (3 volumes)   → 五个 2010 的 PDF   ← 假的
codebook 2018.rar    (727,025 B) : RAR 5 (3 volumes)   → 五个 2010 的 PDF   ← 假的
```

**三份清单一字不差**，而且三个都自称 `(3 volumes)`。
**解压出来也确实是那五个 2010 的 PDF**，所以「验证过了」这个感觉是完整的。

**把三个文件各自 `cp` 到一个空目录再列，真相相反：**

```
iso/a : RAR 5   → cfps2010*.pdf        ×5
iso/b : RAR 5   → ECFPS2014*.xlsx      ×5   ← 完全不同
iso/c : RAR 5   → ecfps2018*.xlsx      ×5   ← 完全不同
```

**`(3 volumes)` 这个标记本身就是被同目录的邻居造出来的。**

**判别式，一行命令**：

> **列一个归档的内容之前，先把它单独放进一个空目录。**
> **`(N volumes)` 这种标记在同目录有别的归档时不可信。**

**同族**：与失败模式 96（值标签表完整而列是空的）、98（`to_numeric` 静默丢掉 98%）一样，
**都是「工具给出了一个完整、自洽、看起来没有任何问题的输出，而那个输出描述的是别的对象」。**
**本条更狠一点：它的输出连内部一致性都是真的** —— 解压确实产出了它列出的那些文件。

**顺带一条不同的账，同一批文件上**：同一个包里有三个文件解压后是 **0 字节**，
而归档头里写着它们分别是 68,846、95,782、72,565 字节。
**换第二个工具（7z 16.02）更糟，它不支持这个格式，十个文件全解成 0 字节而不报错。**
**判别式与第 6 条同源：解压之后逐个比对文件大小与归档头里声明的大小，不相等就是没解出来。**

## 失败模式 101：一整站在问「这个事件之后会怎样」，而没有一条判据先问「这个事件是什么」

**形状**：一个预言说「X 发生之后，Y 会怎样」。设计把力气全花在 Y 上
（样本量、零假设、分层、对齐），**而 X 在这个载体上是不是那个 X，一条判据都没有问。**
**问它通常只要一次扫描，而且答案往往就在已经取到的数据里。**

**实例**（规划指标体系，2026-08-29）。预言是「一个领域从计划里退出之后，
它回来的概率随该领域的恢复年限下降」，也就是把「退出」读成一次能力丢失。
两轮工作全部花在退出之后的那一半：

| 花掉的 | 买到的 |
|---|---|
| 五期的域对齐，两套网格 | 可读退出 23，复现 3 |
| 取两份更早的计划原文，域从 42 扩到 84 | 可读退出 67，越过登记的样本量线 |
| 置换零假设四次（两边边缘全固定，999 抽） | 棘轮读数 8.6 到 10.2 个 sd，0/999 |
| 逐次换期的分层表 | 期与处理变量不正交 |

**而结清它的是一个从开站起就在盘上的列。** 每条指标都有目标值，
四个已完成的期都有实现值，**所以「退出前达标了没有」是一次扫描**：

- **25 次退出里 19 次退出前已达标，2 次未达标（比值 0.973 与 0.986），4 次不可判。**
- **恢复年限 ≥ 8 年那一桶 11 次退出，9 次达标，零次未达标。**
- **三次复现事件退出时也全部达标。**

**这个载体上的退出压倒性是任务达标之后从清单上划掉，不是能力丢失。**
预言要的是后者。**两者是不同的对象，所以整个预言在这个载体上没有可读的东西**，
与样本量无关，与对齐无关。

**代价不止是白花的两轮。** 那两轮里读出来的东西**差点被写成关于世界的话**：
「复现率对恢复年限读不出来」听起来像一个关于路径依赖的否定读数，
**而正确的定性是这里根本没有那个事件**。写错的那一版会让下一个人拿同一个载体再测一遍。

**与失败模式 68 同族而位置不同**：那一条是把器具的上限记到世界头上，
本条是把**事件的定义**记到世界头上。
**与失败模式 102 是同一站的两笔账，位置不同**：102 在取数侧（没有整理好的表就当成没有信息），
**它早一层，而且更常撞到**；本条在判据侧（取到了，而它不是要测的那个对象）。

**第三个实例，2026-08-29 同日，这一次问的是「`A` 是什么」。** 一份源论文把 Leontief
矩阵的漂移写成 `A(T+1) = (1 + Theta) * A(T)`，机制照着实现了，
**矩阵实测动了将近十倍（列和中位 `0.50 → 0.057`），而八个聚合量在五个种子上零方向**。
病因在调用方：路由矩阵**按行归一化**，所以那一步返回的行和绝对水平被整个丢掉，
`A` 在这个模型里只决定「分给谁」不决定「花多少」；
**而论文的 `q = (I - A)^{-1} d` 里 `A` 同时是路由系数与产出乘数**。
**跑前问一句「这两个 `A` 是同一个对象吗」就够了，成本零，而没有人问。****与本仓库为 B7 记下的那条也同族**：
那次花了一天，而结束它的三个计算全部是一遍扫描、零次抽样，在执行顺序里排在最后。
**两次的根因一样：设计跳过了描述对象这一步。**

**可执行的形状，成本一行**：

> **在数事件之前，先把事件逐条印出来看。**

不是抽样，不是检验，是把那 25 行并排印在一张表上。**它比任何一次抽样都便宜，
而且它在花钱之前。** 印出来之后如果多数事件不是预言说的那种事件，这一站就不必开。

**判别式，可机读**：一个预言的形式是「X 之后 Y」的时候，
**问「这个载体上被记成 X 的那些行，有没有一列能证明它们真的是 X」。**
有那一列就先扫它。**没有那一列，才轮到讨论样本量。**
## 失败模式 102：没有整理好的表，就当成没有信息，而正文里全是

**编号按记账顺序，位置按发生顺序：本条比失败模式 101 早一层，而且更常撞到。**
101 管的是取到的东西是不是要测的那个对象；**本条管的是根本没去取。**

**形状**：一份权威文件拿到手了，问的是「里面有没有我要的那张表」，答「没有」，
**然后收口**。而那份文件的**正文**里，要的信息一条不少地写着。

**实例（2026-08-29，规划文件的早期年份）。** 要的是历年计划各自提了哪些量化目标。
近年的文件把它们做成了带编号、带基期值、带目标值的专栏表，一取就是一张干净的表；
早年的文件没有那张表。**拿到早年文件的原文之后问的问题是「有没有那张主要指标表」，
答案是没有，于是判「这个载体在这些年份上不存在」。**

**而正文里有。** 换一个问法再取一次，两份文件分别读出 **33 条与 38 条**
针对期末的带数字目标，一条不少，**每条还带着原句**。
**可读的退出事件从 23 涨到 67，越过了这一站登记的样本量线，成本是两次提取。**

**表是信息的有损投影，而丢掉的那一维往往正是承重的那一维。**
这一次丢掉的是**措辞的强度梯度**。近年的表把每条指标压成一个二值标签
（政府必须做到／引导预期），**而早年的正文保留着原始的分级**：
同一份文件里，「预期为年均 7% 左右」「力争分别达到」「提高到」「达到」
与「确保……不低于」「控制在……以内」并存。
**那个梯度就是后来那个二值标签的前身**，它只活在正文里，
**而把它压成两档的正是「整理成表」这个动作。**

**所以本条的理由不是「聊胜于无」，是反过来的**：
**没有被整理成表的文本，信息维度比表高**，因为整理的人是为别的目的压缩的，
压掉什么由他们的目的决定，不由这一站的需要决定。
**报道也算**：一份新闻稿写「必须确保」和写「切实推进」，
在任何一张下游表里都会变成同一个格子。

**与 `D26` 的关系，这是本条单列的理由**：`D26` 说宣布一个量为零或不可得之前，
先问它有没有一份写着它的文件。**这一次 `D26` 通过了**：文件找到了、拿到手了、读过了。
**`D26` 问文件在不在，本条问读没读它的正文。**

**可执行的形状，一句**：

> **拿到文件之后，问「这份文件里有没有这个信息」，不要问「有没有这张表」。**
> **「没有那张表」这个答案的下一个动作是读正文，不是收口。**

**判别式，跑前零成本**：要宣布某个年份／某个来源上这个量不可得的时候，
**问自己「我读的是它的目录和表，还是它的正文」**。只读了前者，这个判定不成立。

**成本对照**：误判之后一次取数就翻过来了，**而误判本身差点把一条能走通的路记成天花板**，
并且那个天花板会被写成关于世界的话（「这个观测形态在那之前不存在」），
**下一个人读到它就不会再去看。**

## 失败模式 103：一次修改留下了备份，而正文一个字没改，于是「改过了」只活在交接件的一句话里

**形状**：做一次改动的标准动作是**先备份、再改、再写回**。中间那一步漏掉的时候，
盘上留下的是**一份与正文逐字相同的备份**，而交接件里写着「已改进某处，留档某某」。
**下一个读到交接件的人会把备份的存在当成改动落地的证据，而它不是。**

**这是所有失败模式里最难自己发现的一种，因为证据的形状与成功一模一样。**
文件在、时间戳对、命名规范、交接件有记载。**唯一的差别是那两份文件的内容相同，
而没有人有理由去 diff 一份自己刚建的备份。**

**实例（2026-08-29 查出，改动发生在四天前）。** 一份不发表的规矩文档里有一条判别式，
写在两处、措辞一严一宽。四天前的一次裁定把宽的那个措辞定为现行，交接件写着
「已改进那一格，留档 `<文件>.expired_<日期>_pre_<改动名>`」。
**实测：那份备份里的那一格与正文逐字相同，1160 字节，一个字节不差。**
判别式的新措辞在全文里出现零次。

**于是严的那一处原封不动地活了四天**，而它比现行判别式严得多。
四天后一个 station 照严的那一处判了一个机制「不该加」，
**而那个机制在原始论文里有整整一节、两个编号方程**，只是被后来的重组稿漏掉了。
**代价是一个正确的方向被自己的规矩文档否掉，并且否得看起来很合规。**

**判别式，一行**：

> **备份的存在不是改动落地的证据。声称改过某处之后，把备份和正文在那一处 diff 一次；
> diff 为空就是没改。**

**为什么这一条要单列而不是并进「改判之后同轮回写源件」那一条**：那一条要求的是**做**，
本条要求的是**核**。**两者失败的方式不同**：前者是忘了动手，后者是动了手而只完成了一半，
**并且留下了一个看起来像完成的痕迹**。前者靠提醒能防，后者只能靠核对能防。

**同族的第二个位置，同一天买的**：一份公共大件在两次调用之间被另一侧改了，
而写回没出事，靠的是**每次写回都重新读盘上那一份**，不是靠记性。
**「备份一次、读一次、写一次」这三个动作必须紧挨着，中间隔一次调用就是隔一个时刻。**


## 失败模式 104：用「和」比较两组，而组内分布是重尾的，于是比的是那一个最大的成员

**形状**：把一个群体按某个属性切成两半，各求和，比两个和。
**当组内分布重尾时，那个和约等于组里最大的那一个成员**，
**于是两组之差回答的是「最大的那个落在哪一半」，不是那个属性。**

**它伪装得很好，因为它可以是零例外的。** 五个种子全部同号看起来是最强的读数形状，
**而如果每个种子里的最大成员都倾向落在同一半，那个零例外就是那个倾向，不是机制。**

**实例（2026-08-29）。** 二十个产业按一个属性排序切两半，比两半的成员数之和，
**五个种子读到零例外**。换一个环境重跑，**符号整体翻转**，仍然是四比一。
两个读数都写进了记录，第二个还推翻了第一个。

**真因用一行查出来**：每个种子里去掉最大的那一个产业，再看两半之差。

| | 五个种子 |
|---|---|
| 环境甲，原始差 | −2, −19, −5, −2, −18 |
| **去掉最大的那个** | **−40, +8, −27, +29, 0** |
| 环境乙，原始差 | +11, +19, −13, +8, +7 |
| **去掉最大的那个** | **−10, −9, +24, −14, −13** |

**每一格都能翻。** 成员数在产业间是重尾的，一个产业带 20 到 38 而其余带 0 到 10。
环境乙那五个种子里最大的产业**四次落在同一半**，正好对上那四个同号。

**解药是换统计量，不是加种子。** 加种子只会把一个被主导的量估得更准。
这里换成**全部二十个单位上的秩相关**：秩没有量纲、单个成员最多占一个秩位，
**主导不了**。换完之后承重的那两个量在一个环境上零例外、另一个环境上四比一同向，
**而原来那个「零例外」的量两个环境都读不出方向，`|ρ|` 全部小于 0.29。**

**判别式，一行，跑在报任何组间差之前**：

> **把每组去掉最大的那一个成员，再算一次差。符号变了，那个差就是那个成员。**

**与本仓库已经记过的一条同族而更宽**：那一条说某个求和量「被少数几个极值主导」，
**当时看出来了，却只对那一个量做了检查**。
**这一条要求对每一个进入组间比较的求和量都做，而它只要一行。**

## 失败模式 105：可得性筛查跑在闸零之前，于是九次读之后才知道那个窗口只有八年

**`D18` 闸零的正文写着「排在全部闸门之前」，理由是它纯计数、零数据、能一票否决。**
**2026-08-30 一次两图载体的筛查把可得性排在了它前面**，先去查数据源，
**而那个载体的时间维在第一次搜索之前就算得出来。**

**实测的代价**：九次抓取、六类源头，走完之后才补算闸零 ——
中国城乡二元这个载体，两条腿并存的窗口是 **1985–1992，八年**
（1953–57 那五年市场腿无公布记录；1979–84 那六年的第二个价是常数倍，见失败模式 106）。
**以国家-年为单位上限是 8，换成省-年约 240，差三十倍**，
**而这两个数是纯计数，零数据。**

**第 13 条第 4 步说的正是这件事**：「先把乘积写出来，四个已知数相乘，不需要跑任何东西」。
**它此前只被用在算力预算上，本例说明它同样管取数预算。**

**判别式一行**：**要为一个载体去查数据源之前，先写出它的观测数上限，两问都问**
（`D18` 2026-08-27 那一款：以这个观测单位有几个取值，换一个观测单位呢）。
**上限算不出来，就不该开始查。**

**与失败模式 102 是一对，方向相反**：那一条是「没有整理好的表就当成没有信息」，
**本条是「有没有信息还没算，就先去找表」。** 两条都是把顺序做反了。

---

## 失败模式 106：两个价、两个名字、两张公布的表，而第二张是第一张乘一个公布的常数

**`D30` 说「数价格」，数到两个就过。它没说要问这两个数是怎么来的。**

**实例，2026-08-30**：1979 年中国把粮食统购价提高 `20%`
（六种粮食平均每百斤 `10.64` 元到 `12.86` 元，实际 `20.86%`），
**同时把超购加价从「统购价加 30%」改为「新统购价加 50%」**。
于是 1979–1984 年同一种粮食有**统购价**与**超购价**两个价、两个名字、两张公布的表，
**而 `P_超购 ≡ 1.5 × P_统购`。**

> **`D30` 第一款照字面是过的，而那里只有一个价。**
> 两个价之间的比值**按构造恒等于 1.5，环和恒为零**，
> **读它等于读那条加价规则。**

**这不是「套利把它们钉平了」**（`D30` 第一款管的是那件事，是事后的、经验的），
**是它们从一开始就没分开过**（事前的、构造的）。

**判别式一行，纯阅读、零成本、跑前可判**：
**能不能从其中一个价，加一条公布的常数或公式，算出另一个。**
能 → 它们是一个价。

**与第 11 条同源**：由公布规则定死的数不承载主张。
**与 `D26` 反向**：`D26` 说「宣布一个量不可得之前先找那份规定它的文件」，
**本条说找到那份文件之后还要问一句，它是不是把这两个量绑成了一个** ——
**同一份规则文件，一次救活一个载体，一次杀死一个载体。**

## 失败模式 107：一条规矩从「谁报这个数」推到「这个数报成什么形状」，于是它成了跳过「去看一眼」的许可

**2026-08-30 立了一条规矩，同日撤掉，中间隔了一轮对话。**

那条规矩说：一个量若由**造成隔离的同一方**报出，
**它报出来的通常是汇总与指数而不是逐笔水平**，故该载体判死。
它的证据是三个载体（中国城乡、东西德内德贸易、南非 homeland）在一轮检索里
**都只查到指数**，而三个活着的载体报价方都不是隔离方。

**推翻它的是一本书。** 那三个载体里最要紧的一个，其纸本年鉴的目录里有
**29 个大中城市的逐品种零售价格水平、各地区的逐品种收购价格水平**，
**出版者正是那个既隔离又报价的机构。** 前提为假。

**错的那一步很具体：从「谁报」推到「报成什么形状」。**
这两件事之间没有必然联系，**而中间那一步恰恰只能靠去看**。

> **于是这条规矩的净效果是给「不去看」发了许可**，
> 而项目里唯一管这件事的规矩（宣布一个量为零或不可得之前，先问它有没有一份写着它的文件）
> **全部内容就是「去看一眼」。**
> **一条能让人跳过它的规矩，比没有这条规矩更坏。**

**判别式，写给下一条要立的规矩**：
**这条规矩会让人少做哪一个动作？** 若那个动作是「去查一次」，**不要立它。**
一条跑前的零成本规矩，正当的作用是**告诉人去查什么**，
**不是替人预判查了会得到什么。**

**与失败模式 102 同族**（没有整理好的表就当成没有信息）
**与失败模式 105 同族**（可得性跑在计数闸之前）：
**三条都是在该去看的时候，用一个推理代替了看。**

---

## 失败模式 108：为了防住事后拟合，立了一条禁止修补理论的规矩，于是把「找到了机制」也一起禁掉了

**实例，2026-08-30，B30-7。**一条从对手理论借来当第二分支的预测没打中。结果件里写了一句：
用框架去吸收框架自己的失手，正是本站建起来要防的失效模式。

**这句是错的，而且错得有代表性。**它把判别式挂在**时间**上：这个解释是不是事先想到的。
按这条走，任何一门经验科学都得停摆，因为**大部分机制都是在观测之后才被找到的，
「找到机制」本来就是事后发生的事**。一条挂在时间上的禁令，
对正当修补和不正当修补一视同仁地禁，所以它唯一的净效果是**让人不去找机制**。

**真正把两者分开的，是另外两件事，跟时间无关：**

1. **修补引入的参数，是不是在被修补的那份数据之外测得的？**
   拿失手本身去拟合出来的自由参数，是加 epicycle。
   从别处独立测来的参数，是机制。
2. **修补之后，有没有多出至少一条能失败的新预测？**
   没有新预测的修补只是重述，它让理论的每一条陈述在形式上仍然可证伪，
   而理论的内核永远不挨打。**传统经济学的本体不受伤，靠的正是这个。**

**判别式，写给下一次要修补的时候：**
**参数在外面测的吗？修完多出能失败的预测了吗？**
两关都过就采纳，**不必问它是什么时候想到的**。
任一不过，那不是修补，是给内核加一层护甲。

**同一天的正例。**那次修补是把「本地物落在本地收入上」换成
「一个物的比值由它自己的投入构成决定，而有全国挂价的那一档被钉在 1」。
权重取自一份已公布的行业成本规则，三个投入比值各自测自**另一类**物品，
新预测是「落在投入区间之外的物，任何成本加权都产不出来」。
这条预测本可以失败，它没有失败：有全国挂价的一档 88% 落在区间外，没有的一档 35%。

**与失败模式 107 同族**（一条让人少做一个动作的规矩，比没有这条规矩更坏）。
107 让人跳过「去看一眼」，108 让人跳过「去找机制」。
**两条都是用一个程序性的禁令，替掉了实质工作。**

---

## 失败模式 109：承重的引语被译成英文写进结果件，原文和出处都不在，于是那句话谁也核不了

**2026-08-30 附注，写库时的一个操作冲突。**本项目的原子写模板里有一条断言，
禁止长破折号出现在正文里（文风约定）。**但 109 要求原文照抄**，而中文受访者的原话里
就可能带长破折号（实例：郎学红「返利周期集中在2—3个月」）。
**两条规则冲突时，109 优先：原文照抄，不许为了过断言去改别人的话。**
断言要放行「出现在引语块内的长破折号」，写库时人工确认一次它确实在引号里。
**把别人的原话改掉以迎合自己的文风，本身就是 109 要防的那件事的另一种形态。**

**实例，2026-08-30 审出。**B26 结果件里两条承重引语，一条是某方对那个焦点价「常态化、至少持续两年」的表态，
一条是 2024-04-22 客服对参与门店范围的说明，**两条都只有英译，没有原文，没有出处**。
同站的 B25、B26、B27 三个文件**一个 Sources 节都没有**。
本 session 的 B30 结果件也有同一个毛病：文件中段有一个 Sources 节，
之后又追加了六个顶层小节，**那六节的出处全部落空**。

**为什么这条比看上去严重。**译文是一次不可逆的有损变换。
「常态化」译成 normalised 之后，读者无法判断原话是承诺、是描述还是宣传语；
客服那句的时态和范围在中文里是明确的，英译之后全丢。
**而承重引语正是全站最需要被人核的那一句**：它通常就是判据的那一半。
一条核不了的引语，在证据上等于没有。

**追加式写作会自动制造这个洞。**Sources 节写在当时的文件末尾，
下一次追加把它埋进中段，之后每一节都默认没有出处，
而且**没有任何东西会报错**。

**判别式，写给每一次引用：**
1. **非英文来源的引语，必须带原文。**译文可以并列，不能替代。
2. **每一条引语必须能被定位**：URL，或文号加日期，或刊名卷期页。
3. **Sources 节永远在文件末尾**，追加新小节时先把它移到末尾再写。
   文件中段出现 Sources 节，本身就是这个洞已经发生的信号。

**与失败模式 102 同族**（没有整理好的表就当成没有信息）：
两条都是**把一次有损的中间处理当成了原始材料**。

---

## 失败模式 110：审计时按自己预期的形式去找证据，找不到那个形式就判定证据不存在

**实例，2026-08-30，同一次出处审计里连犯两次。**

**第一次。**两个面板的捕获日没有逐项记录，当时判为「补不回」。
**实际上日期是有界的**：读数发生在一个有日期的工作会话里，会话本身和文件备份就把它夹住了。
一个是 2026-08-29 至 08-30，一个是 08-29 09:21 之前。
**而对一个日更的目录和一组一年动几次的国际标价，一天的界都够用。**
判成「不可恢复」不但错，还差点导致两次没必要的重读。

**第二次。**审计脚本按 `http`、`doi`、期刊名去 grep B25，判定 GDP 序列无出处，列进「拦结论」的欠账。
**实际上文件正文第二节写着**：*"Nominal GDP per capita is IMF World Economic Outlook, April 2026."*
价格侧也写着 *"reported by Deutsche Bank (2025-09-20) and were read here from a
secondary compilation"*，还自己加粗警告了「引用到别处之前必须去拉原始来源」。
**两个出处都在，只是以散文形式在，不以 URL 形式在。**

**两次的形状是同一个：拿一个预期的形式去检索，没命中就当成没有。**
而检索器本身不会报「我只查了这一种形式」。

**这条尤其阴险，因为它的产物是一个看起来很负责的动作。**
判「不可恢复」「无出处」听上去比判「有」更严格、更审慎，
**于是它绕过了本该有的那一次核对。**过度定性和过度宽松一样是错，只是它伪装成美德。

**判别式，写给每一次审计：**
1. **在写下「没有」之前，问一句「它会以什么别的形式在？」**
   出处可以是散文；日期可以由容器界定；数据可以在正文里而不在表里。
2. **判「不可恢复」之前，先问「有没有一个更粗但够用的界」**，
   以及**那个界对这个量的变动速度够不够细**。够就闭账，不必回头补。
3. **审计的产物如果全是坏消息，先怀疑审计器而不是被审对象。**

**与失败模式 102 同族**（没有整理好的表就当成没有信息）
**与失败模式 107 同族**（一条让人跳过「去看一眼」的规矩）：
**三条都是用一个自动的推断，替掉了那一次实际的查看。**

---

## 失败模式 111：给两个量词不同的主张开同一把反证的尺，于是把不是反例的东西写成了反例

**实例，2026-08-30。**合并设计件 §1c 论证「供需给的是梯度不是势，
所以均衡价格没有实例」，然后写了一条反证：
同一个物的两个互不通消息的市场，起点不同而最终停在同一水平，则本侧的路径依赖读法错。

**给多了。**两侧主张的量词不同：

| | 主张 | 被什么杀死 |
|---|---|---|
| 全称主张 | 符合条件的**每一对**都落在那个结果上 | **一类有据的反例** |
| 非全称主张 | 那个量**不由 X 单独决定** | **系统性地证明它被 X 决定** |

**一对吻合对非全称一侧是无信息的**：两个起点可能碰巧同侧，
或者碰巧锚在同一个第三参照上，或者被同一条法规强制。
**要用吻合来反证，先得给出机制、排掉这些。**

**为什么这条特别容易犯。**写反证的时候，人会去追求「显得公平」，
而最省事的显得公平就是给自己开一条和对手一样宽的口子。
**但那不是公平，是把两个不同形状的主张按同一个模子裁。**
结果是把一个无信息的观测挂上了「这能杀掉我」的牌子，
**下一次真看到那个观测的人，会据此撤掉一个本来没被反证的结论。**

**判别式，写给每一条要写下来的反证：**
1. **本条主张是全称还是非全称？**全称写「一类反例」，非全称写「系统性证明」。
2. **这个观测在多少组独立载体上出现才算数？**一组还是一批，写出数量级。
3. **有没有第三个解释能同时产生这个观测？**有就先排掉它，否则它不是反证。

**与失败模式 110 同族**（按预期的形式找证据，找不到就判不存在）：
**两条都是把一个程序性的姿态当成了严谨本身。**
110 是判「没有」显得审慎，111 是给自己开宽口子显得公平。
**审慎与公平都不是靠姿态成立的，是靠对不对成立的。**

### 第二次犯，2026-08-31，形状不同：量词不同的两个命题被合成一条前置条件

**实例。**B30-22 第二块查 §4.14 的前置条件「确认意外」，
拿到「捷克斯洛伐克 1993 那次分币被充分预期」的证据（两周内央行外汇储备流失 43%、
货币安排条约自带以资本转移为触发的解散条款），**判前置条件不通过，载体降级。**

**错在把两个命题合成了一条：**

```
命题甲   「惯例要变」被预期        证据支持
命题乙   「惯例变成什么样」被预期   根本没测
```

**而要识别的对象是程序，所以门槛应当是乙不是甲。**
甲是水平方向的信息：它说钱会变毛，**它不说贴花规则、按人限额、五天通知、
支付冻结、按所在地归属这一整套长什么样。**
**更要命的是那 43% 跑在另一条边上**（koruna 兑硬通货），
**而本臂要读的是跨境相对价格与 CZK/SKK。在第一条边上站好位，对第二条边一个字都没说。**

**重裁之后乙通过，载体回到可用的一侧。**关键证据是：分割时两边都 1:1，
**如果市场事前把条款定了价，弱的那一方不会以平价开出**；
贬值 10% 发生在五个月后一个独立的行政动作上。

**与第一次犯的共同结构：**第一次是给两个量词不同的主张开同一把反证的尺，
第二次是给两个量词不同的命题设同一道前置条件。
**两次都是量词被抹平，而抹平的方向都是让自己少做一步。**
第一次少的是「排掉第三解释」，第二次少的是「分开测方向与测内容」。

**判别式，追加一条：**
4. **任何一条写着「确认某某没被预期」的前置条件，必须写明预期的是什么的哪一个属性，
   以及那个属性落在哪条边上。**
   **「它会变」和「它变成这样」是两条前置条件，不是一条。**
   **落在别的边上的预期，对本条边的读数不构成污染。**


## 失败模式 112：逐位复现是一道同机器的闸，拿它跨机器用，它会在极少数格上响，而那不是代码错了

**实例，2026-08-30，A18 的停泊网格。**新加了一个默认关的开关，
按第 19 条在 Windows 上重跑全量 430 格，产出与加它之前的记录**逐字节相同**，闸过。
随后在 Linux 沙箱上抽十二行复算做个二次确认，**十一行逐位对上，一行对不上**
（`circulating_close` 610.645152 对 610.366496，差 0.05%）。

**第一反应是找代码里的错，而错的是那把尺。**
两侧不是同一台机器，`numpy` 的 BLAS 也不是同一个。
本文件「派生文件的写盘纪律」第 5 条早就写着**「不同 BLAS 构建之间末位会差」**，
**而那一条被当成只管写盘格式，没有人把它用在读数上。**

**放大倍数量出来了，是十个数量级。**把那一格的输入扰动 `1e-13`：

| 扰动 | `circulating_close` |
|---|---|
| 0 | 610.366496 |
| `+1e-13` | 611.587750 |
| `−1e-13` | 603.777204 |

**输入动 `2e-13`，输出动 `1e-2`。** 同一时刻测的另一格（`need=0.05`）
在同样的扰动下**六位数字一个不动**。

**不稳定的格不是散的，是一个角，而且方向讲得通。**
在 `need × rate` 上逐格数（每格 9 个抽样）：

| `need` \ `rate` | 1.0 | 2.0 | 4.0 |
|---|---|---|---|
| 0.05 | 0/9 | 0/9 | 0/9 |
| 0.20 | 1/9 | 0/9 | 0/9 |
| **0.50** | **7/9** | 1/9 | 0/9 |

**深底 ＋ 弱补给 ＝ 一堆节点贴着生存线站着**，末位差决定谁跨过去，
而跨不跨是个离散事件。**浅底或强补给的格全部纹丝不动。**
这是本文件第九式（固定绝对门槛 × 异质分布）在数值这一侧的同一件事。

**三条操作：**

1. **第 19 条的逐位比对，两侧必须是同一台机器。**
   那道闸问的是「这次代码改动改了读数没有」，**换机器就同时换了两个变量**，
   它答的就不再是那个问题。**闸本身没有问题，用错了地方。**
2. **跨机器要复核，就复核不敏感的那些格，并且先把敏感的挑出来。**
   挑法零数据、零思考：**输入扰动 `1e-13`，输出动不动。**
   不动的格跨机器可比，动的格不可比。
3. **敏感格的单格数值不要单独引。**
   那个数是这台机器的性质，不是这个模型的性质。
   **聚合量（跨格的均值、符号计数）照旧可引**，因为它们不落在那一格上。

**与失败模式 106 同形，位置换了一层。**
106 是两个数看着独立而第二个是第一个乘一个公布的常数；
**本条是两个数看着可比而它们出自两台机器。**
两条都是**把一个约束条件当成了背景，于是没去核它。**

**还有一把更好的尺，2026-08-30 用过一次。**
要核的是「这次代码改动改了读数没有」，那就**别去比两个文件**，
**把改动前那份装成一个独立包，同一个进程里新旧两个模块跑同一批配置，逐元素比对序列。**
同进程同 BLAS，**跨机器那个自由度根本不存在**，于是敏感格也参加得了比对。
实例：`run()` 改成生成器薄壳那一次，15 条序列、4 组配置全部逐元素相同。
**能这么做就这么做；只有拿不到改动前那份代码的时候，才退回去比文件。**

**判别式一句话：这两个要比的数，是同一台机器上算出来的吗。**
不是 → 先跑那个 `1e-13` 的扰动，动了的格不参加比对。

## 失败模式 115：把方差解释率当成信息含量。这两个量之间差着一个绝对标尺

**【2026-08-31 改号】本条原写作 112，而 112 号已被「逐位复现是一道同机器的闸」占用，两条同为 2026-08-30 立，两个 session 各取了一次号。113 与 114 已占，故本条退到 115。**改号前后全仓引用本条的地方是零处**，所以这次改号不动任何引用。**它在文件里的位置不动**（本表本来就不严格按号排，110 的附注也排在 114 之后）。判别式见 `双图_模型侧可行性_v1.md` §34.4：**往按号编的表里加条目之前，先读现有的最大号，不要按记忆取号。**

**实例，2026-08-30，B30-17 自己抓到的，抓的是本项目自己的工具。**

判别一原来的操作形式是「做 SVD，数秩，看前 k 个因子解释多少方差」。
国债 CMT 曲线上：**三个因子解释水平方差的 99.75%。**
按方差解释率的读法，这条曲线就是三个数。

**但把残差换算成基点，对着财政部实际印刷的精度比：**

```
公布网格         1 个基点（利率印到小数点后两位）
均匀舍入下限     水平 0.2887 bp，日变动 0.4082 bp
三个因子后的残差  水平 6.87 bp  =  下限的 23.8 倍
                日变动 1.26 bp =  下限的 3.10 倍
掉到下限以下需要  日变动 k=8，水平几乎要满秩 11
```

**99.75% 和「携带三个数」是两句不同的话。第一句真，第二句在公布精度上假，
而且差了将近三倍到八倍。**

**机制。方差解释率是无标度的，它只跟这份数据自己的总方差比，没有外部参照。
一个量的方差可以极小，同时仍然远大于「这个系统能表达的最小单位」。
低秩读数要的是后者，而方差解释率量的是前者。**

**规则：**

> **报残差对一个写明的下限，永远不许单报方差解释率。**
> **下限必须来自载体自身的可观测精度**（印刷位数、报价最小变动、焦点价网格），
> **不许假设，不许从数据里估。**

**追溯后果，同日执行：**B30-16 报的是航线内 R²，没有绝对下限。
**它的 0.41 因此不能支撑任何关于「一条运价报价携带几个数」的陈述**，
只能支撑「航线特征解释不了那个价差」。
航空票价的网格比一个基点粗得多，下限是存在的，只是没算。
**B30-16 各块降级为方差份额的测量，信息含量的主张暂缓，直到那个下限被算出来。**

**这条失败模式的来源值得单记：它是本项目第一条由自己的否定结果抓出来的失败模式，
而且它让自己的结论变弱而不是变强。**


## 失败模式 113：在一个机制本来就不起作用的构型上验「两支都到得了」，验过了也是空的

**实例，2026-08-30，双图边界那一站。**第 12 条要求付钱之前先枚举这条臂的输出，
**确认两种结局都到得了**。照做了，而且看起来是好消息：
额度不设时撞零轮、设成历史值时撞 106 到 226 轮（共 300），
**两支都到得了，历史参数还落在中间，一切都对。**

**那一轮是在两张同规模同参数、只差种子的图上跑的。**
**那种设定下跨界净额本来就是零附近的噪声**，
**于是「额度咬不咬得住」测的是噪声的幅度，不是这个机制。**

**把不对称建进去之后，那个「两支都到得了」当场消失。**
实证早就写着这一对是不对称的（内德贸易占西德外贸 5.1%、占东德 9.4%，
Swing 存在正是因为一侧持续逆差），**而那一条没有被建进构型。**
建进去之后只剩两个态：咬得住时本图读数与「边界根本不存在」**逐位相同到小数点后四位**，
咬不住时与「不设额度」逐位相同。**中间那一段不存在。**

**判别式，三问，跑可达性探针之前过：**

1. **这个探针里，被测的那个机制在做事吗？** 印一个它自己的量
   （这里是跨界净额的量级对本图存量的比），**看它是不是零附近的噪声。**
   是 → 这个构型验不了任何东西，先修构型。
2. **构型里有没有漏掉一条已经查过的实证性质？**
   这一次漏的是不对称，**而它写在同一份件的上一节里。**
3. **两支之间有没有中间态？** 只有两个态而中间是空的，
   **通常说明那个开关不是在调节，是在开关一个更大的东西。**

**与失败模式 11 同族而位置不同**：那一条说判据不要卡在估计量上；
**本条说探针不要跑在机制睡着的构型上。**
**两条都是「检查通过了而它什么都没检查」，这一族最贵，因为它看起来像纪律被遵守了。**

**便宜的那一半要记住**：本条是两个小时的探针换来的，
**而那些探针最后给出的是这一站的答案，不是「挡下了这一站」** ——
写成「挡下」会让下一个人以为那是一次止损，
**实际上是那几格探针把承重的问题问完了，全量再跑一次买不到任何东西。**
**探针跑错构型的成本，仍然远低于不跑探针。**


## 失败模式 114：一个恒等式还原出的正好是源头的构造输入，于是它什么也没验证，而它看起来像验证

**实例，2026-08-31，德国 1990 年货币换算。**手上有两个公布的总量
（居民存款换算前 1,656 亿马克、换算后 1,152 亿西德马克），
而条约规定居民只面对两个率：免额内 1:1、超出 2:1。于是一个恒等式一个未知数：

```
115.2 / 165.6 = s·1.0 + (1−s)·0.5   =>   s = 0.3913   =>   648 亿按 1:1
```

**再拿它去比「人口 × 人均上限」算出的免额容量，得到利用率贴着 1**，
据此写下「免额被搬动填满了」。**看起来是两条独立的路走到同一个数。**

**读到那张表的脚注才发现它们是同一条路。**脚注原文：
**「1:1 的换算适用于 2,000 马克 × 320 万人、4,000 × 1,010 万、6,000 × 300 万，
合计 648 亿；其余 1,008 亿按 2:1。」**
**那 648 亿就是「人口 × 人均上限」，是源头自己算出来的，不是它观测到的。**
**三档人数合计 1,630 万，就是当时的全部人口 —— 源头在构造上假定了满额取用。**

> **一个恒等式当然会还原它自己的输入。**
> **两条路走到同一个数，只有在两条路真的独立时才是证据。**

**这一次真正的 outturn 在别处，而且不一样**：储蓄银行自报截至 1990-06-30
按 1:1 换掉的占其存款 **0.3425**，而计划数是 **0.3913**；
按其份额折算，**实际取用率约 0.875**，不是 1。

**判别式，两问，在把一个数当成观测之前：**

1. **这个数是被观测出来的，还是被算出来的？**
   算出来的话，**它的输入是什么** —— 若输入正是你要验证的那个假设，这条路是循环的。
2. **两条「独立」的路，共用了哪个输入？**
   共用了就不独立。**这里共用的是「人口 × 人均上限」。**

**分辨它只花了一件事：去读脚注。**
**同一张表读了三层 —— 正文版给逐类折算（全部成立），明细版给分档，
而脚注推翻了从正文版反解出来的那条读数。**

**与失败模式 113 同族**（在机制睡着的构型上验可达性）：
**两条都是「检查通过了而它什么都没检查」。**
113 是探针跑错了构型，**本条是恒等式绕回了自己的输入。**

### 失败模式 110 附注，2026-08-31 第二次犯

**第一次是捕获日与数据序列，按现行产品的起始年下结论。
第二次是雅典 2015 复市条款：五次英文检索四次抓取全空，据此在设计件 §4.13a
写下「一级文本拿不到」并且用它约束了臂的设计。**

**用希腊文检索，一次就出来了，而且出来的是条款原文，点名「αγοραστή」买方。**

**因此加一条规则：对任何非英语法域，
在用该法域自己的语言检索过之前，不许记下「源头不可得」这个否定。**
**这条对本项目是有成本的：它意味着凡是涉及非英语法域的臂，
取材预算里必须包含一次本地语言检索，不能省。**
## 失败模式 113：判据从被检验的案例之一身上量出来，而且它的各项互相不独立

**实例，2026-08-31，B30-22 第六块。**要检验「按持有人分配同一张纸的值」这件工具
在几个前苏联国家的货币引入文件里出不出现，于是在开搜之前钉了三条判据：
甲 按人的数量上限；乙 绑定证件的一次性装置；丙 超限部分另一种待遇。
**三条逐条对得上哈萨克 1993-11-12 决议第 3 条的三句话，而哈萨克是被判的案例之一。**

**两处错，方向不同：**

**其一，判据不独立。**乙是甲的执行装置，丙是甲的另一侧规则，
**没有甲，乙没有要执行的东西，丙没有「另一侧」。**
于是「3/3」与「0/3」看起来像三条证据，实际是一个二值判断被写了三遍。
**一个反例拿 0/3 只有一个理由，不是三个。证据被通胀了三倍，而且是在自己不知情的情况下。**

**其二，判据是正例的形状。**用一个正例的形状做判别式，
再拿它去判包括那个正例在内的一组案例：
**正例必然满分，而任何用别的形式做同一件事的案例都会被判成反例。**
本例中吉尔吉斯 1993-05 用「一人一次并记入护照」实现按人限制，
而甲被写成「按人的**数量**上限」，只认一种形式，于是被判成没有。
**由此顺带犯了失败模式 110 的第三次，而且这次不是对外部资料犯的，是对自己写的判据犯的。**

**修好之后结果反转：**七例里五例的兑换结果依赖持有人是谁，两例不依赖，
而不依赖的那两例共同点是它们根本没有做一次兑换，是投放平行媒介慢慢替换。
**原判是「两正两反」，实际是「五正两反」。**

**判别式，写给每一组要钉下来的判据：**
1. **这几条里，有没有哪一条在另一条不成立时就无从谈起？**有就合并，不要分开计分。
2. **这些条目是从哪来的？**如果是从某个案例读出来的，**那个案例必须退出被判的名单**，
   或者判据必须换成一个不依赖它的形式。
3. **同一件事有几种写法？**判据要写在「事」的层面，不要写在「某一种写法」的层面。
   写不出「事」的层面，说明还没想清楚要测什么，**这时候不该开跑。**

**与失败模式 110 的关系：**110 是按预期的形式找证据、找不到就判不存在。
**113 是把「预期的形式」提前固化成了判据，于是 110 在开跑之前就已经注定要犯。**
**110 是执行时的错，113 是设计时的同一个错。**
## 失败模式 108 附则，2026-08-31：修补的闸应当按机制计，不按次数计

**起因。**B30-22 第八块给自己立了一条「连着修补两次就冻结，不再补」的规矩。
**这条规矩是坏的，因为次数不是判据。**

**照着观察改理论是正常的科研动作，物理学一直这么做。**
真正区分「拟合」与「修补」的不是改了几次，是**改出来的东西有没有指名一个机制**。

```
拟合   这六个是这样，那两个不是这样。没说为什么。
       在新案例上没有预测力，因为没有可以外推的东西。
修补   这六个有 M，那两个没有 M，而 M 之所以产生这个后果是因为……
       在新案例上有预测力：把 M 叠上新案例自己的局部结构，结果可以在看之前算出来。
```

**用本项目自己那两次修补对照，正好一反一正：**

| | 第一次修补（第七块） | 第二次修补（第八块） |
|---|---|---|
| 规则 | 离散兑换 ⇒ 按人限制 | 按持有人分档需要一个逐人出示的环节 |
| 「离散」「柜台」是什么 | **一个标签**。没说离散为什么会产生分档 | **一个机制**。限额、盖章、审查委员会都需要一个人带着钱站在官员面前 |
| 能不能在新案例上先算后看 | 不能。只能等着看它中不中 | **能。**先问新钱是不是早就在人手里，答案定了有没有柜台，柜台定了分档可不可能 |
| 判 | **拟合** | **修补** |

**所以第一次该死不是因为它是第一次，第二次该活也不是因为它是第二次。**

**换掉的闸：**

> **一次修补要被接受，必须同时给出：**
> **一，它指名的那个机制是什么，用不牵涉结论的话说清楚；**
> **二，那个机制叠上下一批案例各自的局部结构，各生成一条写在纸上的预测；**
> **三，预测写完之后才允许去看结果。**
> **给不出这三样的，无论第几次，都是拟合。给得出的，无论第几次，都可以继续。**

**底层机制与衍生机制的关系，一并写清楚：**
本项目找的是最底层那一个。每个国家有自己的文化、行政史、当时的政治处境，
**这些是衍生层，它们会让同一个底层机制在不同地方长出不同的样子。**
**正确的预测形式因此是「底层机制 ＋ 本案例的局部结构 ⇒ 本案例的预期结果」，
不是「上一批案例是什么样，这一批也该是什么样」。**
**后者是拟合，而且它在衍生层差异大的地方一定会砸。**
## 失败模式 114：自查跑在写盘之后，于是它检测到了违规却没有阻止违规

**实例，2026-08-31。**往一个要上仓库的结果件追加一节的脚本，语句顺序是

```python
s = s.replace(anchor, new_section)
io.open(p, 'w', encoding='utf-8').write(s)   # 先写盘
for bad in BANNED_TERMS:
    assert bad not in s, bad                  # 后自查
```

**那一节正文里有一个被禁的词，assert 正确地炸了，而文件已经落盘。
自查报了错，违规照样发生。**

**这一模式在同一个脚本模板里存在很久了，一直没炸，
因为此前每一节的正文都恰好干净。它靠没人撞到活着**（与渲染器那条、
`diagnostic_only` 那条同形）。

**判别式：一条检查如果排在它要保护的那个动作之后，它就不是闸，是事后报告。
两者的区别只在出事的那一天才看得见。**

**操作，三条：**
1. **凡是「写盘前必须满足」的条件，assert 一律排在 `open(...,'w')` 之前。**
 本条包括那几行扫描，以及死链检查。
2. **检查的对象是即将写出去的那个字符串，不是磁盘上的旧内容。**
   本例中被检查的对象是对的，顺序是错的，两件事分开看。
3. **写盘用第 17 条那个原子写**（写 `.tmp` 再 `os.replace`），
   于是「检查失败」与「文件半写」不可能同时发生。

**第二个实例，同日，同一件事的另一半。**
写本条正文的时候，正文里引用了那段出错脚本的被禁词清单，
**于是这一条失败模式的说明本身触发了它所说明的那道检查。**
**处置：清单在正文里写成占位符，不写字面词。**
**一条规矩的说明文字要能通过那条规矩自己，否则它进不了仓库。**

**与失败模式 21 同族**（工具在纯 ASCII 上正常、在要报中文时才失效）：
**那一条是检查用错了工具，本条是检查排错了位置。两条都是自查在最需要它的那一刻缺席。**
## 失败模式 115：一个检测器给出的否定，在它被证明打得中已知正例之前，功效未知

**实例，2026-08-31，B30-22 那一格。**任务是「找出一个分段函数的折角」，
看起来是两行代码。**实际用了五个仪器，前四个各有一个不同的故障，
而其中两个的故障形态是同一个：报出「无法解释的点有零个」，而那个零是假的。**

| 仪器 | 故障 |
|---|---|
| 月度模拟 ＋ 二阶差分过阈 | 结清月份是整数，逐月台阶被读成折角，一次报出两百多个 |
| 连续时间闭式 ＋ 二阶差分过阈 | 分不出折角与光滑弯曲；绝对阈值必在曲率穿过它处报一点 |
| **中心比值判据** | **只在折角落进 `h/4` 时触发，功效跟网格对齐走而不跟跳量走。漏掉 13 个真折角里的 5 个，且漏的是最大的三个** |
| **递归二分 ＋ 端点斜率比较** | **两端斜率相等时子区间被剪掉，而含偶数个折角的区间正好两端相同。六次运行里两次报零** |
| 均匀区间斜率，不剪枝，分辨率与下限写死 | 无 |

**两个假阴性都不是从检测器内部看出来的，是拿它去打一批已经独立确认存在的折角、
发现打不中才看出来的。**

**规矩：**

> **任何检测器给出的否定（「别处没有」「没有找到」），
> 在它被证明能打中一批已知存在的正例之前，功效未知，不得报。**

**这不是新原理，是功效核算在检测器上的形态：**
`D17` 闸三管估计量的功效，`D24` 闸六管仪器的分辨率底，
**本条管检测器的召回。三者是同一族的三个位置。**

**与第 11 条「打印对象，不打印计数」同源，而且那条读法在这里正好救场：**
**「无法解释的点有零个」是一个计数；
「这些是我找到的，这些是我已知存在的，两张表对不对得上」是打印对象。
四个故障里三个只有后一种读法看得见。**

**操作，两条：**
1. **先造已知正例。**用一个自己写出来的、折角位置已知的函数去打检测器，
   或者用被测对象上已由别的方法独立确认的那几个点。
2. **报否定的时候，同时报召回**：这一次它打中了已知正例里的几个。
   **打中率不写，那个否定就不算数。**

## 失败模式 116：把一个衍生层的量注册成普遍式，于是那条预测在第二个辖区上必然砸

**判别式是 `D33`，本条只装实例。**
**一句话：把程序的结构固定住之后，这个被预测的量还有没有人能把它选成别的样子。**
**选得了，它就随选的人走，而一条以它为内容的普遍式，只是在等下一个辖区来杀它。**

**实例，2026-08-31，B30-22 一线四十一块的全部注册预测按层回读。**
层的归属只用一件事定：那个量由结构给出，还是由某个人选出来。**归属不含任何结局信息。**

| 层 | 注册 | 活 | 死或判错 |
|---|---|---|---|
| **事理层**（管辖范围、信号广播、价格传播、算术） | 7 | **7** | 0 |
| **人因层**（谁设限额、挑哪种装置、参数取值、往哪个方向选） | 6 | 0 | **6** |

**死的那六条，逐条的死因都是同一个形状：**

| 注册的普遍式 | 被谁选成别的样子 | 杀它的那一例 |
|---|---|---|
| 局部结构是离散投放 | 各国自己怎么投放 | 拉脱维亚、亚美尼亚，两次同向 |
| 有数量约束就会有按人限额 | 发行方设不设 | 朝鲜 2009 |
| 一次性身份装置的形式是手印或身份证登记 | 各辖区挑哪一种 | 印度 2016 用的是 PAN |
| 巴西 1990 无柜台装置 | 同上 | 巴西 1990 |
| 还款总额对收入非单调 | 门槛、比例、利率、年限四个数 | 英国 Plan 5 |
| 写下的层级系统性倒置内生层级 | 国家往哪个方向选 | 巴西 1990 |

**七比六这个分离，本线此前没有看见，因为记账是按块记的，而按块记看不出这条轴。**
**能看见它，靠的是把「被预测的量归谁管」这一列补上，一列文字，零成本。**

**最难归的那一格单独记，因为它是本条能不能自证的关键。**
「还款总额对收入非单调」读起来像一句数学陈述，即像事理层。
**而判别式只问参数由谁定，于是当场判给人因层，且这一步用不到结局。**
**独立的第二条路给出同一个答案**：那次 FAIL 的记录里写着
「FAIL 的原因是机械的且事先可算」，**可算意味着它是参数的函数，
是参数的函数就随参数走，随参数走就不该被写成普遍式。**

**与失败模式 113 的分工**：113 说判据不许从被检验的那一例上读下来；
**本条说判据的量级形式不许超过那个量所在的层。** 两条都在注册之前生效，两条都零成本。

**与失败模式 108 那条附则同源**：修补由「它有没有点出一个机制」把关，
**而本条追问的是那个机制住在哪一层** —— 点出一个人因层的机制，
只能买到一条条件式，买不到一条普遍式。

**正面的一半照样要记**（`D31`）：**事理层那七条零死亡，而且其中三条跨了独立谱系。**
**本条不削弱它们，它解释的是另外六条为什么必然砸，以及下一次怎样在花钱之前认出来。**
**同日补一条，而它是本条最值得记的一半：写这条失败模式的那道判别式，自己犯了同一个错。**
第一版判别式只有一问 —— 「还有没有人能把它选成别的样子」 —— **两个盒子，事理与人因。**
**而框架有四层，漏掉的事因层（这一例所处的世界状态）没有人选它，
所以它答「选不了」，被判进事理层并获准写普遍式，而它逐例不同。**

**成因可指认，且它就是失败模式 113 换了个位置**：那道判别式是从一个反例倒推出来的
（「目的」这个量），**于是它只长出了容得下那一个反例的形状。**
**113 说的是判据不许从被检验的那一例上读下来；这里是判别式从被它处理的那一例上读下来。**

**修法**：判别式从分类体系那一侧写，不从案例那一侧写。四层就要有四个出口，
**用不到的那个也要留空并写明留空**，否则下一个人又会从一个反例倒推出一个两格的判别式。

**这一修有一个不属于记账的后果，所以它值钱**：合并写法把事因与人因一起判了死刑，
**而事因那一半本来是活的** —— 世界状态有独立且便宜的指标（通胀率、名义 M 对产出的比、
现金占 M1 的比），全部在措施出台之前就已公布。
**于是一条被撤回两次的候选解释以条件式重新开出来，循环风险原地消失。**
**`D33` 的现行版本是两问三盒。**
## 失败模式 117：一个抽取器静默返回了子集，而子集看起来像一次成功的抽取

**实例，2026-08-31，B34 步二。**任务是从 ASHE 表 6.6a 里抽出各年龄组的分位数与中位数。
脚本跑完没有报错，写出了记录件，屏幕上印着「extracted N cells」，
**而抽出来的统计量只有 `Median` 与 `Mean` 两个，登记的第 10、20、60、70、80 分位一个都没有。**

**根因**：那张表的表头跨两行 —— 一个合并的 `Percentiles` 横幅在上，
裸的 `10 20 25 30 40 60 70 75 80 90` 在下 —— 而抽取器的构造是
**「在前三十行里挑匹配最多的那一行当表头」**。
**它挑中了有 `Median` 与 `Mean` 的那一行，于是那一行是对的，只是它只有两列。**

**这一条要单记，因为失败的方式不是错，是少。**
错会炸，少不会。**`Median` 与 `Mean` 抽得完全正确，量纲对、年份对、组别对、
CV 也配上了，记录件打开来每一格都经得起看。**
**唯一的破绽是登记的那五个分位数不在里面，而那要拿设计件来对才看得出来。**

**与失败模式 22 同形**：那一条是一个字段有两种类型而所有消费者只判真值，于是没有东西撞到；
**本条是一个抽取器有十二个目标而只命中两个，而没有东西在数它命中了几个。**
**两条的解药也一样：拿一份事先写死的清单去对，不要看它有没有报错。**

**与失败模式 115 同族而位置更早**：115 说一个检测器的否定在它被证明打得中已知正例之前功效未知；
**本条说一个抽取器的肯定，在它被证明抽全了之前，覆盖率未知。**

**修法不是打补丁，是换构造**：列标签不再挑某一行，改成
**把第一条数据行以上、该列所有非空单元格叠起来**，于是跨行表头自然拼成 `Percentiles 10`；
数字型表头（`10.0`）归一成 `10`；**并且把每一列的推导标签逐列印出来**，
`col 7 Percentiles 10 -> 10` 这样一行，被跳过的列一眼看得见。

**判别式，给下一个写抽取器的人**：
**抽完之后拿设计件里登记的目标清单去对，缺哪个点名哪个。**
**「没报错」不是覆盖率的证据，「印了多少行」也不是。**

### 同一天的第二个位置：修它的那次编辑，也少数了一次

**修法是换构造，那一步是对的。执行错在别处**：新代码是用
「从 `# Header cells we expect` 切到 `def to_num`」这个位置区间替换进去的，
**而那个区间中间夹着两个不相干的函数 `read_sheets` 与 `title_of`。**
它们跟着被删掉，脚本在下一次运行时抛
`NameError: name 'read_sheets' is not defined`。

**这一次炸了，所以便宜。而它与上半条是同一个判别式的两个位置：**

| | 少了什么 | 谁本该在数 |
|---|---|---|
| 抽取器 | 十二个目标只命中两个 | 设计件里那张登记表 |
| **编辑器** | **一段区间里三个定义被删了两个** | **那一段里的定义名清单** |

**两次都是「没有东西在对清单」。**

**操作**：**按位置区间替换代码之前，先把该区间内的定义名列出来，替换后逐个核在不在。**
一行 `grep -n "^def "` 就够，而它这次能省掉一轮往返。

### 第三个位置，同一天，而这一个在判定层，最危险

**同一个脚本换了一个窗口跑（把主窗口 2015→2017 换成前趋势 2014→2015），
而判定那一段是写死给主窗口的**：主窗口要求承重分位**向上过线**，
前趋势要求它们**不得向上过线**，两条判据方向相反。

**脚本照主窗口的判据算，印出 `ARM FIVE: FAIL`。**
**真值是前趋势 PASS，而且是干净的 PASS。**

**这一个比前两个危险，因为前两个漏的是数据，这一个错的是结论**，
而结论那一行不长得像需要核对的东西。**它印得很有把握。**

**同一次还顺手盖掉了主窗口的记录件**：两次运行写同一个文件名，
后一次把前一次覆盖了。**照第 5 条没有删除，但记录件的内容没了，
主窗口那一轮要重跑才能拿回来。**

**修法两条，都已落地**：判定按 `--mode` 分流，窗口不同判据不同，
且**从窗口自动推断时把推断结果印出来**；**记录件按窗口命名**，两次运行不再互相盖。

**三个位置合起来的判别式**：
**一个工具在被换到新条件下跑之前，先问它内部有没有为旧条件写死的东西。**
**抽取器写死了表头的行号，编辑器写死了区间的位置，判定器写死了判据的方向。**
**三次都印得很干净。**

### 第四个位置：不给筛选条件，拿回来的不是「全部」，是「合计」

**同一天，B36-5，美国普查局国际贸易 API。** 要的是美国牛肉按目的地分开的月度出口量，
于是把目的地过滤去掉，想当然地以为「不筛就是全都给」。

**API 不报错，返回 264 个 cell、755 行，每年每月都齐。**
**而那 755 行的 `CTY_NAME` 只有一个取值：`TOTAL FOR ALL COUNTRIES`。**
不给 `CTY_CODE` 谓词，它给的是**每个商品每月一行的合计**，不是每个目的地一行。
**正确的写法是 `CTY_CODE=*`，那才是「每个取值各给一行」。**

> **在一个带筛选维度的接口上，「不筛」与「每个都要」是两个不同的请求，
> 而它们长得一模一样：都是不写那个条件。**
> **默认行为是沿那一维求和，因为那是最省事的返回，不是最诚实的返回。**

**第二个毛病是独立的，而且更阴**：那种合计行**连数量都没有** ——
`QTY_1_MO` 是 `"0"`，`UNIT_QY1` 是 `"-"`，只有金额。
**所以如果劈分那一步直接去加 `QTY_1_MO`，加出来的是一片零，
而零会被读成「这条线没有出口」，不会被读成「你问错了」。**
**这一次没吃到，是因为劈分脚本先在「找不到一个叫 CHINA 的目的地」上停住了。**
**那道守卫是照本条前三个位置的教训写的，本条是它第一次真的挡住东西。**

**判别式，给下一个用带维度接口取数的人，三句：**

1. **取完先数那一维有几个不同的取值。** 只有一个，而你要的是很多个，就停。
2. **顺手数一下有几行带着你要加的那一列。** 合计行常常缺量纲。
3. **「不筛」这个写法要在文档里找到它到底是什么意思，找不到就用一次探针试。**
   **探针一次调用，而重跑是 264 次。**

**与前三个位置同族**：那三个是工具为旧条件写死了东西，
**本条是工具替你补了一个你没写的条件，而它补的那个不是你要的。**
**四次的共同点仍然是：印得很干净，没有报错。**

### 附一条同日的门况，不升格，只留着省下一次试错

**巴西工贸部 Comex Stat 的开放 API 限速，第四个请求上就返回 `429`，
消息体写着「tente novamente em 10 segundos」。**
**限速是等待不是拒绝**，所以取数脚本对 `429` 退避重试（12 秒起，翻倍，四次），
对其余错误才按「这一年拿不到」记账并继续。
**门本身是好的**：国家表 281 行、NCM 表 13,746 行、逐月逐八位码带公斤，全部免费无注册。

### 第五个位置：改了行为却把旧行为的注释留在旁边，而没有任何东西在管注释

**同一天，同一个脚本。** `--cty` 的语义从两档改成三档，新注释写进去了，
**旧注释留在正上方，写着「两种写法落在同一个空字符串上」，而那句话现在是假的。**
**两条互相矛盾的说明并排放着，读它的人不知道该信哪一条。**

**这是「改规矩就是改字」那一条在代码注释上的同形**：那一条说改规矩就是改字、
不留删除线版本，理由是**机器读不出什么是被划掉的**。
**注释比规矩更糟一点**，因为它离代码近，读的人更容易信它。
**没有任何东西在守它**：不报错、不影响运行、lint 也不管（第 10 条本来就不跑）。

**操作**：**改一段代码的行为时，把它上方那段注释一起读一遍。**
**改行为不改注释，等于同时留下两份规格。**

**与第二个位置成一对**：那一次是替换区间时**多删了**两个定义（当场炸），
这一次是替换时**少删了**一段注释（永远不炸）。
**炸的那个便宜，不炸的那个才是要靠纪律接住的。**

### 第六个位置：通配符给回来的是「这一维的取值」加上「沿这一维的各级小计」，而名字上分不开

**同一天，同一个接口，第四个位置的镜像。** 第四个位置是**不给谓词**拿回一行合计；
把它改成 `CTY_CODE=*` 之后，**确实按目的地分开了，98 个不同的名字，200 行。**
**而那 98 个里混着 `AFRICA`、`APEC`、`ASEAN`、`ASIA`。**

> **通配符返回的不是这一维的原子，是这一维索引表里的全部条目，
> 而索引表里既有国家也有区域、贸易集团、洲。**
> **「把不是中国的都加起来」会把亚洲、APEC、ASEAN 和其中每一个国家重复计入。**

**名字上分不开**：`ASIA` 和 `ARUBA` 长得一样像一个目的地。
**分得开的是代码**（普查局的 `CTY_CODE` 里区域与集团有各自的号段），
**而代码根本没在 `get=` 里要过** —— 要的是 `CTY_NAME`。
**于是这一维的结构信息在取数那一步就被丢掉了，事后无法恢复。**

**判别式，两句：**

1. **用通配符取一个维度时，把这个维度的编码表也一起取回来，或者把编码列一起 `get`。**
   **只取名字，就没有办法把原子和小计分开。**
2. **加总之前先做一次求和自检**：把认成原子的那些加起来，
   **对上索引表里那个总计行**。对不上就是混进了小计，或者漏了原子。

**这一次的处置是绕开而不是修**：要的只有「中国」与「非中国」两个数，
**于是取「全部合计」与「中国」两次，相减。** 两个数各自定义清楚，
**不经过那张混着小计的名单，也就不需要判断谁是原子。**
**能绕开就绕开，比写一张区域码黑名单便宜且不会漂。**

### 顺带一条口径事实，本项目自己踩的，记着省下一次

**普查局出口数据在 `COMM_LVL=HS6` 上没有数量，只有金额。**
实测：`0201`、2016 年 6 月、`CTY_CODE=*`，200 行里**带数量的 0 行**，
`UNIT_QY1` 全是 `"-"`。**同一批数据在 `HS10` 上有公斤**（B36-4 跑过）。

**理由讲得通**：一个六位类底下若干十位行的计量单位可以不同，
**加总之后没有一个共同的单位可写，于是那一列就空着。**
**推论：凡是要数量的读数，普查局这条线一律走 `HS10`，不许走 `HS6` 省事。**
**而 `HS6` 上金额是好的**，只要读数只用金额就不受影响。

---

## 失败模式 118：一个比值的标准差不是它的噪声尺度，于是分辨率闸对着「跌」和「涨」用两把尺

**2026-08-31，B36-9 当场撞到，而它挡掉的是一条本来读得出的臂。**

**闸六（`D24`）要问「这个变化清不清于这条序列自己的噪声」，问法是对的。**
统计量写坏了：那一臂读的是三个月对前三个月的**比值** `S`，
**而闸拿的是 `S` 在原尺度上的中位数与标准差。**

> **`S` 是两个正数之和的比：下界是零，上界没有。**
> **所以它的标准差整个由上尾决定，而任何一次下跌都被低估。**

**实测，牛肉那一条：**

```
中位数 0.5068   标准差 0.4210   最低 0.1820
同一个倍数（2.784 倍）往下走   读作 0.77 个标准差
同一个倍数往上走               读作 2.15 个标准差
```

**同样大小的一次乘性变动，往下读作 0.77，往上读作 2.15，差 2.8 倍。**
**尺子是不对称的，而问题不是。** 于是闸判「不清于噪声」，整条臂被扣下，
**而它扣下的理由完全来自尺子的形状，与那条序列毫无关系。**

**修法是换刻度不是换阈值**：`log S` 的离散度由构造对称，
同一个倍数上下走都是 `1.0239`。**闸的门槛一个数没动，动的是它量什么。**

**这属于判据形状修正**：改完重跑，
**`argmin` 的月份、最低值、恢复比一个字节没变，翻的只有裁决。**
**与 A9 那次 `coupling_holds` 完全同形。**

**判别式，给下一个写闸的人：**

> **要卡的量是乘性的（比值、增长率、相对变化、倍数），
> 就在对数上量它的离散度。在原尺度上量，你对涨和跌用的是两把尺。**

**同族的还有**：变异系数、`sd/mean`、以及任何拿「几个标准差」去读一个恒正量的写法。
**判别式一句话：把这个量取倒数，同一件事该读出同样的距离吗？**
**该，而原尺度不该，那就换对数。**

**顺带记一条本条的边界**：这不放宽第 11 条。
**第 11 条禁的是在估计量上画线，本条讲的是画线之前先把尺子造对。**
**尺子不对的时候，线画在哪里都没有意义**，而这一次的表现是它看起来很像一次谨慎的扣下。

### 第七个位置：照着文档字符串写字段名，而文档字符串说的是它吃什么

**2026-09-01，B37 取数当场。** 复用一个共享解析器，摘要按 `fecha` 取日期，
**而 `fecha` 是那个 API 送来的键，解析器归一化之后吐的是 `date`。**

**那个文档字符串写得很清楚，而且它是对的**：
「This serves `{"compra":1176,"venta":1185,"fecha":"2025-06-12"}`」——
**那句话描述的是输入。** 这里把它当成了输出。

**没有报错。** 盘上的文件是对的（5,720 行、sha 记了），
**而摘要写出一串 null 和「窗口内 0 行」，清单也跟着落盘。**

> **一个函数的文档字符串说它吃什么，`return` 说它吐什么。**
> **要用它的输出，读 `return`，不读文档字符串。**

**两条操作：**

1. **取不到键的时候要停并点名**，不许写 null。
   改后的写法是取不到日期就 `SystemExit` 并把第一行的字段名全印出来。
2. **清单描述的是盘上那份文件，所以走缓存那条路也要重写清单。**
   **原来只在取数那条路写**，于是一份由坏摘要写出来的清单会活过修复本身。

**与第一到第六个位置同族**：工具答了一个别的问题而没有报错。
**本条特有的是它答的那个问题来自一段正确的文档** —— 文档没错，读法错了。

---

## 失败模式 119：取不到的那个网址不报错，它把上一次取过的那一页原样交回来

**2026-09-01，B30-5 取数当场，而抓到它的是取数设计里那道固定参照。**

**载体是一个「两城对比」页**，一次给两个城市的整表。**设计上固定拿哈尔滨当第二城**，
理由是这样每一次取数都自带一次已知答案复核 —— 哈尔滨那一页此前逐位核过。

**并行发三次，回来的是：**

| 请求的 | 实际给的 | 哈尔滨列的工资 |
|---|---|---|
| 北京 对 哈尔滨 | 对 | `3966.67` ✓ |
| **南京 对 哈尔滨** | **页面正确，而哈尔滨列是 `6100.00`** | **✗** |
| **`Xi'an` 对 哈尔滨** | **南京对哈尔滨，逐位相同** | **✗** |

**撇号那个网址单发、编码成 `%27` 再试一次，仍然返回南京。**
**取数器自己在第一行报了「这个页面比的是南京不是西安」，而它不是被要求去报的 ——
要不是那一行，两张一模一样的表会挂着两个不同的城市名进面板。**

**同一批里的深圳那次是干净的**，所以不是这条载体坏，是**那一个解析不了的网址不报错**。

> **一个取不到的网址，交回来的可能是上一次取过的那一页。**
> **它不抛错、不留空、不说自己换了内容 —— 它长得和一次成功完全一样。**

**两条操作，都便宜，而且今天两个毛病各被其中一条抓到：**

1. **每一次取数里放一个固定参照，并核它。**
   参照的值事先知道，对不上就整次作废重取。**这一条抓到了南京那次。**
2. **要求它先报「这一页实际上是什么」，再报内容。**
   **这一条抓到了撇号那次。** 一行字，而它是唯一能分辨「换了页」和「数变了」的东西。

**第三条，本轮登记为纪律**：**对同一个主机不并行取数。**
串页发生在并行那一批里，单发的两次都干净。**慢一点，而错一次要重跑整轮。**

**与 117 那一族同形而更阴**：117 是工具答了一个别的问题，
**本条是工具答了一个别人的问题，而且答得完全合乎格式。**

---

## 失败模式 120：货币符号写成数字实体，剥标签的抽取器把它读成价格的前几位

**形状**：网页把 `¥` 印成 `&#165;`，而抽取器先剥标签、再用「留下数字和小数点」
的过滤器取价。于是 `&#165;30.00` 出来是 **`16530.00`**，
**实体里的三个数字被当成价格的高位。**

**为什么它比一般的抽取错误危险**：**这个前缀是常数。**
同一位数的条目之间，跨城市的比值、秩相关、排序**全部保持不变** ——
一张这样产出的面板，做完相关分析看起来完全正常。
坏掉的只有跨位数的比较（`165` 加在 `30.00` 前面和加在 `1.90` 前面，
放大倍数差一个数量级），而那正是收入载荷这类分析要读的东西。
**它属于「印了数没印对象」那一族**（第 11 条、范畴错误第十二式）：
每一个计数量都正常，坏的是数本身的身份。

**抓到它的是什么**：**一组在抽取器写出来之前、用浏览器读的已知答案。**
北京工资的真值 `11244.87` 被读成 `16511244.87`，第一条就撞死。
**十三个已知答案里十一个当场对上到分**，两个是那一轮还没取到的城市。
**不是靠看输出「像不像」抓到的** —— 那张面板看起来像。

**判别式，可机读**：**凡是从 HTML 里取数，先问实体解码在哪一步做。**
- **没有解码** → 任何 `&#NNN;` 形式的符号都会变成数字，本条的形状。
- **在剥标签之前解码** → 文本里转义的 `&lt;td&gt;` 会变成真标签，反过来错。
- **剥标签之后逐段解码** → 对。

**同族的第二个坑，同一次买来的**：Python 里 `import html` 与一个叫 `html`
的形参撞名。本项目的写法是 `from html import unescape as _unescape`，
因为那个函数的宿主模块名正是网页抽取器最常用的形参名。
**这不是风格问题：撞上了是 `AttributeError` 或者更糟的静默取到形参。**

**同轮买来的第三条，位置在同一个文件里**：
一个「取过没有」的标志位**在页面已经写盘之后**才去问文件系统，
于是它永远答「取过」，而挂在它下面的那个 `sleep` 永远不跑，
请求背靠背发出去，**第一轮就在第二十二页上撞了 429。**
标志位要从产生它的那一层带出来，**不许在下游重算一个同名的**。

**与失败模式 117 的关系**：那一条是抽取器静默返回了**子集**，
本条是抽取器静默返回了**全集但每个数都错**。
**两条的解药是同一个：一组独立取得的已知答案，在抽取器存在之前读。**

---

## 失败模式 121：从名字推接口，而不去读定义它的那份文件

**三处，A22 开工前的同一个小时，形状一样。**

1. **循环写错。** A3 的四循环是 `(a,cash) → (a,q) → (b,q) → (b,cash)`，
   一个层两个类，`docs/a3_asset_channel.md` 把它连同取值一起写在原地。
   从 `tier_field` 的形状去推，推成了**跨两层的差之差**。
   而条款函数 `γ_{i,q} = γ̄_q·(1+κ(1−c_i))` 是乘性可分的，`log` 之后是层效应加节点效应，
   **那个推错的量对任何 κ 都恒等于零**。
2. **同级 import 少两行 `sys.path.insert`。** 本仓 `experiments/*.py` 之间互引要先插两个路径，
   `a1c_household_order.py` 里写着。少了在 import 时炸。
3. **`model.history` 这个访问器不存在。** `Network.run()` **返回**历史，模型不存它，
   `asset.py` 的类文档明写「返回的是模型不是历史」。

**三处都是「按名字猜」，而三处的定义都在盘上、都免费。**

**第一处最贵，因为它不炸。** 后两处在 import 或属性访问时立刻失败，
第一处会安静地跑完并给出「对照臂也是零」，
**而那个读数的自然写法是「这一站的 holonomy 是假的」** ——
一个用错了对象的量，被写成关于世界的结论。

**抓到它的不是推理，是并排印。** 推错的量在对照臂上读回 `3.9e-16`，
而台账里同一个站的那个量是非零的，**两者对不上就说明循环写错了**。
这是第 11 条那句「印对象不画线」的又一次现身，
也是范畴错误第六式（判据的作用域与被测对象的作用域不重合）在花钱之前被挡下的一次。

**判别式**：**要用一个别的站的量之前，先去读定义它的那一节，不要从函数签名推。**
与 `D26` 同源 —— 那一条说宣布一个量不可得之前先问有没有一份写着它的文件，
**这一条说的是那份文件常常就是自己的源码，而它同样要去读。**

## 失败模式 122：参数校验的报错，抛在文件已经被截断之后

**实例，2026-09-01。** 一个补丁脚本读进 `experiments/a24_information_wall.py`（7,398 字节），
做完替换，写回时调的是

```python
p.write_text(t, encoding="utf-8", newline="\\n")   # 多转义了一层，成了非法值
```

`ValueError: illegal newline value` 抛出来了，**而脚本变成 0 字节。**

**机制在 `pathlib.write_text` 的实现里**：它调 `self.open(mode='w', ...)`，
而 `io.open` 是**先打开底层文件**（`'w'` 当场截断）**再构造 `TextIOWrapper`**，
`newline` 的合法性是在后一步校验的。**所以报错时文件已经空了。**

**它危险的地方是报错的内容与后果不一致。** Python 里几乎所有参数错误
（类型不对、路径不存在、编码名拼错）都在动文件之前抛，
**读到「非法参数」这四个字的自然反应是「那这次调用什么都没发生」**，而这一次发生了。

**接住它的是备份，不是任何检查。** 那次补丁的上一条命令是 `cp` 出一份 `.expired`，
**第 5 条（不删，改名留档）当天第二次回本**。而发现它靠的也不是异常 ——
下一个脚本 `read_text` 读回空串，照常跑完，**末尾那句 `print(len(t.encode()))` 印出 `0`**。
**印对象又赢了一次**（第 11 条）。

**判别式，可机读**：**覆盖写一个已经存在的文件，一律先写临时件再 `os.replace`。**

```python
tmp = p.with_name("." + p.name + ".new")
with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(t)
assert tmp.stat().st_size > <下界>          # 空写当场拦住
os.replace(tmp, p)                          # 原子，失败时原件一个字节没动
```

**推广一句**：**「这一步失败了」不等于「这一步什么都没做」。**
凡是又打开又校验的 API，问一句它的顺序是哪个在前。

---

## 失败模式 123：候选集合按命名约定取，而漏掉的正好是不守约定的那一个

**实例，2026-08-25 的 B14 前缀改名。** B14 的判据当年叫裸 `A1`…`A20`（甲的转写），
与 A 轨站名同名，于是全部加 `B14_` 前缀。那一轮自己记着
「已把 **25 个 `b14*` 文件**里的 **173 处**全部加上前缀」。

**`fetch_b14_2018.ps1` 没被改到，因为它的 `b14` 在名字中间**，`b14*` 这个前缀 glob 够不着它。
它的 `.DESCRIPTION` 里留着 `section 7 supplement 2 clause A and its expansion A1`，
对着设计件 `## §7·补2·甲1`，**那个 `A1` 就是 `甲1`** ——
**整轮改名要消灭的那个歧义，原封不动活在唯一一个漏网的文件里。**

**六天没有任何东西撞到它。** 抓到它的不是那一轮、不是测试、不是 CI，
是 2026-09-01 为了另一件事（核「改完了没」）做的一次全量正则扫描：
**173 处带前缀，裸 `A<N>` 剩 1 处。**

**这是同一个形状的第三次**，三次的候选集合是三种建法，三次都漏在边界上：

| 何时 | 候选怎么取的 | 漏了什么 |
|---|---|---|
| 2026-08-21（提交前自查）| `git ls-files` | **十三个未跟踪文件**，其中一个写着运营方的金额。「未跟踪」不等于「不进仓库」，只等于还没 `git add` |
| 2026-08-21（第 21 条）| shell 的 `grep` | **中日韩字符**，默认 locale 下 `grep -o` 对一个两字中文串读 0 而 `str.count` 读 3 |
| 2026-08-25（本条） | `b14*` 前缀 glob | `fetch_b14_2018.ps1`，`b14` 在名字中间 |
| **2026-09-01，本条写下之后同一天** | **判据名正则 `A\d+-\d`，用来数 `RESULTS.md` 里哪些 A 轨站有节** | **`A19` `A20` `A21` `A23` 四节，它们在盘上、带表格，只是判据不按那个格式命名。据此报出「缺五站」，实际只缺一站（`A25`）** |

**三次的共同点不是粗心，是同一个推理**：用一个便宜的规则圈出「该查的那些」，
**而那个规则本身就是待查的性质的一部分**。守约定的文件被查了，**不守约定的没有 ——
而不守约定正是它需要被查的原因。**

**第四例值得单记，因为它是本条写下来之后同一天犯的，犯的人刚写完它。**
写规矩不产生免疫力：**判别式要变成动作才有用**，而当时那个动作没做 ——
「把被排除的那一批印出来数一眼」如果做了，四个标题当场就会看见。
**这也是为什么下面第 2 条要写成一个动作而不是一句提醒。**

**判别式，两条：**

1. **候选集合按内容取，不按名字取。** 要查「哪些文件提到 B14」，就扫内容里的 `B14`，
   不要扫文件名里的 `b14`。
2. **非要按名字取，就把被排除的那一批印出来，数一眼。**
   排除集合通常很小，看一遍是秒级的事，**而它正是漏洞所在的地方**。

**与 `D32` 同源**（缺失通常是源头局部的，穷举源头类别再下结论），
位置在工具这一侧：**`D32` 说别只查一类源头，本条说别只查一类文件名。**
---

## 失败模式 124：拿累计量去对齐两个序列，而两个序列计的是两件不同的事

**形状**：两份记录描述同一条流，一份计**发出**，一份计**到达**。
把「累计到某个数」当成对齐点，相减得到的偏移量**必然错**，
因为到达那一侧的累计里，开头那一段的货是在窗口开始**之前**发出的，
**而那一段根本不在发出那一侧的序列里。**

**实例，2026-09-01，B36-7。** 中方公告：巴西 2026-05-09 清关累计达该国配额的 50%，
即 553,000 吨。巴西海关：2026 年内累计出口到 05-18 才够 553,000 吨。
**相减得时滞 `−9` 天 —— 货比出口还早清关。**
病因是配额计的是**年内清关**，而 1 月清关的货是**上年 11、12 月**装的船。

**抓到它的不是任何统计量，是符号不可能。**
量级是对的（两边都是五十几万吨），相关是对的，**只有方向不可能。**
**如果那个偏移碰巧解出 `+9` 天，它会被当成一个偏短但可信的清关时间一路用下去。**

**解药：不要相减，要解。** 把偏移当未知数，
求一个 `L`，使「窗口起点前移 `L` 天开始累计的发出量」在公告那一天等于公告那个数。
本例解得 **52 天**，正是巴西到中国的航期加清关，
**于是它同时变成一次两个海关系统之间的已知答案检验，而哪一份都不是为它建的。**

**判别式，可机读**：**这两个序列各自计的是什么事件？**

- **同一个事件**（都是清关，或都是装船）⇒ 相减可以。
- **两个事件**（一个发出一个到达）⇒ **累计的起点就不同，必须解偏移，不能相减。**

**推论，比本条更宽**：**两个序列对上之后，先核方向可不可能，再核大小对不对。**
大小落在合理区间是很弱的检验，**错的对齐也常常落在合理区间里**；
**方向不可能是不可辩驳的检验，而且免费。**

**与失败模式 117 同族**：那一条是工具答了一个别的问题；
**本条是两份记录各自答对了各自的问题，而把它们相减是问了第三个问题。**
---

## 失败模式 125：完整性检测器建在一个不带量的字段上，于是它测的是空行

**形状**：要判「这个月的数据发布完了没有」，
拿**行数**（税号数、条目数、类别数）当代理。
**而那些行绝大多数不带量**，于是行数动了、它要代表的那个东西没动。
**检测器读的是空行的有无，不是覆盖的多少。**

**实例，2026-09-02，B36-7。** 巴西对华牛肉月度，
判 2026 年 7 月是不是没发布完，规则写成「税号数远低于中位数」。
6 月五个税号：`158,365 + 12 + 0 + 0 + 0`；7 月两个：`82,714 + 0`。

```
税号数      5 → 2      动了
带量的行    1 → 1      没动
02023000 逐月占公斤量  100%
```

**主导码一个人就是全部的量。** 那个检测器把「有没有几行零」报成了「发布完没完」。

**抓到它的是逐码打印，不是任何汇总量。**
（第 11 条：打印对象，不打印计数。范畴错误第十二式同族。）

**判别式，动手写代理之前问一句**：
**我数的这些行，每一行带多少量？**
- **量集中在少数几行** ⇒ **行数不是覆盖的代理，另找。**
- 量在行之间大致均匀 ⇒ 行数可以当代理。

**这一条比它看起来常见**，因为多数分类体系都是长尾的：
税则、科目、行业分类、错误码，**主类扛掉几乎全部，其余是零或个位数**。
**凡是在这类体系上数条目来判完整性的，默认它是坏的，除非量的分布查过。**

**解药是换一个真的能分开的东西。** 本例换成**控制组**：
同一批税号、同一个月、别的目的地。**发布没完则所有目的地一起短，
只有一条道短则那条道上有事。** 分支写在取控制组之前。

---

## 失败模式 126：目录改了名，而指着它的是纯文本，于是三分之二的指针悄悄死掉

**`D19` 的归档头是纯文本、大写键、grep 得到**，这是它的设计，理由是读它的是机器。
**但纯文本没有任何东西验证它指到的东西在不在。**

**2026-09-01 数出来的**：盘上 88 份带 `ARCHIVED:` 的归档件，
**其中 73 份的 `AUTHORITY:` 指到一个不存在的路径，共 97 个指针**。
病因是单一的：**存放这些件的那个目录改了名**，
而改名之前写下的每一个归档头都还指着旧名。**没有一份文件报过错，因为没有东西在读它们。**

**这一条正好打在 `D19` 自己想买的那件东西上。** 归档件的抬头写着
`DO-NOT-READ: 本件不再是任何东西的依据`，然后把读者送去 authority 件 ——
**送不到，读者手上就只剩那份写着「不要读我」的文件**，
而它的正文往往还扛着已经被推翻的前提。**指针死掉比没有指针糟。**

**修的时候连着犯了两次同形的错，两次都是解析器比对象窄：**

1. 第一版把结尾逗号和中文括号当成了路径的一部分（一个以逗号结尾的路径值），
   于是报出 61 处坏、其中一大半是假的。**先修检查器，再下结论。**
2. 第二版按逗号切，而有 14 份用的是**全角 `＋`** 做分隔符，
   于是那 14 份的后半截没被改到，**第一遍验证还报了「全好」**。

**两次的共同形状**：**分隔符与括号是人手写的，写法不止一种，而解析器只认一种。**
与失败模式 22 同族（一个字段两种类型，而所有消费者只判真值）：
**手写的结构没有任何东西在守，它一定会长出第二种形状。**

**处置**：`push_check.py` 加了一节，遍历带 `ARCHIVED:` 的件，
把 `AUTHORITY:` 的值按 `,` 与 `＋` 都切开、剥掉 `§` 后缀与中文括号，逐个去盘上找。
**它印出来但不改退出码**，因为这些件不进仓库，与那个脚本原来管的泄漏是两件事。

**判别式**：**任何写在纯文本里、指向另一个文件的东西，都要有一个东西定期去走一遍。**
不走的指针不是指针，是一句看起来像指针的话。


## 失败模式 127：把你自己刚提出的框架，写成源头文献的内容

**2026-09-02 买到。** 两条缺口交给另一个语言模型去检索，回来一批很详细的答案。
逐条核之后落成三格：**人名与职位三条全对，具体数字六条一条也核不到，
而其中两条不是编造文献，是把当天刚提出的分析结论安到了真实存在的文献头上。**

**两条实例：**

| 转述说 | 为什么它是生成的 |
|---|---|
| 一篇 2019 年的克罗地亚通俗回顾**指出**，把限额、地域例外与汇率打包进同一份法令，是因为战时行政链条被撕裂，**没有余力像邻国那样建立四层官僚梯队** | **「四层对两层」这个对照是当天才从两国官报原文推出来的。** 一篇 2019 年的单国回顾不会做这个跨国层级对比，**因为它要先有邻国那条授权链的读数** |
| 一篇 2023 年讲 1949 年中国币制的论文，**对逐日递减折算率给出制度解释**并指出它与 1991 年某国的 `1:0.8571` **一脉相承** | **一篇讲 1949 年中国的论文不会提 1991 年那个比率。** 「一脉相承」是当天写下的推论 |

**为什么它比编造引文难抓**：那份文献**真实存在**，作者、年份、主题都对，
人名与职位核下来也全对，**只有「它说了什么」是生成的**。
**而它正好补上你最想要的那个洞** —— 这一点与失败模式里那条编造的逐字引文同源
（「它是被提出来填一个洞的，而那个洞是真的」）。

**判别式，可执行，两句：**

1. **一条转述如果说某文献做了一个你本轮才提出的对比或推论，先假设它是生成的。**
2. **核法是去读那份文献，不是去搜那句话。** 搜那句话只会搜到转述本身。

**同一轮里可核的那三条（人名与职位）全对，这一点要一起记**：
**可核的硬事实往往对，而具体数字与「某文说了什么」往往是生成的。**
**所以「有几条核对了」不构成对其余条目的背书**，逐条核，不按批次背书。

**处置**：人名那类可引，写真实出处；数字一条不引；被判为生成的不进任何件，只留档记形状。

**本轮那条真正承重的结论没有依赖任何转述**：
「配给规则住在不上官报的那一层」站在官报自己的目录与授权条款上
（决议原文写着细则由行长另定，而整期目录里没有那份细则）。
**外部转述在这一点上与一级证据一致，这提高了它的可信度，而它仍然不是出处。**

## 失败模式 128：在一个饱和的结果量上读交叉，二阶差分返回的是主效应取负号

**2026-09-02 买到，A26-4。** 两个处理的交叉跑完，二阶差分在五个种子上全部同号，
写出来就是一句干净的「次可加」。**那个读数是错的。**

**病因是结果量有一个闭式的界，而每一格都坐在界上。**
这里的结果量是索取权存量，而发行规则是
`max(0, 开轮下层进账 − 本轮下层进账)`，逐轮发行。
下层进账一旦掉到零，存量就以固定速率爬向 `开轮进账 × 轮数`。
**闭式 `≈ 29 × 300 ≈ 8700`，实测十五格全部落在 8608 到 8951。**

**两格都在界上的时候，`(A,B) − (A,0) − (0,B) + (0,0)` 里前两项相消，
剩下的就是主效应取负号。** 实测对上到三位数：

| | 值 |
|---|---|
| 二阶差分（深切边，对控制臂，一个种子） | **−6806.9** |
| 同一格的主效应（处理 − 控制臂，零切边） | **+6833.6** |

**同一个数，反号。**

**换一头也一样。** 把发行规则关掉之后天花板没了，
**而结果量掉到地板**：第一个处理一个人就把下层累计进账打到对照的 **0.5%**，
第二个处理上去无处可切。**天花板换成地板，二阶差分还是主效应。**

**判别式，跑前零成本，三句：**

1. **交叉之前先写出这个结果量的闭式上下界。** 由控制规则的算术给出，不必跑。
2. **跑完先数有几格坐在界上。** 印出来，不设阈值。
3. **再印「留给第二个处理的余地」**：结果量随第二个处理走过的幅度，逐臂。
   第一个处理开着时的幅度远小于关着时的幅度 ⇒ **遮蔽，不是交互**。

**记账上要分清的两句**（`D31`）：
**「这两个处理不交互」是关于世界的话，「这个载体上读不出交互」是关于仪器的话。**
**只有后者有证据。** 前者写出来会让下一个人不再去换载体。

**同一轮里连带撤下的一个量，形状不同但同源**：一个诊断计数器在处理关着的时候
**根本不更新**，于是它在那一臂上报的是另一个对象（还活着的边数，
而不是没被碰过的边数）。**放进同一个差分是范畴错误第六式。**
**判别式：一个只在处理开着时才被写入的计数器，不许进任何跨处理的差分。**

## 失败模式 129：一个归一化的比值在互相独立的格上落到同一个数，那是算术不是发现

**2026-09-03 买到。** 两个集合的重叠除以「两个同样大小的集合按随机会共享多少」，
十个格（五个种子 × 两个处理强度），**比值落在 `0.315` 到 `0.328`**。
**读出来就是「重叠只有随机的三分之一」，一个干净的负相关。**

**它是假的。** 期望重叠写成 `|A| × |B| / |E|`，而 `A` 与 `B` 来自**两个不同的全集**：
一个住在路由支撑集里（约 1100 条边），另一个在整张邻接上动（约 3350 条）。
**除数取了小的那个，期望就大了约三倍，于是每一格的比值都被同一个常数除了一遍。**

**`0.32 ≈ 1100 / 3350`。**

**抓到它的不是复核，是那个整齐。** 五个种子是独立的图，两个处理强度是不同的处理，
**十格里没有任何理由让它们落在同一个第三位小数上**。
改对全集之后比值是 `0.963` 到 `0.998`，**而盲切对照是 `0.863` 到 `1.092`**，
两者分不开：**结论从「强负相关」变成「与随机无异」，而后者才是真的。**

**两条判别式：**

1. **看整齐**。一个比值在本该独立的格上方差异常小，先怀疑它被一个共同常数缩放过，
   **再去看那个常数是不是分母。**
2. **看全集**。凡是写下 `|A| × |B| / |E|` 的地方，问一句
   **`A` 与 `B` 是不是都从 `E` 里抽的**。
   一个集合是另一个的子集的子集时，最容易顺手取到里面那一层。

**与失败模式里「共享分母」那一族不同位**：那一族说两个量共享分母会造出符号与断点，
**本条说的是分母取错了层，把一个零效应染成强效应。**
**同族的是第四式与第十五式（共享分母、共享分子），本条是第三种：分母的全集选错。**

**顺带一条，与结论无关但要一起记**：修正之后那条读数仍然承重，只是方向反了 ——
原来读「两个机制抛弃的边强烈不重合」，现在读「重叠正好是随机给的量」，
**而后者一样答掉了那个「会不会是同一个机制」的问题。**
**判据没有变，变的只是它现在站在对的算术上。**

## 失败模式 130：一个每轮被覆盖的状态量，被当成整段跑的性质来读

**2026-09-03 买到。** 一个诊断量在二十个种子上把结果干净地分成两组，
**偶然概率 `2/C(20,3) = 0.0018`，而八个图的汇总统计一个都不分。**
看起来像找到了机制。

**那个量在循环里每轮被赋值一次。** 跑完之后它描述的是**最后一轮**，
不是这段跑。逐轮印出来，它整段是 `1`，只在最后一轮跳成 `3` 到 `5`。

**同一个概念的整段累计版本就在旁边**（另一个诊断量是累积或的，
逐单位求和就是「这一段跑里一共碰过几个」）。**换成它之后分界不干净了**：
二十个里有两个跨过去，落在另一组的值上。

**抓到它的不是复核那个分界，是去问「两个模态什么时候分开」。**
那个问题要逐轮的轨迹，而轨迹一印出来，覆盖就露了。

**判别式，两句：**

1. **任何在循环里被赋值的诊断量，报它之前先问它是快照还是累计。**
   写在名字里最省事：**快照的名字带上「最后一轮」，累计的不带。**
2. **一个量如果分得比周围所有东西都干净，先把它逐轮印出来。**
   **整段平的、末尾跳一下，就是覆盖。**

**与失败模式 129 同族而不同位**：那一条是分母取错了全集，
**本条是分子取错了时间范围。两条都让一个零效应或弱效应看起来干净。**

**代价与收获都要记**：这个错让一节结果多写了一句「干净分界」，
**而那一节别的结论（登记的预言判否、八个图统计量零分界）不受影响**，
因为它们不依赖这个量。**改的只是那一句，不是那一节。**

## 失败模式 131：`Path.write_text` 先截断再校验参数，参数写错就把文件清空

**2026-09-03 买到，代价是一个 43 KB 的脚本被写成 0 字节。**

**这一条不是关于分析的，是关于工具的，而它比本轮任何一个读数都要紧，
因为这个项目的第一条纪律就是不删东西，而这个函数不问自取地删了一个。**

**机制，一句话：**

```python
Path(p).write_text(text, encoding="utf-8", newline="\\n")   # 反斜杠被上一层转义掉了
```

`write_text` 内部是 `self.open(mode="w", ...)`。**`mode="w"` 在打开的那一刻就截断，
而 `newline` 的合法性是在 `open()` 里校验的**，非法值抛 `ValueError`。
**抛的时候文件已经是空的。** 异常信息是
`ValueError: illegal newline value`，**里面一个字都没提文件被清空了。**

**触发它的那个转义是真实的**：脚本经由 shell 的 here-document 传进来，
`\\n` 在那一层被吃成了字面的反斜杠加 n，**而在 Python 源码里它长得完全正常**。

**三条操作，从贵到便宜：**

1. **写盘一律用显式的 `with open(path, "w", encoding="utf-8", newline="") as f: f.write(t)`，
   不用 `Path.write_text` 的 `newline` 参数。** 换行由内容自己带。
2. **改一个文件之前先留 `.expired` 副本**，本项目本来就要求（第 5 条与第 17 条），
   **而这一次正是那份副本把损失从「不可恢复」变成「重贴三处改动」。**
   **副本要与读取在同一个脚本里做**（第 17 条 2026-08-29 那条）。
3. **写完立刻核字节数。** 一次 `stat().st_size` 就抓得到，
   **而本轮抓到它靠的是随后 `grep` 找不到内容，晚了两步。**

**判别式，可复用：任何「先打开再校验参数」的 API，参数错一次就等于删一次文件。**
**`write_text`、`open(mode="w")`、以及任何把 `truncate` 放在校验前面的封装，全在此列。**

**损失的准确范围要记，因为它决定了要补多少**：丢的是同一轮里加进这个文件的三处
（一个 job 条目、一个递归收集函数、三条登记的预期失败），
**全部有原文可依，二十分钟重贴完，逐条核过**。
**没有任何读数、任何记录、任何别的文件受影响。**

## 失败模式 132：一句对自己有利、听起来又对的机制话，写下去之前没有量

**2026-09-03 买到，代价是七秒钟，而它本来的代价是一整节写错的解读。**

**现场**：A26 的拥堵臂读到抛弃随套利强度归零。要解释它，
有一句现成的话摆在手边，而且这句话对本框架有利：

> `eta=5` 上抛弃归零，是因为队伍已经不再是「去找最好的那个」而是「去找空着的那个」，
> **那是另一条规则，不是同一条规则的更强版本。**

**这句话有全部好特征**：机制清楚、语气克制、与已知的构造相容、
并且**把一个不利读数的作用域缩小到对本框架无害**。

**量它只要一个 Kendall tau-b，五个种子六个格，七秒钟。**
**量出来是错的，而且反着错**：`eta=5` 上排序键与中心性序的一致度仍有 **`+0.84`**，
与「进账份额的负数」的一致度是 **`−0.65`**，
**也就是说它与份额本身仍是正相关的。队伍从头到尾都在按位置排。**
在这张图上，「去找最好的」与「去找人多的」本来就是同一个方向。

**同一次量还顺手给出了正确的机制**（另一个七秒的臂）：
排序在总体上几乎不变，**它只是不再连着两轮是同一支队伍** ——
`eta=0` 上队首三百轮一次没换、前十名相邻轮重合精确 `1.0000`，
`eta=5` 上 `9.8` 个队首、`176` 次更换、重合 `0.589`。
**换来的解读比原来那句强，而且是量出来的。**

**判别式，一句话：**

> **一句用来解释自己读数的机制话，如果它里面的名词是一个可以印出来的量，就先印出来。**

「排序不再是按最好排」里的名词是**排序**，而排序是一个数组，
**两个数组之间的一致度是一行代码。**
反例（不适用本条的）：「这个载体上没有这个对象」那一类，
名词是一份不存在的文件，**印不出来，那是 `D26` 管的，不是本条。**

**为什么这一条要单独记，而不是并进第 11 条**：
第 11 条管**判据**的形状，说的是别在估计量上画线、要印对象。
**本条管的是正文里的散文**，而散文没有判据、没有 PASS、没有记录，
**所以它是本项目里唯一一个不经过任何检查就能进入结论的通道。**
本轮实测：那句话已经写进 §21 的草稿标题里了，
**是跑那个臂的时候才被推翻的，而跑它的理由只是「先量一遍再写」。**

**与本项目第 0 条的关系，要写清楚，免得被读反。**
第 0 条要求在**所有为真的写法**里取对本框架最有利的那一个（`D31`）。
**「为真」在前，「最有利」在后。** 一句有利的话仍然是一句关于世界的主张，
**它的真假不因为它有利而变得不必检查** ——
而恰恰因为它有利，它更容易被跳过检查，因为它读起来像是在遵守第 0 条。
**本条是第 0 条的执行细则，不是它的对冲。**

## 失败模式 133：方向登记对了，编码成了逐步的全票通过

**同日同一个臂买到，与失败模式 132 是同一次跑的两笔账。**

**登记的方向是对的**：「抛弃随拥堵弹性下降」，出处是上一节量出来的那条轴。
**编码写成了**「二十个种子，每一步都不上升」。

**那是第 11 条明令禁止的两样叠在一起**：`N` 次全票通过，
加一个零宽度的严格不等式，**画在一条从来没有声称过光滑的路径上**。
它挂在五个种子上，而那五个种子的最大一步上升是 **`2.93` 个百分点，
落在一段 `33` 个百分点以上的下降里面**。

**判别式**：**登记的是端点之间的方向，就把判据写在端点上。**
逐步单调是一个**比方向强得多**的主张，
**而强出来的那一部分从来没有被登记过，也没有任何理论说它该成立。**

**处置**：改判据形状之后重跑，
**六列均值、二十行、逐位相同，翻的只有裁决**，所以它不是自由度，直接改。
**这是「判据不是自由度」的第二个实测形态**，第一个是 A9 的 `coupling_holds`。

## 失败模式 134：把仪器的旋钮写成世界的状态，于是一个站的边界被写成了框架的边界

**2026-09-03 裁，代价是一句已经写进结果件的作用域陈述。**

**写下去的那句**：

> 这条规则在 `eta ≲ 1` 的世界里成立，在 `eta ≳ 2` 的世界里被自己的拥堵反馈吃掉。

**两处错，是两个不同的错，而它们叠在同一句里，所以第一眼看不出来。**

**一、闸四的归档句禁令，明文的那一条**：**一律写成关于仪器的话，
不许写成关于世界的话。** `eta` 是排队键里的一个旋钮，
**它与任何真实经济之间没有任何标定，一个都没有。**
写「`eta ≳ 2` 的世界」等于声称有些经济坐在 `eta ≳ 2` 上，
**而那件事一个字都没量过，也没有可以拿来量它的东西。**

**二、更贵的那一处：把一个站的作用域写成了框架的作用域。**
那条被扫描约束的读数属于一条外挂的路由规则；
**而框架的承重主张是边场非恰当、环和非零，
一般价格理论作为「存在一个标量势」的那个特例被整个收纳在里面。**
**同一份文件的上一节自己已经写明**：这个开关造出来的量只有一个下标，
**所以整条扫描从头到尾跑在恰当的那个特例里，环和恒为零。**

> **也就是说那条扫描在任何一格上都碰不到框架的区别性主张，
> 而写出来的那句话把它说成了框架的边界。**

**判别式，两问，动手之前各问一次：**

1. **这句话里的自变量，有没有一条通向观测量的标定？** 没有 ⇒ 只许说仪器。
2. **这句话在约束谁的主张？** 把它和框架的承重主张各写一行摆在一起，
   **看它们的下标是不是同一批。** 不是同一批 ⇒ 它约束的是这个站，不是框架。

**第二问是本条比闸四多出来的那一半。** 闸四只管「世界还是仪器」，
**而本条管的是就算写成了仪器的话，它约束的到底是哪一层。**
一个站的读数被自己的旋钮吃掉，与框架被吃掉，**是两件差得非常远的事，
而写出来只差几个字。**

**同日的正面处置**：那个天花板改成算出来的 `kappa / s_head`，
**两个量都是参数与集中度，换一组参数换一个数**，
于是「`5`」这个数字自己就不再像一个关于世界的陈述了。
**把一个魔数换成一个由参数写成的式子，是这一族错误最便宜的解药。**

## 失败模式 135：一个头条数字与对手模型的构造常数吻合，而从来没有人核对过

**2026-09-03 买到，代价是零，而它本来的代价是整站。**

**现场**：A26 的头条读数是「静态排序下 `36.7%` 的路由边再也没被碰到」。
**协调摩擦那一支的罐子与球极限是 `1/e = 36.788%`。**
**两个数差 `0.45` 个点，而这个站开了半个月，没有任何人核对过。**

**它为什么危险，而不只是巧合**：那个常数不是随便一个常数，
**它是对手账户对同一个现象给出的闭式答案** ——
`N` 个买家独立挑卖家，空着的卖家占比收敛到 `1/e`。
**如果本站的数就是它，那么本站量了半个月的东西是一个组合恒等式，
而不是关于这条排队规则的读数。**

**判别式是不变性，不是水平，所以它很便宜：**

- **那个极限对出度、层大小、轮数一个都不依赖。**
- **本站的机制全部住在「预算沿一条共用队伍能走多远」上，所以它必须随出度动。**

**读数**：出度减半 `28.9%`，基准 `36.3%`，出度四倍 `41.6%`，层加倍 `43.4%`，
**跨格 `14.5` 个点。不是那个常数。**

**升成规矩的那一句：**

> **报一个数之前，先问它是不是对手模型的构造常数。**
> **判别式是不变性不是水平：找一个那个常数按定义不依赖、而本机制必须依赖的旋钮，动它。**

**同族的构造常数，看见了就要核**：`1/e`、`1/2`、`1/N`、黄金分割、
`1/(1+r)` 一类的稳态、以及任何恰好等于某个份额倒数的数。

### 但这条检查不许做成机械扫描，同日实测

**当天顺手把它扫了全仓**：`RESULTS.md` 加 `docs/` 六十一份文件，
**960 个份额型读数，对十六个常数、`±0.004` 的窗口**。
**命中约五十个，而按机会算的期望是同一个量级**
（每个数落在十六个常数任一个的 `±0.004` 内，概率约 `16 × 0.008 = 12.8%`）。
**逐个看，全部是巧合**：`b9` 的 `0.618` 是溢价对自身离散度的比，没有任何账户预言黄金分割；
`b25` 的 `0.635` 是国产旗舰对同年 iPhone 的价格比；`b7` 的 `0.7222` 是填充率。

> **一张密到有用的常数表，会让假阳性淹掉一切。这个筛子是一台多重比较机器。**

**所以这条检查的正确形状是有触发条件的，不是普查：**

> **只有当存在一个对手账户，它对**这个量**预言**那个常数**时，才去核。**

A26 那一次触发得干净，因为**罐子与球是「产能闲置」这个现象的标准解释，
而它给出的正是 `1/e`**。**没有这个对应关系的时候，数字相近什么也不是。**

**判别式两问**：这个量有没有一个现成的对手闭式？那个闭式给的是不是这个常数？
**两问都答是才核，答否就不看。**

**顺带一条本次当场犯的**：第一版把闸对错了对象。
落在常数上的是**静态排序**那个 `36.7%`，而第一版扫的是**内生排序**（基准 `23.41%`），
**于是它回答了一个关于另一个数字的问题，而且回答得很干净，看不出错**。
**这是范畴错误第六式（判据的作用域与被测对象的作用域不重合）在闸门上的形态**：
**闸本身造得对，只是没对准要闸的那个数。**
**操作：写这一类闸的时候，把「要核的那个数是哪一次跑印出来的」写进闸的第一行。**

## 失败模式 136：一个站没有记录，读数只以散文形式活在台账里，三天后它就不可复现了

**2026-09-03 买到。代价是一个站的承重表整张作废不了也复现不了。**

**现场**：A25 在八月跑过，`RESULTS.md` 有完整一节，四格表带着确切的数
（泵开无额度那一档收盘余额 `+1745` 到 `+9955`）。
**而 `results/` 里没有任何 A25 的记录，`experiments/a25_boundary.py` 是一个库，
没有 `main()`、没有判据、没有写盘，全仓零处 import 它。**

**那一节自己写着**「判据写在产出该记录的脚本里，记录带着判据原文」。
**两半都不为真。**

**补驱动的时候发生了什么，逐步：**

1. **第一版按裸 `NetworkSpec()` 造载体，四格全读零。** 那个载体上 claim 总量恒守恒，
   两侧每轮持有同一个总数，跨界净额恒等于零。**一张干净的零表，看不出错。**
2. **设计件④一行就写着载体**（`config_for("drawdown", need=0.50)`，`target="financial"`）。
   **该先读它的，第 20 条。** 换上去之后边界动了，两个结构性判据当场复现：
   宽度零时 10/10 逐位相同，额度在 30 格里咬住 7 格、首次咬在第 73 到 254 轮。
3. **而四格表复现不出来。** 六个宽度 × 两个泵档 × 两个额度档共 24 格，
   **最大收盘余额 `3.22`，对着记录的 `+9955`。差两个数量级，不是容差。**

**所以那张表的构型不在盘上。** 模块给不出、设计件的载体行给不出、两份结果件也给不出。

**判别式，可机读**：**一个站有没有 `results/` 里的记录。**
没有 ⇒ 它的读数只能靠写它的那个 session 的记忆复现，**而那个记忆随 session 消失。**

**这一条与渲染器那笔账同源而更重**（记录侧那一节）：那一次是索引漏掉四个整站，
**这一次是一个站从来没有进过索引，因为它根本没有可索引的东西。**
`RESULTS.md` 是手写台账这件事本身没问题，**问题是手写的读数背后要有一个跑得出来的记录**，
**否则台账记的是结论而不是证据，而结论不能回推。**

### 同日查完了，缺口定位到设计件的载体格

**把它查到底花了六次跑，结论是缺口不在构型的形状上，在那一格写得够不够。**

**结构事实先钉住**：跨界量是 `width * (m1 − m2)`，**两侧对称则恒等于零**。
所以那张表的每一个非零数都在说那次跑的两侧不对称，
**而载体格写的是「两张图各按同一个配置」，读起来是对称的。**

**符号把第一个不对称指出来了**：记录里泵开为正、泵关为负，
照「泵只在一侧」重建**四格符号全中**，量级差三个数量级。
**第二个锚（总 claim 2996 → 5009）把规模的缺口定位到一个参数**：
那个载体上泵关时claim 恒等于 `initial_claims = 100`，**而 1498 就是它本身**。
补上之后**截流那一格落进记录区间**（`+19.0..+19.3` 对 `+1.9..+30`），
**而泵关那两格符号翻了，说明还有一个与泵无关的第二不对称**。

**到此停手，不再调参**：再往下就是拿四个数去拟合，
**拟合中了也分不清是找回了原构型还是找到了一个构型**（第 12 条）。

> **所以这一条的可执行版本是关于设计件的载体格怎么写：**
> **写到照它重建能跑出同一串数。判别式不是写了几行，是重建之后数对不对得上。**

**处置照第 5 条办，一个字不删**：原读数留在 `RESULTS.md` 与 `A25_结果_v1.md` 原处，
**加一行说明它复现不出来**，判据记 FAIL 并写明失败的是复现不是那次跑。
**驱动留着，因为它已经把两个结构性判据钉住了**，而那两条以后不会再丢。

**一条顺带的**：驱动第一版那句裁定写着「两个分支都可达」，
**而它自己印的数是 0 咬住、30 不咬住**。同一个模板病当天第三次，
**裁定串是在跑之前写的，而它没有为「只到达一个分支」留一句。**
**方向型的臂三分格照写，这已经是今天第二次记同一件事。**

## 失败模式 137：指出一个口径问题之前，没有先把两条腿的口径并排写出来

**2026-09-03 买到，是同一天里第二次推翻自己时抓到的。**

B30-21 的超额读 `+3.1` 点、与预测反号。**第一版诊断说**：符号取决于一个跑前没有注册的
选择，即本地腿读重开日的**收盘**还是**盘中低点**（雅典 2015-08-03 开盘跌超过 22%、
收盘跌约 16%），换一个取价符号就翻。

**那个诊断是错的，而它错得很吸引人。** 两条腿本来就都是**收盘对收盘**：
本地腿是 2015-06-26 收盘对 2015-08-03 收盘，控制腿是同样两个日期的调整收盘。
**口径一致，而且收盘对收盘是标准做法。**
照第一版的建议改，等于把本地腿换成盘中低点而控制腿留在收盘，
**那才是引入不一致，不是消除它。一个坏建议差点被当成发现落盘。**

**真正的缺陷是分辨率。** 那一天自己就摆了约六个点，而要读的超额是 `3.1` 点，
**读数站在自己参照日的摆幅之下**。这条挂闸六（`D24`），不挂 `D3` 的跑后重设计。

**为什么第一版会通过自查，这是本条最要紧的一半。**
那个诊断有一个很好看的形状：**「符号取决于一个没人注册的选择」既像方法论洞察，
又不指责任何数据，还给出一个干净的下一步。** 三样加在一起让它自带说服力，
**于是检查停在了这个诊断自己身上，没有回去核最基本的那一件事** ——
两条腿到底是不是读在同一种价上。

**与 B41 `§R29.4` 那条同族，换了个位置。** 那一条的诊断是
「**干脆的负面读起来像诚实，于是绕过了先印对象那一步**」；
**本条是「漂亮的方法论诊断读起来像洞察，于是绕过了先并排写口径那一步」。**
两条的共同形状：**一个结论因为形状好看而免除了它自己的前置检查。**

**判别式，一行，零成本：**

> **指出任何一个口径问题之前，先把两条腿的口径逐字并排写出来。**

写出来就会看见它们是不是本来就一样。**这一步不要钱，而它挡掉的是一整个诊断，
以及照那个诊断去改数据的后果。**

**同族但不同位的两条**：失败模式 68 说「这一类源头里没有」被写成了「没有」；
本条说的是**一个诊断被它自己的形状说服了**。前者是范围写宽，后者是自查停在半路。

## 失败模式 138：底量在了统计量的输入上，而不是量在统计量本身上

**2026-09-03 买到，是同一个块在一天里第三次改判时抓到的。**

B30-21 读一个超额收益。**第二版诊断说它读在分辨率之下**，理由是雅典重开那一天
自己就摆了约六个点（开盘跌超过 22%、收盘跌约 16%），而要读的超额是 `3.1` 点。

**那个底是错的。** 六个点说的是**那一天有多动荡**，不是**这个统计量有多准**。
判据读的量是「本地腿的对数变化**减去**控制腿的对数变化」，
**它的底是这个差在没有事件时的离散度**。
实测在重开后 42 个共同交易日上，日超额的 sd 是 **`2.326%`**，
**于是原来那个单日读数站在 `1.59` 倍底上，而不是不到一倍。**

**这不是违反闸六（`D24`）。** 闸六的原话是「底要量出来，不许声明」，而这一次
底确实是量出来的，**量错了对象**。所以本条是闸六里一个此前没写出来的前提：

> **底要量在判据实际读的那个量上，不是量在它的任何一个输入上。**

**为什么会差这么多，本例里是两步传递函数：**

1. **取差**把两条腿的共同波动消掉了。那一天两边都在动，六个点里大部分是共同的，
   **差之后只剩 `2.3` 点。**
2. **取 `N` 日均值**再把它除以 `sqrt(N)`。

**两步都发生在输入和统计量之间，而输入的波动一步都没经过它们。**

**判别式，一行，零成本：**

> **写下底之前，先写出判据实际读的是哪一个数，再问「这个数在没有事件的时候会摆多少」。**

摆多少就是底。**输入摆多少不是底**，因为统计量可以是差、可以是均值、可以是比，
每一种对输入波动都有自己的传递函数，而那个函数通常把它缩小。

**与失败模式 137 同一天、同一个块、形状不同**：137 是没有并排写出两条腿的口径，
**本条是没有写清楚判据读的是哪一个数**。两条都是「先写下你实际在读什么」的不同侧面。

**本条同时解释了那三次改判的方向**：第一版说符号取决于取价（错，口径本来一致），
第二版说读在底以下（错，底量错了对象），**第三版把底量在统计量上，读数站到了 `2.75` 倍，
而真正的问题在别处 —— 超额随窗口单调衰减，那是控制在超调，不是处理在起作用。**
**前两版都在找「为什么这个数不算数」，而正确的问题是「这个数在测什么」。**

## 失败模式 139：拿榜单当载体，而榜单深度是平台定的，于是处理变量被压成常数

**2026-09-03 买到，B30-4 的可得性闸上。**

B30-4 要读「定价离散度对可比品密度」，而可比品密度在订阅平台上就是
**同一个类目里有多少个创作者**。六类源头查完，唯一给得出按类目数据的是平台的 leaderboard。

**而 Substack 的 API 自己在类目表的描述里写着：每个类目 top 25。**

**每个类目都是 25，因为那是平台选的展示深度，不是市场的大小。**
于是处理变量在这条路上**只有一个取值**，闸零（`D18`）答一。

**这不是「样本太小」。** 两者的处置完全相反：
「样本太小」叫下一个人去找更多数据，
**「变量没有变异」叫他换观测单位或者换载体**。
把后者写成前者，会让人花钱去买一批同样是常数的东西。

**判别式，一行，跑前零成本：**

> **凡是拿「榜单」「top N」「热门」「精选」当载体的站，先问那个 N 是谁定的。**

- **平台定的** → 它在所有格上相同 → **任何以「这一格里有多少个」为处理变量的设计当场死掉**。
- **数据本身定的**（例如「所有超过某个公布阈值的」）→ 它随格变化 → 可用。

**与失败模式 68 同族不同位**：那一条说「这一类源头里没有」被写成了「没有」，是找的范围不够；
**本条是找到了，而找到的东西是个常数。**

**与同一天同一条臂的 chunk one 是一对**：那一块判定
「一个城市填了多少项是**采集**的性质，不是市场的性质」，
**本条判定「一个类目显示多少个是**平台**的性质，不是市场的性质」。**
**两条都是把展示当成了世界，而两条都是在花钱之前一段话就看出来的。**

---

## 失败模式 140：零假设打乱在流水线的下游，于是它不携带上游造出来的人工痕迹

**2026-09-03 买到，B30-16 stage 4 上，而它已经让一个裁定翻过一次案。**

那个站量七个承运人的票价时间因子子空间之间的主角，读到 `11.7° / 30.9° / 72.6°`。
chunk four 只算了第一角的零假设，拿它去卡第二第三角，判「共享退化」。
chunk five 补了逐角零假设，第二角自己的零假设是 `78.35°`，于是 `30.9°` 翻成「决定性共享」，
chunk four 整块标 `WITHDRAWN`。**观测的角一个数都没有变，变的只有零假设。**

**而那个零假设是这么造的：**

```python
M = fill_demean(raw[c])                      # 先插值填缺，再逐行去均值
M = np.column_stack([rng.permutation(M[:, t]) for t in range(M.shape[1])])
```

**打乱发生在填充之后。** 观测那一侧带着插值造出来的低频结构，零假设那一侧没有。
而这个载体上，**10,021 条航线序列里，120 个季度全有观测的是 0 条**，
活下来的块 8% 到 13% 是填出来的。

把零假设改成在填充**之前**打乱（每列只在已观测的格子之间打乱，保住缺失掩码，
然后走完全相同的填充与去均值）：

| cov | 角 | 观测中位 | 原零假设 均值/最小 | 携带填充的零假设 均值/最小 |
|---|---|---|---|---|
| 0.6 | 2 | **30.90** | 78.35 / **51.83** | **57.12 / 20.70** |
| 0.8 | 2 | 28.50 | 78.37 / 63.46 | 66.02 / 43.34 |
| 0.95 | 2 | 38.65 | 80.39 / 69.02 | 78.89 / 69.85 |

**cov 0.6 那一行的判定翻掉，而那正是 chunk five 引来当头条的那一行。**
**交叉验证在 cov 0.95：那里只有 3.5% 要填，两版零假设逐角相差不到 1.5 度** ——
一个携带填充的零假设在没什么可填的地方就该和不携带的一样，它确实一样。

**判别式，一行：**

> **零假设在流水线的哪一步打乱，就决定了它携带哪些人工痕迹。
> 打乱点之前的每一步，两侧都有；打乱点之后的每一步，只有观测那一侧有。**

所以造零假设的时候要问的不是「打乱了什么」，是**「打乱点站在哪」**。
插值、去均值、重采样、winsorize、对齐、补零，**每一步都在造结构**，
**而它们全都发生在原始数据之后**。零假设要从**最上游**打乱，一路走完同一条流水线。

**这一条比它的实例宽**：任何「置换检验」「bootstrap」「合成对照」，
只要打乱点不在流水线最上游，量到的差值里就含着下游那几步自己造的东西。

**与失败模式 138 同族不同位**：那一条是**底**量在了统计量的输入上而不是统计量本身上；
**本条是零假设建在了流水线的中段而不是起点。** 两条都是基准和读数不在同一个对象上。

### 全仓普查已做，2026-09-03：本条在这个仓库里只有一个实例，就是上面那个

**做了，免得下一个 session 再扫一遍。** 活的站点脚本里有 35 个含打乱或重抽。
逐个过判别式，**只有 B30-16 stage 4 一处撞上**，已修。

**其余 34 个不撞，原因分两类，而这两类本身就是造零假设的正确做法：**

| 类 | 为什么天生免疫 | 实例 |
|---|---|---|
| **打乱的是标签，且打乱点在最上游** | 两侧此后走**完全相同**的流水线，下游造的结构两边都有 | `a24_information_wall` 打乱输入场 `phi` 然后两条臂各跑一遍完整模拟；`b8_3_paths` 逐格内打乱臂标签；`b8_5_hole` 格内打乱类标签；`b10_holonomy_ladder` 的注释自己写着「零假设要携带同一份膨胀」 |
| **打乱的是完整观测，上游没有填充** | 没有人工痕迹可漏 | `b30_17_curve` 的 `balanced()` **丢掉有缺口的行而不填**，所以喂进 PCA 的是完整观测 |

**B30-17 是最值得记的一条**：它和 B30-16 stage 4 在**同一条链上**，
面对同一个「列有缺口怎么办」的问题，**做了相反的选择，而且选对了**。
它的 docstring 还留着理由：要求整列完整太严，先按覆盖率筛列，**再丢掉带缺口的行**。
**同一个坑，一个站填，一个站丢，填的那个后来翻了案。**

**还有一条顺带查出来的**：`b30_17_curve` 的头条本来就不是零假设，
是 `resid_rms_bp / floor_bp` 那个跨底倍数，代码注释写着「floor crossing is the point」。
**架构上它已经是地板不是零假设**，所以它连这次的第二半都不需要。

### 第二层普查，同日：判据本身压在零假设上的有几条

**第一层问「零假设造得对不对」，这一层问「有没有必要用零假设」。同样纯阅读。**

35 个脚本里，**17 个在作通过判定的那一行提到零假设**。逐条读完，
**真正拿一个零假设量去裁定世界的，只有一条。** 其余十六条是五种别的东西，
**而这五种本身就是本条想推的做法**：

| 形状 | 它其实是什么 | 站 |
|---|---|---|
| **零假设自己的已知答案自检** | 植入零效应必须不拒绝，植入 3.0 效应必须拒绝，纯噪声必须给出均匀的 `p` | `b8_3_paths` `b8_4_class` `b8_5_hole` `b8_2_windows` `b8_3_curve` |
| **控制臂必须停在注册的天花板下** | 同上，换个位置 | `a14_scale` 的 A14-6 |
| **名字叫 permutation 的代数恒等式** | 特征值在置换下不变，差必须 `< TOL`；控制格必须 `< 1e-12` | `b17_rank` `a3h_gate_acts` |
| **已经被换掉，正文写着为什么** | 「Why this replaces the permutation」 | `b12_pullback` |
| **叫 null 的分辨率底** | 把**同一个样本**随机对半分 N 次，取最大绝对 gap，那是这个统计量自己的底 | `b2_placebo_products` 的 P5 |

**唯一那一条是 `b6b_informal`**，而它给了理由并且不是单挂：
判据是三个合取，两个零假设 p99 清关，**外加 `c_median > widest_official_round_trip()`** ——
一条**规则派生的带**。它选零假设的理由写在常量旁边：
「日占比不是关于持续性的可证伪陈述，它是混合物的性质，两个干净时期和每天抛一次硬币给出同一个数。
**判它需要选一个常数，而置换零假设没有常数可选。**」**这是第 11 条那条禁令的正当用法，不是它的反例。**

**顺带纠正一处点名。** `b8_5_hole` 的 `N_PERM = 999` 一度被读成「999 次打乱六万个元素」。
**它不打乱。** 那 999 是从**闭式**零假设里抽的次数：标签置换下 `K` 个被改的贷款按固定组大小无放回散开，
落进每组的计数是**多元超几何**，一次向量化调用，比打乱快 140 倍，
而慢的那版 `permute_p_shuffle` 留着专门给自检做对照。

**而同一个 docstring 里已经写着本条的判别式，独立发现的：**

> **The null runs on the population the observation ran on.**
> 落在底线以下或被排除的层根本不在观测范围里，把它们发进存活的层等于给另一个实验算零假设。
> **一个三笔贷款的层把 `p` 从 0.21 推到 0.13，是一次检查抓到的，不是一次读数抓到的。**

`b10_holonomy_ladder` 也独立写过同一条：「零假设要携带同一份膨胀」。

**所以这个仓库在这一族上的实际状态是**：判别式在 B8 与 B10 两个家族里已经在跑，
**B30-16 stage 4 是它没被用上的那一处**，而那一处的读数正好翻了案。
**本节的用途是让下一个 session 不必再扫一遍，也不必再点名 B8-5。**

### 顺带买到的正面器具：修零假设不如把它换掉

**修完之后才看出这条线本来就是坏形状。** 「低于十次打乱的最小值」是
**锚在这次跑碰巧产出的东西上的阈值**，本项目已经量过这一族值多少钱。
换掉它的做法是**两个锚**，两端都由构造给定，中间那个百分比就是答案：

| | 怎么造 | 它是什么 |
|---|---|---|
| **天花板** | 把**同一个**承运人自己的航线随机劈成两半，各算子空间 | 按构造完全共享时，这台仪器读多少 |
| **地板** | 打散路线与时间的对应，保住掩码与填充 | 光靠填充，这台仪器读多少 |

**读到的东西比原来那个 pass/fail 多一整个量级的信息：**

| cov | 角 1 | 角 2 | 角 3 |
|---|---|---|---|
| 0.6 | 64.7 % | 61.2 % | 20.7 % |
| 0.8 | 60.0 % | 68.0 % | 22.6 % |
| 0.95 | 68.7 % | 64.4 % | 30.6 % |

**原始角随门槛动（第二角 30.90 → 38.65，动了四分之一），位置不动（61% → 64%）。**
原因是**填充把读数和基准往同一个方向一起推**（地板 63.65 → 79.78），
**而一个不携带填充的基准看不见这件事**。这就是要有地板的全部理由。

**第三件，一个刻度完全由代数定死的量。** 平均投影算子 `P = (1/C) Σ_c V_c V_cᵀ`
的特征值落在 `[0, 1]`：1 表示这个方向在每一个当事人的子空间里，`1/C` 表示只在一个里，
前 `k` 个之和恒等于 `k`。**两个端点来自代数，不来自这次跑，也不来自任何打乱。**
实测 `0.98 / 0.81 / 0.58`，地板 `0.91 / 0.53 / 0.30`，天花板 `0.99 / 0.96 / 0.83`。

**第四件，也是最便宜的一件：把对象印出来。**
共享方向是三条季度序列，印它们的极值季度一分钱不要。
印出来是**一条三十年的漂移、2008Q1 到 2010Q1、2020Q2 到 2021Q1**。
**三条全是从行业外面来的、有日期的共同冲击。**
于是这个载体对「当事人是否互相抄价」这个问题**没有那个对象**，
两个方向都不承载 —— 而这件事，**十次打乱、逐角零假设、三个覆盖门槛全都没能说出来，
印一次极值季度就说出来了。**


**第五件，也是这一轮最后接上的：留出样本外，而它不需要任何基准。**
把共享子空间**用其余当事人建**，然后去读被留出的那一个 ——
子空间没有见过它的数据，所以这是预测不是拟合。
两端也是构造给的：随机 `k` 维按构造捕获 `k/T`，当事人自己的前 `k` 维是任何 `k` 维的上限。

| cov（填充量） | 自己的因子，样本内 | **其余人的共享子空间，样本外** | **光靠填充加自身总趋势** | 随机 `k` 维 |
|---|---|---|---|---|
| 0.6（最重） | 0.7554 | **0.6498** | **0.6548** | 0.0203 |
| 0.8 | 0.7390 | **0.6649** | **0.5834** | 0.0335 |
| 0.95（3.5%） | 0.7301 | **0.6296** | **0.4744** | 0.0358 |

**这张表说了两件位置上的读数说不出来的事：**

1. **共享子空间预测一个它没见过的当事人，回收了那个当事人自己因子样本内表现的 86% 到 90%。**
   对着随机三维的 0.02 到 0.06，不用任何分布假设。
2. **优势随填充被剥掉而单调长出来**，`-0.005 → +0.081 → +0.155`。
   **真实共享成分必须朝这个方向动，插值人工痕迹朝相反方向动。**
   于是三个门槛里该引哪一个也定了：**最严的那个，不是最松的那个。**

**地板要按它实际是什么来叫。** 逐列打乱保住每个当事人自己的逐期横截面均值，
所以地板子空间不是空的，它是**那个当事人自己的总趋势加上缺失与填充造出的几何**。
**地板把除了要证的那一样之外的东西全给了对面**，这是它该有的样子。

**两件器具答的不是同一个问题，两件都要**：
位置说「读数站得比仪器自己造的高多少」，样本外说「这个结构预测不预测它没见过的数据」。

**这是「打印对象，不打印计数」的第四种形态**（前三种见范畴错误第十二式、
判据形状那一条、以及失败模式 138）。

---

## 失败模式 141：把「谁提交的」当成了「里面装的是谁的东西」，而一份文件第一句就写着它自己是什么

**2026-09-03 买到，B30-23 上，而它差一步就把一个假的负面读数落进台账。**

那一臂要判「甲方的程序有没有随控制权传到乙方」。载体是一次收购，
判据是数乙方费率表在转让前后**互不相同的类值个数**。

**两侧都找到了，都获准，同一个实体、同一个州、同一个险种，转让夹在中间。**
**而且分方位的键看起来很硬**：备案追踪号的前缀从被收购方的组织变成了收购方的组织
（`METX-` → `FAIG-`），同一个 NAIC 码上，实体也已改成收购方的名。

**数出来的结果干净得可疑**：四张表的格数逐格相同（`22,032 / 22,032`，键 100% 匹配），
只有一部分值被乘了 `1.05`，而且恰好是 `4/9`，按年龄档整档整档地动。
**据此写下的裁定是「程序没有随控制权走」。**

**那个裁定是空的，而拆掉它的是同一个 zip 里的一份 PDF 的第一句话：**

> This filing is a rate revision **to a new program which was approved by the department
> on September 20, 2018** (SERFF `METX-131376828`).
> Since our last revision of **1/11/2021** when we lowered rates -18.1% overall...

**所以那份「转让后」的备案根本不是迁移，是对被收购方自己那套 2018 年程序的一次常规费率修订，
而它明写着上一次修订就是被当成「转让前」的那一份。**
**比的是同一套程序的第 N 次和第 N+1 次修订。**
**连续两次修订当然划分完全相同，这一对从一开始就不可能显示出迁移。**

**那个 4/9 也有平凡解释**，说明书第 2 项自己写着：
`The Class table is revised. Factors are revised for drivers aged less than 27.`
**一次普通的精算修订。** 费率变动表也是标准的：家庭构成 3.5%、信用 2.1%、
先前 BI 限额 0.2%、年龄 0.2%、基础费率 3.5%，合计 9.8%，配全国经验支持。

**判别式，一行：**

> **提交者不是程序的作者。一个标识符看起来携带出处，不等于它携带出处。**

前缀说的是**谁把文件递上去**，收购方的备案组织完全可以递一份被收购方程序的修订。
**前缀动了，程序没动。**

**这和同一天同一臂上另外两个陷阱是同一族**：界面显示的公司名是当前的名、
显示的地址是当前的地址。**三个都是「看起来携带出处的标识符」**，
而三个都不携带。**能携带出处的只有文件正文自己说的那句话。**

**解药零成本，而且它在同一个 zip 里**：
**把两份文件各自的说明书第一句读掉，再决定它们构不构成一个前后对。**
这一类文件的说明书通常自己写着「本件修订的是哪一套程序」并给出那套程序的原始核准号，
**那个核准号就是判断「换了程序」还是「改了程序」的机读键。**

**升成一条通用前置检查**：**凡是把两份文件当成一次处理的前后两侧，
先读每一份自己声明的是什么，不要从元数据推。**
元数据回答「谁、什么时候」，**回答不了「这是不是同一件东西的两个版本」**。

**与失败模式 140 同族不同位**：那一条是零假设建在流水线的中段，
**本条是前后两侧根本不是同一次处理的两侧**。两条都是**基准和读数不在同一个对象上**，
而本条更早一步 —— 它错在还没开始比之前。

**这一次没有落进台账，靠的是有人问了一句「收购是什么类型的收购」。**
**不是靠任何检查。所以它写在这里。**

---

## 失败模式 142：传播这一族载体的闸零，问的是「有几个接收方没收到」。一份公开出版的文件给不出这个数

**2026-09-03 在电价表那个载体上买到，而它是在花第二笔钱之前挡下来的，所以这一条便宜。**

那一臂想读的是一条费率设计规则的传播：一个多边机构陈述「第一档应远低于平均用电」，
四十二张公布的费率表里有多少张照办。**读数已经在盘上**：最宽的读法 25/42，
把「远低于」取作二分之一则 14/42，比值 `0.12` 到 `6.44`，中位 `0.74`。

**看起来只差一步**：找到那份陈述这条规则、带日期、有收件人的源头文件，
这个读数就从「有多少张表满足一个机构说的原则」变成「一条规则从一个源头发到四十二个接收方，
其中十七到二十八个没接住」。**那一步没有走通，而它走不通的理由不在于找不到文件。**

**逐类查了三类源头**（`D32`）：

| 源头类别 | 查到什么 |
|---|---|
| 陈述那条规则的那一段自己带的引注 | **没有引注。** 它是普查方自己的规范性表述 |
| 同一份报告的文献综述与参考表 | 底下那条批评有更早的出处（一本 2005 年的多边机构专著与两篇论文），**而它是公开出版物** |
| 按国别交付的费率研究 | 存在，但同期与更晚（`2015`、`2020` 各一例），**盖不住 2015 到 2016 那批表** |

**第三类如果盖得住，这一臂就活。它没盖住，而第二类的性质直接把这一臂关掉：**

> **处理变量「收到了这条规则」，在公开出版的源头上只有一个取值。**
> **每一个国家都读得到它。没有非接收方，就没有可比的那一侧。**

**这就是闸零（`D18`），只是它此前只被用在「这个处理变量在世界上有多少个取值」的横截面形态上。
传播这一族载体上它的形态是「有几个接收方没收到」，而这是同一个问题。**

**第二个理由更硬，而且与「共享环境」那一族同形：**

**一条从机制本身推得出来的设计规则，不需要传播者。**
想要一个补贴档而又不想让多数人落进去，就得把它划在平均以下，**这是构造给的，不是规则给的**。
**于是满足率被过度决定**：机制免费给出它，传播也给出它，两者的预测在这条读数上重合。
要把它们分开，需要一个机制造不出来的签名，**而那个签名是跨国家逐位相同的数值**，
也就是这个载体上另一条臂在做的事。

**判别式，两行，跑前零成本：**

> **一、要读传播，先数非接收方。数不出非接收方，这一臂在闸零上就已经关掉了。**
> **二、要读传播，先问这条规则能不能由机制自己推出来。推得出来，满足率就不承载传播。**

**同一次还量到一件与本条无关但要记的事**：那份报告陈述这个比值的那句话
**自己印得不自洽**，中心值 `50%` 落在它自己声明的下界 `60%` 之下。
**所以这个统计量不能当解析自检用**，而同一份报告的档数均值（报 `4`，解析得 `3.97`）可以。
**一份文件里有的数能当自检，有的不能，要逐个看，不能因为出自同一份文件就一起信。**

---

## 失败模式 143：按效应大小排序，而报告精度给效应封了顶，于是排序选出来的是精度最紧的那几个

**2026-09-03 在同一个电价表载体上买到，零成本，而它把一个已经写好的取数计划整个倒过来了。**

计数律在五十三张国家费率表上的读数是：**画了 179 个块，写出 156 个互不相同的值，
碰撞 23 个**。文档按「块数减值数」这个差从大到小排，选出「最锋利的三张」：
菲律宾 8 块 4 值、埃塞俄比亚 7 块 3 值、澳大利亚 3 块 1 值，
并据此写下取数计划：**去这三国的监管者那里取四位有效数字的原表**。

**那个排序是坏的，而拆掉它的是一行算术。**

调查把电价印到两位小数。**一张表自己印出来的跨度里能放几个两位小数的格点，
就是它最多能写出几个值**。逐张算这个天花板：

| | |
|---|---|
| 碰撞总数 | **23** |
| **被两位小数的格点数逼出来的** | **11** |
| **格点没逼的** | **12** |

**而差最大的那两张，正好是格点全额解释的那两张。**
埃塞俄比亚整张住宅表印在一到三美分之间，天花板就是 3，
**七个块无论底下的费率怎么排都写不出第四个值**；
菲律宾八个块印在三美分的跨度里，天花板 4。
**这两张的碰撞不是关于费率表的证据，是关于报告精度的证据。**

**判别式，一行：**

> **排序用的那个量，被报告精度封了顶没有？封了顶，排序就在选精度，不在选效应。**

**差 `B − V` 恰好在格点最紧的地方最大**，因为格点越少，能写出的值越少，差就越大。
**于是「按差排序」这个动作，系统性地把取数指向了取数买不到东西的那几张表。**

**这是范畴错误第九式的一个新形态**（固定报告精度 × 异质单位），
**新的地方在于它伤的是排序不是估计量**：九式此前的实例都是某个统计量被网格毁掉，
本条是统计量本身没错，**错的是拿它当优先级**。

**顺带一条，天花板这个量自己有一处循环，要标出来。**
天花板是从这张表自己印出来的跨度读的，**所以一张把每个块都印成同一个数的表，
跨度为零、天花板为一，是构造给的**。澳大利亚与希腊就是这一格，
**格点没有在解释它们，是有人把答案递给了格点**。
这两张真正独立的信息在**水平**上：澳大利亚印在 `0.26`，是这张表里最高的，
**一个真的在递减的递减档费率，要在二十六美分上递减不到半美分才藏得住**。
**所以它是十五张里最强的一张，而原来的排序把它排在第三。**

**倒过来之后的取数顺序**：跨度为零而水平高的两张先取，
然后是那十二个未被格点逼出来的碰撞（按水平从高到低），
**差最大的两张最后取**，因为那里的答案已经被精度定死了。

**与失败模式 142 同一天同一个载体，两条都是在花第二笔钱之前挡下来的。**
**共同的动作是 `D21` 那一条：在买更大的样本之前，先在盘上这一份上跑一遍要用的那个量。**

**同日追记，2026-09-03：上面那些数是解析器修好之后的数。** 修之前读的是
43 张表、144 块、124 值、碰撞 20，**而两个解析缺陷都是靠印出解析到的国家名发现的，
不是靠印出行数**：国名换行时第二行也顶格起，被当成新的一行，**六个国家被劈成两半**；
最后一个费率后面粘着页脚注编号，`0.13 34` 整个解析不出来，**四张表因此被当成
「声明档数与费率个数不符」丢掉**。修完之后 53 张表、179 块、156 值、碰撞 23，
**丢弃为零**。
**抓到它的是那条已知答案检查从「接近」变成「精确」**：档数均值先读 `3.97`、
再读 `3.92`，两个缺陷都出来之后读 `4.000`，而调查自己印的就是 4。
**一个接近的检查不是一个通过的检查**，而前两次都被当成通过了。

---

## 失败模式 144：跨国语料的一行，它的载体身份是被一条规则推出来的，不是被印出来的

**2026-09-03 在电价表载体上买到，是去取原表的第一步撞到的，而它撞到的东西比原表值钱。**

那份普查印出四十三国、后来五十三国的住宅费率表，逐国给档数、档界、逐档费率。
**取数计划是去各国监管者那里取四位有效数字的原表，第一站澳大利亚**
（三档同价 `0.26`，标为递减档而不递减，是语料里最锐的一格）。

**没取到，而没取到的理由是一句印在普查自己正文里的话**：
费率取自**「按客户数计最大的、服务于最大商业城市的那家电力公司」**。
澳大利亚的最大商业城市是悉尼，**而悉尼是一个竞争零售市场**：
同一个配电区里有十几家零售商，各自公布各自的费率表。
**普查印了国家，没印零售商，也没印是哪一份要约。**

**实测两张同期悉尼三档住宅表，两张都对不上，而两张都在别的地方给了答案：**

| | 档界原文 | 方向 | 印刷精度 |
|---|---|---|---|
| 某零售商 Ausgrid 区 2015-07-01 标准要约 | 首 `10.9589` kWh/日、次 `10.9589` kWh/日、余量 | **逐档递增** | 分/kWh，两位小数 |
| 监管者公布的该区在位者受管制住宅价 | 首 1,000 kWh/季、次 1,000 kWh/季、余量 | **逐档递增** | 分/kWh，**四位小数** |

`10.9589` kWh/日年化 4,000 kWh、月化 `333.3`，**与普查印的第一个界逐位相同**；
而两张的第二界都是第一界的两倍即月化 `667`，**普查印的是 `583`**。
**所以普查那一行是第三张表，累计界 1,000 与 1,750 kWh/季，而它是谁公布的没有印。**

**三条读数，三条都是关于仪器的：**

1. **单位差了两个数量级。** 原表是分/kWh 的两位到四位小数，普查是美元的两位小数。
   **一张在分的第四位上分开三个档的表，过不了这个取整。**
2. **两张实测的表都是递增，而普查把澳大利亚标成递减。**
3. **同一份普查的商业附录上，澳大利亚同样标递减档，而那一行印的是三个分时价、需量费为 `-`。**
   **一个「递减档」的标签压在三个分时价上面。所以那一列在这个国家上不是从费率表读出来的**，
   两个附录都不是。

**判别式，跑前零成本：**

> **这一行的载体，在那个国家是唯一的一份文件，还是一个市场里的很多份？**
> 唯一 ⇒ 那条规则指得出文件；很多份 ⇒ **规则指出的是一个类，不是一份文件**。

**与 `D26` 同形而位置不同**：`D26` 问「有没有一份写着它的文件」；
**本条问「那条选文件的规则，在这个国家落不落到唯一一份上」**。
规则写得再清楚，落在竞争市场上就选不出唯一一份，
**而普查看起来是印了口径的**，于是这一步很容易被跳过。

**代价与收益。** 代价是最锐的那一格作废：「一张标为递减的表不递减」这句话讲不下去了，
**因为那个标签根本不是那张表的读数**。收益有两条：
碰撞在这一格极可能是取整产物，**这是一个真的答案，不是一个不可判**；
以及**整份语料多了一条共同限定** —— 每一行的载体身份都是那条规则推出来的，
**在有唯一国家费率表的国家它指得出文件，在竞争零售市场的国家它指不出**。

**队列因此重排，而重排的依据是载体不是读数**：下一站换成只有一张全国费率表、
由一家公用事业公布的那个国家。**先问载体唯不唯一，再谈去取它。**

---

## 失败模式 145：一个比值的分子分母来自两个计费周期，而转录方对一部分行做了周期换算、对另一部分没做

**2026-09-03 在电价表载体的第二站买到，一次读原表就结掉，而它同时报废了整份语料里最刺眼的那个读数。**

那个读数是「第一档的界，是平均用电的几倍」。四十二张表算出来的比值，
**最大的那个是希腊的 `6.44`**，配的说法是「基本上每个用户都落在第一档里，这个结构什么也不干」。

**去读那家公用事业自己公布的费率表，`2000 kWh` 是四个月的总用电**
（原文 `συνολικό ύψος της 4μηνιαίας κατανάλωσης`），
**而被除的那个 `310.6` 是月平均用电。分子四个月、分母一个月。**
同周期算是 `500 / 310.6 = 1.61`。**「什么也不干」变成「第一档略高于平均」，一个普通设计。**

**要命的一半在于转录方并不是一律不换算。** 同一份语料里澳大利亚印的第一档界是 `333`，
而那是把年度 `4000 kWh` 除以十二得来的，**换算过**；希腊印的 `2000` 是四个月的原数，
**没换算**。**于是那一列里有的数是月量、有的不是，而它们被同一个分母除。**

**判别式，零成本，先做再读：**

> **这个比值的分子和分母，是同一个时间周期上的量吗？**
> **而且要逐行问，不能按列问** —— 转录方对一部分行做了换算，对另一部分没做，
> **列名说的是它想是的东西，不是它每一格实际是的东西。**

**可操作的旗子**：**比值异常大的那几行，先查那个国家的计费周期，再读它的结构。**
一个大比值最常见的成因是分子按季度或按四个月计，而不是那个结构真的失效。

**与范畴错误第九式同族而位置不同**：九式是固定绝对门槛撞异质分布，
**本条是同一列里混着两个单位，而列名只有一个**。
**与失败模式 144 是同一次取数买来的一对**：那一条说转录里的载体身份不唯一，
本条说转录里的量纲不统一。**两条都只有去读原件才看得见，而两条都在盘上留下了可疑的痕迹** ——
一个是档界对不上，一个是比值大得离谱。**离谱的读数是要去查的信号，不是要去报的发现。**

**同一站还买到一条零成本的**：那一行自己把希腊标成 IBT，
**而这份普查自己的正文写明 IBT 的机制是第一档折扣、由最大用户的加价来补**。
**一张所有档同价的表不执行那个机制。** 于是**行的类型标签与同一行的数字互相矛盾，
不需要取任何数就能读出来**。
**扫全语料**：十五张有碰撞的表里，**两张是全档同价**（澳大利亚、希腊），
这两张被各自的类型标签否证，**而两张实测都是取整产物**；
**其余十三张是部分同价**，而递增档费率按定义是非递减的，**中间有一段平的不构成矛盾**。
**先按「全同」与「部分同」分格，再决定去取哪一张。**

---

## 失败模式 146：索引不是文件，而一份读得像文件的索引会让人以为对象已经在手上

**2026-09-03 买到，代价是一次取数（一份文件，12,463 字节），而它挡下的是五十二次。**

那一臂要数的是**一份备案费率表里互不相同的类值个数**。载体换成美国证券交易所之后，
取到了联邦公报里 SEC 二十二年的全部通知 **44,604 条**，其中自律组织通知 **32,059 条**，
逐家算出首末备案日期，**27 家的备案停止，接缝与已知收购逐个对缝到几周之内**。

**那份索引读起来像一份备案语料**：它有标题、有日期、有文号、有实体名，
**每一条都对应一份真实的备案**。**而要数的那个对象一条都不在里面。**

**按第 13 条第 1 步先量最坏那一格，取了一份，一份就够了。**
`SR-NYSECHX-2019-01` 全文印的是**对费率表的修改说明**
（「E.6 节全文换成 Reserved」「E.9 节整节删除」「Q 节整节删除」），
**而费率表在哪，它自己第一段就写着**：

> *"The proposed rule change is available on the Exchange's website at www.nyse.com"*

**费率表是一份附件，挂在交易所自己的网站上，不进公报正文。**

**判别式，一行，而且它就是「印对象」的取数版本：**

> **在取第二份之前，取第一份，然后问：要数的那个对象，印在这份文件里没有？**

**为什么这个坑不容易避开**：索引的每一个字段都是真的，
**它错的不是内容而是层级** —— 它是一份关于文件的记录，不是文件。
**而它足够丰富，丰富到可以在它上面做完整的普查、算出人口、找出接缝、
排除两个错误的判别式**，全部有效，**然后在要读那个数的时候才发现数不在这里**。

**与 `D26` 同族而方向相反**：`D26` 说宣布一个量不可得之前，先找有没有一份写着它的文件；
**本条说找到了一份看起来是那份文件的东西，仍然要问它印没印出那个量**。
**两条都是在花钱之前，而本条的成本是一次取数不是零。**

**这一次那一份文件同时付清了自己的账**：同一页里当事方自己声明，
被收购交易所独有的那个机制在转让完成半年后停用，**它的两个费率章节被整节删除、
第三个被清空**。**那是这条臂要的那个数的方向，由收购方自己的备案给出，
不是从名字推的。** 一份文件关掉一条路线，同时交回一个读数。


## 失败模式 147：两个判别式一起失效，因为它们共享一条关于失效者行为的假设，而那条假设把失效者想成了懒得报的人

**要判的是一批行政上报的记录里，有多少行是抄前一天的纸，有多少行是那个量真的没动。**

**两个判别式看起来是独立的，其实不是：**

1. **间隔衰减。** 真实的稳定随间隔衰减，隔一天没变比隔十五天没变常见得多；
   抄表不衰减，因为抄的是上一张纸，不管那张纸多旧。
2. **整行齐同的比例。** 抄一整行会让三个字段同时相同，所以抄的那一份比值恒为 1；
   随着会衰减的那一份死掉，`整行齐同 / 单字段相同` 应当**升向 1**。
   代数是 `R = (c + rho*m)/(c + m)`，`dR/dm = c(rho-1)/(c+m)^2 < 0`，`m` 随间隔下降，故 `R` 上升。

**两条都判反了，而原因是同一条假设：它们都假设抄表与报送密度无关。**

> **实际上抄表者天天报，因为抄是最省事的合规方式。**
> **抄出来的行落在间隔 1 的桶里，正好和真实的日间黏性住在一起，两条判别式因此都分不开它们。**

**实例，印度 APMC 逐日行情，三个品种约 15 万行**（`experiments/agmark_repeat.py`、
`agmark_repeat_within.py`）。合并读数上 Cowpea 由间隔 1 天的 25.53% 掉到间隔 15 天的 3.27%，
看起来是干净的衰减；**按市场配对之后，同一市场内的短减长中位差只有 +1.67 pp**
（41 个市场里 29 个为正），**水平却在 20% 以上**。第二条判别式预测比值升，
**实测由 81.4 降到 54.3。**

**管用的第三条是连长，因为真实黏性有 hazard 而抄表没有**（`agmark_repeat_runs.py`）。
一个真的没动的量每次报送都有一定概率动，所以连长按几何尾衰减；抄过一次的更可能再抄。
**实测连长 `>= 5` 的段 389 与 1,189 段，同均值的几何标尺给 28 与 106，厚 11 到 14 倍；
最长的一段是 279 次连续报送，三个价字段全部逐字相同。**
拆账的结果是 18.84 个百分点的重复里，**12.24 个来自五连以上的段**，
且集中在 5.0% 与 13.7% 的市场上。

**判别式，跑前零成本：**

> **拿「缺失」或「间隔」这一维去检验记录质量之前，先问失效者在这一维上往哪边走。**
> **如果失效的那个动作比诚实的那个动作更省事，失效者的报送密度就不低于诚实者，可能更高。**
> **这时任何以稀疏度为轴的判别式都失效，而以「同一个动作的连续次数」为轴的判别式仍然有效。**

**与 `D27` 同族而位置不同**：`D27` 说一族器具全灭时先写出它们共有的那条假设；
**本条给出那条假设的一个具体形态，即它可以是一条关于失效者的行为假设，而不是关于测量的物理假设。**
**共有假设写在行为上的时候特别难看出来，因为每个判别式各自看都是关于数据的。**

**同一批数据上的对照，说明这个坑不是「所有判别式都没用」**：
到货量那一侧的重复率随间隔**上升**（14.45% 到 24.91%），既不是抄的形状也不是稳定的形状。
**把两端都限制在 10 吨以上之后斜率消失**，说明那是对值的选择，
即少交易的月份干脆不报，于是长间隔的对两端都是小量，而小量住在一张很短的离散清单上。
**同一个「按间隔看」的动作，在另一个字段上给出了一个干净的、可控制的答案。**


## 失败模式 148：一个按季循环的对象没有「有多厚」这个数，只有一条相位曲线，而在一个任意日历点上量它，量到的是相位

**被量的是一个逐月计数：某个品种在某个邦有几个市场在报。**
**候选里大半是有产出期的作物，而取样规则没有一处提到过季节。**

**三层后果，一层比一层贵：**

1. **一次比较错。** 把两个不同月份的读数并排当成一个时间序列的两端。
   实例：同一个品种在北方邦，`2018-07` 读 41，`2025-01` 读 3，被读成支撑集塌了八成五。
   **逐月序列拉出来之后，它一到三月是 0 到 8，六到十月是 40 到 61，每一年都一样，
   而年内和 2018 到 2025 走的是 296 / 328 / 312 / 310 / 333 / 316 / 331 / 379，没有断点。**
2. **一张排序表错。** 取样规则先用一个月问全部单位，只在结果太薄时才补问别的月，
   **于是在第一个月有数的单位一辈子只被问过那个月**，而薄的单位拿到的是三个月的最大值。
   **同一张厚度表里混着两种量法，排序里混着季节相位。**
   实例：按一月读，那个品种是 16 个市场，排在候选的中段；按七月读是 60 到 78，是最厚的一个。
3. **一批排除错，而这一层最难看出来。** 一条判据问的是「在某个日期之前有没有序列」，
   而实现它的探针问的是「在七月有没有序列」。**对一个秋冬收的作物，七月的零是按季节保证的。**
   **这是范畴错误第六式：判据的作用域与被判对象的作用域不重合**，
   而它伪装得很好，因为探针本身没有错，错的是它回答的不是被问的那个问题。
   实例：三个 (品种, 邦) 对因为七月读零被判「没有前窗」而剔除，其中一个是菱角，秋冬收。

**判别式，三句，跑前零成本：**

> **这个对象按月循环吗？循环的话，「它有多厚」这个问题没有答案，
> 要么问「它的峰有多高」，要么问「它的年内和是多少」。**
> **每一个零，先问那个月在不在这个对象的活跃期里。**
> **任何跨时间的比较，两端必须是同一个日历月，或者两端都是整年。**

**与失败模式 147 同族而位置不同**：147 说两个判别式共享一条关于失效者行为的假设；
**本条说一个判别式与它的实现之间差了一个轴，而那个轴在设计里从没被写出来过。**
**两条的解药是同一个动作：把对象印出来。**
**这一次「印出来」就是拉一条逐月序列，116 个月两条线，三分钟。
而它一次结清了上面三层，外加一个没人问过的东西**：那条序列在最后一年整年断了，
**同一个邦的年round参照序列同期反向断**，于是最后一年的可用性成了一个独立的问题。

**便宜的护栏，两条：**

- **取样规则对所有单位问同一组固定的月份**，或者把每个计数是哪个月读的记进产物。
  **两样都不做的话，那张表连自己都不一致。**
- **逐月序列在买全量之前拉一条**，选最厚的那个单位。**它是第 13 条第 2 步（先跑描述）
  在有季节的对象上的形态，而第 13 条原文没有提到季节。**

**第四层，同一个对象上的**：**在这样一个小基数上，比值不是可用的统计量。**
`2 → 6` 写成「三倍」而它是 4 个单位；基数为零时比值根本没有定义;
而相位一漂，月对月的比值就摆，**吃气候的单位摆得更厉害**。
**计数用差，或者把计数当计数建模，不要取对数比。** 归一化也写成差：
`这个单元的计数 − 参照组预测的计数`，减法在零上仍然有定义。

**第五层，最贵的一层，因为它没有事后补救**：
**发现比值离谱之后按「比值异常」把那些单元剔掉，是按因变量筛样本。**
剔掉的每一个单元，都是因为它测出了一个大的变化，**而大的变化正是要找的东西**，
所以这样筛会把结果压向空，而且压多少事后估不出来。
**同一批单元改挂在处理前的基数上就没有这个问题**：
「处理前的活跃期里，计数中位不低于 `k`」是一个处理前的量，跑前就写得下来。
**门槛本身不必改，改的是它挂在哪个量上。**

**顺带一条免费的**：**每个单元自己的年内和变异系数就是它的分辨率底**，
量出来而不是声明（`D24`）。本仓那个单元读 `7.7%`。
**「吃气候的单位噪声更大」这句话因此不必猜，那张 cv 表直接就是答案，
而它是处理前的量，所以拿它筛也不是按因变量筛。**


## 失败模式 149：从引证的数字拼出来的 URL 会返回 200，而它打开的是另一份文件；404 才是干净的信号

**一条二手引证给的是 `Riigi Teataja 1992, 28, 381`。**
**那个三元组的后两位被接成了 `28381`，拼成 `riigiteataja.ee/akt/28381`。**

**它打得开。打开的是 1990 年一份关于贸易代表机构章程的条例（RT 1990, 11, 120），与被查的事无关。**

**同一轮里的对照，两条，一正一反：**

| | 这个 URL 从哪来 | 结果 |
|---|---|---|
| **反** | 从引证的数字拼出来 | 200，一份**别的**文件 |
| **正** | 从另一份文件的外链里拿到 | 200，**要的那一份**（同一站点，id `193155`）|

**有效那一份的 id 形状与引证三元组完全不同**，
**这说明那个站点的 id 根本不是从三元组生成的，所以拼一定错。**
**而拼错的代价不是拿不到，是拿到一份看着像法条的东西。**

**根因是自增 id 空间的稠密性**：一个五位数落在一个连续的自增区间里，
**几乎必然命中某一份东西**。所以「拼一个试试」这个动作的失败形式**不是 404，是命中错的**。

> **判别式：这个 URL 是从引证里的数字构造出来的吗？**
> **是 ⇒ 它打开了也不算证据。**
> **要核的是打开的那份东西自报的编号与日期，跟引证对不对得上。**

**这一条最贵的地方在自查那一侧**：一个 404 会被立刻当成「没找到」，
**而一个 200 加一份格式正确的法条页面会被当成「找到了」**，
于是**它恰好在自查看起来最干净的那一刻失效**——与「工具在纯 ASCII 上正常、
只在要报中文时才失效」是同一个形状。

**护栏，一句**：**正本的 URL 只许有三个来源——站内检索、另一份可信文件的外链、
或搜索引擎返回的结果。不许从引证的数字构造。**
**若只有引证没有 URL，正确的记法是「有引证，未取到正本」，不是拼一个然后说取到了。**

**与失败模式 148 的分工**：148 说一个判别式与它的实现之间差了一个轴；
**本条说取到的对象根本不是要的那一个，而所有表面特征都对**——
站点对、格式对、是一份法条、编号是五位数。
**这是「印了数没印对象」在检索这一侧的形态：要印的对象是那份文件自报的编号与日期。**

---

## 失败模式 150：边界住在两个刻度之间，而检测器按刻度编号。三次撞到，三次本地修好，零次升成规矩

**2026-09-04 已升成纪律 `D44`。**本条留在坑账里不搬，纪律那一侧写的是要做什么，本条写的是这套工具会怎么咬你。

**一条边界不是一个点。** 法条写「满 21 岁起」，那一跳发生在 20 与 21 之间；
一次改革写「6 月 29 日生效」，那一跳发生在 28 日与 29 日之间。
**而二阶差分、折角检测器、结构断点检验，输出的都是一个按刻度编号的数。**

**纯代数，零数据。** 设序列除了 `(a, a+1)` 这一格之外都平，那一格落差 `d`，则

```
ch(a)   = x(a+1) − 2x(a) + x(a−1) = −d
ch(a+1) = x(a+2) − 2x(a+1) + x(a)  = +d
其余全部为零
```

**一个台阶在两个刻度上各留一半，符号相反。**
**所以「折角在 a 上」这句话说不出台阶在 a 的哪一侧，而判据问的正是这个。**
范畴错误第六式：判据的作用域（边界，住在格上）与被测对象的作用域（统计量，住在刻度上）不重合。

**本仓三次撞到，逐条：**

| 站 | 形态 | 当时怎么处理 | 代价 |
|---|---|---|---|
| **B15，`b15_calibration.py`** | 结构断点的置换零假设把事件前后几天都算成「打败了注册日」 | 原地写下**「A break test cannot tell a break at t from a break at t+1」**，并把秩报两遍，一遍照注册、一遍剔掉事件邻域 | 只多报一个数 |
| **B15，`b15_typing.py`** | 第一版问「第一跳落没落在 26 日」 | 量出时钟之后那一跳落在 27 日 `00:35:56`，即 `6.96` 整个 26 日都成立，正是公告说的 | **一次假 FAIL**，改对之后翻过来 |
| **B34，`b34_lfs_step3_kink.py`** | 折角检测器按单岁编号，而档界住在两岁之间 | 判据改成按格编号，`excess(a) = D(a) − (D(a−1)+D(a+1))/2 = (ch(a+1) − ch(a))/2` | **两个 session**，且期间把 `ch(20) < 0` 写成「法条之外的折角」，而它是法定档界 `20-21` 那个台阶的下半个偶极子（盘上 `ch(20)<0` 24/24，`ch(21)>0` 22/24）|

**这一条最要紧的不是它出现过三次，是三次都被就地修好而没有升成规矩。**
**每一次的修法都写在那一站的脚本注释里，下一站看不见。**
**与「一条规矩写在最前面、写了两遍、还有一个检查器，仍然漏了三十二处」是同一笔账：
没有东西在守它，靠没人撞到活着。**

> **判别式，跑前零成本，一句：这个检测器的模板比它输出的那个下标宽吗？**
> **宽 ⇒ 按格编号，不按刻度编号。**

**两个仓库扫完的结果，作为这条的作用域**（2026-09-04，`.py` 与 `.md`，排除虚拟环境）：

**这个形状只有 B15 与 B34 两个站命中。其余的多点模板逐个查过，都不是：**

- **B30-22 的三台折角检测器**跑在**连续**变量上，把折角**定位成一个数**再去对法定门槛；
  **第五台直接读区间斜率，本来就是按格的**。
  **B34 是把它从连续收入移植到整数岁的时候丢了这一步**，不是继承来的。
- **A26 的「second difference」是两臂两格的双重差分**，不是有序轴上的模板，没有下标问题。
- **B14 的窄带断点**读的是**第 2 桶（刚好在一个 nickel 之下）与第 3 桶（刚好在其上）之间那一步**，
  且窄带检验按切点的**取值**编号。**本来就是按格的。**
- **`ri_wid_coverage.linear_runs`** 是二阶差分，而它数的是线性内插占比，**不认领任何位置**。
- **`a3e_step_or_gradient.nearest_other`** 的三点比较是最近邻配对规则，不是检测器。
- **B36 / B37 / B44** 的事件日**来自文件，不来自检测器**；B37 读的是平段的首末日，天然按区间。
- **A7-A-2** 说「a step at the first grid point」，措辞松，**而它印的是那一格的两个端点**
  （`+18.9854` 到 `−0.1157`），**判据问的是「梯度还是台阶」不是「台阶在哪」，不受影响。**

**与失败模式 149 的分工**：149 说取到的对象不是要的那一个；
**本条说对象是对的，而它被记在了错的位置上。**
**两条都在自查看起来最干净的那一刻失效**，因为一个下标永远是一个能打印出来的整数。

---

## 失败模式 151：从一次具体安装的行政档案里读处理变量的起止，量的是那个机构的铺设进度

**处理变量是「这件事到不到得了这个地方」。而一次具体的安装只是它的一个载具。**
电报是一个载具，邮路、报纸、行商、驿站各是另一个。
**从电报局的接通登记里读出来的那一列年份，是那个部门接通了哪些地方的名录，
不是信息什么时候到那些地方的记录。**

> **这是失败模式「名录不是记录」换一根轴。** 两件事写出来一模一样，都是一列年份。

**误差是两侧的，而符号取决于一件可查的事：更早那个形式的地理，与具名开关相关不相关。**

| 更早那个形式 | 后果 |
|---|---|
| 地理**相关** | 具名开关**高估**有效处理变异（它是在已有通道的地方加第二条）|
| 地理**不相关** | 具名开关**低估**总变异，**而按它筛会误杀** |
| 只是把既存的事**写成文** | 那个日期是文书日期，**死因换类**：不是「变异不够」，是「没有可定日的处理」 |

**第三行按 `D27` 的分野最贵**：那两个死因对下一个人是相反的信号。

**实例，2026-09-05。** 一道用「开关变异的起止对因变量覆盖的起止」筛载体的闸，
把一个载体判掉，理由写「开关变异集中在因变量开始之前，重叠太薄」。
**而下这个判断的那一节末尾自己写着「残余有多大没有量」** —— 闸开了火，
**而它开火依据的那个量在同一段里被承认没有量过。** 撞闸六：底要量出来不许声明。

**回头查，那一炮打错了，三个数**（外部资料，按工程纪律第 9 条当 literature 引）：

```
线路里程   1881 年 20,346 英里 → 1920 年 88,417；全期增长的 88.6% 在 1881 之后
接入点     1881 年全印 310 个电报局 → 1900 年 1,851 个，六倍，100% 落在窗口内
机制       1883 年起的邮电合一支局；1900 年那 1,851 个里 1,612 个设在邮局内
```

**而更早那个形式也找到了，地理确实不相关**：1881 年邮局 4,500 余个对电报局 310 个，
**同一批作者量出铁路与邮局选址「largely independent」，`R²` 约 5%**；
1905 年约 145,000 英里邮路里 92,000 以上靠跑差与船，不在铁路线上。
**所以它落在上表第二行：具名开关低估了总变异，闸太严。**

**顺带一条口径**：那批作者写「1883 年电报与邮政两部合并」措辞松，
**1883 年是邮电合一支局，1914 年才是两部正式合并，混用会把处理时点定错三十一年。**

**处置照第 23 条**：这一族的闸**降为诊断，四个数照印，永不一票否决**。
一道单向开火的选载体闸，设松了多看一眼，**设紧了直接毙掉一个好用的载体，
而毙的时候看起来还很像在守纪律。** 它当时的战绩是两个 kill 里一个可疑。

> **判别式，纯提问、零数据：**
> **写下这个处理的起止之前，先问它在具名开关之前有没有别的形式承载过，
> 以及那个形式的地理与具名开关相关不相关。答不出「有更早的形式」，行政日期才是日期。**

**与失败模式 150 的分工**：150 说对象被记在错的格上，**本条说起止是从错的册子上读的。**


## 失败模式 152：一个程序自己的漂移和两个程序之间的差一样大，于是「拿 B 事后去比 A」这一族判据全部不可分辨，换形状换不出来

**买它的是 B30-23 同一天里死掉的两个判据形状，而两次的死因是同一个数。**

第一个形状数值的个数。同一家交易所，八年，中间没有换过东家：
NYSE American 2018 是 **10 格 7 值**，2026 是 **25 格 19 值**。
**一个程序自己的漂移把值数抬到接近三倍**，所以跨一次控制权转移的值数差什么也不承载。

第二个形状比值的集合，登记的理由正是「集合重叠对那个漂移免疫」。
在花钱去取缺的那份表之前，先拿盘上已有的七份量了一次可达性：

| | 对数 | Jaccard |
|---|---|---|
| 同一实体，两个时点 | 4 | **0.250 – 0.404** |
| 不同交易所，中间没有任何转移 | 17 | **0.042 – 0.565** |

**两个分布完全重叠**，而不同交易所那一族的上端（NYSE American 2026 对 NYSE National 2026，
`0.565`）**高于任何一对同一实体**。按 `D15` 两个结局分不开，判据不成立。

**两次都不是判据写坏了。** 载体的**组内变异不小于组间变异**，
而那是**载体的性质，不是判据的性质**，所以换形状换不出来 ——
第三种形状（秩相关、分布距离、逐值对齐）会死在同一个地方。

**组内变异就是这一族判据的分辨率底**（`D24`），而那一条此前只被用在估计量上。
**一个比较型判据的底，是同一个对象在没有处理的情况下自己能走多远。**

**操作，零成本，位置在 `D15` 之前**：`D15` 问「这个判据的结局分不分得开」，
**本条问「这个载体上任何比较型判据的结局分不分得开」**。
手上有几份同一实体不同时点的样本就够 —— 先量一次组内对组间，
**组内够不着组间就整族不开，不必逐个形状去试。**

**这一次它是正面用上的**：七份表全部已经在盘上，量这一次一分钱没花，
**而它挡下的是去取第三份表的那一趟。**
