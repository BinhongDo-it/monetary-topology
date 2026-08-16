# B8 availability check: does the Fannie file carry what the loop needs?

**Status: check specification. Nothing retrieved, nothing run.** Written 2026-08-16.

Companion to [`b8_fannie_slice.md`](b8_fannie_slice.md), whose §10 step 2 registers
this as an availability check that **may terminate the stage**. Same role as
[`b3_slice_availability.md`](b3_slice_availability.md) and
[`a1_inputs_availability.md`](a1_inputs_availability.md), and the same rule:
**write the answer down whichever way it comes out.**

---

## 0. Inventory first, because the honest starting point is nothing

| what B8 would need | what exists |
|---|---|
| `data/fetch_fannie.py` | **does not exist** |
| `data/raw/fannie/` | **does not exist** |
| `experiments/b8_*.py` | **does not exist** |
| an entry in `data/SOURCES.md` | **none** |
| anything Fannie in the repository | **only `docs/b8_fannie_slice.md`, written 2026-08-16** |

**No Fannie row has ever been read by this project.** Everything below is a
specification of what to check, not a report of a check.

---

## 1. What the loop needs, field by field

`b8_fannie_slice.md` §3.1 fixes `ω` as the log ratio of the present value of the
remaining contractual obligation. That requires, **on both sides of a modification
and for the same loan**:

| field | used for | side |
|---|---|---|
| current interest rate | the payment stream | both |
| current actual UPB | the principal | both |
| remaining months to maturity | the horizon | both |
| delinquency status | the tier index `q` | path |
| modification flag | the `delinquent → modified` edge | path |
| zero balance code and its effective date | the hole: who exits to liquidation instead | §5's B8-5 |
| principal forgiveness amount | forgiveness, which is not deferral | `ω` |
| interest-bearing vs non-interest-bearing UPB | deferral, which is not forgiveness | `ω` |

From the acquisition side, for the agent classes of §5: credit score band, LTV,
DTI, first-time buyer flag, occupancy, property state, loan purpose, channel.

**The two UPB fields are not interchangeable and the check must confirm both are
present.** `b8_fannie_slice.md` §3.1 counts deferred principal at zero interest to
maturity and does **not** write it off; if only a single UPB field exists, that
distinction cannot be made and the `ω` construction has to be rewritten before
anything is computed.

---

## 2. The check that goes first, because it can change §11's branch table

**Is the modification programme identifiable?**

`b8_fannie_slice.md` §5 restricts B8-4 to the **Flex Modification** sub-population,
and the entire discriminating power of B8-4 rests on that restriction: Flex Mod is
rules-based, so *"the servicer priced the risk"* does not explain class dispersion
inside it. Outside it, B8-4 is reported but is **not** discriminating.

**A `modification flag` records that a loan was modified. It does not record under
which programme.** Whether the public file carries a programme identifier, or any
field from which HAMP-era and Flex-era modifications can be separated other than by
date, **is not known to this project** and is the first thing to establish.

Three outcomes, mapped here rather than after looking:

| finding | consequence |
|---|---|
| a programme field exists | B8-4 runs as registered |
| no programme field, but the eras are cleanly separated by date (HAMP wound down, Flex began) | B8-4 runs on a **date-defined proxy**, and the proxy is labelled as one wherever B8-4 is quoted. Discipline 6 applies: **the proxy's validity is checked before it is used**, by confirming that modification terms inside the Flex window actually cluster on a posted benchmark rather than dispersing with borrower risk |
| neither | **B8-4 loses its discriminating restriction.** It is demoted to a reported association, and `b8_fannie_slice.md` §11's first branch (B8-3 and B8-4 both pass → subprime auto ABS) becomes unreachable as written. §11 is then re-registered **before** B8 runs, not after |

**This ordering is the point of the section.** Discovering it after B8-4 has run
would mean choosing the branch table with the answer in hand.

---

## 3. The field-completeness audit proper

Sample: one acquisition and performance pair from each of several vintages, chosen
to span `b8_fannie_slice.md` §6's four windows. **Vintages are chosen by window
coverage, not by convenience, and the list is written down before retrieval.**

