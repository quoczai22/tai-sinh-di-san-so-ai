const assert = require('node:assert/strict');
const { readAwsBudget, parseBudgetSnapshot } = require('../../web_ui/lib/aws_budget_client');
const { formatCreditReport } = require('../../web_ui/api/bot_ops_commands');

(async () => {
    const sample = {
        Budget: {
            BudgetName: 'tai-sinh-di-san-so-ai-aws-5usd',
            CalculatedSpend: { ActualSpend: { Amount: '0.42', Unit: 'USD' } },
            BudgetLimit: { Amount: '5', Unit: 'USD' },
        },
    };
    assert.deepEqual(parseBudgetSnapshot(sample), { actualUsd: 0.42, limitUsd: 5 });
    assert.equal(parseBudgetSnapshot({ Budget: { ...sample.Budget, BudgetLimit: null } }), null);
    assert.equal(parseBudgetSnapshot({ Budget: { ...sample.Budget, CalculatedSpend: { ActualSpend: { Amount: null, Unit: 'USD' } } } }), null);

    process.env.AWS_BUDGET_ROLE_ARN = 'arn:aws:iam::879541989575:role/tai-sinh-di-san-so-ai-budget-read';
    const budget = await readAwsBudget(async ({ accountId, roleArn }) => {
        assert.equal(accountId, '879541989575');
        assert.match(roleArn, /budget-read$/);
        return sample;
    });
    assert.deepEqual(budget, { actualUsd: 0.42, limitUsd: 5 });
    assert.match(formatCreditReport(budget), /\$0\.42 \/ \$5\.00/);
    assert.match(formatCreditReport(budget), /cập nhật trễ/);
    assert.match(formatCreditReport(budget), /https:\/\/modal\.com\/settings/);
    assert.doesNotMatch(formatCreditReport(budget), /credit còn lại|100% miễn phí/);

    assert.equal(await readAwsBudget(async () => { throw new Error('AccessDenied'); }), null);
    assert.match(formatCreditReport(null), /Chưa xác minh được mức chi AWS Budget/);
    process.env.AWS_BUDGET_ROLE_ARN = '';
    assert.equal(await readAwsBudget(() => { throw new Error('must not call'); }), null);
    console.log('Zalo AWS Budget: validated data, no guessed balance, safe fallback passed');
})().catch((error) => { console.error(error); process.exitCode = 1; });
