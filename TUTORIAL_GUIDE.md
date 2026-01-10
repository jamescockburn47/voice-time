# Tutorial & Testing Guide 🎓

## Realistic Sample Data

The app now includes **12 realistic legal matters** across different practice areas:

### Litigation - Commercial
1. **Thompson Industries Ltd v Apex Manufacturing** (2024/CL/087)
   - Aliases: "Thompson", "Apex dispute", "TI matter"
   - Typical tasks: Witness statements, disclosure, drafting

2. **R (Greenfield) v Planning Authority** (2024/CL/142)
   - Aliases: "Greenfield", "planning JR", "judicial review"
   - Typical tasks: Research, skeleton argument, grounds of challenge

### Employment
3. **Williams v DataTech Solutions - Unfair Dismissal** (2025/EMP/023)
   - Aliases: "Williams", "employment", "DataTech"
   - Typical tasks: Witness statements, correspondence, tribunal prep

### Personal Injury
4. **Chen v London Transport Authority** (2024/PI/156)
   - Aliases: "Chen", "PI matter", "transport injury"
   - Typical tasks: Medical reports, quantum, settlement

### Corporate
5. **TechGrowth PLC - Acquisition** (2025/CORP/034)
   - Aliases: "TechGrowth", "acquisition", "M&A deal"
   - Typical tasks: Due diligence, SPA drafting, completion

6. **Riverside Ventures - Shareholder Agreement** (2024/COM/208)
   - Aliases: "Riverside", "SHA", "venture deal"
   - Typical tasks: Drafting, negotiation, board minutes

### Property
7. **Harbour Properties - Lease Dispute** (2024/PROP/134)
   - Aliases: "Harbour", "lease", "commercial property"
   - Typical tasks: Lease review, correspondence, court

### Family
8. **Patel v Patel - Divorce** (2024/FAM/091)
   - Aliases: "Patel", "divorce", "family"
   - Typical tasks: Financial disclosure, FDR, consent order

### Criminal
9. **R v Johnson - Fraud** (2025/CRIM/017)
   - Aliases: "Johnson", "fraud case", "R v Johnson"
   - Typical tasks: Unused material, defence statement, conference

### Regulatory
10. **Sterling Financial - FCA Investigation** (2024/REG/045)
    - Aliases: "Sterling", "FCA", "regulatory"
    - Typical tasks: Disclosure, submissions, interviews

### Probate
11. **Estate of Elizabeth Montgomery** (2024/PROB/078)
    - Aliases: "Montgomery", "probate", "estate"
    - Typical tasks: Grant application, IHT, distribution

### Immigration
12. **Dr. Sharma - Visa Application** (2025/IMM/012)
    - Aliases: "Sharma", "visa", "immigration"
    - Typical tasks: Application, supporting docs, Home Office

## Tutorial Scenarios

### Scenario 1: Complete Morning to Evening

**Morning (9:15 AM):**
```
Ctrl+Space → "Today I need to review Thompson witness statements, draft the Greenfield skeleton, and conference with counsel at 3 about Greenfield"
```

**10:00 AM:**
```
Ctrl+Space → "Working on Thompson witnesses"
```

**12:30 PM:**
```
Ctrl+Space → "Done with Thompson - took all morning"
```

**12:35 PM:**
```
Ctrl+Space → "Quick email to Williams about disclosure"
```

**12:45 PM:**
```
Ctrl+Space → "Taking lunch"
```

**1:30 PM:**
```
Ctrl+Space → "Back, starting Greenfield skeleton"
```

**2:45 PM:**
```
Ctrl+Space → "Urgent call from Chen about medical report"
```

**2:55 PM:**
```
Ctrl+Space → "Back to the skeleton"
```

**3:00 PM:**
```
Ctrl+Space → "Conference starting"
```

**4:15 PM:**
```
Ctrl+Space → "Conference done, ran over a bit"
```

**4:20 PM:**
```
Ctrl+Space → "Back to skeleton, final amendments"
```

**5:00 PM:**
```
Ctrl+Space → "Skeleton complete"
```

**Expected Log:**
- Thompson: 3.5h (DOCREV)
- Williams: 0.15h (EMAIL)
- Chen: 0.15h (CALL)
- Greenfield: 4.0h (DRAFT 2.5h, CONF 1.25h, amendments 0.25h)

### Scenario 2: Interruption Testing

**Start:**
```
"Working on Thompson drafting"
```

**Interruption 1:**
```
"Quick call about Williams"
(handle call)
"Back to what I was doing"
```

**Interruption 2:**
```
"Urgent - need to review Chen medical report"
(review document)
"Done with Chen, back to Thompson"
```

**Complete:**
```
"Finished the Thompson drafting"
```

**Expected:** System correctly resumes Thompson context after each interruption

### Scenario 3: Ambiguous References

**Try these to test the smart matching:**

```
"Working on the acquisition"
→ Should match TechGrowth (only acquisition)

"Done with the planning matter"
→ Should match Greenfield (planning context)

"Quick call about the employment case"
→ Should match Williams (only employment matter)
```

### Scenario 4: Natural Duration

```
"Spent a couple of hours on Thompson this morning"
→ Should log 2.0 hours

"All afternoon on the Greenfield research"
→ Should infer ~3-4 hours

"Quick 10 minute email to Harbour client"
→ Should log 0.15-0.2 hours

"Since lunch on the acquisition due diligence"
→ Should calculate time from 1:00 PM
```

## How to Access Tutorial

1. Run the app: `⭐ START HERE.bat`
2. Choose option 2 (WEB MODE)
3. Click **"Tutorial"** in the navigation
4. See all scenarios with examples
5. Reference the matter list
6. Click "Try It Now" to practice

## Loading Demo Data

If you want to reload the sample data:

```
load_demo_data.bat
```

Or add your own matters through the app!

## Tips for Testing

1. **Start with planning** - Say what you'll work on
2. **Use aliases** - Try different ways to reference matters
3. **Test interruptions** - Switch tasks and return
4. **Try natural duration** - "couple of hours", "all morning"
5. **Check the review** - See if time was allocated correctly
6. **Export to CSV** - Verify the output format

## Practice Makes Perfect

The more you use it, the better the system gets at understanding your patterns!

Enjoy testing! 🚀