| # | check | terminates the stage if |
|---|---|---|
| **C1** | for loans where `modification flag` first turns Y, are rate, UPB and remaining maturity populated in the month **before** and the month **after** | the populated rate is low in any window. Report **per vintage**, not pooled: a field that appears in 2015 and not in 2009 kills one window and not the stage |
| **C2** | is the modification month identifiable, that is does the flag turn Y once and stay Y | the flag is not monotone and no other field dates the event |
| **C3** | do loans traverse the **full triangle**: current → delinquent → modified → current, with the post-modification return to a performing delinquency status observable | the third leg is unobservable, in which case the loop does not close and there is no stage |
| **C4** | **count** the loans completing the triangle, per window | the count is small. Conclusion 28's event-count wall applies: a discrete-event claim must count its events first, and no estimator repairs too few |
| **C5** | do loans that cure **without** modification exist in quantity | they do not, in which case **B8-0a has no sample** and the gate cannot be run, and per §8 nothing after the gate may be read |
| **C6** | are the two UPB fields both present, per §1 | only one exists, in which case `ω` is rewritten before anything is computed |
| **C7** | are the acquisition-side class fields present and populated for the loans that complete the triangle | they are missing, in which case B8-4 and B8-5 have no agent index and B8 collapses to B8-1 and B8-2 |

**C4 and C5 are counts, not rates, and they are reported as counts.** This project
has been stopped by an event-count wall once already and the diagnosis was that no
estimator could have saved it.

---

## 4. Retrieval, which is its own open question

Fannie's Single-Family Loan Performance data is published free, and access is
gated by registration and acceptance of a licence rather than by payment. **Whether
that gate can be scripted, and whether the licence permits the derived series to be
kept in this repository's `data/raw/`, is not established and must be read from the
licence rather than assumed.**

If the download cannot be scripted, this repository's fetch convention (resumable,
truncation-detecting, manifest with content hash, never deletes) applies to the
**post-download** handling instead, and that departure is recorded in
`data/SOURCES.md` rather than left implicit.

**Freddie Mac is a separate layout and is out of scope for this check.**
`b8_fannie_slice.md` §7 already fixes that Freddie is a distinct arm with its own
record, not a sample extension.

---

## 5. One item closed while writing this check: NMDB

`b1_theorem.md`'s Corollary 2 scoping block left an open question:

> **Whether NMDB links a borrower across successive loans is an availability
> question and is not settled here.**

**On what this repository holds, the answer is no.** `data/raw/nmdb/` contains
`nmdb_new_national.csv`, `nmdb_outstanding_national.csv` and
`nmdb_outstanding_states.csv`, 18 KB, 30 KB and 1.4 MB. Those are FHFA's published
**aggregate** statistics, and `data/fetch_nmdb.py`'s own docstring says it retrieves
the aggregate series for stage B2 loop B. **There is no loan-level NMDB here and the
loan-level product is restricted-use rather than downloadable.**

So NMDB does not reach the slice summand on anything obtainable, and the
borrower-linked panel candidate in Corollary 2's scoping block is **CRISM or
nothing**, at a price. This does not affect B8, whose entire cycle happens inside a
single loan and therefore needs no borrower linkage at all. **It affects the
alternative carriers, and it is recorded so the question is not re-opened as though
it were unexamined.**

---

## 6. What this check cannot decide

**It cannot decide whether `ω` is well constructed.** That is
`b8_fannie_slice.md` §10 step 1, it is paper work, and §3.2 is where a stage of this
shape goes wrong. A file that carries every field in §1 is still no guarantee that
the delinquency leg has been defined without padding.

**It cannot decide whether the loop sum is non-zero.** That is B8-1 and it is
downstream of everything here.

---

## 7. Status

Nothing retrieved. §2's programme-identifier question is unanswered and is the
first thing to establish. §3's seven checks are specified and unrun. §5 is the only
finding in this document and it came from reading what was already on disk.

---

# 实跑记录（2026-08-16）

**六个季度档全扫完毕，七条检查全过，本站不终止。**
脚本 `experiments/b8_layout_probe.py`、`b8_layout_probe_b.py`、`b8_field_audit.py`；
结果 `results/b8_layout_probe.md`、`b8_layout_probe_b.md`、`b8_field_audit.md`。

**规模**：170,013,011 行、2,942,295 笔贷款、六个收购季（§3 跑前钉死的那六个，未改）。

## R0 C0：布局一致

六档全部 **113 字段、pipe 分隔、前 1000 行零参差**，**CRC 六档全 ok**。
压缩比 13.9–16.1 倍：压缩态 3.1 GB，解压是 46.9 GB。**不解压、流式读 zip 成员的决定
实测省了十五倍磁盘，而且 CRC 是裸 CSV 拿不到的完整性检查。**

