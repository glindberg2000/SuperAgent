# FMV (Fair Market Value) Resolution Research PRD

## Objective
Design and recommend a robust, scalable method for resolving missing FMV (Fair Market Value) values in cryptocurrency transaction data for IRS-compliant tax reporting, with a focus on:
- 2024 tax year (2,018 transactions, 45.1% missing FMV)
- Priority tokens: USDC, USD, WETH, ETH, PEPE, AERO
- LP positions: Velodrome, Uniswap V3, KyberSwap
- Multi-chain support: BASE, OP, ETH, MATIC, BSC, ARBI

## Background
- Data covers 2024 tax-relevant transactions and LP positions (see `2024_transactions.csv` and `2024_tax_analysis.txt`)
- 45.1% of transactions are missing FMV (USDEquivalent)
- FMV is required for accurate tax calculation and reporting

## Representative Sample Data

### Transaction Format (15 Columns)
```
Type,BuyAmount,BuyCurrency,SellAmount,SellCurrency,FeeAmount,FeeCurrency,Exchange,ExchangeId,Group,Import,Comment,Date,USDEquivalent,UpdatedAt
Trade,1.0,ETH,2000.0,USDC,5.0,USDC,Binance,12345,GroupA,Yes,First batch,2024-04-15,,2024-04-15T12:00:00Z
Deposit,1000.0,USDC,0.0,,0.0,,Coinbase,67890,GroupB,Yes,Monthly deposit,2024-01-10,,2024-01-10T09:30:00Z
Spend,0.5,ETH,1000.0,USD,0.0,,Airdrop,abcde,GroupC,No,Promo,2024-08-21,,2024-08-21T15:45:00Z
LP,500.0,USDC,0.0,,0.0,,Velodrome,lp001,GroupLP,Yes,LP position,2024-02-11,,2024-02-11T10:15:00Z
```

### Missing FMV Data Example
```
Type,BuyAmount,BuyCurrency,SellAmount,SellCurrency,FeeAmount,FeeCurrency,Exchange,ExchangeId,Group,Import,Comment,Date,USDEquivalent,UpdatedAt
Deposit,100.0,USDC,0.0,,0.0,,BASE,xyz01,GroupD,Yes,Test,2024-03-15,,2024-03-15T10:00:00Z
Trade,2.0,AERO,400.0,USDC,1.0,USDC,OP,op567,GroupE,No,DeFi,2024-11-02,,2024-11-02T13:20:00Z
LP,200.0,WETH,0.0,,0.0,,Uniswap V3,lp002,GroupLP,Yes,LP withdrawal,2024-07-19,,2024-07-19T18:00:00Z
```

### FMV Gap Analysis (2024)
- Total 2024 transactions: 2,018
- Missing FMV: 2,473 (45.1%)
- LP positions: 112 (Velodrome, Uniswap V3, KyberSwap)
- Priority tokens/currencies: USDC, USD, WETH, ETH, PEPE, AERO
- Top exchanges: BASE, OP, ETH, MATIC

## Requirements & Questions for Grok4
1. What are the most reliable and cost-effective APIs, MCP tools, or databases for obtaining historical FMV for:
   - Major tokens (ETH, USDC, USD, etc.)
   - DeFi tokens (AERO, VELO, OP, PEPE, etc.)
   - LP positions (Velodrome, Uniswap V3, KyberSwap, etc.)
   - Multiple chains (BASE, OP, ETH, MATIC, BSC, ARBI)
   - 2024 date range
2. What are the best practices for handling missing data (interpolation, estimation, fallback sources)?
3. How should FMV for LP positions be calculated and validated?
4. How should caching and rate limiting be managed for large batch lookups and real-time queries?
5. Are there open-source or commercial solutions that can be integrated as MCP tools or microservices?
6. What are the failure modes and reliability considerations for FMV lookup at scale?
7. Are there any regulatory or compliance factors to consider for FMV sourcing?

## Deliverables
- List of recommended APIs, MCP tools, and/or databases (with pros/cons, rate limits, cost, and reliability)
- Architectural diagram or outline for FMV resolution integration
- Best practices for LP FMV, error handling, caching, and data validation
- Summary of open questions or risks

## Notes
- See `data/samples/fmv_analysis_summary.txt`, `data/samples/missing_fmv_data.csv`, `2024_tax_analysis.txt`, and `2024_transactions.csv` for full data context
- The final solution should be modular and extensible for new tokens/chains and DeFi/LP use cases
- Focus on 2024 data and IRS-compliant reporting
