# Why results/b14_legb_price2016.json is not on disk

B14_A18 clause 2 registered slice B's bin variable as `5c / P_2016`. Three free routes
have now been tried for the 2016 price and all three fail, for three different
reasons. They are listed so the fourth attempt does not repeat one of them.

1. **Appendix B.I carries no price field.** 52 fields, every one a spread, a count
   or a time. Measured, not assumed.

2. **Per-ticker free APIs do not serve delisted names.** A large share of the 108
   are delisted or renamed since 2016. Measured 2026-08-20: stooq returns HTTP 200
   with a `noindex,nofollow` anti-bot HTML page for every URL form tried; Yahoo's
   v8 chart endpoint returns HTTP 404 `"No data found, symbol may be delisted"`.

3. **The stooq bulk archive is split adjusted, and covers survivors only.**
   `d_us_txt.zip`, 13,321 members, is the currently-listed US universe: 53 of the
   registered 108 are present, and coverage is flat across test groups (0.471 /
   0.480 / 0.467 / 0.588; on the full 2,396-security pilot set 0.516 / 0.492 /
   0.462 / 0.508), so the absence is not correlated with treatment. But the prices
   are adjusted backward for later splits: FET reads $310.70 for 2016 against an
   actual 2016 level near $15 (1-for-20 reverse split in 2020), VNCE $60.05 against
   about $3, FTK $56.67 against about $11. The pilot's own eligibility required a
   price at or above $2 with market cap at or below $3B and ADV at or below one
   million shares, so a small cap reading $310 is the adjustment, not the market.

   `5c / P_2016` needs the price actually quoted in 2016. A split-adjusted series
   is a different quantity and using it would silently mis-rank the bins.

The extracted-but-unusable file is parked at
`b14_legb_price2016.json.expired_20260820_split_adjusted_unusable`. It is kept, not deleted,
because it is a correct extraction of the wrong quantity and re-deriving it costs
a 540 MB download.

**What would work:** an unadjusted contemporaneous price series that includes
delisted issues. CRSP carries both the adjusted and the unadjusted series plus the
delisting record; that is a WRDS-class item.

**Why this does not matter for any verdict:** slice B's reading was "not a
reversal", and that reading came from the ARM DECOMPOSITION (dG is flat across
bins at +0.054 / +0.063 / +0.056 while dC slopes at +0.016 / +0.028 / +0.033, so
the monotonicity lives in the control arm). That decomposition does not depend on
which variable defines the bins. A registered-variable rerun would move the bin
boundaries and leave the verdict where it is.
