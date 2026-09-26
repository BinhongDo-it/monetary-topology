"""B102: two published block schedules on one position axis.

A Chinese residential electricity tariff defines a price on a pair: which class
of household is buying, and which kilowatt hour of the month it is. Both indices
are published, both before any electricity is used, and neither is inferred from
a transaction. That makes the whole object readable off paper.

The class index is not a label this station invented. The provinces write it. A
household of five or six people (the threshold is provincial) may register and
then face a different set of block boundaries for the same month, the same grid,
the same voltage and the same kilowatt hour. Nothing about the commodity changes;
the buyer does.

**Two arms, one position axis, two class dimensions.**

  arm A   class = tier,      position = time of day
  arm B   class = household,  position = cumulative kilowatt hours this month

**Three rivals, and they are not the same claim.**

    bare        P(a, j) = phi(j)                one scalar per position
    additive    P(a, j) = phi(j) + psi(a)        class enters as a level shift
    multiplicative  P(a, j) = alpha_a * phi(j)   class enters as a scale

The first predicts the class difference is zero everywhere. The second predicts
it is a constant in j, so every four-cycle sum is exactly zero. The third permits
the difference to vary with j but not to change sign, because it is the same
price curve scaled. Each is registered on its own and scored on its own, because
they fail on different readings and folding them would hide which one died.

**What the class difference does here.** With the ordinary boundaries at T1 and
T2 and the registered household's at T1+s and T2+s, the difference

    d(j) = P(ordinary, j) - P(registered, j)

is zero below T1, equal to the second tier's increment between T1 and T1+s, zero
again to T2, equal to the third increment minus the second between T2 and T2+s,
and zero above. It leaves zero and returns to zero twice. A constant cannot do
that, a scaled copy of a non-decreasing price cannot do that, and the sign of the
four-cycle sum flips at each return.

**d does not depend on the base price.** Only on the increments and on where the
boundaries sit relative to one another, which is why a province that publishes
increments without a base is still fully readable here, and why two provinces
with different absolute prices can have identical d.

**A province whose ordinary boundaries were not read lands in the third cell.**
The shape of d is known from the shift alone, but the positions where it steps
are not, so the pointwise reading has no object. That is recorded as undecided,
not as a reading that came out false.

Run:
    python experiments/b102_cn_power_tariff.py
    python experiments/b102_cn_power_tariff.py --selftest
"""

import argparse
import json
import pathlib
import sys

# Money is carried as an integer count of 0.0001 yuan so that every comparison
# and every difference is exact. A float tail from one machine's libm is the
# thing the derived-file rule is there to keep out of a committed record.
TICK = 10000  # units per yuan


def y(value):
    """Yuan as a string to integer units. Exact: no float ever enters."""
    text = str(value)
    if "." not in text:
        text = text + ".0"
    whole, frac = text.split(".")
    frac = (frac + "0000")[:4]
    sign = -1 if whole.startswith("-") else 1
    return sign * (abs(int(whole)) * TICK + int(frac))


