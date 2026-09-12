# V3 Five-Scenario Mathematical Financial Proof

Aggregate: **PASS** (5/5)

## A_Residential_500_Riyadh — **PASS**

### INPUTS
```json
{
  "capex": 250000000,
  "revenues": [
    90000000.0,
    110000000.0,
    95000000.0,
    40000000.0
  ],
  "costs": [
    25000000.0,
    18000000.0,
    12000000.0,
    8000000.0
  ],
  "discount_rate": 0.12,
  "units": 500
}
```

### CALCULATION
- Cash flows: `[-250000000, 65000000.0, 92000000.0, 83000000.0, 32000000.0]`
- NPV hand `-39208109.9` vs engine `-39208109.9` → PASS
- IRR `0.0376` display `3.8%` → PASS
- Payback years: `3.31`


### OUTPUT
- **PASS**

## B_DataCenter_20MW_Riyadh — **PASS**

### INPUTS
```json
{
  "capex": 320000000,
  "revenues": [
    80000000.0,
    95000000.0,
    110000000.0,
    120000000.0
  ],
  "costs": [
    45000000.0,
    48000000.0,
    52000000.0,
    55000000.0
  ],
  "discount_rate": 0.12,
  "mw": 20
}
```

### CALCULATION
- Cash flows: `[-320000000, 35000000.0, 47000000.0, 58000000.0, 65000000.0]`
- NPV hand `-168689958.29` vs engine `-168689958.29` → PASS
- IRR `-0.1453` display `-14.5%` → PASS
- Payback years: `None`

- Unrealistic 20MW@25M warning PASS=True: ['CAPEX looks unusually low for a 20 MW data center (~SAR 1,250,000/MW). Expected range about SAR 160,000,000–400,000,000.']

### OUTPUT
- **PASS**

## C_Cyber_MSSP_Services — **PASS**

### INPUTS
```json
{
  "capex": 2000000,
  "revenues": [
    16200000.0,
    20250000.0,
    24300000.0
  ],
  "costs": [
    8910000.0,
    11137500.0,
    13365000.000000002
  ],
  "discount_rate": 0.12,
  "formula": "billing_rate\u00d7utilization\u00d7resources\u00d7billable_period",
  "notes": [
    "services_billable_period_annual_hours",
    "services_revenue_from_billing_rate_x_utilization_x_resources"
  ]
}
```

### CALCULATION
- Cash flows: `[-2000000, 7290000.0, 9112500.0, 10934999.999999998]`
- NPV hand `19556674.79` vs engine `19556674.79` → PASS
- IRR `3.8243` display `382.4%` → PASS
- Payback years: `0.27`

- Zero-OPEX guard PASS=True; formula PASS=True

### OUTPUT
- **PASS**

## D_SaaS_ARR_Churn_CAC — **PASS**

### INPUTS
```json
{
  "capex": 1500000,
  "revenues": [
    3600000,
    4471200.0,
    5553230.400000001
  ],
  "costs": [
    2400000,
    2800000,
    3100000
  ],
  "discount_rate": 0.12
}
```

### CALCULATION
- Cash flows: `[-1500000, 1200000, 1671200.0, 2453230.4000000013]`
- NPV hand `2649859.92` vs engine `2649859.92` → PASS
- IRR `0.8664` display `86.6%` → PASS
- Payback years: `1.18`


### OUTPUT
- **PASS**

## E_Uber_like_Mobility — **PASS**

### INPUTS
```json
{
  "capex": 15000000,
  "revenues": [
    19008000.0,
    24710400.0,
    30412800.0
  ],
  "costs": [
    13305600.0,
    16803072.0,
    19768320.0
  ],
  "discount_rate": 0.12,
  "drivers": 2000,
  "take_rate": 0.22
}
```

### CALCULATION
- Cash flows: `[-15000000, 5702400.0, 7907328.0, 10644480.0]`
- NPV hand `3971632.65` vs engine `3971632.65` → PASS
- IRR `0.2529` display `25.3%` → PASS
- Payback years: `2.13`


### OUTPUT
- **PASS**
