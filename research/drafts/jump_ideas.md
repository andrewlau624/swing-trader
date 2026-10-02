# Jump & ride hunt: idea list (round 1), written before any outcome

Session llm-trader-51, 2026-10-02. Brief: `prompt_jump_hunt.md`. **No event outcome has been computed for any idea
below.** Each idea names the death it is built to dodge (death map, prompt section 1).

Method tags: **H** hype/attention/news, **D** death-dodge (names the dead study), **C** collision, **V** hype-venue lag,
**S** scheduled-hype run-up (RIDE), **W** wildcard. Track: J = JUMP, R = RIDE (both are always printed; the tag is the
one the idea is built for).

Data tags (verified = one request returned real rows today): **N** Alpaca/Benzinga news archive 2016+ (verified;
headline, summary, symbols, created_at), **R** Reddit posts via Arctic Shift (verified; title, created_utc),
**WP** Wikipedia pageviews for 3,524 Wikidata tickers (verified), **E** EDGAR (verified: FTS, submissions incl.
formerNames, XBRL frames for shares outstanding), **P** cached night panel 2020-10..2026-09 (13,933 symbols incl.
trade_count), **SI** cached FINRA short interest, **F4** Form 4 (cached zips 2020+, `insider_buys()`), **FDA** openFDA
(verified), **US** USAspending (verified), **WB** Wayback CDX (not verified yet), **CT** ClinicalTrials.gov (not verified).

Timestamps: a post/story/filing at ET time t is assigned `fd` = the ET date of (t − 9h30m): anything before the 09:30
open is traded at that day's open, anything after at the next session's open. Daily-bar signals (panel, pageviews)
use the session's date (decided after the close, traded at the next open). Pageview days are UTC days, which end
at 20:00 ET (before the next open): fine.

Novelty 1-5: "memory" = scored from what I know of the literature; "searched: ..." = a WebSearch run today.