def fmt(units):
    """Integer units back to a fixed four-decimal string. No repr, no bare str."""
    sign = "-" if units < 0 else ""
    units = abs(units)
    return sign + str(units // TICK) + "." + str(units % TICK).rjust(4, "0")


# ---------------------------------------------------------------------------
# Arm A: class = tier, position = time of day.
#
# Each entry gives, per tier, the published price in each period. A province
# that publishes increments rather than levels is entered as increments; the
# square is the same either way because the base cancels.
# ---------------------------------------------------------------------------

ARM_A = {
    "shanghai": {
        "source": "Shanghai DRC tiered-tariff implementation notice, read in the "
                  "browser and checked twice against the original sentences",
        "kind": "increments",
        "periods": ["peak", "valley"],
        "tick": y("0.01"),
        "tiers": {
            "1": {"peak": y("0.00"), "valley": y("0.00")},
            "2": {"peak": y("0.06"), "valley": y("0.03")},
            "3": {"peak": y("0.36"), "valley": y("0.18")},
        },
    },
    "shandong": {
        "source": "Tai'an municipal reprint of the provincial notice, PDF",
        "kind": "levels",
        "periods": ["peak", "valley"],
        "tick": y("0.0001"),
        "tiers": {
            "1": {"peak": y("0.5769"), "valley": y("0.3769")},
            "2": {"peak": y("0.6269"), "valley": y("0.4269")},
            "3": {"peak": y("0.8769"), "valley": y("0.6769")},
        },
    },
    "zhejiang": {
        "source": "provincial compilation, level: other (D32), original not yet checked",
        "kind": "levels",
        "periods": ["peak", "valley"],
        "tick": y("0.0001"),
        "tiers": {
            "1": {"peak": y("0.5680"), "valley": y("0.2880")},
            "2": {"peak": y("0.6180"), "valley": y("0.3380")},
            "3": {"peak": y("0.8680"), "valley": y("0.5880")},
        },
    },
    "sichuan": {
        "source": "the Xuzhou district implementing guide's worked example, "
                  "where a 400 kilowatt hour month split 100 peak, 150 flat and "
                  "150 valley is charged the tier surcharge on quantity alone",
        "kind": "increments",
        "periods": ["flat", "valley"],
        "tick": y("0.0001"),
        "tiers": {
            "1": {"flat": y("0.0000"), "valley": y("0.0000")},
            "2": {"flat": y("0.1000"), "valley": y("0.1000")},
            "3": {"flat": y("0.3000"), "valley": y("0.3000")},
        },
    },
    "jiangsu": {
        "source": "Yixing municipal explainer of the provincial tiered tariff, "
                  "which prints the block increments and the two period prices "
                  "without ever qualifying one by the other; the province also "
                  "bills 先峰谷后阶梯, period first and block second, which is "
                  "the same construction as Guangdong's",
        "kind": "increments",
        "periods": ["peak", "valley"],
        "tick": y("0.0001"),
        "tiers": {
            "1": {"peak": y("0.0000"), "valley": y("0.0000")},
            "2": {"peak": y("0.0500"), "valley": y("0.0500")},
            "3": {"peak": y("0.3000"), "valley": y("0.3000")},
        },
    },
    "shenzhen": {
        "source": "Shenzhen DRC residential price schedule, PDF, official",
        "kind": "levels",
        "periods": ["peak", "flat", "valley"],
        "tick": y("0.0001"),
        "tiers": {
            "1": {"peak": y("1.1121"), "flat": y("0.6542"), "valley": y("0.2486")},
            "2": {"peak": y("1.1621"), "flat": y("0.7042"), "valley": y("0.2986")},
            "3": {"peak": y("1.4121"), "flat": y("0.9542"), "valley": y("0.5486")},
        },
    },
}

# Provinces whose arm-A square is registered to be zero because the published
# text carries one increment for all periods. Read back, they must return zero.
ARM_A_ZERO = ["shandong", "zhejiang", "shenzhen", "sichuan", "jiangsu"]

# ---------------------------------------------------------------------------
# Arm B: class = household type, position = cumulative kilowatt hours.
#
# `bounds` are the upper edges of the finite blocks, ordinary schedule first.
# `shift` is how much each finite edge moves for the registered household; an
# entry of None means the province delegated the structure and it was not read.
# `increments` are the published per-tier increments over tier one.
# ---------------------------------------------------------------------------

ARM_B = {
    "beijing": {
        "source": "Beijing DRC notice on multi-person households, its policy "
                  "explainer, and the municipal retail price schedule (three "
                  "official documents)",
        "threshold_people": 6,
        "bounds_ordinary": [240, 400],
        "bounds_registered": [340, 500],
        "increments": [y("0.0000"), y("0.0500"), y("0.3000")],
        "levels": [y("0.4883"), y("0.5383"), y("0.7883")],
        "tick": y("0.0001"),
        "note": "the explainer says the added kilowatt hours go on the first "
                "tier while the block table moves both finite edges by 100; "
                "both sentences are official and they do not say the same "
                "thing. The block table is used here because it is the one "
                "that can be put straight into the price schedule. Recorded "
                "rather than flattened.",
    },
    "guangdong_summer": {
        "source": "Guangdong DRC letters 2021/826 and 2023/553 for the shift, "
                  "Guangzhou DRC price explainer for the ordinary boundaries "
                  "and the increments",
        "threshold_people": 5,
        "bounds_ordinary": [260, 600],
        "bounds_registered": [360, 700],
        "increments": [y("0.0000"), y("0.0500"), y("0.3000")],
        "levels": None,
        "tick": y("0.01"),
        "note": "increments published without a base; d does not need one.",
    },
    "guangdong_nonsummer": {
        "source": "same two letters and the same explainer",
        "threshold_people": 5,
        "bounds_ordinary": [200, 400],
        "bounds_registered": [300, 500],
        "increments": [y("0.0000"), y("0.0500"), y("0.3000")],
        "levels": None,
        "tick": y("0.01"),
        "note": "",
    },
    "hunan_springautumn": {
        "source": "Hunan DRC 2024/14 (湘发改价调规), full text, republished by "
                  "Huarong county government with the document number",
        "threshold_people": 5,
        "bounds_ordinary": [200, 350],
        "bounds_registered": [300, 350],
        "increments": [y("0.0000"), y("0.0500"), y("0.3000")],
        "levels": [y("0.588"), y("0.638"), y("0.888")],
        "tick": y("0.001"),
        "note": "March, April, May, September, October, November. The notice "
                "raises the first tier's base alone, so the second edge stays "
                "where it is. Guangdong raises all three. Same national "
                "increments, same 100 kilowatt hours, different structure, and "
                "both provinces say which one in their own text.",
    },
    "hunan_wintersummer": {
        "source": "same notice, the other season",
        "threshold_people": 5,
        "bounds_ordinary": [200, 450],
        "bounds_registered": [300, 450],
        "increments": [y("0.0000"), y("0.0500"), y("0.3000")],
        "levels": [y("0.588"), y("0.638"), y("0.888")],
        "tick": y("0.001"),
        "note": "January, February, June, July, August, December. Same levels "
                "and same tick as the other season: a province publishes one "
                "price list, and the seasons differ only in where the second "
                "edge sits.",
    },
    "sichuan_summer_five": {
        "source": "the 2026 provincial adjustment as reported with the DRC's "
                  "own explanation, for the ordinary summer blocks; the "
                  "registered blocks are derived, see note",
        "threshold_people": 5,
        "bounds_ordinary": [260, 460],
        "bounds_registered": [360, 560],
        "increments": [y("0.0000"), y("0.1000"), y("0.3000")],
        "levels": None,
        "tick": y("0.0001"),
        "note": "July to September from 2026-07-01: ordinary blocks 0-260, "
                "261-460, 460 and up, with the prices unchanged at 0.5224, "
                "0.6224 and 0.8224, which confirms the 0.10 increment "
                "independently. The registered blocks are DERIVED, not quoted: "
                "the implementing guide moves both edges by 100 and the "
                "adjustment says 阶梯电量基数同步调整. Recorded as derived so "
                "that a later reader does not take it for a quotation. This "
                "row exists because it gives the same province two shapes in "
                "two seasons off one policy: the summer second block is 200 "
                "wide against a shift of 100, so the segment where the "
                "difference returns to zero survives, while in the other "
                "months that block is exactly 100 wide and it collapses. Same "
                "province, same rule, same shift, different arithmetic, "
                "different shape.",
        "derived_registered_bounds": True,
    },
    "sichuan_five": {
        "source": "Sichuan DRC 2024/668 for the policy; the implementing guide "
                  "issued by Xuzhou district, Yibin, for the blocks and the "
                  "increments, with two worked examples",
        "threshold_people": 5,
        "bounds_ordinary": [180, 280],
        "bounds_registered": [280, 380],
        "increments": [y("0.0000"), y("0.1000"), y("0.3000")],
        "levels": None,
        "tick": y("0.0001"),
        "note": "October to June, and from 2026-07-01 this is the "
                "non-summer schedule rather than the whole year. Sichuan's "
                "second-tier increment is 0.10, not the 0.05 every "
                "other province read here took. The national guidance set 0.05 "
                "as a floor, not a number, and this province went to double it. "
                "The guide states it twice, in words and in a worked example "
                "where 0.5224 becomes 0.6224. Level: an implementing guide "
                "republished, not the provincial price notice itself.",
    },
    "sichuan_six": {
        "source": "same guide, its second worked example",
        "threshold_people": 6,
        "bounds_ordinary": [180, 280],
        "bounds_registered": [310, 410],
        "increments": [y("0.0000"), y("0.1000"), y("0.3000")],
        "levels": None,
        "tick": y("0.0001"),
        "note": "October to June, as above. Above five people the base rises "
                "30 kilowatt hours per person "
                "per month, so a six-person household's edges are 280+30 and "
                "380+30. The class is a family indexed by household size rather "
                "than a two-way split, and this is the second member of it.",
    },
    "shanghai": {
        "source": "Shanghai DRC notice on water, electricity and gas (2020) for "
                  "the policy and 沪发改价管〔2012〕020号 for the blocks; the "
                  "resulting edges from Xinmin Evening News the day after the "
                  "policy took effect, with a worked example",
        "threshold_people": 5,
        "bounds_ordinary": [3120, 4800],
        "bounds_registered": [4320, 6000],
        "increments": [y("0.0000"), y("0.0500"), y("0.3000")],
        "levels": [y("0.617"), y("0.667"), y("0.917")],
        "tick": y("0.01"),
        "note": "neither notice names a tier; the clause stops at 每户每月增加"
                "100度的阶梯电量基数. The edges come from the newspaper's "
                "restatement, 第一档为0-4320度(360×12); 第二档为4320-6000度, "
                "and from its worked example, where a 6000 kilowatt hour year "
                "is charged 4320 at the first price and the rest at the first "
                "price plus 0.05. Both finite edges move by 1200. Blocks are "
                "annual here, unlike every other province in this table.",
    },
    "anhui": {
        "source": "Anhui DRC notice on the multi-person policy, republished in "
                  "full with the issuing body named",
        "threshold_people": 5,
        "bounds_ordinary": [180, 350],
        "bounds_registered": [280, 450],
        "increments": [y("0.0000"), y("0.0500"), y("0.3000")],
        "levels": None,
        "tick": y("0.01"),
        "note": "the notice prints the registered household's blocks, "
                "第一档电量为0-280千瓦时，第二档电量为281-450千瓦时，第三档电量为"
                "451千瓦时及以上, and says they follow from adding 100. The "
                "ordinary edges are that arithmetic run backwards and are "
                "recorded as derived rather than quoted. Seven and up may also "
                "elect the pooled rate, whose number has not been read.",
    },
    "jiangsu": {
        "source": "the provincial DRC's reply to proposal 1164 of the 2021 "
                  "provincial congress, which restates 苏发改价格发〔2021〕106号",
        "threshold_people": None,
        "bounds_ordinary": None,
        "bounds_registered": None,
        "shift_pattern": "100 kilowatt hours a month at five people; which "
                         "edges that moves is not stated in any text found, "
                         "exactly as in Shanghai's and Sichuan's notices",
        "increments": [y("0.0000"), y("0.0500"), y("0.3000")],
        "levels": None,
        "tick": None,
        "note": "the amount is known and the structure is not, so this row "
                "stays in the third cell with its numbers ready. The reply "
                "gives the blocks as monthly 230 and 400 at 0.5283, 0.5783 and "
                "0.8283. That corrects something written earlier in this "
                "station's life: a caliber warning said Jiangsu had moved to "
                "annual blocks in 2021 and that the Yixing figures were stale. "
                "It had no source, it was inferred from a headline that was "
                "never opened, and this text says the blocks are monthly and "
                "unchanged. Withdrawn.",
        "bounds_if_settled": [230, 400],
        "shift_if_settled": 100,
    },
}


# ---------------------------------------------------------------------------
# Arm C: the low-income allowance, and a published mechanism that is neither
# of the two this arm was first written to choose between.
#
# Several provinces give a household on income support a free quota. This arm
# was registered asking whether the quota comes off the metered quantity before
# the blocks apply, which would move every edge, or off the bill afterwards,
# which would leave the marginal price alone and make it a transfer. Yixing's
# explainer of the Jiangsu rule answers with a third thing:
#
#     由供电企业从其抄表月份第一档电量中扣除对应的免费电量后计算当月应收电费
#
# The deduction comes out of the first block's quantity. The edges do not move
# and the bill is not credited after the fact; the first fifteen kilowatt hours
# of the month are simply priced at zero for that class. So the class difference
# is the full first-tier price on those fifteen positions and zero on every
# position after them, and the single square is the whole price of the good.
#
# Shanghai's rule has the same shape on a different axis: the quota bites in the
# peak bucket rather than in the first block, so what is free is a time of day
# rather than a place in the month's running total.
#
# **A household above the quota pays the same money either way.** A refund of
# fifteen times the first-tier price and a price of zero on the first fifteen
# kilowatt hours differ in the schedule, not in the bill, for anyone who uses
# more than fifteen. What this arm reads is the schedule, which is what the
# rivals make claims about; it does not claim the money differs.
# ---------------------------------------------------------------------------

ARM_C = {
    "jiangsu": {
        "source": "Yixing municipal government's explainer of the provincial "
                  "tiered tariff (2014) for the mechanism, and Lianyungang's "
                  "current municipal Q&A for the same sentence, the same "
                  "fifteen kilowatt hours, and the added fact that the free "
                  "quantity is settled annually",
        "quota_kwh": 15,
        "classes": "城乡低保户 and 农村五保户",
        "deducts_from": "the first block's quantity for that month",
        "bites_price": y("0.5283"),
        "bites_price_name": "the undifferentiated first-tier price",
        "tick": y("0.0001"),
        "note": "由供电企业从其抄表月份第一档电量中扣除对应的免费电量后计算当月"
                "应收电费. The deduction comes out of the first block, so the "
                "block edges do not move and the first fifteen kilowatt hours "
                "are priced at zero for that class. Level: two municipal "
                "explainers of a provincial rule, 2014 and current, agreeing "
                "word for word. The 0.5283 is the undifferentiated residential "
                "price and the provincial DRC still gives it as that in 2021, "
                "so it is stable across at least seven years.",
    },
    "shanghai": {
        "source": "沪发改价管〔2012〕020号, quoted",
        "quota_kwh": 15,
        "classes": "低保户",
        "deducts_from": "the peak period's quantity first, then the valley's, "
                        "capped at actual use",
        "bites_price": y("0.617"),
        "bites_price_name": "the first-tier price, which is what a peak "
                            "kilowatt hour costs before the tier surcharge",
        "tick": y("0.01"),
        "note": "先扣减峰时段电量，后扣减谷时段电量，最多不超过实际用电量. The "
                "quota bites in the peak bucket rather than the first block, "
                "so the position it is free on is a time of day rather than a "
                "place in the month's running total. Same shape, different axis.",
    },
    "hunan": {
        "source": "Hunan DRC 2024/14, the provincial original read in full",
        "quota_kwh": 10,
        "classes": "最低生活保障户 and 城乡特困人员救助户",
        "deducts_from": "the first block's quantity, stated as 免费用电量纳入"
                        "第一档分档电量",
        "bites_price": y("0.588"),
        "bites_price_name": "the first-tier base price below 1 kV, printed in "
                            "the same notice",
        "tick": y("0.001"),
        "note": "the province says in five characters what Jiangsu says in a "
                "municipal explainer: the free quantity is counted into the "
                "first block. Two provinces, worded independently, same "
                "mechanism.",
    },
    "anhui": {
        "source": "the provincial implementing rules as reported in 2012, and "
                  "Xuancheng's explainer, which grants the quota and says "
                  "具体办法另行规定",
        "quota_kwh": 10,
        "classes": "城乡低保户 and 农村五保户",
        "deducts_from": None,
        "bites_price": None,
        "tick": None,
        "mechanism": "transfer",
        "note": "采取先征后返方式，由民政部门统一将退电费款发放到低保户、五保户的"
                "存折上. Jilin's mechanism in different words and through the "
                "same department: the money is refunded by civil affairs into a "
                "passbook, nothing leaves any block, and the marginal price is "
                "untouched at every position. Two provinces do it this way and "
                "two do it as a price, and all four say which in their own rule.",
    },
    "jilin": {
        "source": "Jilin City's published answers on current water, heat, gas "
                  "and electricity policy",
        "quota_kwh": 10,
        "classes": "城乡低保户 and 农村五保户",
        "deducts_from": None,
        "bites_price": None,
        "tick": None,
        "mechanism": "transfer",
        "note": "先收后返. The household pays the ordinary bill, the supply "
                "company works out what the free quantity was worth, the "
                "provincial finance department pays it to civil affairs, and it "
                "is handed back together with the 低保 payment itself. Nothing "
                "is deducted from any block. This is the failure case for this "
                "arm and it is published: the marginal price is untouched at "
                "every position, so by the rule about two prices this is a "
                "transfer and not a price, and it does not enter the station. "
                "Three provinces do it as a price and this one does it as a "
                "transfer, and each of them says which in its own rule.",
    },
}


# ---------------------------------------------------------------------------
# Arm D: a household of seven or more in Shanghai may elect a flat surcharge.
#
# 户籍人口为7人及以上的家庭，也可以选择按照每度电 0.024 元加价计费.
#
# That replaces the block structure with one number for every kilowatt hour, so
# the two classes face price curves of different shape rather than different
# level. The class difference is the ordinary increment minus the flat one, and
# it is negative on the first tier and positive on the other two: an ordinary
# household pays less early in the year and more later. That crossing is what
# kills the multiplicative rival on this arm, by a different route than the
# alternating squares of arm B.
# ---------------------------------------------------------------------------

# One table, two class dimensions, and only one of them is additive.
#
# Anhui's residential price table prints every row at two voltages. The gap is
# 0.0150 on the first tier, on the second, on the third and on the pooled rate:
# four rows, one constant. So the voltage dimension is a level shift and its
# square is zero, exactly as the additive rival says a class index should
# behave. The household dimension sits in the same table and is not.
#
# That is the cleanest form the reading takes. It is not that published tariffs
# are non-additive in general; it is that some of their class dimensions are and
# some are not, and the same document shows both.
VOLTAGE_ROWS = {
    "anhui": {
        "source": "Anhui residential price table (Lu'an DRC) and Xuancheng's "
                  "explainer, which print the same four rows at two voltages",
        "below_1kv": [y("0.5653"), y("0.6153"), y("0.8653"), y("0.5853")],
        "one_to_ten_kv": [y("0.5503"), y("0.6003"), y("0.8503"), y("0.5703")],
        "row_names": ["tier 1", "tier 2", "tier 3", "pooled rate"],
        "tick": y("0.0001"),
    },
    "beijing": {
        "source": "Beijing municipal retail price schedule, table 1",
        "below_1kv": [y("0.4883"), y("0.5383"), y("0.7883")],
        "one_to_ten_kv": [y("0.4783"), y("0.5283"), y("0.7783")],
        "row_names": ["tier 1", "tier 2", "tier 3"],
        "tick": y("0.0001"),
    },
}


# Considered for arm D and kept out, with the reason, so that the next reader
# does not have to work out afresh why a published flat surcharge is missing.
ARM_D_EXCLUDED = {
    "hunan_pooled": {
        "source": "Hunan DRC 2024/14",
        "flat_surcharge": "0.016 yuan on every kilowatt hour, no blocks",
        "why_out": "this rate is for dwellings with no household meter, not an "
                   "option a metered household may elect. Without a household "
                   "meter the position index, the j-th kilowatt hour of this "
                   "household's month, is not defined on that side, so the two "
                   "classes are not standing at the same position and the "
                   "square has no object. The elective versions in Shanghai, "
                   "Guangdong and Anhui are different: those households keep "
                   "their own meter and elect the rate.",
    },
    "hunan_nonresidential": {
        "source": "Hunan DRC 2024/14",
        "flat_surcharge": "0.046 yuan on every kilowatt hour, no blocks",
        "why_out": "a different kind of buyer altogether, schools and welfare "
                   "premises rather than households, so the class is not the "
                   "one this station indexes on.",
    },
}

ARM_D = {
    "shanghai_seven": {
        "source": "沪发改价管〔2012〕020号, quoted",
        "threshold_people": 7,
        "flat_surcharge": y("0.024"),
        "increments": [y("0.0000"), y("0.0500"), y("0.3000")],
        "bounds": [3120, 4800],
        "tick": y("0.001"),
        "note": "the flat surcharge is printed to three decimals and the block "
                "increments to two, so the finer of the two published ticks "
                "governs. The option is elective within the class: a household "
                "of seven may take it or stay on the blocks, and one of four "
                "cannot take it at all.",
        "elective_within_class": True,
    },
    "anhui_seven": {
        "source": "Anhui's residential price table (Lu'an DRC) for the levels "
                  "and the pooled rate, Xuancheng's explainer for the same "
                  "numbers and the wording 每度提高2分钱但不执行阶梯分档, and "
                  "the provincial multi-person notice for who may elect it",
        "threshold_people": 7,
        "flat_surcharge": y("0.0200"),
        "increments": [y("0.0000"), y("0.0500"), y("0.3000")],
        "bounds": [180, 350],
        "tick": y("0.0001"),
        "note": "0.5853 against a first tier of 0.5653, so the surcharge is "
                "0.02 flat with no blocks. Three provinces now offer this and "
                "all three put the flat number strictly inside the first "
                "block's gap of 0.05: Anhui 0.020, Shanghai 0.024, Guangdong "
                "0.037. None of them had to.",
        "elective_within_class": True,
    },
    "jiangsu_seven": {
        "source": "the provincial DRC's reply to proposal 1164 of the 2021 "
                  "provincial congress, quoting 苏发改价格发〔2021〕106号",
        "threshold_people": 7,
        "flat_surcharge": y("0.0200"),
        "increments": [y("0.0000"), y("0.0500"), y("0.3000")],
        "bounds": [230, 400],
        "tick": y("0.0001"),
        "note": "人数满7人及以上的，也可选择申请执行居民合表电价（高于居民生活用电"
                "基本电价每度电2分钱），不执行阶梯式电价. Same flat number as "
                "Anhui's and the same clause shape as Shanghai's and "
                "Guangdong's: the household keeps its own meter and elects the "
                "pooled rate.",
        "elective_within_class": True,
    },
    "guangdong_seven": {
        "source": "粤价〔2012〕146号 for the flat surcharge, quoted by the "
                  "provincial DRC's own price desk; 粤发改价格函〔2021〕826号 "
                  "for who may elect it",
        "threshold_people": 7,
        "flat_surcharge": y("0.037"),
        "increments": [y("0.0000"), y("0.0500"), y("0.3000")],
        "bounds": [260, 600],
        "tick": y("0.001"),
        "note": "the pooled-meter rate is the residential rate raised by a "
                "flat 0.037 yuan on every kilowatt hour, with no blocks. A "
                "household of seven or more may elect it. Guangdong and "
                "Shanghai chose different flat numbers, 0.037 and 0.024, and "
                "both landed strictly inside the first block's gap of 0.05, "
                "which is what produces the crossing in each.",
        "elective_within_class": True,
    },
}


def arm_d_readings(spec):
    """Class difference per tier, and the squares between tiers."""
    d = [inc - spec["flat_surcharge"] for inc in spec["increments"]]
    squares = []
    for i in range(len(d) - 1):
        for j in range(i + 1, len(d)):
            squares.append({"tier_low": i + 1, "tier_high": j + 1,
                            "square": fmt(d[j] - d[i])})
    return d, squares


def tier_at(j, bounds):
    """Which tier the j-th unit falls in, given the finite upper edges."""
    for index, edge in enumerate(bounds):
        if j <= edge:
            return index
    return len(bounds)


def difference_steps(spec):
    """The class difference as a list of (lo, hi_or_None, value) segments.

    Built from the definition: the segment edges are the union of the two block
    edge sets, and on each segment the difference is the ordinary increment
    minus the registered one.
    """
    a, b = spec["bounds_ordinary"], spec["bounds_registered"]
    inc = spec["increments"]
    edges = sorted(set(a) | set(b))
    segments = []
    lo = 1
    for edge in edges:
        value = inc[tier_at(lo, a)] - inc[tier_at(lo, b)]
        segments.append((lo, edge, value))
        lo = edge + 1
    value = inc[tier_at(lo, a)] - inc[tier_at(lo, b)]
    segments.append((lo, None, value))
    return segments


def difference_scan(spec, upper):
    """The same difference, by walking every position. An independent path.

    This shares no code with `difference_steps` beyond `tier_at`, which is the
    definition of a block tariff and not a step of either construction.
    """
    a, b = spec["bounds_ordinary"], spec["bounds_registered"]
    inc = spec["increments"]
    return [inc[tier_at(j, a)] - inc[tier_at(j, b)] for j in range(1, upper + 1)]


def steps_to_scan(segments, upper):
    out = []
    for lo, hi, value in segments:
        top = upper if hi is None else min(hi, upper)
        for _ in range(lo, top + 1):
            out.append(value)
        if hi is None or hi >= upper:
            break
    return out


def squares_from(segments):
    """Every four-cycle sum between consecutive segments.

    A square takes one position from each of two segments and one class from
    each of two classes; its sum is the difference of the class differences.
    """
    out = []
    for index in range(len(segments) - 1):
        lo_a, hi_a, va = segments[index]
        lo_b, hi_b, vb = segments[index + 1]
        out.append({
            "position_low": lo_a if hi_a is None else (lo_a + hi_a) // 2,
            "position_high": lo_b if hi_b is None else (lo_b + hi_b) // 2,
            "d_low": fmt(va),
            "d_high": fmt(vb),
            "square": fmt(vb - va),
            "sign": 0 if vb == va else (1 if vb > va else -1),
        })
    return out


def arm_a_squares(spec):
    """Tier by period. The square is the tier step read in two periods.

    Every pair of tiers is taken, not only neighbours. Tier three against tier
    one is as much a four-cycle as tier three against tier two, and the two give
    different numbers; picking one of them would be a choice with no reading
    behind it, so both are printed.
    """
    periods = spec["periods"]
    tiers = sorted(spec["tiers"])
    out = []
    for index in range(len(tiers) - 1):
      for jndex in range(index + 1, len(tiers)):
        low, high = tiers[index], tiers[jndex]
        for pi in range(len(periods) - 1):
            p, q = periods[pi], periods[pi + 1]
            step_p = spec["tiers"][high][p] - spec["tiers"][low][p]
            step_q = spec["tiers"][high][q] - spec["tiers"][low][q]
            out.append({
                "tier_low": low, "tier_high": high, "period_a": p, "period_b": q,
                "step_in_a": fmt(step_p), "step_in_b": fmt(step_q),
                "square": fmt(step_p - step_q),
                "floor_multiple": (abs(step_p - step_q) // spec["tick"]
                                   if spec["tick"] else None),
            })
    return out


def independent_policies(names):
    """Collapse schedules that are one policy read twice.

    Two seasons of one province share a notice, a threshold and a shift, and
    since the class difference depends only on the increments and the shift, the
    two seasons are forced to the same numbers. Counting them as two readings
    would inflate the independent count with a bijection, which is the thing the
    rule about identical arms is for.
    """
    return {n.split("_")[0] for n in names}


def _crit(name, kind, result, extra=None):
    """One criterion, third cell kept out of both verdicts.

    A branch with no object returns None, which becomes `passed: null` plus a
    `void` field, so that neither the ledger nor the census reads it as a
    reading that came out false.
    """
    verdict = result[0]
    crit = {"name": name, "kind": kind, "detail": result[1],
            "passed": None if verdict is None else bool(verdict)}
    if verdict is None:
        crit["void"] = True
    if extra:
        crit.update(extra)
    return crit


def run():
    report = {"arm_a": {}, "arm_b": {}, "independence": {}}

    # ---- arm A -----------------------------------------------------------
    for name in sorted(ARM_A):
        spec = ARM_A[name]
        squares = arm_a_squares(spec)
        report["arm_a"][name] = {
            "source": spec["source"], "kind": spec["kind"],
            "periods": spec["periods"], "tick": fmt(spec["tick"]),
            "squares": squares,
            "any_nonzero": any(s["square"] != fmt(0) for s in squares),
        }

    # ---- arm B -----------------------------------------------------------
    for name in sorted(ARM_B):
        spec = ARM_B[name]
        entry = {"source": spec["source"],
                 "threshold_people": spec["threshold_people"],
                 "increments": [fmt(v) for v in spec["increments"]],
                 "note": spec.get("note", "")}
        if spec["bounds_ordinary"] is None:
            entry["structure_published"] = False
            entry["shift_pattern"] = spec.get("shift_pattern", "")
            report["arm_b"][name] = entry
            continue
        entry["structure_published"] = True
        entry["bounds_ordinary"] = spec["bounds_ordinary"]
        entry["bounds_registered"] = spec["bounds_registered"]
        entry["tick"] = fmt(spec["tick"])
        segments = difference_steps(spec)
        entry["segments"] = [{"from": lo, "to": hi, "d": fmt(v)}
                             for lo, hi, v in segments]
        squares = squares_from(segments)
        entry["squares"] = squares
        entry["nonzero_squares"] = sum(1 for s in squares if s["sign"] != 0)
        signs = [s["sign"] for s in squares if s["sign"] != 0]
        entry["sign_changes"] = sum(1 for i in range(len(signs) - 1)
                                    if signs[i] != signs[i + 1])
        entry["distinct_d"] = sorted({fmt(v) for _, _, v in segments})
        segment_values = [v for _, _, v in segments]
        entry["floor_multiples"] = sorted(
            {abs(sb - sa) // spec["tick"]
             for sa, sb in zip(segment_values, segment_values[1:]) if sa != sb})
        report["arm_b"][name] = entry

    report["voltage"] = {}
    for name in sorted(VOLTAGE_ROWS):
        spec = VOLTAGE_ROWS[name]
        gaps = [a - b for a, b in zip(spec["below_1kv"], spec["one_to_ten_kv"])]
        report["voltage"][name] = {
            "source": spec["source"],
            "rows": spec["row_names"],
            "gaps": [fmt(v) for v in gaps],
            "constant": len(set(gaps)) == 1,
            "squares": [fmt(b - a) for a, b in zip(gaps, gaps[1:])],
            "tick": fmt(spec["tick"]),
        }

    report["arm_c"] = {}
    for name in sorted(ARM_C):
        spec = ARM_C[name]
        entry = {"source": spec["source"], "quota_kwh": spec["quota_kwh"],
                 "classes": spec["classes"], "note": spec["note"],
                 "deducts_from": spec["deducts_from"]}
        if spec["deducts_from"] is None or spec["bites_price"] is None:
            entry["mechanism_published"] = False
            # A province that publishes a transfer and a province that publishes
            # nothing both produce no square, and they are opposite signals: one
            # says this arm does not apply here, the other says go and look.
            entry["mechanism"] = spec.get("mechanism", "not published")
        else:
            entry["mechanism_published"] = True
            entry["bites_price"] = fmt(spec["bites_price"])
            entry["bites_price_name"] = spec["bites_price_name"]
            entry["tick"] = fmt(spec["tick"])
            # d is the full price of the bucket the quota bites from, on the
            # free positions, and zero on every position after them.
            entry["segments"] = [
                {"from": 1, "to": spec["quota_kwh"],
                 "d": fmt(spec["bites_price"])},
                {"from": spec["quota_kwh"] + 1, "to": None, "d": fmt(0)}]
            entry["squares"] = [{"position_low": 1,
                                 "position_high": spec["quota_kwh"] + 1,
                                 "square": fmt(-spec["bites_price"])}]
            entry["floor_multiple"] = spec["bites_price"] // spec["tick"]
        report["arm_c"][name] = entry

    report["arm_d"] = {}
    for name in sorted(ARM_D):
        spec = ARM_D[name]
        d, squares = arm_d_readings(spec)
        report["arm_d"][name] = {
            "source": spec["source"],
            "threshold_people": spec["threshold_people"],
            "flat_surcharge": fmt(spec["flat_surcharge"]),
            "bounds": spec["bounds"],
            "tick": fmt(spec["tick"]),
            "d_by_tier": [fmt(v) for v in d],
            "d_changes_sign": any(a < 0 < b or b < 0 < a
                                  for a, b in zip(d, d[1:])),
            "squares": squares,
            "floor_multiples": [abs(v) // spec["tick"] for v in d],
            "note": spec["note"],
            "elective_within_class": spec.get("elective_within_class", False),
        }

    read = sorted(n for n, e in report["arm_b"].items()
                  if e.get("structure_published"))
    report["independence"] = {
        "schedules_read": read,
        "independent_policies": sorted(independent_policies(read)),
        "why": "the two Guangdong seasons share one notice, one threshold and "
               "one shift; d depends on the increments and the shift alone, so "
               "the seasons are forced to the same numbers and are one reading",
    }
    return report


def criteria(report):
    crits = []

    # B102-1 instrument: every published schedule is internally sound.
    bad = []
    for name, spec in sorted(ARM_A.items()):
        for tier, row in sorted(spec["tiers"].items()):
            for period in spec["periods"]:
                if period not in row:
                    bad.append(name + " tier " + tier + " missing " + period)
    for name, spec in sorted(ARM_B.items()):
        for key in ("bounds_ordinary", "bounds_registered"):
            edges = spec[key]
            if edges is None:
                continue
            if sorted(edges) != edges or len(set(edges)) != len(edges):
                bad.append(name + " " + key + " not strictly increasing")
        if spec["increments"] != sorted(spec["increments"]):
            bad.append(name + " increments not non-decreasing")
        levels = spec.get("levels")
        if levels is not None:
            derived = [v - levels[0] for v in levels]
            if derived != spec["increments"]:
                bad.append(name + " levels and increments disagree: "
                           + ", ".join(fmt(v) for v in derived) + " vs "
                           + ", ".join(fmt(v) for v in spec["increments"]))
    crits.append(_crit(
        "B102-1", "instrument",
        (not bad,
         "schedules read from the constant table: "
         + str(len(ARM_A)) + " arm-A provinces, " + str(len(ARM_B))
         + " arm-B schedules. Problems: "
         + ("none" if not bad else "; ".join(bad)))))

    # B102-2 instrument: the two paths to the class difference agree.
    mismatch = []
    checked = []
    for name, spec in sorted(ARM_B.items()):
        if spec["bounds_ordinary"] is None:
            continue
        upper = max(spec["bounds_registered"]) + 200
        built = steps_to_scan(difference_steps(spec), upper)
        walked = difference_scan(spec, upper)
        checked.append(name)
        if built != walked:
            first = next(i for i in range(len(walked)) if built[i] != walked[i])
            mismatch.append(name + " first differs at position " + str(first + 1))
    crits.append(_crit(
        "B102-2", "instrument",
        (not mismatch,
         "segment construction against a pointwise walk on "
         + ", ".join(checked) + ". Disagreements: "
         + ("none" if not mismatch else "; ".join(mismatch)))))

    # B102-3 known answer: provinces registered as additive must read back zero.
    wrong = []
    for name in ARM_A_ZERO:
        for square in report["arm_a"][name]["squares"]:
            if square["square"] != fmt(0):
                wrong.append(name + " " + square["tier_low"] + "->"
                             + square["tier_high"] + " " + square["period_a"]
                             + "/" + square["period_b"] + " = " + square["square"])
    crits.append(_crit(
        "B102-3", "known_answer",
        (not wrong,
         "provinces whose text carries one increment for all periods, read back: "
         + ", ".join(ARM_A_ZERO) + ". Non-zero squares among them: "
         + ("none" if not wrong else "; ".join(wrong)))))

    # B102-4 own reading, load bearing: print the objects, no line on them.
    lines = []
    for name, entry in sorted(report["arm_b"].items()):
        if not entry.get("structure_published"):
            lines.append(name + ": structure not published")
            continue
        lines.append(name + ": d takes " + ", ".join(entry["distinct_d"])
                     + "; squares "
                     + ", ".join(s["square"] for s in entry["squares"]))
    read = [n for n, e in report["arm_b"].items() if e.get("structure_published")]
    # The registered reading is the floor gate (D24): does each non-zero square
    # stand above the tick the province itself publishes to. Three cells, and
    # the middle one is reached by any schedule whose structure was not published.
    below = []
    multiples = []
    for name in read:
        spec = ARM_B[name]
        for square in report["arm_b"][name]["squares"]:
            if square["sign"] == 0:
                continue
            units = abs(y(square["square"]))
            multiples.append((name, square["square"], units // spec["tick"]))
            if units < spec["tick"]:
                below.append(name + " " + square["square"])
    crits.append(_crit(
        "B102-4", "own_reading",
        (None if not read else not below,
         "arm B, per schedule, objects printed not counted. " + " | ".join(lines)
         + " || floor multiples: "
         + ", ".join(n + " " + v + " = " + str(m) + "x"
                     for n, v, m in multiples)
         + ". Squares inside their own floor: "
         + ("none" if not below else ", ".join(below)))))

    # B102-5 own reading: sign changes, printed, nothing registered about them.
    counts = {n: report["arm_b"][n]["sign_changes"] for n in read}
    crits.append(_crit(
        "B102-5", "own_reading",
        (None if not read else True,
         "sign changes per schedule, reported not scored (D48, fourth shape): "
         + ", ".join(n + "=" + str(counts[n]) for n in sorted(counts)))))

    # B102-6/7/8 the three rivals. Polarity: PASS means the rival is wrong.
    all_squares = []
    for n in read:
        all_squares.extend(report["arm_b"][n]["squares"])
    nonzero = [s for s in all_squares if s["sign"] != 0]
    # Sign changes are counted inside each schedule and never across the join.
    # Concatenating three schedules and walking the seam would add a change
    # that belongs to no schedule: the criterion's scope is one schedule and
    # the object's scope has to be the same one.
    per_schedule = {n: report["arm_b"][n]["sign_changes"] for n in read}
    changes = min(per_schedule.values()) if per_schedule else 0

    crits.append(_crit(
        "B102-6", "rival",
        (None if not read else len(nonzero) > 0,
         "bare rival predicts the class difference is zero at every position. "
         "Read: d takes the values "
         + ", ".join(sorted({s["d_low"] for s in all_squares}
                            | {s["d_high"] for s in all_squares}))
         + " across " + str(len(read)) + " published schedules."),
        {"rival_premise": "a scalar phi(j) on positions; one kilowatt hour at "
                          "one position has one price",
         "rival_entailment": "phi carries no class index, so the difference "
                             "between any two classes is zero at every "
                             "position and every four-cycle sum is zero",
         "rival_shape": "point prediction of zero",
         "grid": "B"}))

    crits.append(_crit(
        "B102-7", "rival",
        (None if not read else len(nonzero) > 0,
         "additive rival predicts the class difference is constant in j, so "
         "every four-cycle sum is exactly zero. Read: "
         + str(len(nonzero)) + " of " + str(len(all_squares))
         + " squares non-zero; values "
         + ", ".join(sorted({s["square"] for s in nonzero}))
         + ". These are not that many independent readings: the two Guangdong "
         "seasons are one policy, and d depends only on the increments and the "
         "shift, not on where the edges sit, so the two seasons return the same "
         "numbers by construction. Independent schedules here: "
         + str(len(independent_policies(read))) + " ("
         + ", ".join(sorted(independent_policies(read))) + ")."),
        {"rival_premise": "P(a, j) = phi(j) + psi(a) for some phi on positions "
                          "and psi on classes",
         "rival_entailment": "the difference P(a,j) - P(a',j) equals "
                             "psi(a) - psi(a'), which does not depend on j, so "
                             "every four-cycle sum is exactly zero",
         "rival_shape": "point prediction of zero",
         "grid": "B"}))

    crits.append(_crit(
        "B102-8", "rival",
        (None if not read else changes > 0,
         "multiplicative rival permits the class difference to vary with j but "
         "not to change sign, because it is one price curve scaled. Two "
         "independent routes refute it here: arm B's squares alternate, and on "
         "arm D the difference itself crosses zero, which a scaled copy of a "
         "non-negative price curve cannot do. Arm B, "
         "counted inside each schedule and never across the join: "
         + ", ".join(n + "=" + str(per_schedule[n]) for n in sorted(per_schedule))
         + ". The weakest schedule alone already carries " + str(changes) + "."),
        {"rival_premise": "P(a, j) = alpha_a * phi(j) with phi non-decreasing "
                          "in j and alpha_a a per-class scale",
         "rival_entailment": "the difference is (1 - alpha) * phi(j), which "
                             "keeps the sign of phi, so the four-cycle sums "
                             "cannot change sign",
         "rival_shape": "one-sided (no sign change)",
         "grid": "B"}))

    # B102-11 own_reading: arm D, where the class difference itself crosses zero.
    lines_d = []
    crossed = []
    for name in sorted(report["arm_d"]):
        entry = report["arm_d"][name]
        lines_d.append(name + ": flat surcharge " + entry["flat_surcharge"]
                       + " against block increments, so d by tier is "
                       + ", ".join(entry["d_by_tier"])
                       + "; squares " + ", ".join(s["square"]
                                                  for s in entry["squares"])
                       + "; floor multiples "
                       + ", ".join(str(m) for m in entry["floor_multiples"]))
        if entry["d_changes_sign"]:
            crossed.append(name)
    crits.append(_crit(
        "B102-11", "own_reading",
        (None if not report["arm_d"] else bool(crossed),
         "arm D: a household of seven or more may elect one surcharge for every "
         "kilowatt hour instead of the blocks, so the two classes face curves of "
         "different shape rather than different level. The squares here are the "
         "block increments and nothing else, so provinces are forced to the "
         "same squares whatever flat number they picked; what carries the "
         "reading is where that number sits relative to the increments, and "
         "that is one reading per province. " + " | ".join(lines_d)
         + " || kept out of this arm, with the reason: "
         + " | ".join(n + " (" + ARM_D_EXCLUDED[n]["flat_surcharge"] + "): "
                      + ARM_D_EXCLUDED[n]["why_out"]
                      for n in sorted(ARM_D_EXCLUDED))
         + ". The difference itself crosses zero in "
         + ("none" if not crossed else ", ".join(crossed))
         + ": the ordinary household pays less on the first block and more on "
         "the other two, at the same position. What is read here is the set of "
         "published schedules and who may reach each one, not what any "
         "household paid. The flat option is elective, so a household of seven "
         "may take it or stay on the blocks and will presumably take whichever "
         "is cheaper; that choice is inside the class and does not open the "
         "flat schedule to a household of four, which cannot reach it at any "
         "price. No claim is made here about realised bills, because the "
         "election is not published.")))

    # B102-10 own_reading: arm C, where a class is charged nothing at all on
    # the first few positions and the same as everyone after them.
    rows = []
    readable = []
    for name in sorted(report["arm_c"]):
        entry = report["arm_c"][name]
        if not entry["mechanism_published"]:
            if entry.get("mechanism") == "transfer":
                rows.append(name + ": " + str(entry["quota_kwh"])
                            + " kWh free to " + entry["classes"]
                            + ", and it is handed back as money through the "
                            "civil affairs payment rather than taken off any "
                            "block, so the marginal price is the same at every "
                            "position and this arm does not apply here. This is "
                            "the arm's failure case and it is published")
            else:
                rows.append(name + ": " + str(entry["quota_kwh"])
                            + " kWh free to " + entry["classes"]
                            + "; where the quota is deducted from is not "
                            "published, so there is no object to read")
            continue
        readable.append(name)
        rows.append(name + ": " + str(entry["quota_kwh"]) + " kWh free to "
                    + entry["classes"] + ", deducted from "
                    + entry["deducts_from"] + ", so d is "
                    + entry["bites_price"] + " on the first "
                    + str(entry["quota_kwh"]) + " positions and "
                    + fmt(0) + " after them; one square of "
                    + entry["squares"][0]["square"] + ", which is "
                    + str(entry["floor_multiple"]) + " times this province's tick")
    crits.append(_crit(
        "B102-10", "own_reading",
        (None if not readable else True,
         "arm C. The registered question was whether the quota comes off the "
         "metered quantity before the blocks apply or off the bill afterwards. "
         "The published mechanism is neither: it comes out of the first block's "
         "quantity, so the edges do not move and the first few kilowatt hours "
         "are priced at zero for that class. " + " | ".join(rows)
         + ". A household above the quota pays the same money either way, so "
         "what differs is the schedule and not the bill; the schedule is what "
         "the rivals make claims about and no claim is made here about money.")))

    # B102-12 known_answer: the voltage dimension, in the same tables, is
    # additive. A class index that behaves the way the additive rival says one
    # should is the control this station would otherwise be missing.
    lines_v = []
    bad_v = []
    for name in sorted(report["voltage"]):
        entry = report["voltage"][name]
        lines_v.append(name + ": gaps " + ", ".join(entry["gaps"])
                       + " across " + ", ".join(entry["rows"])
                       + "; squares " + ", ".join(entry["squares"] or ["none"]))
        if not entry["constant"]:
            bad_v.append(name)
    crits.append(_crit(
        "B102-12", "known_answer",
        (not bad_v,
         "the voltage dimension is registered as additive and read back at "
         "zero. " + " | ".join(lines_v)
         + ". Non-constant: " + ("none" if not bad_v else ", ".join(bad_v))
         + ". This matters because it is the same table: Anhui prints four rows "
         "at two voltages with one constant gap, and the household dimension "
         "that is not additive sits beside it. The reading is not that "
         "published tariffs are non-additive in general, it is that some of "
         "their class dimensions are and some are not, and one document shows "
         "both."))) 

    # B102-9 bookkeeping: every number carries a source, zero-yield rows included.
    missing = [n for n, s in list(ARM_A.items()) + list(ARM_B.items())
               if not s.get("source")]
    crits.append(_crit(
        "B102-9", "bookkeeping",
        (not missing,
         "every schedule in the constant table carries a source string, "
         "including the ones that read zero. Without one: "
         + ("none" if not missing else ", ".join(missing)))))

    return crits


def config_block():
    """What this run actually chose (rule 18d): the schedules and their edges."""
    return {
        "money_unit": "1e-4 yuan, integer",
        "arm_a_provinces": sorted(ARM_A),
        "arm_a_registered_zero": sorted(ARM_A_ZERO),
        "arm_b_schedules": sorted(ARM_B),
        "arm_b_structure_published": sorted(
            n for n, s in ARM_B.items() if s["bounds_ordinary"] is not None),
        "arm_b_bounds": {n: {"ordinary": s["bounds_ordinary"],
                             "registered": s["bounds_registered"]}
                         for n, s in sorted(ARM_B.items())},
        "arm_b_increments": {n: [fmt(v) for v in s["increments"]]
                             for n, s in sorted(ARM_B.items())},
        "voltage_rows": sorted(VOLTAGE_ROWS),
        "arm_d_schedules": sorted(ARM_D),
        "arm_d_excluded": sorted(ARM_D_EXCLUDED),
        "arm_d_flat_surcharge": {n: fmt(s["flat_surcharge"])
                                 for n, s in sorted(ARM_D.items())},
        "arm_c_registered": sorted(ARM_C),
        "arm_c_readable": sorted(n for n, s in ARM_C.items()
                                 if s["deducts_from"] is not None
                                 and s["bites_price"] is not None),
    }


def selftest():
    checks = []

    def ok(label, condition):
        checks.append((label, bool(condition)))

    ok("yuan parsing is exact", y("0.0500") == 500 and y("0.25") == 2500)
    ok("formatting round trips", fmt(y("0.4883")) == "0.4883")
    ok("formatting pads", fmt(500) == "0.0500" and fmt(0) == "0.0000")
    ok("tier_at reads the edges", tier_at(240, [240, 400]) == 0
       and tier_at(241, [240, 400]) == 1 and tier_at(401, [240, 400]) == 2)

    spec = ARM_B["beijing"]
    segs = difference_steps(spec)
    ok("beijing d takes three values",
       sorted({v for _, _, v in segs}) == [0, 500, 2500])
    ok("beijing returns to zero twice",
       [v for _, _, v in segs] == [0, 500, 0, 2500, 0])
    sq = squares_from(segs)
    ok("beijing has four non-zero squares",
       sum(1 for s in sq if s["sign"] != 0) == 4)
    signs = [s["sign"] for s in sq if s["sign"] != 0]
    # Four squares, +0.05 / -0.05 / +0.25 / -0.25, so the sign alternates on
    # every step: three changes, not two. The earlier wording counted how many
    # times d left zero, which is a different quantity.
    ok("beijing squares alternate in sign",
       signs == [1, -1, 1, -1]
       and sum(1 for i in range(len(signs) - 1) if signs[i] != signs[i + 1]) == 3)
    ok("beijing squares are the two increments and their negatives",
       sorted(s["square"] for s in sq)
       == ["-0.0500", "-0.2500", "0.0500", "0.2500"])
    ok("two paths agree on beijing",
       steps_to_scan(segs, 700) == difference_scan(spec, 700))

    # A province that shifts only the first edge: fewer squares, still non-zero.
    one_edge = {"bounds_ordinary": [240, 400], "bounds_registered": [340, 400],
                "increments": [0, 500, 3000]}
    segs1 = difference_steps(one_edge)
    ok("one moved edge gives two non-zero squares",
       sum(1 for s in squares_from(segs1) if s["sign"] != 0) == 2)
    ok("one moved edge still returns to zero",
       [v for _, _, v in segs1] == [0, 500, 0, 0])
    # The seeded shape above is not hypothetical: Hunan is it, on published
    # numbers, and its edges sit somewhere else entirely. The reading does not
    # depend on where the edges are, only on which of them moved.
    hunan = difference_steps(ARM_B["hunan_springautumn"])
    ok("hunan has the one-moved-edge shape",
       [v for _, _, v in hunan] == [0, 500, 0, 0])
    ok("hunan's two seasons agree despite different second edges",
       [v for _, _, v in hunan]
       == [v for _, _, v in difference_steps(ARM_B["hunan_wintersummer"])]
       and ARM_B["hunan_springautumn"]["bounds_ordinary"]
       != ARM_B["hunan_wintersummer"]["bounds_ordinary"])

    # A per-kilowatt-hour discount instead of a boundary shift: the additive
    # rival survives. This is the criterion's failure mode and it must be live.
    flat = {"bounds_ordinary": [240, 400], "bounds_registered": [240, 400],
            "increments": [0, 500, 3000]}
    ok("identical edges give no non-zero square",
       all(s["sign"] == 0 for s in squares_from(difference_steps(flat))))

    saved = ARM_B["beijing"]["levels"]
    ARM_B["beijing"]["levels"] = [y("0.4883"), y("0.5383"), y("0.7983")]
    seeded = criteria(run())
    ARM_B["beijing"]["levels"] = saved
    ok("a level that disagrees with its increments is reported",
       any(c["name"] == "B102-1" and c["passed"] is False for c in seeded))

    rep = run()
    ok("sichuan's arm A row is read off an example's arithmetic, and says so",
       "worked example" in ARM_A["sichuan"]["source"])
    ok("registered-zero provinces read back zero",
       all(not rep["arm_a"][n]["any_nonzero"] for n in ARM_A_ZERO))
    ok("shanghai arm A reads non-zero", rep["arm_a"]["shanghai"]["any_nonzero"])
    crits = criteria(rep)
    ok("every criterion carries a kind",
       all(c.get("kind") in ("instrument", "premise", "known_answer", "rival",
                             "own_reading", "bookkeeping") for c in crits))
    ok("every rival criterion carries premise, entailment, shape and grid",
       all(all(k in c for k in ("rival_premise", "rival_entailment",
                                "rival_shape", "grid"))
           for c in crits if c["kind"] == "rival"))
    ok("no criterion writes the undecided cell as a verdict",
       all(("void" in c) == (c["passed"] is None) for c in crits))
    # One province, one price list: two seasons must not carry two ticks. The
    # first version of this table had 0.001 on one Hunan season and 0.01 on the
    # other, which put the same reading at 50 times its floor in one season and
    # 5 in the other.
    by_province = {}
    for name, spec in ARM_B.items():
        if spec["tick"] is None:
            continue
        by_province.setdefault(name.split("_")[0], set()).add(spec["tick"])
    ok("one province never carries two ticks",
       all(len(v) == 1 for v in by_province.values()))
    ok("the two Guangdong seasons collapse to one policy",
       independent_policies(["guangdong_summer", "guangdong_nonsummer",
                             "beijing"]) == {"guangdong", "beijing"})
    ok("the two Guangdong seasons return the same squares",
       [s["square"] for s in rep["arm_b"]["guangdong_summer"]["squares"]]
       == [s["square"] for s in rep["arm_b"]["guangdong_nonsummer"]["squares"]])
    dvals, dsq = arm_d_readings(ARM_D["shanghai_seven"])
    ok("arm D's difference is negative on tier one and positive after",
       dvals[0] < 0 < dvals[1] and dvals[1] < dvals[2])
    ok("arm D's difference is the increments less the flat surcharge",
       [fmt(v) for v in dvals] == ["-0.0240", "0.0260", "0.2760"])
    ok("arm D's squares are the block increments",
       sorted(s["square"] for s in dsq) == ["0.0500", "0.2500", "0.3000"])
    # The failure mode for arm D: a flat surcharge at or below the first tier's
    # increment leaves the difference one-signed, and the multiplicative rival
    # survives on this arm. The reading turns on 0.024 sitting strictly between
    # 0 and 0.05, which is a published number and could have been elsewhere.
    saved_flat = ARM_D["shanghai_seven"]["flat_surcharge"]
    ARM_D["shanghai_seven"]["flat_surcharge"] = y("0.0000")
    seeded_d, _ = arm_d_readings(ARM_D["shanghai_seven"])
    ARM_D["shanghai_seven"]["flat_surcharge"] = saved_flat
    ok("a flat surcharge at tier one's increment leaves no crossing",
       not any(a < 0 < b or b < 0 < a
               for a, b in zip(seeded_d, seeded_d[1:])))
    repv = run()["voltage"]
    ok("the voltage gap is constant in both tables that print it",
       all(e["constant"] for e in repv.values()))
    ok("anhui's voltage gap covers the pooled row too, not only the tiers",
       len(repv["anhui"]["gaps"]) == 4
       and set(repv["anhui"]["gaps"]) == {"0.0150"})
    ok("a voltage gap that is not constant would be caught",
       not all(a == b for a, b in
               zip(VOLTAGE_ROWS["anhui"]["below_1kv"],
                   [v + 1 for v in VOLTAGE_ROWS["anhui"]["one_to_ten_kv"]])))
    ah_d, ah_sq = arm_d_readings(ARM_D["anhui_seven"])
    ok("anhui's arm D difference crosses zero like the other two",
       ah_d[0] < 0 < ah_d[1]
       and [fmt(v) for v in ah_d] == ["-0.0200", "0.0300", "0.2800"])
    ok("all three arm D flat surcharges sit inside the first block's gap",
       all(0 < s["flat_surcharge"] < s["increments"][1] for s in ARM_D.values()))
    gd_d, gd_sq = arm_d_readings(ARM_D["guangdong_seven"])
    ok("guangdong's arm D difference also crosses zero",
       gd_d[0] < 0 < gd_d[1] and [fmt(v) for v in gd_d]
       == ["-0.0370", "0.0130", "0.2630"])
    # The squares in arm D are the block increments and nothing else, so the
    # two provinces are forced to the same squares whatever their flat number
    # is. What differs, and what carries the reading, is where the flat number
    # sits relative to the increments.
    ok("the two arm-D provinces are forced to the same squares",
       [s["square"] for s in gd_sq] == [s["square"] for s in dsq])
    ok("their crossings are two readings, not one",
       [fmt(v) for v in gd_d] != [fmt(v) for v in dvals])
    ok("a published flat surcharge kept out of arm D carries its reason",
       all(e["why_out"] for e in ARM_D_EXCLUDED.values()))
    ok("the excluded pooled rate is excluded on the position index, not on size",
       "position index" in ARM_D_EXCLUDED["hunan_pooled"]["why_out"])
    ok("arm D records that its option is elective within the class",
       all(e["elective_within_class"] for e in run()["arm_d"].values()))
    ok("shanghai's edges both move, by a year's worth of the monthly addition",
       ARM_B["shanghai"]["bounds_registered"]
       == [b + 1200 for b in ARM_B["shanghai"]["bounds_ordinary"]])
    ok("shanghai's levels and increments agree",
       [v - ARM_B["shanghai"]["levels"][0] for v in ARM_B["shanghai"]["levels"]]
       == ARM_B["shanghai"]["increments"])
    ok("the third cell is still occupied, so it is not vacuous",
       any(s["bounds_ordinary"] is None for s in ARM_B.values()))
    # Pinned to the property, not to a province: which province occupies the
    # third cell moves every time something is read, and a check named after
    # one of them breaks on the day that province is read rather than on the
    # day the property fails.
    ok("every row with no structure carries no threshold either, so nothing in "
       "it can be mistaken for a reading",
       all(s["threshold_people"] is None for s in ARM_B.values()
           if s["bounds_ordinary"] is None))
    repc = run()["arm_c"]
    ok("arm C has both a readable province and an unreadable one",
       any(e["mechanism_published"] for e in repc.values())
       and any(not e["mechanism_published"] for e in repc.values()))
    ok("arm C's readable square is the whole first-tier price, negated",
       repc["jiangsu"]["squares"][0]["square"] == "-0.5283"
       and repc["hunan"]["squares"][0]["square"] == "-0.5880")
    ok("arm C's free range is the quota and nothing more",
       repc["jiangsu"]["segments"][0]["to"] == ARM_C["jiangsu"]["quota_kwh"]
       and repc["jiangsu"]["segments"][1]["from"]
       == ARM_C["jiangsu"]["quota_kwh"] + 1)
    ok("an unreadable arm C province produces no square",
       all("squares" not in e for e in repc.values()
           if not e["mechanism_published"]))
    ok("arm C's failure case is published, not hypothetical",
       sum(1 for e in repc.values() if e.get("mechanism") == "transfer") >= 2)
    ok("arm C has provinces on both sides of its own dividing line",
       any(e["mechanism_published"] for e in repc.values())
       and any(e.get("mechanism") == "transfer" for e in repc.values()))
    # The third state, a province that grants the quota and says nothing about
    # the mechanism, has no live occupant now that Anhui and Jilin both turned
    # out to publish transfers. It is seeded instead of being kept occupied by a
    # row: what has to hold is that the three states stay distinguishable, not
    # that each has a member on any given day.
    ARM_C["__seed__"] = {"source": "seeded", "quota_kwh": 1, "classes": "seed",
                         "deducts_from": None, "bites_price": None, "tick": None,
                         "note": "seed"}
    seeded_c = run()["arm_c"]["__seed__"]
    del ARM_C["__seed__"]
    ok("a province that says nothing is told apart from one that publishes a transfer",
       seeded_c["mechanism"] == "not published"
       and repc["jilin"]["mechanism"] == "transfer"
       and "squares" not in seeded_c)
    ok("the two provinces that state the mechanism state the same one",
       "first block" in ARM_C["jiangsu"]["deducts_from"]
       and "first block" in ARM_C["hunan"]["deducts_from"])
    ok("shanghai's quota bites in a period, not in a block",
       "peak" in ARM_C["shanghai"]["deducts_from"]
       and "block" in ARM_C["jiangsu"]["deducts_from"])
    ok("provinces with no published structure produce no square",
       all("squares" not in e for e in rep["arm_b"].values()
           if not e.get("structure_published")))

    width = max(len(label) for label, _ in checks)
    for label, good in checks:
        print(("PASS  " if good else "FAIL  ") + label.ljust(width))
    bad = [label for label, good in checks if not good]
    print("")
    print(str(len(checks) - len(bad)) + " of " + str(len(checks)) + " checks pass")
    return 1 if bad else 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--out", default="results/b102_cn_power_tariff.json")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

    report = run()
    crits = criteria(report)

    for name in sorted(report["arm_b"]):
        entry = report["arm_b"][name]
        print("== arm B  " + name)
        if not entry.get("structure_published"):
            print("   structure not published: " + entry["shift_pattern"])
            continue
        print("   ordinary  " + str(entry["bounds_ordinary"])
              + "   registered  " + str(entry["bounds_registered"]))
        for seg in entry["segments"]:
            span = (str(seg["from"]) + "-"
                    + (str(seg["to"]) if seg["to"] is not None else "up"))
            print("   " + span.ljust(12) + "d = " + seg["d"])
        for square in entry["squares"]:
            print("   square " + str(square["position_low"]) + " vs "
                  + str(square["position_high"]) + " = " + square["square"])
        print("   non-zero " + str(entry["nonzero_squares"])
              + "   sign changes " + str(entry["sign_changes"]))
    print("")
    for name in sorted(report["voltage"]):
        entry = report["voltage"][name]
        print("== voltage  " + name + "   gaps "
              + ", ".join(entry["gaps"])
              + "   constant: " + ("yes" if entry["constant"] else "no"))
    print("")
    for name in sorted(report["arm_c"]):
        entry = report["arm_c"][name]
        if entry["mechanism_published"]:
            shown = entry["deducts_from"]
        elif entry.get("mechanism") == "transfer":
            shown = "a transfer, refunded through civil affairs"
        else:
            shown = "not published"
        print("== arm C  " + name + "   quota " + str(entry["quota_kwh"])
              + " kWh   mechanism: " + shown)
        if entry["mechanism_published"]:
            for seg in entry["segments"]:
                span = (str(seg["from"]) + "-"
                        + (str(seg["to"]) if seg["to"] is not None else "up"))
                print("   " + span.ljust(12) + "d = " + seg["d"])
            print("   square " + entry["squares"][0]["square"]
                  + "   floor multiple " + str(entry["floor_multiple"]))
    print("")
    for name in sorted(report["arm_d"]):
        entry = report["arm_d"][name]
        print("== arm D  " + name + "   flat " + entry["flat_surcharge"])
        print("   d by tier  " + ", ".join(entry["d_by_tier"])
              + "   crosses zero: "
              + ("yes" if entry["d_changes_sign"] else "no"))
        for square in entry["squares"]:
            print("   square tier " + str(square["tier_low"]) + "->"
                  + str(square["tier_high"]) + " = " + square["square"])
    print("")
    for name in sorted(report["arm_a"]):
        entry = report["arm_a"][name]
        print("== arm A  " + name + "   non-zero: "
              + ("yes" if entry["any_nonzero"] else "no"))
        for square in entry["squares"]:
            print("   tier " + square["tier_low"] + "->" + square["tier_high"]
                  + "  " + square["period_a"] + "/" + square["period_b"]
                  + "  square " + square["square"])
    print("")

    failed = []
    for crit in crits:
        if crit["passed"] is None:
            mark = "VOID   "
        elif crit["passed"]:
            mark = "PASS   "
        else:
            mark = "FAILED[" + crit["kind"] + "]: "
            failed.append(crit["name"])
        print(mark + crit["name"] + "  " + crit["detail"])

    record = {"stage": "B102", "config": config_block(),
              "criteria": crits, "report": report}
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("")
    print("wrote " + str(out))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
