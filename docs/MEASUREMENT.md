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

## Eight failure modes, each with an instance in this repository
（八种失败模式，每一种都有本仓库的实例）

### 1. Window error　(four instances)　（窗口错，四次）

**Symptom**: the size or the sign of the number is decided by **how long a
stretch was measured** rather than by the mechanism.

（**症状**：数字的大小或符号由「量了多长一段」决定，而不是由机制决定。）

| Instance（实例） | What went wrong（错在哪） | 原文 |
|---|---|---|
| A3-4 v1, 78.7% error | The loop sum is a **per-trade** quantity, and it was fitted against an exponent **in time**. | A3-4 v1，误差 78.7%：圈和是**每笔交易**的量，却去拟合**对时间**的指数 |
| A3-4 v2, sign flipped on 4 of 5 seeds | The four-cycle **enters and leaves at the same points**, while an agent who trades less holds each unit longer, so appreciation swamps the terms. | A3-4 v2，符号 5 个种子翻 4 个：四圈是**同进同出**的，而交易少的人每笔持有更久、涨幅盖过条款 |
| A5-4, "crossing at round 1" | The origin of the series sits two steps away from the configured value, so the configured value was never observed. | A5-4「第 1 轮穿越」：序列的原点比配置值远两步，配置的值从未被观测 |
| A6-1, tail slope `+1.1e-05` while the support fell 27% | The slope answers "is it still contracting". The question was "did it contract". | A6-1，尾部斜率 `+1.1e-05` 而支撑集掉 27%：斜率答「还在不在收缩」，问题是「收缩过没有」 |

**Rule**: **write down the time quantifier in the claim first, then choose the
window.** "Per trade", "per period", "cumulative" and "end of period against
opening" are four different quantities. If the claim is "per trade", the
denominator of the measurement must be the number of trades and not the number
of rounds.

（**规则**：**先写下主张里的时间量词，再选窗口。** 「每笔」「每期」「累计」「期末对开
局」是四个不同的量。若主张是「每笔」，度量的分母必须是笔数不是轮数。）

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

### 5. Population error　(three instances, two of them consecutive)　（人群错，三次，其中两次连续发生）

**Symptom**: the two groups being compared are selected **on an outcome**, and
the treatment changes that outcome.

（**症状**：比较的两组是**按结果**选出来的，而处理会改变那个结果。）

| Instance（实例） | What went wrong（错在哪） | 原文 |
|---|---|---|
| A5-1/A5-2, 0% across the whole grid | Participation measured at the end of the period measures **survival** and not entry. | A5-1/A5-2，全网格 0%：期末测参与率，量的是**存活**不是进场 |
| Rent sweep v1 | The set of "never-holders" moves with the rent rate. | 租金扫描 v1：「从不持有者」这个集合随租金率改变 |
| Rent sweep v2 | Pinning the population to the `rent=0` set still fails: some of them **acquire units at other rates and are therefore on the receiving side of the rent**. | 租金扫描 v2：把人群固定到 `rent=0` 那批仍不行——其中一些在别的费率下**买到了单位，于是是收租方** |

**Rule**: **the population has to be defined by the state before treatment, or
matched by node.** Matching is the strongest form: the same node is compared
against itself across the two arms. Where stratifying on an outcome is
unavoidable, **stratify inside each arm separately** and report the transition
matrix (holds in both arms / holds in one only / holds in neither), rather than
imposing one arm's strata on the other.

（**规则**：**人群必须由处理之前的状态定义，或者按节点配对。** 配对是最强的：同一个节点
在两臂之间比它自己。若必须按结果分层，则**在每一臂内部各自分层**，并报出转移矩阵（两
臂都持有／只有一臂持有／都不持有），而不是把一臂的分层套到另一臂上。）

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
   an outcome?
   （**我的人群是按处理**之前**的状态定义的吗？** 还是按结果选的？）
6. **Is my tolerance the same order of magnitude as the effect being measured?**
   （**我的容差和被量的效应同量级吗？**）
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

Item 7 is the only one **designed to catch an error rather than to avoid one**:
A5-6's zero calibration was the only one of the eleven caught by an automatic
guard, and the other ten were all caught by a human inspecting a number that
looked wrong. **A zero calibration is standard equipment on every new carrier,
not an option.**

（第 7 条是唯一一条**设计出来专门抓错**的：A5-6 那条零标定是本 session 十一次里唯一被自
动守卫抓到的，其余十次全靠人工审视异常数字。**每个新载体标配零标定，不是可选项。**）

---

## One meta-rule　（一条元规则）

**A self-check catches self-contradiction and does not catch coherent drift.**
That all eleven were caught in-house is precisely what says they were all of the
self-contradicting kind: numbers that did not add up, signs that flipped. The
dangerous ones are the drifts that are **internally coherent**. They raise no
error. They quietly answer a different question.

（**自查抓得到自相矛盾，抓不到自洽的漂移。** 十一次全部被自己抓到，恰恰说明它们都是自相
矛盾型的（数字对不上、符号翻转）。真正危险的是那些**自洽的**漂移——它们不会报错，只会
安静地回答一个不同的问题。）

There are only two ways at them: route the judgement to a model holding a
different context (a review session), and **require a written list of everything
changed but believed not to matter**. The most dangerous deviation is never the
one that was recorded. It is the one judged irrelevant and therefore never
written down.

（对付它们只有两个办法：把判断路由到一个 context 不同的模型上（复核 session），以及**强
制列出「我改了但认为不影响」的清单**——因为最危险的从来不是被记录下来的偏离，是被判为
无关紧要因而没写的那些。）
