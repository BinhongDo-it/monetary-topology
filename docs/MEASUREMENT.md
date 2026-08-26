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
> rather than a third book.** The nineteen failure modes below are stated in
> general form with one instance each. The fifty numbered incidents they were
> distilled from are in **[`b8_pitfalls.md`](b8_pitfalls.md)**, every one of them
> paid for by at least one full scan of the archives. Roughly two thirds of those
> fifty are about measurement practice rather than about Fannie Mae's files, so
> that file is worth reading even by someone who will never open a mortgage
> archive. **It has its own numbering, frozen because entries are cited by number
> from outside this repository, and it does not share a scheme with this file.**
>
> Until 2026-08-19 that log lived only in a handoff file, which
> `.gitignore` excludes, **so the four documents that cite it by number were
> citing something no reader of this repository could open.** Moved here for that
> reason.
>
> （**2026-08-19：本臂之内还有第三份，那是原始记录不是第三本账。** 下面十九条是
> 抽象化的失效模式，各带一个实例；它们被蒸馏自的五十条具体事故在
> **`b8_pitfalls.md`**，每一条都至少花掉过一次全扫。**那五十条里约三分之二
> 不是 Fannie 文件专有的**，是测量实践本身的病。**它自带编号并且冻结**，
> 因为仓库外有四份文档按号引它。
> 2026-08-19 之前那份记录只活在一份被 `.gitignore` 排除的交接件里，
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
| **A3-8's paired population** (2026-08-13) | The set is `cycles > 0` in **every** cell, which is an outcome. What it leaves is the top eighth of the production layer by centrality, band `[86.8, 100]` over twenty seeds, and `gate_spread` disperses terms **along** centrality. **So the gate arm is read on a population inside which its own treatment barely varies, and it reads as zero for that reason rather than for a reason about the mechanism.** The peripheral tercile trades zero times in every cell **including the null**, so the gate is not what removed it. | `a3_asset_channel.md` §5.3, `experiments/a3d_gate_margin.py` |

**Rule**: **the population has to be defined by the state before treatment, or
matched by node.** Matching is the strongest form: the same node is compared
against itself across the two arms. Where stratifying on an outcome is
unavoidable, **stratify inside each arm separately** and report the transition
matrix (holds in both arms / holds in one only / holds in neither), rather than
imposing one arm's strata on the other.

**And a second half, added with the fourth instance: report the treatment's
variation over the measured population before reporting its effect.** The first
three instances are a population that moves with the arm. The fourth is a
population that does not move at all and still breaks the reading, because the
treatment has no room to act inside it. Both produce a number that looks like an
effect size and is a fact about the sampling frame. One line of output prevents
it: the range of the treatment variable over the nodes actually measured.

（**规则**：**人群必须由处理之前的状态定义，或者按节点配对。** 配对是最强的：同一个节点
在两臂之间比它自己。若必须按结果分层，则**在每一臂内部各自分层**，并报出转移矩阵（两
臂都持有／只有一臂持有／都不持有），而不是把一臂的分层套到另一臂上。

**随第四个实例补的后半条：报任何处理效应之前，先报处理变量在被测人群上的变异范围。**
前三个实例是人群随臂移动，第四个是人群一动不动也照样坏读数，因为处理在它内部没有作用
余地。两者产出的都是看起来像效应量、实际是关于抽样框的事实。一行输出就能防住：被实际
测量的那些节点上，处理变量的取值范围。）

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
| A6 的税基 | The levy fell on `_l1_idx`, twenty node indices fixed at construction, not on whoever held most. No real net wealth tax uses fixed membership. | `PROJECT_PLAN` §16.4：加 `LevySpec` 开关，默认仍是层制所以既有结果逐位不动，另一支按门槛累进 |
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
operational form is the same one section 11.12 of `PROJECT_PLAN.md` gives for
call sites: **before moving a default, enumerate every stage that constructs from
the object it belongs to, and re-run all of them.** Putting the stage into the
runner is the durable version of that, because it does not depend on anyone
remembering to enumerate.

（**规则**：**没有东西重跑的阶段，它没有记录，它只有记忆。** 当共用机器上的某个默认值移
动时，站在那台机器上的阶段，其存盘数字就已经是关于另一个经济的了，而在 runner 之外的那
些，恰恰是不会说出这件事的那些。可操作的形式与 `PROJECT_PLAN.md` §11.12 对调用点给的那
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
本条上面那两批修完之后，它又报出 **64 处**指向 `PROJECT_PLAN.md`（47）、
`SESSION_INIT.md`（6）、`HANDOFF.md`（6）、`HANDOFF_B8.md`（4）、`OBJECTIONS.md`（1）
的引用，**全部在已发布的树上**。
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

研·3 给纪律表加 `D` 前缀，理由就是 `纪律 15` 与 `§5 第 15 条` 撞过车。
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
**六条判据的裁定逐条不变**（实测），所以按研·5 第 2a 是自由的判据形状修正，
直接改字。**结果件那一条读数开作废栏**，因为读数变了：
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
**这是研·0「印全」的落地，不是新判据**：没有任何东西在这两个数上通过或失败，
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
