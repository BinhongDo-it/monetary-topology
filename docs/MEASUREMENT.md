# Measurement conventions: run through this before reporting any number
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

**"I ran a lot, so I am conservative and compliant" is not a reason and is banned
as one.** This is not a university compute centre and there is no committee to
satisfy. Compute spent to look rigorous is compute not spent on the next question,
and this repository has now measured the exchange rate: an afternoon of a loaded
machine bought a two-hundred-draw confirmation of an outcome fixed in advance by
`28` sigma.

（**「我跑得够多所以我够保守够符合规矩」不是理由，并且作为理由被禁止。** 这里不是学校
的算力中心，没有委员会要满足。为显得严谨而烧掉的算力就是没花在下一个问题上的算力，而
这个仓库已经把汇率量出来了：一个下午的满载机器，换来一次对「事先由 28 个 sigma 定死的
结果」的两百抽样确认。）

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

**Rule**: **stop writing criteria that threshold an estimated quantity.** A
criterion should be one of two things and nothing else:

1. **structural** and about the code rather than the world: did every arm finish,
   is this decomposition an identity to `1e-16`, does this design's group count
   match its level count;
2. **a printed number with a reading declared in advance**, and no line drawn
   across it.

（**规则**：**停止写「给估计量卡阈值」的判据。** 一条判据只能是两种东西之一：一是
**结构性的**、关于代码而不关于世界的（每条臂跑完没有、这个分解是不是恒等式到 `1e-16`、
这个设计的组数和层级数对不对）；二是**一个印出来的数，外加一条事先声明的读法**，不在
它上面画线。）

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
retrodicted from the bug, which is how the bug was confirmed. **Register to leave a
record. Do not register expecting to be protected.**

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
毛病不在于剩余项没被解释，而在于**把「臣妾没想到」报成了「没有」**，
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

14. **Does this criterion draw a line across an estimated quantity?** Then it is
    the wrong shape. Make it structural, or make it a printed number with a
    reading declared in advance. Mode 13 has seven instances and five of them were
    written in one day.
    （**这条判据是不是在一个带估计误差的量上画了一条线？** 那形状就错了。要么改成结
    构性的，要么改成一个印出来的数加一条事先声明的读法。）

15. **How many draws and repetitions, and what is the smallest that still settles
    it?** Five repetitions is the reference. Above ten on a homogeneous arm needs a
    stated reason that is a property of the arm. "Enough to be safe" is not one.
    （**抽多少次、重复多少轮，仍然能结掉这个问题的最小值是多少？** 五轮是参考值。同
    质化的臂上超过十轮要给出理由，而且理由必须是这条臂的性质。「够多才保险」不是。）

Item 7 is the only one **designed to catch an error rather than to avoid one**:
A5-6's zero calibration was the only one of the eleven caught by an automatic
guard, and the other ten were all caught by a human inspecting a number that
looked wrong. **A zero calibration is standard equipment on every new carrier,
not an option.**

（第 7 条是唯一一条**设计出来专门抓错**的：A5-6 那条零标定是本 session 十一次里唯一被自
动守卫抓到的，其余十次全靠人工审视异常数字。**每个新载体标配零标定，不是可选项。**）

---

16. **Am I about to write that something is unexplained?** Then what is the most
    boring thing that would produce it, and why is that not it? A residual that is
    left over after fitting two functions, and that still has structure, is the
    **expected** shape when the truth is a smooth family and the two functions are
    two of its modes. Write that down and rule it out, or do not use the word.
    （**臣妾是不是正要写「这一块没有解释」？**那么，最无聊的那个解释是什么，
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
the author was not thinking about.

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
marker is in `CLAUDE.md`, section 收尾: `experiments/*.py` is single-station and
`src/monetary_topology/*.py` is shared. This file does not keep a second copy of it.

（**第九种失败模式是那条元规则的第一个标本，而且专门是第二个触发条件的标本。** 它不报错，
它带的每一条判词都是对的，它安静地回答了一个关于仓库早已不再描述的那个经济的问题。
本文件开头计的十一次实例全部是自相矛盾型、全部靠人工审视在内部抓到；这一次只能靠重跑抓到。）

（**它确立的东西同样带作用域（2026-08-16）。**重述 A3 的那次提交在共享机器上打开了默认的
`rent_rate`，而 A5 整个跑在那台机器上。**一个阶段要重跑，是因为它脚下的默认值动过，
不是因为一轮结束了。**这里原来的写法「重跑一个代码没有变过的阶段，不是一个多余的动作」
会被读成「随时都该把所有东西重跑一遍」的常设义务，而那不是第九种失败模式所证明的。
带可查标记的作用域判别式在 `CLAUDE.md` §收尾：`experiments/*.py` 是单站的，
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

散文改动（docstring、注释、空白）会推动源码哈希，于是陛下为一次注释改动
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
