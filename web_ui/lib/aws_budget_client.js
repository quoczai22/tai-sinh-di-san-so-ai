const BUDGET_NAME = 'tai-sinh-di-san-so-ai-aws-5usd';

function parseBudgetSnapshot(result) {
    const budget = result?.Budget;
    const actual = budget?.CalculatedSpend?.ActualSpend;
    const limit = budget?.BudgetLimit;
    if (budget?.BudgetName !== BUDGET_NAME || actual?.Unit !== 'USD' || limit?.Unit !== 'USD') return null;
    if (typeof actual.Amount !== 'string' && typeof actual.Amount !== 'number') return null;
    if (typeof limit.Amount !== 'string' && typeof limit.Amount !== 'number') return null;
    if (String(actual.Amount).trim() === '' || String(limit.Amount).trim() === '') return null;
    const actualUsd = Number(actual.Amount);
    const limitUsd = Number(limit.Amount);
    if (!Number.isFinite(actualUsd) || actualUsd < 0 ||
        !Number.isFinite(limitUsd) || limitUsd <= 0) return null;
    return { actualUsd, limitUsd };
}

async function queryBudgetWithOidc({ accountId, roleArn }) {
    const [{ BudgetsClient, DescribeBudgetCommand }, { awsCredentialsProvider }] = await Promise.all([
        import('@aws-sdk/client-budgets'),
        import('@vercel/oidc-aws-credentials-provider'),
    ]);
    const client = new BudgetsClient({
        region: 'us-east-1',
        credentials: awsCredentialsProvider({ roleArn }),
    });
    try {
        return await client.send(new DescribeBudgetCommand({ AccountId: accountId, BudgetName: BUDGET_NAME }));
    } finally {
        client.destroy();
    }
}

async function readAwsBudget(query = queryBudgetWithOidc) {
    const roleArn = (process.env.AWS_BUDGET_ROLE_ARN || '').trim();
    const match = roleArn.match(/^arn:aws:iam::(\d{12}):role\/[A-Za-z0-9_+=,.@\/-]+$/);
    if (!match) return null;
    try {
        return parseBudgetSnapshot(await query({ accountId: match[1], roleArn }));
    } catch (_) {
        return null;
    }
}

module.exports = { readAwsBudget, parseBudgetSnapshot };