**但 113 ≠ 手上那份 2023-06 layout 的 108。** 外部核对未通过，故 C0b 存在。

## R1 C0b：位置由数据确认，不由文档

十八个锚点在六档上**全部 1.000**，无一 0.99x。五个多出的字段**追加在 109–113**，
1–108 未动。

**顺带得到本站最有价值的结构结论**：六档的 `id runs` 与 `distinct loan ids`
**逐位相等**，即**每笔贷款的行完全连成一块**。B8 因此可以单趟流式、按贷款分块、
常数内存，**46.9 GB 从头到尾不需要被持有，也不需要排序**。§3 原先要为排序留的预算是零。

**一处更正入档**：C0b 的锚点最高只到 44，所以它的「1–108 未动」当时超出了证据。
45–108 由 C1–C7 的行为画像补齐（63、64、106 各自在修改行上的行为与文档一致）。

## R2 §2 的第一个问题：没有修改项目标识符

**确认。** 42 号只有 Y/N。106 号是 Alternative Delinquency Resolution，
取值 `7 / C / P / D`，**`7` 是「以上皆非」不是数据**——102 与 106 的**空白行数完全相同**
（同一批引入），而 `7` 的计数差 38,356 恰等于两者非 `7` 值总数之差。
v1 与 v2 把 `7` 当填充，62.5% 就是这么来的。

**§2 映射的第二支触发**：只能用日期代理，且代理效度须先验。**但见 R6，那条路比预想的窄。**

## R3 C1：`ω` 的三个分量齐了，靠 17 号不靠 18 号

| | prev | at | next |
|---|---|---|---|
| 9 现行利率 | 1.0000 | 1.0000 | 0.989–0.999 |
| 12 现行 UPB | 1.0000 | 1.0000 | 0.996–1.000 |
| **17 剩余法定期限** | 1.0000 | **0.9514–1.0000** | 0.948–0.999 |
| 18 剩余期限 | 1.0000 | **0.0000** | ≤0.0056 |
| 19 到期日 | 1.0000 | 同 17 | 同 17 |

**18 号一旦修改就永久变空，六档无例外。17 与 19 照常填**（最差 0.9514，在 2002Q1）。
`ω` 用 17，或用 19 减 3 自己算。**C1 通过。**

## R4 C2 与状态标记：两个字段都不持久

| | Y 到末尾 | 一个 Y 块然后转 N |
|---|---|---|
| 2002Q1 | 893 | 5,900 |
| 2006Q1 | 2,019 | 11,671 |
| 2007Q1 | 2,574 | 15,287 |
| 2012Q1 | 1,179 | 1,897 |
| 2017Q1 | 3,190 | 2,703 |
| 2019Q1 | 3,472 | 1,512 |
| **合计** | **13,327** | **38,970** |

**四分之三回落。** 63 号同样回落（老 cohort 上八成），且 2002Q1 有 1,329 笔修改贷款
**根本没有 63**（该字段生得晚）。

**裁定：数据里没有持久的「已修改」状态标记。42 号定事件月份，状态由分析者 carry forward。**
`b8_fannie_slice.md` §2 关于 `modified` 节点的写法照此改。

## R5 C3/C4/C5/C6/C7：全部通过

**C4**（按事件月份分窗）：

| 路线 | 危机前 | HAMP | Flex | COVID | post-2022 | 合计 |
|---|---|---|---|---|---|---|
| 修改 | 3,315 | **33,316** | 4,655 | 7,122 | 2,878 | **51,286** |
| 递延 | 0 | 0 | 0 | **31,057** | 1,476 | **32,533** |

递延码：`C` 34,030、`P` 1,464、`D` 123。**四个窗口都有样本，结论 28 的事件量墙不触发。**

**C5**：清洁自愈 **366,345** 笔。B8-0a 的闸有样本。
**C6**：63、64、106、107、108 全部存在且填充。
**C7**：完成三角的贷款上，class 字段最差 0.9621（2002Q1 的 DTI），其余基本 1.0000。

## R6 一条本站没在找、但找到了的东西，并撤回一个提法

到期日在修改时的移动比例与中位延长月数按档差异极大：

| | 移动比例 | 中位延长月数 |
|---|---|---|
| 2002Q1 | 0.6713 | 35 |
| 2006Q1 | 0.7497 | 112 |
| 2007Q1 | 0.7413 | 113 |
| 2012Q1 | 0.9885 | 187 |
| 2017Q1 | 0.9850 | 173 |
| 2019Q1 | 0.9921 | 158 |