| # | idea | track | tag | cause sentence | death dodged, how | data | sig/yr | novelty |
|---|---|---|---|---|---|---|---|---|
| H1 | **Reddit first mention after silence**: a ticker named in >= 2 posts within 3 days in the small subs (pennystocks, smallstreetbets, RobinHoodPennyStocks, shortsqueeze) after >= 365 days with no post naming it | R | H | Small-sub posters find a quiet name first; it then spreads to bigger subs and media; most people only notice when it trends on WSB or StockTwits, and that's when it moves | GAP: Reddit precedes the press; PRICE PROXY: each stock vs itself | R (verified) | 200+ | 3 (memory: Reddit-attention papers use WSB counts, not first mentions in small subs) |
| H2 | **Mention velocity without a price move**: posts naming a ticker on day d >= 5x its trailing-30d daily mean (>= 3 posts) across the small subs, AND the day's close-to-close |return| < 5% | R | H | Talk builds before buying: retail posts their thesis before the crowd buys; buy while attention is up and price isn't | GAP (attention before price), RIDE not price-first | R + bars | 100+ | 3 (memory) |
| H3 | **Shortsqueeze-sub DD**: first r/Shortsqueeze or r/shortsqueeze post with "DD" in title/flair naming a ticker (first in 180 days) | R | H | Squeeze hunters publish short-interest DD and coordinate; the squeeze attempt comes days later | GAP; LOTTERY tested by ex-top-3 | R | 50-150 | 3 |
| H4 | **WSB first mention of a small cap** (ADV$ < $20M at the time): first WSB post naming it in 365 days | R | H | WSB is the biggest retail amplifier; a small cap's first WSB post is the first moment millions see it | GAP; PRICE PROXY | R | 100+ | 3 |
| H5 | **Pageview spike, no price move**: Wikipedia views >= 5x the trailing-60d median while the same session's |return| < 5% | R | H | People look up a company (TV, a product, a viral post) before they buy it; the price catches up | GAP (attention before price), PRICE PROXY (vs itself) | WP | 100+ | 3 (memory: Wikipedia views and returns studied for large caps, Moat et al. 2013; not "spike without move") |
| H6 | **Pageview slow build**: 20-day mean views >= 2x the prior 120-day mean, monotone rise (each of the last 4 weeks above the one before), price 20d return within ±10% | R | H | A slowly building audience (a product getting popular) is invisible on price charts; 60-day hold rides adoption | REGIME (not a theme bet), RIDE not price-first | WP | 30-80 | 4 (memory) |
| H7 | **First Benzinga coverage**: a ticker's first-ever news story in the archive after it has traded >= 2 years | R | H | Media discovery of a forgotten name puts it in front of every terminal and app feed for the first time | GAP: test both buy-open and only-if-gap-small; TEXTBOOK (no paper uses first coverage in Benzinga) | N | 50-200 | 4 (memory) |
| H8 | **News velocity burst without a move**: >= 4 stories in 5 days vs < 1/month before, with |5d return| < 10% | R | H | Media attention snowballs a few days before the retail buying; the price hasn't reacted yet | GAP; PRICE PROXY | N + bars | 100+ | 3 |
| H9 | **"Why is X trading higher" first explainer**: Benzinga's first "why is ... shares are trading higher/soaring" story on a ticker (none in 365d) | R | H | Explainers are syndicated to Yahoo/apps and pull a second wave of buyers into a name that just moved | TEXTBOOK; risk PRICE-FIRST (named; graded anyway as a wildcard of attention syndication) | N | 200+ | 4 |
| H10 | **First-ever analyst initiation on a micro cap** ("initiates coverage" headline, no initiation in 2y, ADV$ < $5M) | R | H | A first analyst note brings institutional and retail eyes; small brokers initiate before financings, so the 60-day ride is the test | TEXTBOOK (initiation drift is published on larger caps; micro-cap first-ever is not); GAP via buy-open only if gap < 10% | N | 100+ | 2 (memory: Irvine 2003, Demiroglu-Ryngaert 2010 neglected stocks: +) |
| H11 | **Unusual options activity headlines on small caps** (Benzinga "unusual options activity"/"options sweep"/"whale" stories, bullish/calls, ADV$ < $50M) | J | H | Someone is buying calls (informed or a promoter); Benzinga broadcasts it; dealers hedge by buying stock | GAP (headline is intraday; buy next open); LOTTERY (many events) | N | 100+ | 4 |
| H12 | **"Short squeeze" in a headline, first time for a ticker** | J | H | The word squeeze in media recruits buyers into a crowded short | LOTTERY (ex-top3); GAP | N | 50-150 | 3 |
| H13 | **Cross-sub spread**: ticker first named in one small sub, then within 10 days in a second, different sub (buy at the 2nd sub) | R | H/V | Epidemic spread: a second community picking it up means R > 1; the third and fourth follow | GAP; LOTTERY | R | 50-150 | 4 |
| H14 | **PR blitz by a micro cap**: >= 4 press releases (Benzinga wires: Globe/PRN/Accesswire/BusinessWire sources) in 10 days by a ticker that averaged < 1/month, ADV$ < $5M | R | H | Promotion campaigns front-load PRs; buy at the start of the blitz, trail out before the dump | GAP; LOTTERY (trail exits) | N | 50-150 | 4 |
| H15 | **Wikipedia article born**: first day with >= 50 views for a listed ticker's article after 2016-07 (article created after listing) | R | H | Someone writes an article when a company becomes notable to the public: a lagging popularity marker | GAP | WP | 20-50 | 4 |
| H16 | **Weekend pageview spike**: Sat+Sun views >= 5x a normal weekend, bought Monday open | J | H | Attention gathered while the market is shut lands in the Monday open; test whether the open captures all of it | GAP (named; tests it directly) | WP | 50+ | 3 |
| H17 | **Trade-count spike, quiet price**: trade_count >= 5x its 60d median, |return| < 3%, close within the day's middle | R | H | Retail apps send many small orders when a name is being talked about; a large trade count with a flat price is attention not yet priced | PRICE PROXY (vs itself), RIDE attention-first; TEXTBOOK (the high-volume premium uses volume, not count, and 1 month) | P | 300+ | 2 (memory: Gervais-Kaniel-Mingelgrin 2001) |
| H18 | **Squeeze talk + short interest**: Reddit posts naming a ticker with "squeeze" in the title, FINRA SI >= 20% of float proxy | J | H/C | Shorts are trapped and a crowd is organizing; covering produces the jump | LOTTERY; GAP | R + SI | 30-100 | 3 |
| H19 | **Wikipedia theme spike -> theme small caps**: a theme article (Quantum computing, Uranium, Nuclear fusion, Hydrogen economy, Lidar, Psilocybin, Metaverse, ChatGPT, Bitcoin, Cannabis, eVTOL, GLP-1 drugs, Small modular reactor, Rare-earth element, Drone) at >= 3x its 90d median; buy small caps whose name/SIC/10-K mention the theme | R | H/V | Public curiosity about a theme precedes retail buying of its smallest, most "pure" names | REGIME (a family of 15 themes, any year); price-first banned theme momentum: this is attention-first | WP + E | 20-60 | 4 |
| H20 | **Reddit mention by a new sub for the ticker**: a subreddit named after the ticker or company is created (r/<TICKER>) | R | H/W | A community forming around a stock = a cult following starting | GAP | R (subreddit metadata) | 10-50 | 5 |
| H21 | **News count drought, then a non-earnings story**: first story in >= 180 days that is not an earnings/filing headline | R | H | A dormant company "wakes up" (new management, new product) and the first story gets little reaction | GAP | N | 100+ | 3 |
| H22 | **Big-name partnership headline on a micro cap**: headline names NVIDIA / Microsoft / Amazon / Google / Apple / OpenAI / Tesla / Meta + "partner/collaborat/agreement/selected", ADV$ < $10M | J | H | Retail reads "partners with NVIDIA" as validation and piles in over days | GAP: only when the next open gaps < 10% (the market under-reacted); LOTTERY | N | 50-150 | 3 |
| H23 | **Pageview spike of the CEO's article** (Wikidata P169 CEO -> pageviews), views >= 10x median | R | H/W | A CEO going viral (interview, controversy, podcast) pulls attention to the company before its own page | GAP | WP + Wikidata | 10-30 | 5 |
| H24 | **First appearance on Yahoo Finance trending tickers** (Wayback daily snapshot; small cap, not on the list in the prior 180 days) | R | H/V | Yahoo's trending list is what millions of app users see; a small cap's first appearance is attention arriving; buy the next open, trail | GAP (the list itself is the venue; test it), PRICE PROXY | WB (verified: 2,275 snapshots) | 50-150 | 4 |
| D1 | **FDA approvals died of GAP + LOTTERY -> 510(k) clearances in openFDA before the press release**, micro-cap device makers (company name -> ticker), bought the day the clearance is in the database if no press release yet | J | D | The clearance letter sits in openFDA's weekly database; most people only notice at the company's press release; that's when it moves | GAP (earlier than news), LOTTERY (many clearances) | FDA + N | 50+ | 4 (searched later) |
| D2 | **Announcement-gap drift (Lab-BH) died of GAP -> material-contract stories that did NOT gap**: headline with a $ amount (extracted) >= 10% of market cap (XBRL shares x price), next open gap < 3% | R | D | The market missed the size of the contract relative to the company; it reprices over weeks as holders do the arithmetic | GAP (only un-gapped), COST (big moves) | N + E | 50-150 | 4 |
| D3 | **8-K phrase drift died -> slow databases**: defense.gov daily contract announcements (17:00 ET) naming a small-cap prime, $ amount >= 5% of market cap | J | D | DoD posts awards after the close in a long text page nobody reads; the company PRs it days later or never | GAP (a slow venue), TEXTBOOK | defense.gov (unverified) + E | 20-60 | 4 |
| D4 | **Theme momentum died of REGIME/price-first -> theme pivot by filing text**: first 10-Q/10-K/8-K mentioning a hot theme ("blockchain" 2017-18, "artificial intelligence" 2023, "metaverse" 2021, "bitcoin mining" 2021, "CBD" 2018-19, "quantum" 2024...) by a company that never mentioned it (FTS) | R | D | Retail scans for theme words; a company that pivots its story to the hot word gets a hype premium for weeks | REGIME (family across themes and years), price-first (filing-first) | E (FTS verified) | 50-200 | 3 (memory: Cheng et al. 2019 blockchain name changes) |
| D5 | **Spin-offs / index adds died of GAP -> corporate name change to a hot word** (EDGAR formerNames: new name contains blockchain, crypto, bitcoin, AI, quantum, metaverse, cannabis, hemp, lithium, uranium, hydrogen, EV, solar, nuclear, drone) | R | D/W | Renaming into a hot theme recruits theme scanners; the name change date in EDGAR comes before most listings update | GAP (EDGAR effective date vs press), LOTTERY | E | 20-60 | 3 (memory: Cooper et al. 2001 dot-com names; Akyildirim 2020 blockchain) |
| D6 | **Earnings drift (TEXTBOOK) -> first profitable quarter ever** (XBRL NetIncomeLoss > 0 after >= 8 negative quarters), small caps | R | D | "First profit" is a story milestone that brings in new holders (screens filter on positive earnings) over weeks | TEXTBOOK (milestone, not surprise) | E (frames) | 50-150 | 3 |
| D7 | **Uplisting (banned) died of concurrent offerings -> uplistings with NO offering within 30 days** (first exchange bar after OTC history, no 424B within ±30d) | R | D | Exchange listing opens the stock to brokers/funds that can't buy OTC; without new supply, the demand shock is clean | the death (dilution), LOTTERY | bars + E index | 20-50 | 3 |
| D8 | **First insider buys (EV2, a 1-day effect) -> RIDE version on micro caps with a news drought** (no Benzinga story 60d before) | R | D/C | Insiders buy what nobody covers; the price only moves when coverage arrives | REGIME (L19 20d drift was 2020-only): only the uncovered subset | F4 + N | 50-150 | 3 |
| D9 | **Breakthrough/topline died -> ClinicalTrials.gov first posting of a pivotal (Phase 3) trial by a micro-cap sponsor** | R | D | The registry shows a company has reached Phase 3 before many holders notice; run-up into the readout over months | GAP (slow registry), LOTTERY | CT (unverified) | 30-60 | 4 |
| D10 | **13D originals died of GAP -> activist 13D/A that raises the stake** (amendment, ownership up >= 1pp) on small caps | R | D | The second filing shows conviction, gets less press than the first, and sets up a campaign | GAP (amendments get little attention) | E | 50-100 | 3 |
| D11 | **Index adds died of GAP -> predicted Russell 2000 adds** (rank by XBRL shares x May price; names crossing into ranks 1001-3000 that weren't there a year ago), bought mid-May, exit June recon | R | D | Index funds must buy at the June recon close; predictable from arithmetic nobody does at small size | GAP (arithmetic before the list), REGIME (published, decayed: named) | E frames + bars | 100+ (once a year) | 2 (memory: Madhavan 2003; decayed) |
| C1 | **Wikipedia spike + insider buy within 10 days** | R | C | Insiders bought quietly and the public is starting to look | each weak alone; PRICE PROXY | WP + F4 | 10-30 | 4 |
| C2 | **First Reddit mention + an insider buy in the prior 30 days** | R | C | The crowd finds a name insiders already bought | GAP; LOTTERY | R + F4 | 10-40 | 4 |
| C3 | **First news coverage + low float** (shares outstanding < 10M, XBRL) | J | C | Low float + first attention = small supply meets new demand | LOTTERY (median test) | N + E | 30-80 | 3 |
| C4 | **Reddit velocity + high days-to-cover (FINRA SI)** | J | C | Organized buyers meet trapped shorts | LOTTERY | R + SI | 30-80 | 3 |
| C5 | **Contract $ >= 10% of mcap (D2) + float < 20M shares** | J | C | A big contract in a tiny float | GAP (un-gapped only) | N + E | 10-40 | 4 |
| C6 | **Insider buy + no news in 90 days** | R | C | Quiet buying nobody reports | REGIME | F4 + N | 30-80 | 3 |
| C7 | **Reddit mention spike within 60 days after a reverse split** | J | C | Post-split floats are tiny; one wave of attention moves them | LOTTERY; PRICE PROXY (vs itself) | R + Alpaca CA | 20-60 | 4 |
| C8 | **Unusual options headline (H11) + no other news that day** | J | C | Calls bought with no public reason = informed or promotion ahead of news | GAP | N | 30-80 | 4 |
| C9 | **Theme news spike (headline counts of a theme word >= 3x 90d) + a small cap whose 10-K names the theme** | R | C/V | News flow on a theme reaches its smallest names last | REGIME (family), price-first | N + E | 20-60 | 4 |
| C10 | **Short interest up >= 50% in a FINRA period + Reddit/news attention spike** | J | C | Shorts piled in just as attention rises: a squeeze setup | LOTTERY | SI + R/N | 20-60 | 3 |
| C11 | **Trade-count spike (H17) + first news story in 90 days the same day** | R | C | Retail flow arrives with the first story; both weak alone | GAP | P + N | 30-100 | 3 |
| V1 | **Small subs -> WSB**: >= 3 posts in the small subs within 5 days naming a ticker with no WSB post in 90 days; buy, trail | R | V | Hype graduates from small subs to WSB with a lag; WSB brings the money | GAP | R | 50-150 | 4 |
| V2 | **Reddit -> Benzinga**: Reddit mention spike (H2 rule) with no Benzinga story in the prior 30 days | R | V | Media follows Reddit with a lag; the first story brings the second wave | GAP | R + N | 50-150 | 4 |
| V3 | **Theme leader's big up day -> its small listed suppliers** (XBRL ConcentrationRisk customer members naming the leader, e.g. "AppleInc"; or 10-K text), next open | R | V | Analysts of the leader don't cover tiny suppliers; their holders notice days later | TEXTBOOK (Cohen-Frazzini customer momentum: monthly, large; this is daily, micro, event) | E | 30-100 | 2 |
| V4 | **Korea/Japan retail theme stocks -> US peers** (KOSDAQ theme leader +15% -> US-listed same-theme small caps next US open) | J | V | Asian retail themes (batteries, robots, nuclear) run before US retail hears of them | GAP (Asia trades first, a different venue) | yfinance KRX (unverified) + LLM theme map | 20-60 | 4 |
| V5 | **Benzinga premarket "movers" list of yesterday's after-hours: names that moved < 5% after hours on a material headline** | J | V | After-hours prints are thin and few see them; the regular session reprices | GAP | N | 100+ | 3 |
| S1 | **Conference run-up**: micro/small caps announcing they will present at J.P. Morgan Healthcare, CES, Nvidia GTC, ASCO, BIO; buy at the announcement, sell the session before the conference | R | S | Retail and small funds buy into "presenting at JPM/GTC" stories; the event itself is sell-the-news | GAP; LOTTERY | N | 100+ | 3 |
| S2 | **PDUFA run-up**: buy 30 sessions before a PDUFA date (date extracted from a news headline/summary), sell the session before | R | S | Biotech traders buy the catalyst into the date and sell before the binary | LOTTERY (exit before the binary) | N | 50-100 | 2 (memory: published "PDUFA run-up" folklore and papers) |
| S3 | **Investor/analyst day announced** by a small cap: buy at announcement, sell the session before the day | R | S | Companies schedule investor days to tell a growth story; holders buy into it | GAP | N | 50+ | 3 |
| S4 | **Medical-conference data presentations** (ASCO/ASH/AACR/ESMO abstract presentations announced by micro-cap biotechs): buy at the announcement, sell before the abstract release | R | S | Data catalysts on a calendar attract run-up buying | LOTTERY (exit before data) | N | 100+ | 3 |
| S5 | **Forward-split announcement -> run into the ex-date** (Lab-BM tested AFTER the ex-date; this is before) | R | S | Retail loves "cheaper shares"; buying runs into the split date | the dead study's window (after ex-date), GAP | N + Alpaca CA | 20-40 | 3 |
| W1 | **Ticker spells a hot word** while that theme's news count spikes (e.g. AI, BTC, NUKE, QBTS...: a pre-written list of theme-word tickers) | J | W | Lazy hype buyers search the word and buy the ticker | REGIME | N + list | 10-30 | 5 |
| W2 | **Press release that says "artificial intelligence"/"AI" >= 5 times, first time for the company** (headline+summary) | R | W | AI-washing works on retail | REGIME (dates), GAP | N | 50-150 | 4 |
| W3 | **Wikipedia edit burst** (>= 10 edits in a day on the company article vs < 1/week) | R | W | Edit wars and updates happen when something is happening to a company in public | GAP | Wikimedia edits API (unverified) | 20-50 | 5 |
| W4 | **Super Bowl / big-event ad buyers that are small caps** (announced in news) | R | W | A national ad blitz = attention spike scheduled ahead | TOO RARE (named) | N | 2-5 | 4 |
| W5 | **"Meme stock" word in a headline for the first time for a ticker** | J | W | Media labeling a stock a meme recruits more meme buyers | GAP | N | 30-80 | 4 |
| W6 | **ARK Invest first buy of a small/mid cap** (daily trade emails, archived) | R | W | ARK followers copy first buys | REGIME (2020-21) | WB/news headlines "Cathie Wood buys" | 20-50 | 3 |

Count: H 24 (quota 20; H24 added 13:05, before any outcome), D 11 (10), C 11 (10), V 5 (5), S 5 (5), W 6 (5) = **62 ideas**.

## Ranking (filled after the reachability checks; no outcomes)
Score = P(dodges its death) x signals/yr x payoff x novelty x P(data works), each 1-5, scored before any outcome.

Written 13:45 (after H17 and D5 died; no other outcome seen). H17 taught a new death, **TWO-WAY** (attention with no
direction raises the jump AND crash rates; the cost makes the mean negative), so ideas that carry a DIRECTION
(own money, contracts, scheduled catalysts, squeezes) rank above pure attention counts.

| rank | idea | P(dodge) | sig/yr | payoff | novelty | P(data) | note |
|---|---|---|---|---|---|---|---|
| 1 | D2 un-gapped big contracts | 4 | 4 | 4 | 4 | 3 | direction from $ size; needs news + XBRL shares |
| 2 | S1 conference run-up | 3 | 5 | 3 | 3 | 5 | news headlines "to present at" |
| 3 | S2 PDUFA run-up | 3 | 4 | 4 | 2 | 4 | dates in headline text |
| 4 | D8 first insider buy + news drought (RIDE) | 3 | 4 | 3 | 3 | 4 | own money = direction |
| 5 | H24 Yahoo trending first appearance | 2 | 4 | 3 | 4 | 5 | snapshot fetch running |
| 6 | V1 small subs -> WSB | 2 | 4 | 4 | 4 | 4 | Reddit downloading |
| 7 | H1 Reddit first mention | 2 | 5 | 3 | 3 | 4 | |
| 8 | C4 Reddit velocity + days-to-cover | 3 | 3 | 4 | 3 | 3 | squeeze = direction |
| 9 | D6 first profitable quarter | 3 | 3 | 3 | 3 | 5 | building |
| 10 | D4 theme pivot 8-K | 2 | 4 | 3 | 3 | 5 | building |
| 11 | H5 pageview spike, no move | 2 | 4 | 3 | 3 | 4 | TWO-WAY risk |
| 12 | H2 Reddit velocity, no move | 2 | 4 | 3 | 3 | 4 | TWO-WAY risk |
| 13 | H14 PR blitz | 3 | 3 | 3 | 4 | 4 | |
| 14 | H11 unusual options headlines | 3 | 4 | 3 | 4 | 4 | |
| 15 | D1 510(k) before the press release | 3 | 3 | 3 | 4 | 3 | name matching |
| 16 | S4 medical-conference data run-up | 3 | 4 | 3 | 3 | 4 | |
| 17 | S5 forward-split run-up | 3 | 3 | 3 | 3 | 4 | |
| 18 | H22 big-name partnership, un-gapped | 3 | 3 | 3 | 3 | 4 | |
| 19 | H7 first Benzinga coverage | 2 | 4 | 3 | 4 | 5 | |
| 20 | H10 first-ever initiation, micro cap | 3 | 4 | 3 | 2 | 5 | |
Order of work = data readiness within this ranking (news-based ideas wait for the archive's 2016-23 months).

## Round 2 (early adds, 16:05, before any outcome of these): informed or forced buyers only
Written after 12 explored ideas died of EXIT LIQUIDITY / TWO-WAY / LOTTERY. Each names the informed or forced party.

| # | idea | track | tag | cause sentence | death dodged, how | data | sig/yr | novelty |
|---|---|---|---|---|---|---|---|---|
| R2-1 | **First executed buyback**: XBRL PaymentsForRepurchaseOfCommonStock > 0 (original 10-Q/10-K) after >= 8 reported periods with none, ADV$ < $20M | R | D | The company (the best-informed buyer) actually spends cash on its own stock; the cash-flow line is read by almost nobody, unlike an announcement | GAP + TEXTBOOK of buyback announcements (X3, Ikenberry): execution in a slow table, not a headline; EXIT LIQ: no crowd | E companyfacts | 50-150 | 4 (memory) |
| R2-2 | **Going-concern doubt removed**: a 10-K without "substantial doubt" after the company's prior 10-K had it (FTS), small caps | R | D | The auditor (informed) signs off on survival; lenders, funds and screens that exclude going-concern names can own it again | LOTTERY (many events, survival is the bet), EXIT LIQ | E FTS + form.idx | 100+ | 3 (memory: going-concern withdrawal literature, older) |
| R2-3 | **Net cash above market cap**: (cash + short-term investments − total liabilities) > market cap at a 10-Q/10-K filing, first time in 365 days, ADV$ < $20M | R | D/W | Arithmetic nobody does on tiny names; activists, acquirers and reverse-merger shells buy the cash at a discount | LOTTERY (a cash floor under the downside), EXIT LIQ (no crowd) | E frames/companyfacts + bars | 50-200 | 3 (memory: negative-EV biotech folklore) |
| R2-4 | **Big own-money buy**: an officer/director buys >= $100k in the open market in a company with 20-day ADV$ < $5M (relative size: buy >= 20% of ADV$) | R | C | A large personal bet in an illiquid stock: the most informed money relative to the market's size | EXIT LIQ; LOTTERY (many events) | F4 | 100+ | 3 |
| R2-5 | **Insider buys after a 30% fall**: officer/director buy when the stock is down >= 30% over 60 sessions | R | C | Insiders buy the panic; the price fall is the crowd leaving, insiders are the informed side | EXIT LIQ (the crowd already left); price is a filter, the Form 4 is the event | F4 + bars | 100+ | 2 (memory: insider contrarian, Lakonishok-Lee) |
| R2-7 | **Strategic-alternatives review announced** (headline), RIDE: a sale process starts; a deal arrives in some months | R | H/D | The board (informed) invites bidders; acquirers pay premiums; most holders are bored by "review" headlines | GAP (headline is mild), LOTTERY (many deals) | N | 30-80 | 3 |
| R2-9 | **Congress member buys a small cap** (STOCK Act periodic transaction reports, free dumps) | R | W | Possibly informed; disclosed with a lag, but small caps are thinly followed | EXIT LIQ | House/Senate watcher dumps (unverified) | 20-50 | 3 |
| R2-13 | **Listing compliance regained** (8-K / headline: "regained compliance" with the minimum bid / equity rule) | R | D | Funds forced to avoid delisting-risk names can hold it again; the threat of forced selling is gone | EXIT LIQ (forced sellers done), GAP | E FTS | 100+ | 3 |
| R2-14 | **Emergence from Chapter 11 with new listed equity** (headline) | R | D | Old creditors receive shares they must sell (forced), then the new equity re-rates | LOTTERY, forced sellers | N | 10-30 | 2 (memory: Eberhart-Altman-Aggarwal 1999) |

### Round 2, continued (17:20, before any outcome of these). New method: **filing arithmetic + own-money / forced
buyers, each checked against a same-stock no-event control before registering** (J2's lesson).

| # | idea | track | tag | cause sentence | death dodged, how | data | sig/yr | novelty |
|---|---|---|---|---|---|---|---|---|
| R2-15 | **Share count shrinks >= 3% in a quarter** (dei cover-page shares, original filings), ADV$ < $20M | R | D | The company retired stock with its own cash (informed); nobody reads the cover page | TEXTBOOK (buyback announcements) -> execution; EXIT LIQ | E companyfacts | 50-150 | 4 |
| R2-16 | **Revenue doubles year on year for the first time** (XBRL Revenues, original filing) after >= 4 flat/down quarters, micro caps | R | D | A business inflects; screens and growth funds notice over weeks | TEXTBOOK (revenue drift: milestone, micro caps) | E | 50-150 | 3 |
| R2-17 | **Insider buy into heavy shorts**: officer/director buy while the last published days-to-cover >= 5 | J | C | The informed side bets against the crowded short; covering creates the jump | EXIT LIQ (no crowd buying); LOTTERY (many) | F4 + SI | 50-150 | 3 |
| R2-18 | **Double own money**: an officer/director buy in a quarter in which the company also repurchased stock (XBRL) | R | C | Both informed parties buy at once | EXIT LIQ | F4 + E | 30-80 | 4 |
| R2-19 | **Two upgrades in 10 days** on a small cap (headlines "Upgrades ... to Buy/Outperform") | R | H/D | Analysts (semi-informed) move together; institutions follow over weeks | TEXTBOOK (single upgrades) -> clusters on small caps | N | 50-150 | 3 |
| R2-20 | **Big-name counterparty in an 8-K exhibit** (FTS 8-K "Amazon.com Services" / "Walmart Inc." / "Apple Inc." / "Microsoft Corporation" / "NVIDIA Corporation" / "Department of Defense"), small caps | R | D | The contract sits in an exhibit; the press release (if any) undersells it | GAP (slow exhibit text) | E FTS | 50-150 | 4 |
| R2-21 | **New major customer named in XBRL** (ConcentrationRiskPercentage on a customer member that never appeared before), micro caps | R | D/W | A new >10% customer is disclosed in a footnote, not a headline | GAP, EXIT LIQ | E companyfacts (dimension members: may be unavailable) | 30-80 | 5 |
| R2-22 | **Dividend raised >= 50%** by a small cap (headline amounts) | R | D | The board (informed) commits cash; income funds add over weeks | TEXTBOOK (dividend initiation dead) -> big raises | N | 30-80 | 2 |
| R2-23 | **Tiny-float de-SPAC**: first session after a business combination closes with >= 90% trust redemptions (8-K text) | J | W | The float is a few hundred thousand shares; any buying or short covering moves it | LOTTERY (many 2021-23 deals) | E FTS + LLM extraction | 30-80 | 4 |
| R2-24 | **After an issuer's Dutch tender closes** (SC TO-I final amendment): RIDE once the supply is removed | R | D | The company (informed) bought a big block; remaining holders are sticky | GAP (after, not at, the announcement) | E | 20-40 | 3 |
| R2-25 | **Buyback authorization >= 15% of market cap, un-gapped** (headline $ amount vs XBRL shares x price; next open gap < 3%) | R | D | The size relative to the company is missed by the market at the open | GAP (un-gapped only), TEXTBOOK | N + E | 30-80 | 3 |

Round 2 total: 20 ideas (R2-1..R2-5, R2-7, R2-9, R2-13, R2-14, R2-15..R2-25).

## Round 3 (18:50, before any outcome of these): new data sources and LLM fact extraction
Why things die so far: EXIT LIQUIDITY (crowd attention), TWO-WAY, LOTTERY, PRICE PROXY/REGIME, TOO WEAK (own money
and filing milestones earn the stock's usual +1-2% over 60 sessions). Round 3 uses data and methods not used yet:
SEC fails-to-deliver files, the Federal Register, SEC Form 13F data sets, USPTO grants, the cached Nasdaq earnings
calendar, and LLM extraction of FACTS from filings (prompt section 3a). Every idea still needs an informed or forced
buyer, and any MEETS gets a same-stock no-event control before registering.

| # | idea | track | tag | cause sentence | death dodged, how | data | sig/yr | novelty |
|---|---|---|---|---|---|---|---|---|
| R3-1 | **First revenue ever**: XBRL revenue > 0 in an original filing after >= 4 reported quarters of zero/absent, micro caps | R | D | A pre-revenue company becomes a business; screens and funds that need revenue can own it | TOO WEAK? milestone with a forced buyer (revenue screens) | E companyfacts | 30-80 | 3 |
| R3-2 | **Fails-to-deliver spike**: SEC FTD quantity >= 0.5% of shares outstanding for a small cap (file published ~2 weeks after) | J | W | Persistent fails force buy-ins (Reg SHO close-out); short covering then jumps | EXIT LIQ (forced buyers, not the crowd) | SEC FTD files (to verify) | 100+ | 4 |
| R3-3 | **FDA advisory committee run-up**: Federal Register notice of an adcom naming a listed sponsor's product; buy 21 sessions before the meeting, sell the session before | R | S | Biotech traders buy into a dated binary event and sell before it | LOTTERY (exit before the binary), GAP (notice weeks ahead) | Federal Register API (to verify) | 20-40 | 3 |
| R3-4 | **First patent ever granted** to a listed micro-cap assignee (USPTO weekly grants, public Tuesday) | R | D | A first patent is a moat milestone few holders see in the USPTO feed | GAP (slow database), EXIT LIQ | USPTO/PatentsView (to verify) | 30-80 | 4 |
| R3-5 | **Earnings date moved earlier** by >= 7 days vs the same quarter last year (Nasdaq calendar snapshots) | J | D | Companies with good news report early (informed timing); bought when the date is known, held through the report | TEXTBOOK (published, but not on small caps with a daily calendar) | cached earn_cal | 100+ | 2 |
| R3-6 | **13F discovery**: >= 3 different 13F filers open a new position in the same micro cap in one quarter (SEC 13F data sets; public at the filing deadline) | R | D | Institutions discover a name together; their next quarters of buying follow | EXIT LIQ (institutions, not retail); TEXTBOOK (herding papers use large caps) | SEC 13F data sets (to verify) | 50-150 | 3 |
| R3-7 | **LLM-extracted big contract vs revenue**: 8-K Item 1.01 exhibit -> counterparty and contract value (verbatim) >= 25% of last-year revenue (XBRL) | R | D | The size vs the company is buried in an exhibit | GAP (slow text), TOO WEAK (big relative size only) | E + OpenCode Go (<= 3,000 calls) | 30-80 | 4 |
| R3-8 | **Russell inclusion announced** by the company (8-K/PR "set to join the Russell 2000/3000/Microcap") in June; held to the recon | R | S | Index funds must buy at the June recon close | REGIME (published effect; small adds only) | E FTS | 100+ | 2 |
| R3-9 | **Short interest collapses >= 50%** in one FINRA period with the price flat (+-10%) | R | D | Informed shorts leave; the overhang that capped the price is gone | PRICE PROXY (vs itself), EXIT LIQ | SI | 100+ | 3 |
| R3-10 | **Unsolicited non-binding proposal made public** (FTS 8-K/SC 13D "non-binding proposal" / "unsolicited"), small caps; RIDE to a deal | R | D | A bidder (informed) names a price; boards often extract more or another bidder appears | GAP at the announcement (RIDE after it), LOTTERY | E FTS | 30-80 | 3 |
| R3-11 | **Treasury in bitcoin** announced by a small cap (headline "adds/purchases bitcoin ... treasury") | J | W | Crypto buyers treat it as a proxy; 2020-21 and 2024-26 waves | REGIME (two waves), EXIT LIQ risk named | N | 20-60 | 3 |
| R3-12 | **Special dividend >= 10% of price** announced (headline amount vs price), un-gapped | R | D | Income and dividend-capture buyers arrive before the ex-date | GAP (un-gapped), TOO WEAK | N | 20-50 | 2 |
| R3-13 | **New CEO buys stock in the first 90 days** (8-K Item 5.02 new CEO + their Form 4 P) | R | C | A newcomer with fresh information puts money in | TOO WEAK (own money alone earns ~usual) -> only new-CEO buys | E FTS + F4 | 30-80 | 3 |
| R3-14 | **Price target raised >= 50% in one note** on a small cap ("Raises PT from $a to $b") | R | H/D | A big target jump drags institutional estimates up over weeks | TEXTBOOK (revisions) -> only huge revisions on small caps | N | 100+ | 2 |
| R3-15 | **Initiation with >= 100% upside** to the target on a micro cap | R | H | A broker sees double; the buyers it brings arrive over weeks | EXIT LIQ (institutional), TEXTBOOK | N | 100+ | 3 |
| R3-16 | **Fails-to-deliver collapse after a spike** (FTD back under 0.05% of shares after >= 0.5%): buy-ins done | R | W | The forced buying is over and shorts that covered can't re-short easily | PRICE PROXY | SEC FTD | 50+ | 4 |
| R3-17 | **Two-year high in Wikipedia views AND an insider buy within 30 days** | R | C | Attention arrives where insiders already bought | EXIT LIQ (only with own money) | WP + F4 | 10-30 | 4 |
| R3-18 | **First 10-K risk factor naming a hot theme by a micro cap** (FTS 10-K, not 8-K: the slow venue) | R | D | Same as D4 but in the annual report, not a press 8-K | TWO-WAY (D4 died) -> quieter venue | E FTS | 50-150 | 3 |
| R3-19 | **LLM-extracted "first commercial sale / first order" in a 10-Q MD&A** of a micro cap (verbatim sentence) | R | D | A product reaches its first customer; told in a 10-Q, not a headline | GAP, EXIT LIQ | E + OpenCode Go | 30-80 | 4 |
| R3-20 | **Analyst coverage dropped by the last broker** (headline "Discontinues/Suspends Coverage") then an insider buy within 60 days | R | C | Orphaned stock, informed buyer, no analyst: maximum neglect + own money | EXIT LIQ, TOO WEAK | N + F4 | 10-30 | 4 |
