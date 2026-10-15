# Lab 13 — Portfolio Mandate Defense

## S1–S10: statement types and IPS map

An investment policy statement (IPS) is the client's documented agreement about the portfolio's purpose, return objective, constraints, governance, and how success is measured. It turns the client's intent into decision rules before implementation.

| Statement | Type | Reason / IPS role |
|---|---|---|
| S1 | Hard constraint | The seven-year horizon and annual rebalancing set the planning period and required implementation cadence. |
| S2 | Objective | CPI + 4% net of costs over rolling five-year periods defines the desired investment outcome. |
| S3 | Hard constraint | It specifies both a $3.0m one-year payout reserve and permitted instruments for it. |
| S4 | Preference | The 60/40 benchmark is a performance comparison, but it does not say a portfolio must track it or stay within a tracking-error limit. |
| S5 | Hard constraint | Long-only expressly prohibits borrowing, short sales, and derivatives. |
| S6 | Hard constraint | It places a clear 8% ceiling on a single company, with stated exemptions. |
| S7 | Hard constraint | Turnover may not exceed 25% annually without committee approval; this is an implementation/governance constraint. |
| S8 | Hard constraint | At least 90% must be redeemable within five business days. |
| S9 | Unverifiable promise | The 10% calendar-year loss wording supplies neither a measure nor a breach/action rule, so it cannot be tested as written. |
| S10 | Missing | It declines sector, ESG, tax, and home-bias preferences, but leaves the pilot's optimization target unspecified. |

## Checker result

Run the checker from this folder with:

```powershell
python mandate.py
```

The computed reserve minimum is 3.0%. Candidates A, B, and C produce the known results: A passes every checkable rule; B fails three rules; and C fails one rule. The Acme calculation aggregates its bonds and stock, so B is 9.0% and C is 8.0% in the largest-single-company test.

### Long-only probe

I temporarily changed A's Cash from 2 to -2 and its global equity index fund from 60 to 64, then ran `python mandate.py`. A's lowest weight became -2.0 and failed long-only; its reserve weight remained 10.0 and no other check failed. I restored the original A weights afterward.

### Read-the-code check

The line I focused on is:

```python
if issuer not in EXEMPT_ISSUERS:
    company_weights[issuer] = company_weights.get(issuer, 0) + weights[holding]
```

It skips cash, the U.S. Treasury, and diversified funds because the mandate exempts them. For every other issuer, `get(issuer, 0)` retrieves the exposure already counted for that company (or starts at zero), then adds the current holding's weight.

Quiz question: Why are Acme bonds and Acme stock added before comparing with the issuer limit?

My answer: The mandate limits one company, not one holding. Both securities have issuer `Acme Corp`, so their weights must be summed to measure the company exposure.

## Attack portfolio D

Candidate D is 100% Cash, with every other holding at 0%. It runs and passes every rule in `mandate.py`: it is fully liquid under the five-day test, holds more than the required 3.0% reserve, and has no non-exempt company exposure.

The objection holds as a suitability concern because passing static liquidity, allocation, and concentration rules does not demonstrate a viable path to meeting the required real return net of costs. Statement S2 decides the issue: the CIO can reject an all-cash allocation for structurally failing the rolling five-year CPI + 4% objective, even though the program marks it as passing all checkable constraints.

As the sceptical colleague, I would cite S2 against a partner's passing candidate D if it has no credible route to the rolling five-year CPI + 4% net objective. Passing the current code is not evidence that the portfolio meets the mandate's return objective.

## Question for the CIO before optimization

Under Statement S10, is the pilot's mathematical objective function to minimize tracking error relative to the 60/40 benchmark (S4), or to minimize total portfolio variance subject to achieving the CPI + 4% net return target (S2)?

If the CIO chooses tracking-error minimization, the optimizer anchors tightly to the 60/40 policy benchmark and penalizes large allocation deviations regardless of absolute volatility or cash yield. If the CIO chooses total-variance minimization, the optimizer can deviate substantially from the 60/40 mix—using more cash, T-bills, or intermediate bonds—provided the CPI + 4% target remains feasible.

## Reflection

A portfolio can pass every checkable rule and still be wrong because the checker only enforces complete, measurable instructions. It cannot decide whether the portfolio offers a viable path to the CPI + 4% net objective, whether it is appropriate relative to the benchmark, or what an incomplete loss promise means; D demonstrates that gap.

I was least sure about S4. I classified the benchmark as a preference because it gives a comparison standard but not a required allocation, tracking band, or active-risk limit. If the CIO intended it as a binding 60/40 allocation, that intent needs to be stated as a hard constraint before optimization.
