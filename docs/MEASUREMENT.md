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

## Six failure modes, each with an instance in this repository
（六种失败模式，每一种都有本仓库的实例）

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

### 4. Stratification error　(two instances)　（分层错，两次）

**Symptom**: what should have been held fixed was not, so what got measured is
the thing that moved.

（**症状**：没把该固定的东西固定住，于是量到的是没固定的那个。）

| Instance（实例） | What went wrong（错在哪） | 原文 |
|---|---|---|
| A3-3, drift 0.583 | Constancy was not grouped by **tier**, so the entire drift is tier changes. | A3-3 漂移 0.583：常数性没按**档位**分组，漂移全是换档 |
| A3-5, sign reversed | `open_tiers` changes the **threshold** and the **bidding pool** at once, so what was measured is the price response and not access. | A3-5 符号相反：`open_tiers` 同时改**门槛**和**竞标池**，量到的是价格反应不是准入 |

**Rule**: **move one thing at a time; where moving one is impossible, decompose
the compound operation and report the parts separately.** If a switch
necessarily changes two things, as `open_tiers` does in A3-5, then the arm with
**the other one frozen** has to be run alongside it, both reported, and the
difference between them is itself the result.

（**规则**：**一次只动一个东西；动不了一个的，把复合操作拆开单独报。** 若一个开关必然改
两样东西（如 A3-5），就必须同时跑「另一样被冻住」的那一臂，两个都报，差值本身是结果。）

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