**曾提出可以用「延到 480 个月」这个指纹识别 Flex Mod 而不必有字段。撤回。**
cohort 与窗口在这张表里混淆：2012Q1 的修改横跨 HAMP(1,145)/Flex(1,044)/COVID(586)
而仍有 98.85% 移动，2007Q1 的修改九成在 HAMP 窗口却只有 74% 移动。**同窗口、不同 cohort、
行为差很远，所以那不是项目的指纹。**

**它是贷款自身发放利率的指纹**：2002–2007 那批发放在 6–7%，降利率就能救；
2012–2019 那批发放在 3–4.5%，没有利率可降，唯一杠杆是延期限。

**对 `ω` 的后果**：修改的价值变化在老 cohort 由利率驱动、在新 cohort 由期限驱动，
PV 计算两者都吃得下。**但 B8-4 的类间离散必须对 cohort 的利率环境取条件**，
否则 cohort 效应会伪装成类效应。写进 §10 第 1 条。

## R7 §5 结清：NMDB 那条

`b1_theorem.md` Corollary 2 收窄块留的「NMDB 是否按借款人跨笔链接」——**就可下载的口径而言
是否**。`data/raw/nmdb/` 里是 FHFA 的**聚合**统计（18 KB / 30 KB / 1.4 MB），
`fetch_nmdb.py` 自述取的是 B2 loop B 的聚合序列。贷款级 NMDB 是受限用途。
**borrower-linked panel 那条候选因此是 CRISM 或者没有，要花钱。本站不受影响**
（B8 的环整个发生在一笔贷款内部）。

## R8 一个抽样方法的验证，附带产出

字段 111 在 2002–2024 **逐年 0.0000**，2025 年 **0.0797**，2026 年 **0.9991**。
**它诞生于 2025 年末。**

C0b 的头部抽样曾看到它「随 vintage 单调上升」，那是假象：文件按贷款排序，头部是
**最早的日历月份**，一个有诞生日期的字段在老 cohort 的头部必然为空。

**这正是 C1/C6 必须全扫不能抽头的理由，现在有 25 年 1.7 亿行的实测支撑。**
任何 2025 年才诞生的字段对窗口截止在 2022 年的 B8 都没用。

## R9 裁定

**本站不终止。§3 的七条检查全部通过，§10 第 3 步之后的动作可以开始。**

**下一步是 §10 第 1 步，不是写代码**：三条边的 `ω` 构造完整写在纸上，
含 R6 那条 cohort 条件。§3.2 是这种站会出错的地方。

---

# 6. C8：`ω` 编码之前必须结清的算术

由 `b8_fannie_slice.md` §14.8 注册到这里，理由写在那一节：**答案属于可得性记录，
不属于某个实验脚本的内部。** 六条全部是数数，都不构成预测，**没有一条会终止本站**，
每一条的任何结果都只是一个构造选择，先问的意义在于这个选择是对着文件做的、不是对着
结果做的。

| # | 问题 | 为什么它改变 `ω` |
|---|---|---|
| **C8-1** | 字段 12 **含不含** 字段 63 | 决定计息余额是 `12 − 63` 还是 `12`。在递延当月读：12 是掉了约等于 63 的一笔，还是纹丝不动 |
| **C8-2** | 字段 64 是当期额还是累计额 | 累计额每月减一次，等于把同一笔本金反复减免 |
| **C8-3** | 字段 63 是余额还是累计递延 | 实跑发现 63 会重新变空，**余额会这样，累计额不会** |
| **C8-4** | 修改当月，字段 12 有没有**上跳**一笔资本化欠款 | 没有的话欠款不在余额里，第二条边的残差就漏了它 |
| **C8-5** | 17 与 19 在两者都有的地方是否一致 | 实跑说完全吻合，**在修改月上再确认一次** |
| **C8-6** | 107、108 是不是在描述递延，108 与 63 的变动对不对得上 | §14.4 的 `deferred` 层需要递延额能从一个字段读出来，不能靠推 |

**C8 的输出追加到本文件，不是只写进 `results/`。**

## 6.1 本站此刻的执行顺序

1. **C8**，一个脚本，六个计数。
2. `experiments/b8_omega.py`：只有 `V`、`V̂`、`r(t)`，别的都不要。**先用手算的
   摊还表做单元测试，再让它碰真贷款。**
3. **B8-0a(i)** 闸，然后 B8-0a(ii)。
4. B8-0b，然后各条预测，每条都跑 §14.4 的两张网格。
