// Runs InsightTrack's ORIGINAL correlation engine on benchmark inputs, for
// tests/test_parity.py. Reads JSON cases on stdin, writes gold answers on stdout.
//
// The citation derivation below is copied verbatim from
// searchVisibilityService.checkKeyword(), which is not exported on its own.
const root = process.env.INSIGHTTRACK_API;
const { detectChange, explain, serpDiff } = await import(`${root}/src/services/correlationService.js`);
const { domainMatches } = await import(`${root}/src/services/serpapi/normalize.js`);

const cited = (snap, domain) => (snap.ai_quotes || []).some((d) => domainMatches(d, domain));

function finding(domain, { keyword, before, after }) {
    const domainIsCited = cited(after, domain);
    const prev = { hasAiOverview: !!before.ai_answer, isCited: cited(before, domain) };
    const hasAiOverview = !!after.ai_answer;
    let citationChange = 'unknown';
    if (!prev.hasAiOverview && hasAiOverview) citationChange = 'new_overview';
    else if (prev.isCited && !domainIsCited) citationChange = 'lost';
    else if (!prev.isCited && domainIsCited) citationChange = 'gained';
    else citationChange = 'unchanged';
    const diff = serpDiff({
        previous: { organic: [], features: before.features },
        organic: [], features: after.features, domain,
        previousPosition: before.position, position: after.position,
    });
    return {
        keyword, position: after.position, previousPosition: before.position,
        positionChange: before.position != null && after.position != null ? before.position - after.position : null,
        citationChange, domainIsCited, hasAiOverview,
        featuresAdded: diff.featuresAdded, featuresRemoved: diff.featuresRemoved, overtakenBy: [],
        changeObservedAt: new Date().toISOString(),
    };
}

let input = '';
for await (const chunk of process.stdin) input += chunk;
const out = JSON.parse(input).map((c) => {
    const traffic = detectChange(c.weeks.map((views, i) => ({ weekStart: `w${i}`, views })), { excludePartial: false });
    const r = explain({ path: '/p', traffic, keywordFindings: c.keywords.map((k) => finding(c.domain, k)) });
    const causes = [...new Set((r.causes || []).map((x) => x.code))].sort();
    return traffic.significant
        ? { significant: true, direction: traffic.direction, causes }
        : { significant: false, direction: null, causes: [] };
});
process.stdout.write(JSON.stringify(out));
